"""Model-selected click between two pages (plan W1X-F01): Boston -> Massachusetts.

The model sees screenshots plus visible link IDs and may scroll, click, or finish. It must find the
link to the state Boston is the capital of and click it with the real pointer. Pass
requires the adapter to record that the tab actually opened the target article (not
just the model saying so) and the answer to name it. Uses E2B and Groq (metered).
"""
import argparse
from contextlib import nullcontext
import json
import math
import os
from pathlib import Path
import time
from uuid import uuid4
import webbrowser

from crescendo_agent.e2b_desktop import open_e2b_desktop
from crescendo_agent.local_env import load_local_env
from crescendo_agent.vision import GroqVision
from crescendo_agent.vision_loop import run_vision_agent
from crescendo_security.policy import TaskGrant

START_URL = "https://en.wikipedia.org/wiki/Boston"
TARGET_URL = "https://en.wikipedia.org/wiki/Massachusetts"
# The goal names the link text, so this tests pointing and clicking, not knowledge.
# An earlier wording ("the state Boston is the capital of") also mixed in reasoning: the
# model clicked the infobox heading "State capital" (live run, Nov 16, 2026). Model
# judgement is compared in W1-F12; this check is about the click itself.
GOAL = ("You are viewing the Wikipedia article about Boston in Chrome. In the article's first "
        "paragraph, click the blue link whose text is exactly 'Massachusetts'. After the "
        "Massachusetts article has opened, finish with only that article's title.")


def grade(answer, final_url, visited, tools):
    """Return (passed, reason) from what the browser did, not what the model said."""
    if not {"click", "click_link"}.intersection(tools):
        return False, "FAIL: the model never clicked."
    if TARGET_URL not in visited or final_url != TARGET_URL:
        return False, f"FAIL: the tab did not end on {TARGET_URL} (visited {visited}, final {final_url})."
    if answer is None or "massachusetts" not in answer.lower():
        return False, "FAIL: the answer does not name the opened article."
    return True, "PASS: the model clicked the link, the tab opened the target article, and the answer names it."


def actions(transcript):
    return [json.loads(entry.text) for entry in transcript if entry.kind == "action"]


def load_source(desktop, *, on_attempt=None):
    """Admit the model only after an HTTP success containing the article.

    Retry the same authorized GET once on 429/5xx or navigation timeout. A refusal,
    unknown failure, or unexpectedly long/invalid Retry-After stops immediately.
    """
    from playwright.sync_api import Error as PlaywrightError, TimeoutError as PlaywrightTimeout

    attempts = []
    for number in (1, 2):
        problem = None
        try:
            desktop.navigate(START_URL)
        except PlaywrightTimeout:
            problem = "navigation_timeout"
        except PlaywrightError:
            problem = "navigation_error"
        status = desktop.last_navigation_status
        status = status if type(status) is int else None
        try:
            title = desktop.page.title()
            article = desktop.page.locator("#mw-content-text").count() > 0
        except PlaywrightError:
            title, article = None, False
        title = " ".join(title.split())[:200] if isinstance(title, str) else None
        ready = problem is None and status is not None and 200 <= status < 300 and article
        transient = status == 429 or (status is not None and 500 <= status < 600)
        # A generic browser failure (e.g. certificate failure) is not retried.
        transient = problem == "navigation_timeout" or (problem is None and transient)
        raw_delay = desktop.last_navigation_retry_after
        try:
            delay = 5.0 if raw_delay is None else float(raw_delay)
        except (TypeError, ValueError):
            delay = float("inf")
        retry = (not ready and number == 1 and transient
                 and math.isfinite(delay) and 0 <= delay <= 15)
        diagnostic_problem = problem
        if not ready and diagnostic_problem is None:
            diagnostic_problem = ("unknown_http_status" if status is None else
                                  "http_error" if not 200 <= status < 300 else "missing_article")
        info = {"attempt": number, "http_status": status, "title": title,
                "article_present": article, "ready": ready, "problem": diagnostic_problem,
                "retry_in": delay if retry else None}
        attempts.append(info)
        if on_attempt is not None:
            on_attempt(info)
        if ready or not retry:
            return attempts
        # Keep Playwright's request filter/event callbacks running during backoff.
        desktop.page.wait_for_timeout(delay * 1000)
    return attempts


