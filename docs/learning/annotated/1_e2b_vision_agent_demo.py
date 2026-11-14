# ANNOTATED READING COPY — not executed, not imported, may drift from the source.
# Source: scripts/e2b_vision_agent_demo.py (working tree on top of 9130a21, Nov 13 2026).
# Read order: 1 (this file) -> 2 vision_loop -> 3 vision -> 4 policy -> 5 e2b_desktop.

"""Model-selected scrolling on a controlled E2B page; at most five model calls."""
# ^ Module docstring: shown by `--help` (argparse uses __doc__ as the description).

import argparse  # Parses command-line flags such as --model and --save-screenshots.
from contextlib import nullcontext  # A "do nothing" `with` block, used when --watch is off.
import json  # Turns the trace into readable JSON for printing and result.json.
import os  # Reads environment variables (API keys, optional model name).
from pathlib import Path  # Builds file paths for the saved screenshots.
import re  # Regular expressions; used to check the answer looks like 6 hex characters.
import select  # Waits for keyboard input with a timeout (only for --watch).
import sys  # Gives access to stdin (the keyboard) for the --watch "press Enter" step.
import webbrowser  # Opens the live viewer URL in your browser (only for --watch).
from uuid import uuid4  # Random unique ID, used to name each run's artifact folder.
from secrets import token_hex  # Cryptographically random hex; used to make the two secret codes.

from crescendo_agent.local_env import load_local_env  # Loads keys from the git-ignored .env file.
from crescendo_agent.e2b_desktop import open_e2b_desktop  # Creates the cloud desktop and cleans it up after.
from crescendo_agent.vision import GroqVision  # The model adapter: screenshot in, one action out.
from crescendo_agent.vision_loop import run_vision_agent  # The loop: capture -> decide -> check -> act.
from crescendo_security.policy import TaskGrant  # The permission slip: which tools/hosts this run may use.


def wait_for_viewer(viewer):  # Only used with --watch: pause until you can see the desktop.
    viewer.wait_connected()  # Block until the local live-view stream has connected.
    print("Viewer stream transport connected. Confirm that the actual remote page is visible.", flush=True)  # Tell you it connected.
    print("When the desktop is visible, press Enter here to start the agent (45-second limit).", flush=True)  # Ask you to confirm.
    if not select.select([sys.stdin], [], [], 45)[0]:  # Wait up to 45 s for keyboard input; empty list = timed out.
        raise TimeoutError("Viewer wait expired; desktop will be cleaned up.")  # Give up; the `with` blocks still clean up.
    if not sys.stdin.readline():  # Read the line; an empty string means stdin was closed (not a real terminal).
        raise RuntimeError("Interactive terminal required for --watch.")  # --watch needs a human at a keyboard.


def validate_code_answer(answer):  # Extra check on the model's final answer for THIS demo only.
    if re.fullmatch(r"[0-9A-Fa-f]{6}", answer.strip()) is None:  # Is the whole answer exactly 6 hex characters?
        # If not, return a reason. The loop turns it into a "denied" message the model sees,
        # so the model can retry. Note: it never tells the model what the correct code is.
        return "Return exactly six hexadecimal characters read from the target section, without labels or coordinates. Inspect the screenshot again."
    return None  # None means "the format is fine" (correctness is checked later, outside the loop).


