"""Fetch job postings from ATS public APIs (JOB-F00): Greenhouse, Lever, Ashby.

No E2B, no model, no keys: public listing APIs only. Boards are 'source:company'.
Postings are normalized (see crescendo_agent.job_sources.Posting); posting URLs
are rebuilt from the board name and a checked ID.

Examples:
  python scripts/fetch_jobs.py greenhouse:anthropic lever:palantir ashby:openai
  python scripts/fetch_jobs.py --boards-file my_companies.txt --title-contains engineer --json
"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
from uuid import uuid4


def read_boards(args):
    from crescendo_agent.job_sources import CompanyBoard

    specs = list(args.boards)
    if args.boards_file:
        for line in Path(args.boards_file).read_text().splitlines():
            line = line.split("#", 1)[0].strip()
            if line:
                specs.append(line)
    if not specs:
        raise SystemExit("Name at least one board, e.g. lever:palantir, or use --boards-file.")
    try:
        boards = [CompanyBoard.parse(spec) for spec in specs]
    except ValueError as error:
        raise SystemExit(str(error)) from None
    return list(dict.fromkeys(boards))  # drop duplicates, keep order


def main():
    from crescendo_agent.job_sources import fetch_boards

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("boards", nargs="*", help="Boards as source:company, e.g. ashby:openai.")
    parser.add_argument("--boards-file", help="Text file with one source:company per line; # comments.")
    parser.add_argument("--title-contains", help="Show only postings whose title contains this text.")
    parser.add_argument("--show", type=int, default=5, help="Postings to print per board (default 5).")
    parser.add_argument("--json", action="store_true",
                        help="Write all normalized postings to ignored .demo-artifacts/jobs-<id>.json.")
    args = parser.parse_args()
    boards = read_boards(args)
    results = fetch_boards(boards)
    needle = (args.title_contains or "").lower()
    total = 0
    for result in results:
        name = f"{result.board.source}:{result.board.slug}"
        if result.error:
            print(f"\n{name}: ERROR {result.error}")
            continue
        shown = [p for p in result.postings if needle in p.title.lower()]
        total += len(shown)
        print(f"\n{name}: {len(result.postings)} postings ({result.skipped} skipped: unlisted or malformed)"
              + (f", {len(shown)} with {args.title_contains!r} in the title" if needle else ""))
        for posting in shown[:args.show]:
            where = "; ".join(posting.locations[:2]) or "location not stated"
            extra = " | ".join(x for x in (posting.workplace, posting.compensation) if x)
            print(f"  - {posting.title} — {where}" + (f" ({extra})" if extra else ""))
            print(f"    {posting.url}")
    print(f"\n{total} postings across {sum(1 for r in results if not r.error)}/{len(results)} boards.")
    if args.json:
        directory = Path(".demo-artifacts")
        directory.mkdir(exist_ok=True)
        path = directory / f"jobs-{uuid4().hex}.json"
        path.write_text(json.dumps([{
            "board": f"{r.board.source}:{r.board.slug}", "error": r.error, "skipped": r.skipped,
            "postings": [asdict(p) for p in r.postings if needle in p.title.lower()]} for r in results],
            indent=2, ensure_ascii=False) + "\n")
        print("Saved:", path.resolve())
    if all(r.error for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
