"""Find and rank jobs for a resume (JOB-F02): resume + search words -> ranked postings with links.

1. Read the resume locally and list the skills found in it (from job_match.SKILLS).
2. Ashby postings come from Postgres, where scripts/crawl_jobs_daily.py (run daily by
   launchd) stores the last 30 days from every Common Crawl-discovered company.
   --live fetches those boards instead (each cached ~24 hours under .cache/jobs/).
3. Optional extra boards (--boards-file, --hn-months) are fetched live.
4. Keep postings published in the last 30 days (--max-age-days) whose title matches
   the search; score each against the resume.

The resume never leaves this machine: only the HN API and ATS listing APIs are
called, and they receive no resume text or search words. No E2B, no model, no keys.

Example:
  python scripts/find_jobs.py --resume ~/resume.pdf --search "applied ai engineer" \\
      --country "united states" --no-senior --json
"""
import argparse
import json
from pathlib import Path
import sys
import time
from uuid import uuid4


def main():
    from crescendo_agent.company_discovery import hn_hiring_boards, read_boards_file
    from crescendo_agent.job_cache import JobCache, fetch_boards_cached
    from crescendo_agent.job_match import (age_days, company_label, posting_countries, rank,
                                           resume_skills as skills_of)
    from crescendo_agent.resume import ResumeError, read_resume_text

    import httpx

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--resume", required=True, help="Resume as .pdf, .txt, or .md.")
    parser.add_argument("--search", required=True, help='What you are looking for, e.g. "applied ai engineer".')
    parser.add_argument("--boards-file", help="Extra boards, one source:company per line.")
    parser.add_argument("--hn-months", type=int, default=0,
                        help="Recent HN 'Who is hiring?' threads to read (default 0: off). Adds Greenhouse/Lever boards the Common Crawl list lacks.")
    parser.add_argument("--live", action="store_true",
                        help="Fetch the saved Ashby company list live (file cache) instead of reading the "
                             "postings the daily crawl stored in Postgres.")
    parser.add_argument("--no-crawled", action="store_true",
                        help="Skip the Common Crawl Ashby companies (database or saved list).")
    parser.add_argument("--cache-hours", type=float, default=24,
                        help="Reuse a board's cached postings for this long (default 24; 0 always refetches).")
    parser.add_argument("--country",
                        help='Drop postings known to be in another country, e.g. "united states". Remote '
                             'roles abroad are dropped too; postings naming no country are kept and marked.')
    parser.add_argument("--location", action="append",
                        help='Keep postings whose location contains this, e.g. "new york". Repeat for '
                             'any-of; "remote" matches remote postings.')
    parser.add_argument("--remote", action="store_true", help="Keep only remote postings.")
    parser.add_argument("--max-years", type=int,
                        help="Drop postings that ask for more years of experience than this.")
    parser.add_argument("--no-senior", action="store_true",
                        help="Drop Senior / Staff / Lead / Principal / Manager / Director titles.")
    parser.add_argument("--max-age-days", type=int, default=30,
                        help="Drop postings published longer ago than this (default 30; 0 keeps all).")
    parser.add_argument("--min-title-match", type=float, default=0.6,
                        help="Share of search words the title must contain (default 0.6).")
    parser.add_argument("--top", type=int, default=20, help="Results to print (default 20).")
    parser.add_argument("--json", action="store_true",
                        help="Save all ranked results to ignored .demo-artifacts/jobs-ranked-<id>.json.")
    args = parser.parse_args()

    try:
        resume_text = read_resume_text(Path(args.resume).expanduser())
    except ResumeError as error:
        raise SystemExit(f"Resume: {error}") from None
    resume_skills = skills_of(resume_text)
    print(f"Resume skills (named or implied, {len(resume_skills)}): {', '.join(sorted(resume_skills)) or 'none'}")
    if not resume_skills:
        print("  No known skills were found, so every skill score will be 0.")

    started = time.monotonic()
    cache = JobCache()
    postings, stored_slugs = [], set()
    if not args.live and not args.no_crawled:
        postings, stored_slugs = postings_from_db(args.max_age_days)
    with httpx.Client(headers={"User-Agent": "AgentCrescendo-job-sources/0.1"}) as client:
        boards = []
        if args.boards_file:
            try:
                boards = read_boards_file(args.boards_file)
            except (OSError, ValueError) as error:
                raise SystemExit(f"Boards file: {error}") from None
        if args.live and not args.no_crawled:
            known = set(boards)
            boards += [b for b in saved_ashby_boards(cache) if b not in known]
        if args.hn_months:
            hn_boards, threads, error = hn_hiring_boards(client, args.hn_months)
            if error:
                print(f"HN: {error}", file=sys.stderr)
            else:
                print(f"HN 'Who is hiring?' ({', '.join(threads)}): {len(hn_boards)} company boards")
            boards += [b for b in hn_boards if b not in boards]
        # Ashby boards the daily crawl already stored are read from the database, not refetched.
        boards = [b for b in boards if not (b.source == "ashby" and b.slug.lower() in stored_slugs)]
        results = []
        if boards:
            print(f"Fetching {len(boards)} boards live...", flush=True)
            results, hits = fetch_boards_cached(boards, cache, client, max_age_hours=args.cache_hours)
            if hits:
                print(f"  {hits} from the local cache (< {args.cache_hours:g} h old), {len(boards) - hits} fetched.")
        elif not postings:
            raise SystemExit("Nothing to search: run scripts/crawl_jobs_daily.py (or install its schedule), "
                             "or use --live, --boards-file, or --hn-months.")
    live_postings = [p for r in results for p in r.postings]
    if args.max_age_days:
        # Postings without a date are kept; their age is shown as unknown.
        live_postings = [p for p in live_postings if (age_days(p.published_at) or 0) <= args.max_age_days]
    postings += live_postings
    failed = [r for r in results if r.error]
    if results:
        print(f"{len(live_postings)} postings from {len(results) - len(failed)} live boards "
              f"({len(failed)} unavailable).")
    print(f"{len(postings)} postings to rank ({time.monotonic() - started:.0f}s).")

    try:
        matches = rank(postings, resume_skills, args.search, min_title_match=args.min_title_match,
                       location=args.location, remote=args.remote, max_years=args.max_years,
                       no_senior=args.no_senior, country=args.country)
    except ValueError as error:
        raise SystemExit(str(error)) from None
    print(f"{len(matches)} postings match {args.search!r}"
          + (f" in {args.country}" if args.country else "")
          + (f" in {' or '.join(args.location)}" if args.location else "") + (" (remote)" if args.remote else "")
          + (f", asking at most {args.max_years} yrs" if args.max_years is not None else "")
          + (", early-career titles" if args.no_senior else "")
          + ". Score = 30% title match + 70% share of the job's skills on your resume (smoothed).\n")
    for number, match in enumerate(matches[:args.top], start=1):
        p = match.posting
        age = age_days(p.published_at)
        where = "; ".join(p.locations[:3]) + (f" (+{len(p.locations) - 3} more)" if len(p.locations) > 3 else "")
        unknown_country = "country not stated" if args.country and not posting_countries(p) else None
        facts = [x for x in (where or None, unknown_country, p.workplace, p.compensation,
                             f"asks {match.years_asked}+ yrs" if match.years_asked else None,
                             f"posted {age}d ago" if age is not None else None) if x]
        print(f"{number:>2}. [{match.score:>3}] {p.title} — {company_label(p)}")
        print(f"      {' | '.join(facts)}")
        print(f"      have: {', '.join(match.matched_skills) or '-'}")
        print(f"      gaps: {', '.join(match.missing_skills) or '-'}")
        print(f"      {p.url}")
    if args.json:
        directory = Path(".demo-artifacts")
        directory.mkdir(exist_ok=True)
        path = directory / f"jobs-ranked-{uuid4().hex}.json"
        path.write_text(json.dumps({
            "search": args.search, "country": args.country, "location": args.location, "remote": args.remote,
            "max_years": args.max_years, "no_senior": args.no_senior,
            "resume_skills": sorted(resume_skills), "database_postings": len(postings) - len(live_postings),
            "live_boards": len(boards),
            "unavailable_boards": [f"{r.board.source}:{r.board.slug}: {r.error}" for r in failed],
            "results": [m.as_dict() for m in matches]}, indent=2, ensure_ascii=False) + "\n")
        print("\nSaved:", path.resolve())


