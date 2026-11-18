"""Daily Ashby crawl into Postgres (JOB-F07). Run once a day by launchd.

1. Refresh the Common Crawl company list incrementally (only crawls not yet read,
   bounded by --budget-minutes; usually one quick request).
2. Fetch every saved Ashby company's live postings from Ashby's public API.
3. Store postings published in the last 30 days; close ones that disappeared from a
   board that answered; delete ones older than 30 days (crescendo_api.job_store).
4. Record the run in job_crawl_runs (status, counts, error).

Install the schedule with scripts/install_jobs_schedule.py. Logs go to stdout
(launchd sends them to .cache/jobs/daily.log). Only Common Crawl's index and Ashby's
public API are contacted; no resume or search data is involved.
"""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parent.parent


def log(message: str) -> None:
    print(f"{datetime.now().astimezone():%Y-%m-%d %H:%M:%S} {message}", flush=True)


def wait_for_database(engine, *, start_db: bool, attempts: int = 12, wait: float = 10.0) -> None:
    """Connect, starting the Compose Postgres service once if it is down. Raises SystemExit."""
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError

    started = False
    for attempt in range(attempts):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return
        except OperationalError:
            if start_db and not started:
                started = True
                log("Postgres is not reachable; running `docker compose up -d db`.")
                try:
                    subprocess.run(["docker", "compose", "up", "-d", "db"], cwd=REPO, timeout=120,
                                   check=False, capture_output=True)
                except (OSError, subprocess.TimeoutExpired) as error:
                    log(f"Could not start Postgres: {type(error).__name__}.")
            if attempt < attempts - 1:
                time.sleep(wait)
    raise SystemExit("Postgres is not reachable (is Docker running?). Nothing was crawled.")


def main():
    from crescendo_agent.job_cache import JobCache, refresh_company_list
    from crescendo_agent.job_sources import fetch_boards
    from crescendo_api.job_store import WINDOW_DAYS, JobDbSettings, sync_board_results
    from crescendo_api.models import JobCrawlRun

    import httpx
    from sqlalchemy import create_engine, inspect
    from sqlalchemy.orm import Session

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--budget-minutes", type=float, default=10,
                        help="Time limit for reading new Common Crawl crawls (default 10).")
    parser.add_argument("--window-days", type=int, default=WINDOW_DAYS,
                        help=f"Keep postings published within this many days (default {WINDOW_DAYS}).")
    parser.add_argument("--retry-failed-days", type=float, default=7,
                        help="Retry a Common Crawl crawl that failed only after this many days (default 7).")
    parser.add_argument("--workers", type=int, default=8, help="Parallel board requests (1-16; default 8).")
    parser.add_argument("--no-start-db", action="store_true",
                        help="Do not run `docker compose up -d db` when the database is down.")
    args = parser.parse_args()

    engine = create_engine(JobDbSettings().database_url, pool_pre_ping=True)
    wait_for_database(engine, start_db=not args.no_start_db)
    if "job_postings" not in inspect(engine).get_table_names():
        raise SystemExit("The job tables do not exist yet: run `alembic upgrade head` from the repository root.")

    started = time.monotonic()
    # expire_on_commit=False: the run row stays readable after the session closes (first live run
    # crashed on the final log line with DetachedInstanceError after committing successfully).
    with Session(engine, expire_on_commit=False) as session:
        run = JobCrawlRun(started_at=datetime.now(timezone.utc), status="running", companies=0, boards_failed=0,
                          postings_seen=0, inserted=0, updated=0, closed=0, deleted=0)
        session.add(run)
        session.commit()
        log(f"Crawl run {run.id} started.")
        try:
            with httpx.Client(headers={"User-Agent": "AgentCrescendo-job-sources/0.1"}) as client:
                summary = refresh_company_list(client, JobCache(), budget_seconds=args.budget_minutes * 60,
                                               retry_failed_after_days=args.retry_failed_days,
                                               progress=lambda line: log("  Common Crawl " + line))
                if summary["deferred"]:
                    log(f"  Common Crawl: not retrying {len(summary['deferred'])} crawls that failed in the "
                        f"last {args.retry_failed_days:g} days ({', '.join(summary['deferred'])}).")
                boards = summary["boards"]
                if not boards:
                    raise RuntimeError("No saved Ashby company list and Common Crawl could not be read.")
                log(f"Fetching {len(boards)} Ashby boards (+{summary['added']} new companies)...")
                results = fetch_boards(boards, client, workers=args.workers)
            stats = sync_board_results(session, results, now=datetime.now(timezone.utc),
                                       window_days=args.window_days)
            for name, value in stats.as_dict().items():
                setattr(run, name, value)
            run.status, run.finished_at = "ok", datetime.now(timezone.utc)
            session.commit()
        except BaseException as error:  # also record Ctrl-C / launchd stops
            session.rollback()
            run.status, run.finished_at = "failed", datetime.now(timezone.utc)
            run.error = f"{type(error).__name__}: {error}"[:2000]
            session.commit()
            log(f"Crawl run {run.id} failed: {run.error}")
            raise SystemExit(1) from None
    log(f"Crawl run {run.id} ok in {time.monotonic() - started:.0f}s: {stats.companies} companies "
        f"({stats.boards_failed} failed), {stats.postings_seen} postings in the last {args.window_days} days; "
        f"+{stats.inserted} new, {stats.updated} updated, {stats.closed} closed, {stats.deleted} deleted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
