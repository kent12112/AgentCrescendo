"""Model-selected scrolling on a controlled E2B page; at most five model calls."""
import argparse
from contextlib import nullcontext
import json
import os
from pathlib import Path
import re
import select
import sys
import webbrowser
from uuid import uuid4
from secrets import token_hex

from crescendo_agent.e2b_desktop import open_e2b_desktop
from crescendo_agent.vision import GroqVision
from crescendo_agent.vision_loop import run_vision_agent
from crescendo_security.policy import TaskGrant


def wait_for_viewer(viewer):
    viewer.wait_connected()
    print("Viewer stream transport connected. Confirm that the actual remote page is visible.", flush=True)
    print("When the desktop is visible, press Enter here to start the agent (45-second limit).", flush=True)
    if not select.select([sys.stdin], [], [], 45)[0]:
        raise TimeoutError("Viewer wait expired; desktop will be cleaned up.")
    if not sys.stdin.readline():
        raise RuntimeError("Interactive terminal required for --watch.")


def validate_code_answer(answer):
    if re.fullmatch(r"[0-9A-Fa-f]{6}", answer.strip()) is None:
        return "Return exactly six hexadecimal characters read from the target section, without labels or coordinates. Inspect the screenshot again."
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=os.environ.get("GROQ_VISION_MODEL", "qwen/qwen3.8-27b"))
    parser.add_argument("--watch", action="store_true", help="Open the real desktop in a local live viewer before starting.")
    parser.add_argument("--save-screenshots", action="store_true", help="Save the exact model-input PNGs under ignored .demo-artifacts/ for diagnosis.")
    args = parser.parse_args()
    if args.watch:
        # Check the optional viewer dependency before creating a metered desktop.
        import crescendo_agent.live_view
    for name in ("E2B_API_KEY", "GROQ_API_KEY"):
        if not os.environ.get(name):
            raise SystemExit(f"Set {name} in this terminal first.")
    top_code, target_code = token_hex(3).upper(), token_hex(3).upper()
    tools = {"screenshot", "scroll", "finish"}
    if args.watch:
        tools.add("view_desktop")
    grant = TaskGrant("vision-agent-demo", frozenset(tools), frozenset())
    model = GroqVision(args.model)
    record_screenshot = None
    if args.save_screenshots:
        directory = Path(".demo-artifacts") / ("vision-" + uuid4().hex)
        directory.mkdir(parents=True)
        print("Diagnostic screenshots:", directory.resolve(), flush=True)
        def record_screenshot(step, screenshot):
            with (directory / f"step-{step:02d}.png").open("xb") as output:
                output.write(screenshot.png)
    with open_e2b_desktop(grant) as desktop:
        desktop.page.set_content(
            '<main style="font:28px Arial;padding:32px;background:#eef4ee;color:#183c2d">'
            '<section style="height:650px"><h1>Crescendo vision check</h1>'
            f'<p style="font-size:48px">Visual code: <strong>{top_code}</strong></p>'
            '<p>The After scrolling section is below.</p></section>'
            '<section style="height:650px"><h2>After scrolling</h2>'
            f'<p style="font-size:48px">Visual code: <strong>{target_code}</strong></p></section></main>',
            wait_until="domcontentloaded")
        desktop.page.bring_to_front()
        with desktop.live_view() if args.watch else nullcontext() as viewer:
            if args.watch:
                print("Local live viewer:", viewer.url, flush=True)
                webbrowser.open(viewer.url)
                wait_for_viewer(viewer)
            result = run_vision_agent(
                "Find the section headed 'After scrolling'. Scroll down as needed. "
                "Report exactly the six hexadecimal characters of the Visual code visible in that section, "
                "not the code in the first section. Do not report coordinates or add labels.",
                grant, desktop, model, on_screenshot=record_screenshot, finish_validator=validate_code_answer)
    print("Model:", model.model)
    print("Status:", result.status)
    print("Answer:", result.answer)
    print("Expected target code:", target_code)
    print("Denied proposals:", len(result.denied))
    print("Trace:", json.dumps([{"kind": e.kind, "text": e.text} for e in result.transcript], indent=2))
    if result.status != "finished" or target_code != (result.answer or "").strip().upper():
        raise SystemExit("FAIL: agent did not finish with the target code.")
    print("PASS: agent finished with the target code supplied only through screenshots")
    print("Cleanup returned without exception; provider termination not independently checked.")


if __name__ == "__main__":
    main()
