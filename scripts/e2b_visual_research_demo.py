"""Visual research on a permitted public page: navigate, screenshots, model-selected scrolling, cited answer."""
import argparse
from contextlib import nullcontext
import json
import os
from pathlib import Path
import time
from urllib.parse import urlsplit
from uuid import uuid4
import webbrowser

from crescendo_agent.local_env import load_local_env
from crescendo_agent.e2b_desktop import open_e2b_desktop
from crescendo_agent.vision import GroqVision
from crescendo_agent.vision_loop import run_vision_agent
from crescendo_security.policy import TaskGrant

SOURCE_URL = "https://en.wikipedia.org/wiki/Boston"
# An obscure infobox value: a model is unlikely to know it without reading the screen.
QUESTION = "What is Boston's GNIS feature ID, as listed in this article's infobox?"
EXPECTED = "617565"
DESKTOP_LIFETIME_SECONDS = 300
ARTICLE_SELECTOR = "#mw-content-text"  # Wikipedia's article body; absent on error pages.

# Fixed expression run by automation (page scripts stay disabled). The needle is passed
# as data, never as code. True when the text is drawn inside the current viewport.
VISIBLE_IN_VIEWPORT = """needle => {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
        const node = walker.currentNode;
        const index = node.textContent.indexOf(needle);
        if (index < 0) continue;
        const range = document.createRange();
        range.setStart(node, index);
        range.setEnd(node, index + needle.length);
        for (const box of range.getClientRects()) {
            if (box.width > 0 && box.bottom > 0 && box.top < window.innerHeight) return true;
        }
    }
    return false;
}"""


def validate_short_answer(answer):
    if len(answer.strip()) > 200:
        return "Answer in at most 200 characters with only the requested value. Inspect the screenshot again."
    return None


def grade(answer, expected, page_text, visible_at_finish):
    """Return (passed, reason). Text reading is for grading only; the model never saw it."""
    if expected not in page_text:
        return False, "FIXTURE CHANGED: the source page no longer contains the expected value."
    if answer is None or expected not in answer:
        return False, "FAIL: the answer does not contain the expected value."
    if not visible_at_finish:
        return False, "FAIL: the expected value was not on screen when the model finished."
    return True, "PASS: correct answer, supported by the cited page and visible on screen at finish."


def model_tools(transcript):
    """Tools the model actually proposed, in order (its only evidence channel is screenshots)."""
    return [json.loads(entry.text)["tool"] for entry in transcript if entry.kind == "action"]


def decision_lines(transcript):
    """One readable line per proposal. Reasons are the model's own, untrusted account."""
    lines = []
    for number, action in enumerate((json.loads(e.text) for e in transcript if e.kind == "action"), start=1):
        args = ", ".join(f"{key}={value!r}" for key, value in action["args"].items())
        lines.append(f"  {number}. {action['tool']}({args}) — reason: {action.get('reason', '(none given)')!r}")
    return lines