def main():  # Everything the script does when you run it.
    load_local_env()  # Copy E2B_API_KEY / GROQ_API_KEY from .env into the environment (shell exports win).
    parser = argparse.ArgumentParser(description=__doc__)  # Create the flag parser; --help shows the docstring.
    parser.add_argument("--model", default=os.environ.get("GROQ_VISION_MODEL", "qwen/qwen3.8-27b"))  # Which Groq model; env var or default.
    parser.add_argument("--watch", action="store_true", help="Open the real desktop in a local live viewer before starting.")  # Optional live view.
    parser.add_argument("--save-screenshots", action="store_true", help="Save the exact model-input PNGs under ignored .demo-artifacts/ for diagnosis.")  # Save evidence.
    args = parser.parse_args()  # Read the flags you actually typed.
    if args.watch:  # Only if you asked for the live viewer...
        # Check the optional viewer dependency before creating a metered desktop.
        import crescendo_agent.live_view  # ...import it now, so a missing package fails BEFORE we pay for a desktop.
    for name in ("E2B_API_KEY", "GROQ_API_KEY"):  # Both keys are required.
        if not os.environ.get(name):  # Missing or empty?
            raise SystemExit(f"Set {name} in this terminal first.")  # Stop early with a clear message (nothing paid yet).
    top_code, target_code = token_hex(3).upper(), token_hex(3).upper()  # Two random 6-character codes (3 bytes = 6 hex chars).
    tools = {"screenshot", "scroll", "finish"}  # The only actions this run is allowed to perform.
    if args.watch:  # With --watch we also need permission...
        tools.add("view_desktop")  # ...to open the live viewer.
    grant = TaskGrant("vision-agent-demo", frozenset(tools), frozenset())  # Permission slip: these tools, and NO web hosts.
    model = GroqVision(args.model)  # Create the model adapter (it creates the Groq client, which reads GROQ_API_KEY).
    record_screenshot = None  # By default, don't save screenshots.
    if args.save_screenshots:  # If you asked to save them...
        directory = Path(".demo-artifacts") / ("vision-" + uuid4().hex)  # ...pick a new unique folder (git-ignored).
        directory.mkdir(parents=True)  # Create it (and .demo-artifacts/ if missing). Fails if it somehow exists.
        print("Diagnostic screenshots:", directory.resolve(), flush=True)  # Print the full path so you can open it.
        def record_screenshot(step, screenshot):  # Callback the loop calls with each image it sends to the model.
            with (directory / f"step-{step:02d}.png").open("xb") as output:  # "xb" = create new binary file; never overwrite.
                output.write(screenshot.png)  # Write the exact PNG bytes the model received.
    with open_e2b_desktop(grant) as desktop:  # Start the paid cloud desktop; it is killed when this block exits, even on error.
        desktop.page.set_content(  # Replace the browser tab's page with our own HTML (no network request needed).
            '<main style="font:28px Arial;padding:32px;background:#eef4ee;color:#183c2d">'  # Page wrapper and styling.
            '<section style="height:650px"><h1>Crescendo vision check</h1>'  # First section: 650 px tall, fills the screen.
            f'<p style="font-size:48px">Visual code: <strong>{top_code}</strong></p>'  # The distractor code, visible at the start.
            '<p>The After scrolling section is below.</p></section>'  # A hint that more content exists below.
            '<section style="height:650px"><h2>After scrolling</h2>'  # Second section: off-screen until you scroll.
            f'<p style="font-size:48px">Visual code: <strong>{target_code}</strong></p></section></main>',  # The code we want.
            wait_until="domcontentloaded")  # Return once the HTML is parsed.
        desktop.page.bring_to_front()  # Make sure this tab is the visible one before any screenshot.
        with desktop.live_view() if args.watch else nullcontext() as viewer:  # Open the viewer only with --watch; otherwise do nothing.
            if args.watch:  # Live-viewer setup:
                print("Local live viewer:", viewer.url, flush=True)  # Print the local viewer address.
                webbrowser.open(viewer.url)  # Open it in your browser.
                wait_for_viewer(viewer)  # Wait for you to press Enter.
            result = run_vision_agent(  # Run the actual agent loop (see file 2).
                "Find the section headed 'After scrolling'. Scroll down as needed. "  # The goal, in plain English...
                "Report exactly the six hexadecimal characters of the Visual code visible in that section, "  # ...note: the codes
                "not the code in the first section. Do not report coordinates or add labels.",  # are NOT in the text; only in pixels.
                grant, desktop, model, on_screenshot=record_screenshot, finish_validator=validate_code_answer)  # Permissions, desktop, model, hooks.
    # Leaving the `with` blocks above closed the viewer and killed the desktop.
    print("Model:", model.model)  # Which model ran.
    print("Status:", result.status)  # "finished", "step_limit", or "deadline".
    print("Answer:", result.answer)  # What the model reported (None if it never finished).
    print("Expected target code:", target_code)  # The correct answer, for you to compare.
    print("Denied proposals:", len(result.denied))  # How many proposed actions the permission check rejected.
    trace = [{"kind": e.kind, "text": e.text} for e in result.transcript]  # Convert the history into plain dicts.
    print("Trace:", json.dumps(trace, indent=2))  # Print the step-by-step history.
    if args.save_screenshots:  # If saving evidence...
        # Keep the outcome beside the exact images the model saw, pass or fail.
        record = {"model": model.model, "status": result.status, "answer": result.answer,  # Run outcome...
                  "expected_target": target_code, "expected_top": top_code,  # ...both codes, so you can tell a distractor answer...
                  "denied": len(result.denied), "trace": trace}  # ...denials and the full history.
        (directory / "result.json").write_text(json.dumps(record, indent=2) + "\n")  # Save it next to the PNGs.
        print("Saved result:", (directory / "result.json").resolve())  # Print where it went.
    if result.status != "finished" or target_code != (result.answer or "").strip().upper():  # Didn't finish, or wrong code?
        raise SystemExit("FAIL: agent did not finish with the target code.")  # Exit with an error status.
    print("PASS: agent finished with the target code supplied only through screenshots")  # Success.
    print("Cleanup returned without exception; provider termination not independently checked.")  # Honest limit: we didn't verify E2B shut it down.


if __name__ == "__main__":  # True only when run directly (`python scripts/...`), not when imported by tests.
    main()  # Start.
