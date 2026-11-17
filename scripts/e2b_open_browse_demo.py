"""Open browsing (plan W1X-F03): search Wikipedia by typing, then open a named site by URL.

The host opens Wikipedia's main page. The model has no host allowlist. It must
type "Boston Common" into Wikipedia's search box and submit it (type_text), which
opens the article, then open https://www.boston.gov/ itself (navigate) and
finish with that site's domain. The browser, not the model, records where the
tab went. Private and internal destinations stay blocked by the request filter
and E2B's firewall. Uses E2B and Groq (metered).
"""
import argparse
from contextlib import nullcontext
import json
import os
from pathlib import Path
import time
from urllib.parse import unquote, urlsplit
from uuid import uuid4
import webbrowser

START_URL = "https://en.wikipedia.org/wiki/Main_Page"
ARTICLE = "/wiki/Boston_Common"
TARGET_HOST = "boston.gov"
GOAL = ("You are viewing Wikipedia's main page in Chrome. First, use Wikipedia's search box to search "
        "for Boston Common (type the words and submit). After its article has opened, go to "
        "https://www.boston.gov/ directly. When that site has opened, finish with only the site's "
        "domain name as shown in the address bar.")


def on_target(url):
    """True when url is on boston.gov itself or one of its subdomains."""
    host = urlsplit(url or "").hostname or ""
    return host == TARGET_HOST or host.endswith("." + TARGET_HOST)


def on_article(url):
    """True when url is the English Wikipedia article for Boston Common."""
    parts = urlsplit(url or "")
    return parts.hostname == "en.wikipedia.org" and unquote(parts.path) == ARTICLE


def grade(answer, final_url, visited, steps):
    """Return (passed, reason) from what the browser did, not what the model said.

    `steps` are the loop's action records ({"tool", "args"}) in order.
    """
    typed = [i for i, s in enumerate(steps) if s["tool"] == "type_text" and s["args"].get("submit") is True]
    navigated = [i for i, s in enumerate(steps) if s["tool"] == "navigate"]
    if not typed:
        return False, "FAIL: the model never typed and submitted a search."
    if not navigated:
        return False, "FAIL: the model never opened a URL itself."
    article = [i for i, url in enumerate(visited) if on_article(url)]
    site = [i for i, url in enumerate(visited) if on_target(url)]
    if not article:
        return False, f"FAIL: the search never opened {ARTICLE} (visited {visited})."
    if not site or not on_target(final_url) or site[-1] < article[0]:
        return False, f"FAIL: the tab did not end on {TARGET_HOST} after the article (visited {visited})."
    if answer is None or TARGET_HOST not in answer.lower():
        return False, f"FAIL: the answer does not name {TARGET_HOST}."
    return True, (f"PASS: the model searched Wikipedia by typing, then opened {TARGET_HOST} by URL "
                  "with no host allowlist, and named the site.")


def main():
    from crescendo_agent.e2b_desktop import open_e2b_desktop
    from crescendo_agent.local_env import load_local_env
    from crescendo_agent.vision import GroqVision
    from crescendo_agent.vision_loop import run_vision_agent
    from crescendo_security.policy import TaskGrant

    load_local_env()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", default=os.environ.get("GROQ_VISION_MODEL", "qwen/qwen3.8-27b"))
    parser.add_argument("--max-steps", type=int, default=8)
    parser.add_argument("--image-width", type=int, default=768)
    parser.add_argument("--request-timeout", type=float, default=45)
    parser.add_argument("--watch", action="store_true", help="Open the live viewer before starting.")
    parser.add_argument("--save-screenshots", action="store_true",
                        help="Save model-input PNGs and result.json under ignored .demo-artifacts/.")
    args = parser.parse_args()
    for name in ("E2B_API_KEY", "GROQ_API_KEY"):
        if not os.environ.get(name):
            raise SystemExit(f"Set {name} in this terminal first.")
    tools = {"screenshot", "scroll", "click", "read_visible_links", "type_text", "navigate", "finish"}
    if args.watch:
        tools.add("view_desktop")
    grant = TaskGrant("open-browse-demo", frozenset(tools), frozenset(), public_web=True)
    model = GroqVision(args.model, allow_click=True, click_mode="links", allow_typing=True,
                       allow_navigate=True, request_timeout=args.request_timeout)
    directory, record = None, None
    if args.save_screenshots:
        directory = Path(".demo-artifacts") / ("open-" + uuid4().hex)
        directory.mkdir(parents=True)
        print("Diagnostic screenshots:", directory.resolve(), flush=True)

        def record(step, screenshot):
            (directory / f"step-{step:02d}.png").write_bytes(screenshot.png)

    with open_e2b_desktop(grant, lifetime_seconds=300) as desktop:
        desktop.open_start_page(START_URL)
        if desktop.page.locator("input[name=search]").count() == 0:
            raise SystemExit(f"SOURCE UNAVAILABLE: {START_URL} showed no search box. No model calls were made.")
        with desktop.live_view() if args.watch else nullcontext() as viewer:
            if args.watch:
                from crescendo_agent.live_view import wait_for_viewer
                print("Local live viewer:", viewer.url, flush=True)
                webbrowser.open(viewer.url)
                wait_for_viewer(viewer)
            started = time.monotonic()
            result = run_vision_agent(GOAL, grant, desktop, model, max_steps=args.max_steps,
                                      deadline_seconds=120, max_image_width=args.image_width,
                                      on_screenshot=record, link_grounding=True, max_rate_limit_wait=60,
                                      on_rate_limit=lambda step, wait: print(
                                          f"Step {step}: provider throttled; one retry in {wait:.1f}s.", flush=True))
            seconds = round(time.monotonic() - started, 1)
            final_url, visited = desktop.page.url, list(desktop.visited)
            blocked = list(desktop.blocked_requests)
    steps = [json.loads(e.text) for e in result.transcript if e.kind == "action"]
    passed, reason = grade(result.answer, final_url, visited, steps)
    outcomes = [e.text for e in result.transcript if e.text.startswith("Authorized")]
    print("Model:", model.model, "| status:", result.status, "| agent time:", seconds, "s")
    print("Answer:", result.answer)
    print("Visited (recorded by the adapter):", visited, "| final:", final_url)
    print("Model decisions (reasons are the model's own account):")
    for number, action in enumerate(steps, start=1):
        print(f"  {number}. {action['tool']}({action['args']}) reason: {action.get('reason')!r}")
    print("Outcomes:", outcomes)
    print("Denied:", [d.reason for _, d in result.denied])
    print("Blocked browser requests:", len(blocked))
    if directory is not None:
        (directory / "result.json").write_text(json.dumps({
            "model": model.model, "status": result.status, "answer": result.answer,
            "visited": visited, "final_url": final_url, "agent_seconds": seconds,
            "blocked_requests": len(blocked), "denied": [d.reason for _, d in result.denied],
            "result": reason, "trace": [{"kind": e.kind, "text": e.text} for e in result.transcript]},
            indent=2) + "\n")
    print(reason)
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
