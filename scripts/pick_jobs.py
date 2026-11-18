"""Pick up to 3 ranked jobs for research and cover letters (JOB-F03).

    python scripts/find_jobs.py --resume resume.pdf --search "applied ai engineer" --json
    python scripts/pick_jobs.py                 # newest ranked list, interactive
    python scripts/pick_jobs.py --pick "1 4"    # no prompt

Reads a ``find_jobs.py --json`` file (the newest one under .demo-artifacts by default),
shows the top rows, and saves the choice to .demo-artifacts/jobs-picked-<id>.json for
the next steps. No network, no model calls. See decision 0009.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from uuid import uuid4

from crescendo_agent.job_picker import (MAX_PICKS, PickError, candidates, format_row,
                                        parse_choice, selection)

ARTIFACTS = Path(".demo-artifacts")
MAX_ATTEMPTS = 3


def newest_ranked(directory: Path = ARTIFACTS) -> Path | None:
    files = sorted(directory.glob("jobs-ranked-*.json"), key=lambda path: path.stat().st_mtime)
    return files[-1] if files else None


def main(argv=None, stdin=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--ranked", help="A find_jobs.py --json file (default: the newest one).")
    parser.add_argument("--show", type=int, default=10, help="Rows to show (default 10, at most 50).")
    parser.add_argument("--pick", help='Your choice without a prompt, e.g. "1 4 7".')
    args = parser.parse_args(argv)
    if not 1 <= args.show <= 50:
        parser.error("--show must be 1-50.")
    stdin = sys.stdin if stdin is None else stdin

    path = Path(args.ranked).expanduser() if args.ranked else newest_ranked()
    if path is None:
        print("No ranked list found. Run scripts/find_jobs.py ... --json first.", file=sys.stderr)
        return 2
    try:
        ranked = json.loads(path.read_text())
        rows = candidates(ranked)
    except (OSError, json.JSONDecodeError, PickError) as error:
        print(f"Could not read {path}: {error}", file=sys.stderr)
        return 2
    if not rows:
        print(f"{path.name} has no ranked jobs.", file=sys.stderr)
        return 2

    shown = rows[:args.show]
    print(f"Ranked list: {path.name} ({len(rows)} jobs). Top {len(shown)}:\n")
    for row in shown:
        print(format_row(row))
    print()

    attempts = [args.pick] if args.pick is not None else None
    picked = None
    for attempt in range(MAX_ATTEMPTS):
        if attempts is not None:
            text = attempts[0]
        else:
            print(f"Pick up to {MAX_PICKS} by number (e.g. 1 4 7), or press Enter to cancel: ",
                  end="", flush=True)
            text = stdin.readline()
            if not text:  # End of input: treat as cancel.
                text = ""
        try:
            picked = parse_choice(text, shown)
            break
        except PickError as error:
            print(error, file=sys.stderr)
            if attempts is not None:
                return 2
    if picked is None:
        print("Too many invalid attempts; nothing saved.", file=sys.stderr)
        return 2
    if not picked:
        print("Nothing picked; nothing saved.")
        return 1

    ARTIFACTS.mkdir(exist_ok=True)
    out = ARTIFACTS / f"jobs-picked-{uuid4().hex[:12]}.json"
    picked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out.write_text(json.dumps(selection(ranked, path.name, picked, picked_at),
                              indent=2, ensure_ascii=False) + "\n")
    print(f"\nPicked {len(picked)}:")
    for row in picked:
        print(f"  {row.rank}. {row.title} — {row.company}\n     {row.ref.url}")
    print("Saved:", out.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
