"""Refresh the Ashby company list from Common Crawl (JOB-F06). Meant to run in the background.

Common Crawl's index is slow and often overloaded, so discovery is kept out of the
search path: this script saves the list under the ignored .cache/jobs/. The daily
crawl (scripts/crawl_jobs_daily.py) also calls the same refresh when the list is
older than 30 days. Run it by hand to retry failed crawls sooner, for example:

  nohup python scripts/refresh_job_companies.py > .cache/jobs/refresh.log 2>&1 &

Incremental: crawls already read are skipped, new companies are merged into the
saved list, and a crawl that failed is retried next time. --full starts over.
Only Common Crawl's public index is contacted; no resume or search data is involved.
"""
import argparse
import sys
import time


def main():
    from crescendo_agent.common_crawl import MAX_CRAWLS
    from crescendo_agent.job_cache import JobCache, refresh_company_list

    import httpx

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--crawls", type=int, default=6,
                        help=f"Consider the latest N monthly crawls (1-{MAX_CRAWLS}; default 6).")
    parser.add_argument("--budget-minutes", type=float, default=20,
                        help="Stop starting new crawls after this long (default 20); found companies are kept.")
    parser.add_argument("--full", action="store_true",
                        help="Ignore the saved list and crawls already read; rebuild from scratch.")
    args = parser.parse_args()

    started = time.monotonic()
    with httpx.Client(headers={"User-Agent": "AgentCrescendo-job-sources/0.1"}) as client:
        summary = refresh_company_list(client, JobCache(), crawls=args.crawls, full=args.full,
                                       budget_seconds=args.budget_minutes * 60,
                                       progress=lambda line: print("  " + line, flush=True))
    for error in summary["errors"]:
        print(f"  {error}", file=sys.stderr)
    print(f"Saved list had {summary['previous']} companies from {len(summary['read_before'])} crawls; "
          f"read {len(summary['read'])} new crawls in {time.monotonic() - started:.0f}s; "
          f"now {len(summary['boards'])} (+{summary['added']}).")
    return 1 if summary["errors"] and not summary["boards"] else 0


if __name__ == "__main__":
    sys.exit(main())