def postings_from_db(max_age_days):
    """Open Ashby postings the daily crawl stored, as Posting objects, plus the stored company slugs."""
    from datetime import timezone

    from crescendo_agent.job_sources import Posting
    from crescendo_api.job_store import JobDbSettings, last_crawl, open_postings
    from sqlalchemy import create_engine, select
    from sqlalchemy.exc import OperationalError, ProgrammingError
    from sqlalchemy.orm import Session

    from crescendo_api.models import JobCompany

    def iso(moment):
        if moment is None:
            return None
        moment = moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)
        return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    engine = create_engine(JobDbSettings().database_url, pool_pre_ping=True)
    try:
        with Session(engine) as session:
            run = last_crawl(session)
            rows = open_postings(session, window_days=max_age_days or 3650)
            # Companies the crawl checked (live or gone); boards that only errored are left to --live.
            checked = dict(session.execute(
                select(JobCompany.slug, JobCompany.status).where(JobCompany.source == "ashby",
                                                                 JobCompany.status != "error")).all())
            slugs = set(checked)
    except (OperationalError, ProgrammingError) as error:
        raise SystemExit("Postgres is not reachable or not migrated (`docker compose up -d db`, then "
                         f"`alembic upgrade head`), or use --live. ({type(error).__name__})") from None
    finally:
        engine.dispose()
    when = f"last crawl {iso(run.finished_at or run.started_at)[:16].replace('T', ' ')} UTC, {run.status}" \
        if run else "no crawl recorded yet"
    live = sum(1 for status in checked.values() if status == "live")
    print(f"Database: {len(rows)} open Ashby postings from {live} live companies ({when}).")
    postings = [Posting(source=r.source, company=r.company_slug, posting_id=r.posting_id, title=r.title, url=r.url,
                        locations=tuple(r.locations or ()), workplace=r.workplace, department=r.department,
                        employment_type=r.employment_type, published_at=iso(r.published_at),
                        compensation=r.compensation, description=r.description or "",
                        company_name=r.company_name, countries=tuple(r.countries or ())) for r in rows]
    return postings, slugs


REFRESH_HINT ="run scripts/refresh_job_companies.py (it can run in the background)"


def saved_ashby_boards(cache, stale_days: float = 45):
    """Ashby boards from the saved Common Crawl list; never crawls (that is the refresh script's job)."""
    import time
    from datetime import datetime

    saved = cache.load_companies("ashby", max_age_days=None)
    if not saved:
        print(f"Common Crawl: no saved company list yet; {REFRESH_HINT}. Continuing without it.", file=sys.stderr)
        return []
    boards, saved_at, details = saved
    age = (time.time() - saved_at) / 86400
    print(f"Common Crawl: {len(boards)} Ashby companies (saved {datetime.fromtimestamp(saved_at):%Y-%m-%d}, "
          f"{len(details.get('indexes_read') or [])} crawls)")
    if age > stale_days:
        print(f"  The list is {age:.0f} days old; {REFRESH_HINT}.", file=sys.stderr)
    return boards


if __name__ == "__main__":
    main()