def main():
    load_local_env()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=os.environ.get("GROQ_VISION_MODEL", "qwen/qwen3.8-27b"))
    parser.add_argument("--max-steps", type=int, default=8, help="Model decisions allowed (1-10).")
    parser.add_argument("--image-width", type=int, default=768,
                        help="Downscale model screenshots to this width to reduce input tokens (default 768).")
    parser.add_argument("--watch", action="store_true", help="Open the real desktop in a local live viewer before starting.")
    parser.add_argument("--save-screenshots", action="store_true", help="Save model-input PNGs and result.json under ignored .demo-artifacts/.")
    args = parser.parse_args()
    if args.watch:
        # Load the optional viewer dependency before creating a metered desktop.
        from crescendo_agent.live_view import wait_for_viewer
    for name in ("E2B_API_KEY", "GROQ_API_KEY"):
        if not os.environ.get(name):
            raise SystemExit(f"Set {name} in this terminal first.")
    host = urlsplit(SOURCE_URL).hostname
    # The model may only scroll and finish; "navigate" is used by this host code alone.
    tools = {"navigate", "screenshot", "scroll", "finish"}
    if args.watch:
        tools.add("view_desktop")
    grant = TaskGrant("visual-research-demo", frozenset(tools), frozenset({host}))
    model = GroqVision(args.model)
    directory = None
    record_screenshot = None
    rate_waits = []
    if args.save_screenshots:
        directory = Path(".demo-artifacts") / ("research-" + uuid4().hex)
        directory.mkdir(parents=True)
        print("Diagnostic screenshots:", directory.resolve(), flush=True)
        def record_screenshot(step, screenshot):
            with (directory / f"step-{step:02d}.png").open("xb") as output:
                output.write(screenshot.png)
    # Longer than the 180 s default: setup + optional viewer wait + up to 120 s of
    # agent time, which rate-limit pauses can fill. The agent deadline is unchanged.
    with open_e2b_desktop(grant, lifetime_seconds=DESKTOP_LIFETIME_SECONDS) as desktop:
        desktop.navigate(SOURCE_URL)  # Authorized by the grant; blocked pages raise or become an observation.
        # The site can answer with an error page (e.g. "Too many requests"). Stop before
        # spending model calls rather than grading an agent on a page without the source.
        if desktop.page.locator(ARTICLE_SELECTOR).count() == 0:
            raise SystemExit(f"SOURCE UNAVAILABLE: {SOURCE_URL} did not show the article "
                             f"(page title: {desktop.page.title()!r}). No model calls were made.")
        with desktop.live_view() if args.watch else nullcontext() as viewer:
            if args.watch:
                print("Local live viewer:", viewer.url, flush=True)
                webbrowser.open(viewer.url)
                wait_for_viewer(viewer)
            started = time.monotonic()
            result = run_vision_agent(
                f"You are viewing a Wikipedia article in Chrome. {QUESTION} "
                "Scroll as needed and read the value from the screen. "
                "Finish with only the value, no labels or explanation.",
                grant, desktop, model, max_steps=args.max_steps,
                on_screenshot=record_screenshot, finish_validator=validate_short_answer,
                max_image_width=args.image_width,
                on_rate_limit=lambda step, seconds: (rate_waits.append(seconds), print(
                    f"Model provider rate limit at step {step}; waiting {seconds:.1f} s.", flush=True)))
            agent_seconds = round(time.monotonic() - started, 1)
            # Grading evidence, gathered after the model finished and never shown to it.
            source = desktop.page.url
            visible = bool(desktop.page.evaluate(VISIBLE_IN_VIEWPORT, EXPECTED))
            article = desktop.page.locator(ARTICLE_SELECTOR)
            page_text = article.inner_text(timeout=10000) if article.count() else ""
            blocked = len(desktop.blocked_requests)
    if urlsplit(source).hostname != host:
        raise SystemExit(f"FAIL: finished on an unexpected page: {source}")
    passed, reason = grade(result.answer, EXPECTED, page_text, visible)
    tools_used = model_tools(result.transcript)
    trace = [{"kind": e.kind, "text": e.text} for e in result.transcript]
    print("Model:", model.model)
    print("Status:", result.status)
    print("Answer:", result.answer)
    print("Source:", source)
    print("Expected:", EXPECTED, "| visible on screen at finish:", visible)
    print("Model tools (evidence came only from screenshots):", tools_used)
    print("Model decisions (reasons are the model's own account, not verified):")
    print("\n".join(decision_lines(result.transcript)))
    print("Denied proposals:", len(result.denied), "| blocked browser requests:", blocked)
    print(f"Agent time: {agent_seconds} s (deadline 120 s) | rate-limit waits: {len(rate_waits)}"
          f" totalling {sum(rate_waits):.1f} s")
    print("Trace:", json.dumps(trace, indent=2))
    if directory is not None:
        record = {"model": model.model, "image_width": args.image_width,
                  "status": result.status, "answer": result.answer,
                  "source": source, "question": QUESTION, "expected": EXPECTED,
                  "visible_at_finish": visible, "page_contains_expected": EXPECTED in page_text,
                  "model_tools": tools_used, "denied": len(result.denied),
                  "blocked_requests": blocked, "agent_seconds": agent_seconds,
                  "rate_limit_waits_seconds": rate_waits, "result": reason, "trace": trace}
        (directory / "result.json").write_text(json.dumps(record, indent=2) + "\n")
        print("Saved result:", (directory / "result.json").resolve())
    if result.status != "finished" or not passed:
        raise SystemExit(reason if result.status == "finished" else f"FAIL: run ended with status {result.status}.")
    print(f"{reason}\nCited answer: {result.answer.strip()} [{source}]")
    print("Cleanup returned without exception; provider termination not independently checked.")


if __name__ == "__main__":
    main()
