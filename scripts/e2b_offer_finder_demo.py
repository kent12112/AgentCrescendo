"""Offer finder (JOB-F01): the model browses a company job board and picks matching postings.

The host opens a Greenhouse or Lever board in public-web mode. The model may only
scroll, follow visible links by ID, and finish; it cannot type or open URLs. It
finishes with link IDs, never titles or URLs: the host looks each ID up in the
browser and accepts it only when it links to a posting on the same board. Titles
and URLs in the result therefore come from the page, and the model's "why" is
labeled untrusted. Uses E2B and Groq (metered).

Example:
  python scripts/e2b_offer_finder_demo.py --board https://jobs.lever.co/palantir \\
      --looking-for "software engineer, New York" --watch --save-screenshots
"""
import argparse
from contextlib import nullcontext
import json
import os
from pathlib import Path
import time
from uuid import uuid4
import webbrowser

DEFAULT_BOARD = "https://job-boards.greenhouse.io/anthropic"
DEFAULT_LOOKING_FOR = "software engineering role"


def grade(status, offers):
    """Return (passed, reason). Offers were already checked against the browser by the validator."""
    if status != "finished":
        return False, f"FAIL: the run stopped with status {status!r} before an accepted answer."
    if not offers:
        return False, "NO MATCH: the model honestly reported no matching posting on the screens it saw."
    return True, (f"PASS: {len(offers)} offer(s), each a posting link the browser showed on this "
                  "board; titles and URLs come from the page, not the model.")


def main():
    from crescendo_agent.e2b_desktop import open_e2b_desktop
    from crescendo_agent.local_env import load_local_env
    from crescendo_agent.offers import (MAX_OFFERS, board_from_url, is_generic_label, offer_goal,
                                        offer_validator, posting_company)
    from crescendo_agent.vision import GroqVision
    from crescendo_agent.vision_loop import run_vision_agent
    from crescendo_security.policy import TaskGrant

    load_local_env()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--board", default=DEFAULT_BOARD, help="Greenhouse or Lever company board URL.")
    parser.add_argument("--looking-for", default=DEFAULT_LOOKING_FOR,
                        help="What the user wants, one line of at most 200 characters.")
    parser.add_argument("--max-offers", type=int, default=3, choices=range(1, MAX_OFFERS + 1))
    parser.add_argument("--model", default=os.environ.get("GROQ_VISION_MODEL", "qwen/qwen3.8-27b"))
    parser.add_argument("--max-steps", type=int, default=8)
    parser.add_argument("--image-width", type=int, default=768)
    parser.add_argument("--request-timeout", type=float, default=45)
    parser.add_argument("--watch", action="store_true", help="Open the live viewer before starting.")
    parser.add_argument("--save-screenshots", action="store_true",
                        help="Save model-input PNGs, evidence.png, and offers.json under ignored .demo-artifacts/.")
    args = parser.parse_args()
    board = board_from_url(args.board)
    if board is None:
        raise SystemExit("--board must be an https Greenhouse or Lever company board URL, "
                         "e.g. https://jobs.lever.co/<company>.")
    goal = offer_goal(board, args.looking_for, args.max_offers)  # validates looking_for
    for name in ("E2B_API_KEY", "GROQ_API_KEY"):
        if not os.environ.get(name):
            raise SystemExit(f"Set {name} in this terminal first.")

    tools = {"screenshot", "scroll", "click", "read_visible_links", "finish"}
    if args.watch:
        tools.add("view_desktop")
    grant = TaskGrant("offer-finder-demo", frozenset(tools), frozenset(), public_web=True)
    model = GroqVision(args.model, allow_click=True, click_mode="links", request_timeout=args.request_timeout)
    directory, record = None, None
    if args.save_screenshots:
        directory = Path(".demo-artifacts") / ("offers-" + uuid4().hex)
        directory.mkdir(parents=True)
        print("Diagnostic screenshots:", directory.resolve(), flush=True)

        def record(step, screenshot):
            (directory / f"step-{step:02d}.png").write_bytes(screenshot.png)

    accepted = []
    with open_e2b_desktop(grant, lifetime_seconds=300) as desktop:
        desktop.open_start_page(board.url)
        # Startup check before any model call: the first screen must show a posting link.
        first = desktop.visible_links()
        records = desktop.link_records([link["id"] for link in first])
        if not any(posting_company(r["href"]) == (board.platform, board.company)
                   and not is_generic_label(r["label"]) for r in records.values()):
            raise SystemExit(f"SOURCE UNAVAILABLE: {board.url} showed no posting links "
                             f"(final URL {desktop.page.url}). No model calls were made.")
        with desktop.live_view() if args.watch else nullcontext() as viewer:
            if args.watch:
                from crescendo_agent.live_view import wait_for_viewer
                print("Local live viewer:", viewer.url, flush=True)
                webbrowser.open(viewer.url)
                wait_for_viewer(viewer)
            started = time.monotonic()
            result = run_vision_agent(
                goal, grant, desktop, model, max_steps=args.max_steps, deadline_seconds=120,
                max_image_width=args.image_width, on_screenshot=record, link_grounding=True,
                finish_validator=offer_validator(desktop, board, accepted, max_offers=args.max_offers),
                max_rate_limit_wait=60,
                on_rate_limit=lambda step, wait: print(
                    f"Step {step}: provider throttled; one retry in {wait:.1f}s.", flush=True))
            seconds = round(time.monotonic() - started, 1)
            if directory is not None and accepted:
                # Full-resolution screen at finish: screen_point values are in these pixels.
                (directory / "evidence.png").write_bytes(desktop.capture_screen().png)
            final_url, visited = desktop.page.url, list(desktop.visited)
            blocked = list(desktop.blocked_requests)
    steps = [json.loads(e.text) for e in result.transcript if e.kind == "action"]
    passed, reason = grade(result.status, accepted if result.status == "finished" else [])
    print("Model:", model.model, "| status:", result.status, "| agent time:", seconds, "s")
    print("Board:", board.url, "| looking for:", repr(args.looking_for))
    print("Model decisions (reasons are the model's own account):")
    for number, action in enumerate(steps, start=1):
        print(f"  {number}. {action['tool']}({action['args']}) reason: {action.get('reason')!r}")
    print("Denied:", [d.reason for _, d in result.denied])
    print("Visited (recorded by the adapter):", visited, "| final:", final_url)
    print("Blocked browser requests:", len(blocked))
    if result.status == "finished":
        for number, offer in enumerate(accepted, start=1):
            print(f"\n  Offer {number}: {offer['title']}\n    {offer['url']}\n"
                  f"    why (model, untrusted): {offer['why_untrusted']}")
    if directory is not None:
        (directory / "offers.json").write_text(json.dumps({
            "board": board.url, "looking_for": args.looking_for, "model": model.model,
            "status": result.status, "agent_seconds": seconds, "result": reason,
            "offers": accepted if result.status == "finished" else [],
            "evidence": "evidence.png" if accepted else None,
            "visited": visited, "final_url": final_url, "blocked_requests": len(blocked),
            "denied": [d.reason for _, d in result.denied],
            "trace": [{"kind": e.kind, "text": e.text} for e in result.transcript]}, indent=2) + "\n")
    print("\n" + reason)
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