def main():
    load_local_env()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", default=os.environ.get("GROQ_VISION_MODEL", "qwen/qwen3.8-27b"))
    parser.add_argument("--max-steps", type=int, default=6)
    parser.add_argument("--image-width", type=int, default=768)
    parser.add_argument("--request-timeout", type=float, default=45,
                        help="Seconds per Groq request (default 45; maximum 60).")
    parser.add_argument("--click-mode", choices=("links", "coordinates"), default="links",
                        help="Choose visible link IDs (default) or estimate screenshot pixels.")
    grid_options = parser.add_mutually_exclusive_group()
    grid_options.add_argument("--grid", dest="grid", action="store_true",
                             help="Draw the experimental pixel grid (off by default).")
    grid_options.add_argument("--no-grid", dest="grid", action="store_false")
    parser.set_defaults(grid=False)
    parser.add_argument("--watch", action="store_true", help="Open the live viewer before starting.")
    parser.add_argument("--save-screenshots", action="store_true",
                        help="Save model-input PNGs and result.json under ignored .demo-artifacts/.")
    args = parser.parse_args()
    for name in ("E2B_API_KEY", "GROQ_API_KEY"):
        if not os.environ.get(name):
            raise SystemExit(f"Set {name} in this terminal first.")
    # navigate: only the adapter uses it (start page, and the request filter's host check);
    # the vision loop never offers navigate to the model, so it moves only by clicking.
    tools = {"navigate", "screenshot", "scroll", "click", "finish"} | ({"view_desktop"} if args.watch else set())
    if args.click_mode == "links":
        tools.add("read_visible_links")
    grant = TaskGrant("click-demo", frozenset(tools), frozenset({"en.wikipedia.org"}))
    model = GroqVision(args.model, allow_click=True, click_mode=args.click_mode,
                       request_timeout=args.request_timeout)
    directory, record = None, None
    if args.save_screenshots:
        directory = Path(".demo-artifacts") / ("click-" + uuid4().hex)
        directory.mkdir(parents=True)
        print("Diagnostic screenshots:", directory.resolve(), flush=True)

        def record(step, screenshot):
            (directory / f"step-{step:02d}.png").write_bytes(screenshot.png)

    with open_e2b_desktop(grant, lifetime_seconds=300) as desktop:
        source_records = []

        def record_source(info):
            source_records.append(info)
            if not info["ready"]:
                print(f"Source attempt {info['attempt']}: HTTP {info['http_status']}, "
                      f"title {info['title']!r}, problem {info['problem']!r}.", flush=True)
                if directory is not None:
                    filename = f"source-{info['attempt']:02d}.png"
                    try:
                        (directory / filename).write_bytes(desktop.capture_screen().png)
                        info["screenshot"] = filename
                    except Exception:
                        info["screenshot_error"] = "Source screenshot could not be captured."
            if directory is not None:
                (directory / "source-attempts.json").write_text(json.dumps(source_records, indent=2) + "\n")
            if info["retry_in"] is not None:
                print(f"Temporary source failure; retrying the same page once in {info['retry_in']:.1f}s.", flush=True)

        source_attempts = load_source(desktop, on_attempt=record_source)
        source = source_attempts[-1]
        if not source["ready"]:
            reason = (f"SOURCE UNAVAILABLE: {START_URL} did not load "
                      f"(HTTP {source['http_status']}, title {source['title']!r}). No model calls were made.")
            if directory is not None:
                (directory / "result.json").write_text(json.dumps({
                    "model": model.model, "status": "source_unavailable", "answer": None,
                    "model_calls": 0, "source_attempts": source_attempts, "result": reason}, indent=2) + "\n")
            raise SystemExit(reason)
        with desktop.live_view() if args.watch else nullcontext() as viewer:
            if args.watch:
                from crescendo_agent.live_view import wait_for_viewer
                print("Local live viewer:", viewer.url, flush=True)
                webbrowser.open(viewer.url)
                try:
                    wait_for_viewer(viewer)
                except (RuntimeError, TimeoutError):
                    # Viewer URLs/passwords and raw network exception text are private.
                    codes = [code for code in viewer.errors if isinstance(code, str)
                             and code.startswith(("UPSTREAM_", "WEBSOCKET_"))
                             and all(char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for char in code)]
                    reason = ("VIEWER UNAVAILABLE: " + (codes[-1] if codes else "connection or confirmation did not complete")
                              + ". No model calls were made.")
                    if directory is not None:
                        diagnostic = {"model": model.model, "status": "viewer_unavailable", "answer": None,
                                      "model_calls": 0, "viewer_errors": codes,
                                      "source_attempts": source_attempts, "result": reason}
                        try:
                            (directory / "viewer-desktop.png").write_bytes(desktop.capture_screen().png)
                        except Exception:
                            diagnostic["screenshot_error"] = "Desktop screenshot could not be captured."
                        (directory / "result.json").write_text(json.dumps(diagnostic, indent=2) + "\n")
                    raise SystemExit(reason) from None
            started = time.monotonic()
            result = run_vision_agent(GOAL, grant, desktop, model, max_steps=args.max_steps,
                                      max_image_width=args.image_width, on_screenshot=record,
                                      grid=args.grid, link_grounding=args.click_mode == "links",
                                      max_rate_limit_wait=60,
                                      on_model_timeout=lambda step: print(
                                          f"Step {step}: Groq request timed out; retrying inference once.", flush=True),
                                      on_model_unavailable=lambda step, wait: print(
                                          f"Step {step}: Groq temporarily unavailable; one retry in {wait:.1f}s.", flush=True),
                                      on_rate_limit=lambda step, wait: print(
                                          f"Step {step}: provider throttled; one retry in {wait:.1f}s.", flush=True))
            seconds = round(time.monotonic() - started, 1)
            final_url, visited = desktop.page.url, list(desktop.visited)
            blocked, closed = len(desktop.blocked_requests), list(desktop.closed_pages)
    steps = actions(result.transcript)
    passed, reason = grade(result.answer, final_url, visited, [a["tool"] for a in steps])
    print("Model:", model.model, "| click mode:", args.click_mode,
          "| grid:", args.grid, "| image width:", args.image_width,
          "| status:", result.status, "| agent time:", seconds, "s")
    print("Answer:", result.answer)
    if result.status == "model_timeout":
        print("MODEL TIMEOUT: Groq did not return a decision; the model-request retry budget is exhausted.")
    if result.status == "model_unavailable":
        print("MODEL UNAVAILABLE: Groq returned a temporary server error. Try again when capacity recovers.")
    print("Visited (recorded by the adapter):", visited, "| final:", final_url)
    print("Model decisions (reasons are the model's own account):")
    for number, action in enumerate(steps, start=1):
        screen = f" -> screen {action['screen']}" if "screen" in action else ""
        print(f"  {number}. {action['tool']}({action['args']}){screen} reason: {action.get('reason')!r}")
    print("Denied:", [d.reason for _, d in result.denied])
    print("Blocked browser requests:", blocked, "| new tabs closed:", closed)
    trace = [{"kind": e.kind, "text": e.text} for e in result.transcript]
    if directory is not None:
        (directory / "result.json").write_text(json.dumps({
            "model": model.model, "click_mode": args.click_mode, "grid": args.grid,
            "image_width": args.image_width, "status": result.status, "answer": result.answer,
            "request_timeout": args.request_timeout,
            "source_attempts": source_attempts,
            "visited": visited, "final_url": final_url, "agent_seconds": seconds,
            "denied": [d.reason for _, d in result.denied], "result": reason, "trace": trace},
            indent=2) + "\n")
    print(reason)
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
