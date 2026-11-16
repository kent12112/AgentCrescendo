"""Model-selected scrolling on a controlled E2B page; at most five model calls."""
# Import argparse: parses the explicit command-line options for this demo.
import argparse
# Import from contextlib: nullcontext (supplies a no-op with-block when optional viewing is
# disabled).
from contextlib import nullcontext
# Import json: encodes/decodes JSON for tool arguments, transcripts, or HTTP payloads.
import json
# Import os: reads process environment/configuration and OS facilities.
import os
# Import from pathlib: Path (represents filesystem paths and explicit file operations).
from pathlib import Path
# Import re: matches bounded text patterns such as query words or answer formats.
import re
# Import webbrowser: opens the local viewer in the user browser.
import webbrowser
# Import from uuid: uuid4 (generates independent random UUID identifiers).
from uuid import uuid4
# Import from secrets: token_hex (generates random bytes encoded as hexadecimal text).
from secrets import token_hex

# Import from crescendo_agent.local_env: load_local_env (loads root .env values without replacing
# existing process values).
from crescendo_agent.local_env import load_local_env
# Import from crescendo_agent.e2b_desktop: open_e2b_desktop (owns restricted sandbox setup, browser
# connection, and cleanup).
from crescendo_agent.e2b_desktop import open_e2b_desktop
# Import from crescendo_agent.vision: GroqVision (adapts screenshot observations to Groq vision
# requests).
from crescendo_agent.vision import GroqVision
# Import from crescendo_agent.vision_loop: run_vision_agent (runs the bounded
# screenshot/proposal/authorization/action loop).
from crescendo_agent.vision_loop import run_vision_agent
# Import from crescendo_security.policy: TaskGrant (holds the task identity and immutable tool/host
# allowlists).
from crescendo_security.policy import TaskGrant


# Define validate_code_answer with parameters answer.
def validate_code_answer(answer):
    # Check whether re.fullmatch('[0-9A-Fa-f]{6}', answer.strip()) is None.
    if re.fullmatch(r"[0-9A-Fa-f]{6}", answer.strip()) is None:
        # Return 'Return exactly six hexadecimal characters read from the target section, without
        # labels or coordinates. Inspect the screenshot again.'.
        return "Return exactly six hexadecimal characters read from the target section, without labels or coordinates. Inspect the screenshot again."
    # Return None.
    return None


# Define main with no parameters.
def main():
    # Call load_local_env with no arguments.
    load_local_env()
    # Set parser to argparse.ArgumentParser(description=__doc__).
    parser = argparse.ArgumentParser(description=__doc__)
    # Call parser.add_argument with '--model'.
    parser.add_argument("--model", default=os.environ.get("GROQ_VISION_MODEL", "qwen/qwen3.8-27b"))
    # Call parser.add_argument with '--watch'.
    parser.add_argument("--watch", action="store_true", help="Open the real desktop in a local live viewer before starting.")
    # Call parser.add_argument with '--save-screenshots'.
    parser.add_argument("--save-screenshots", action="store_true", help="Save the exact model-input PNGs under ignored .demo-artifacts/ for diagnosis.")
    # Set args to parser.parse_args().
    args = parser.parse_args()
    # Check whether args.watch.
    if args.watch:
        # Load the optional viewer dependency before creating a metered desktop.
        # Import from crescendo_agent.live_view: wait_for_viewer (waits for transport connection and
        # the user confirmation before agent actions).
        from crescendo_agent.live_view import wait_for_viewer
    # Iterate over the tuple ('E2B_API_KEY', 'GROQ_API_KEY') (positional values), binding name for
    # each item.
    for name in ("E2B_API_KEY", "GROQ_API_KEY"):
        # Check whether not (os.environ[name], or None if absent).
        if not os.environ.get(name):
            # Raise SystemExit(f'Set {name} in this terminal first.') to stop the normal path.
            raise SystemExit(f"Set {name} in this terminal first.")
    # Set (top_code, target_code) to (token_hex(3).upper(), token_hex(3).upper()).
    top_code, target_code = token_hex(3).upper(), token_hex(3).upper()
    # Set tools to {'screenshot', 'scroll', 'finish'}.
    tools = {"screenshot", "scroll", "finish"}
    # Check whether args.watch.
    if args.watch:
        # Add 'view_desktop' to tools.
        tools.add("view_desktop")
    # Set grant to TaskGrant('vision-agent-demo', frozenset(tools), frozenset()).
    grant = TaskGrant("vision-agent-demo", frozenset(tools), frozenset())
    # Set model to GroqVision(args.model).
    model = GroqVision(args.model)
    # Set record_screenshot to None.
    record_screenshot = None
    # Check whether args.save_screenshots.
    if args.save_screenshots:
        # Set directory to Path('.demo-artifacts') divided by 'vision-' plus uuid4().hex.
        directory = Path(".demo-artifacts") / ("vision-" + uuid4().hex)
        # Call directory.mkdir with no arguments.
        directory.mkdir(parents=True)
        # Print 'Diagnostic screenshots:', directory.resolve().
        print("Diagnostic screenshots:", directory.resolve(), flush=True)
        # Define record_screenshot with parameters step, screenshot.
        def record_screenshot(step, screenshot):
            # Use (directory / f'step-{step:02d}.png').open('xb') as output; leave the context and
            # run its cleanup when this block ends.
            with (directory / f"step-{step:02d}.png").open("xb") as output:
                # Call output.write with screenshot.png.
                output.write(screenshot.png)
    # Use open_e2b_desktop(grant) as desktop; leave the context and run its cleanup when this block
    # ends.
    with open_e2b_desktop(grant) as desktop:
        # Call desktop.page.set_content with f'<main style="font:28px
        # Arial;padding:32px;background:#eef4ee;color:#183c2d"><section
        # style="height:650px"><h1>Crescendo vision check</h1><p style="font-size:48px">Visual code:
        # <strong>{top_code}</strong></p><p>The After scrolling section is
        # below.</p></section><section style="height:650px"><h2>After scrolling</h2><p
        # style="font-size:48px">Visual code: <strong>{target_code}</strong></p></section></main>'.
        desktop.page.set_content(
            '<main style="font:28px Arial;padding:32px;background:#eef4ee;color:#183c2d">'
            '<section style="height:650px"><h1>Crescendo vision check</h1>'
            f'<p style="font-size:48px">Visual code: <strong>{top_code}</strong></p>'
            '<p>The After scrolling section is below.</p></section>'
            '<section style="height:650px"><h2>After scrolling</h2>'
            f'<p style="font-size:48px">Visual code: <strong>{target_code}</strong></p></section></main>',
            # Pass keyword wait_until = 'domcontentloaded'.
            wait_until="domcontentloaded")
        # Call desktop.page.bring_to_front with no arguments.
        desktop.page.bring_to_front()
        # Use desktop.live_view() if args.watch else nullcontext() as viewer; leave the context and
        # run its cleanup when this block ends.
        with desktop.live_view() if args.watch else nullcontext() as viewer:
            # Check whether args.watch.
            if args.watch:
                # Print 'Local live viewer:', viewer.url.
                print("Local live viewer:", viewer.url, flush=True)
                # Call webbrowser.open with viewer.url.
                webbrowser.open(viewer.url)
                # Call wait_for_viewer with viewer.
                wait_for_viewer(viewer)
            # Set result to the result of run_vision_agent using the arguments below.
            result = run_vision_agent(
                "Find the section headed 'After scrolling'. Scroll down as needed. "
                "Report exactly the six hexadecimal characters of the Visual code visible in that section, "
                "not the code in the first section. Do not report coordinates or add labels.",
                # Pass keyword on_screenshot = record_screenshot.
                grant, desktop, model, on_screenshot=record_screenshot, finish_validator=validate_code_answer)
    # Print 'Model:', model.model.
    print("Model:", model.model)
    # Print 'Status:', result.status.
    print("Status:", result.status)
    # Print 'Answer:', result.answer.
    print("Answer:", result.answer)
    # Print 'Expected target code:', target_code.
    print("Expected target code:", target_code)
    # Print 'Denied proposals:', the length of result.denied.
    print("Denied proposals:", len(result.denied))
    # Set trace to [{'kind': e.kind, 'text': e.text} for e in result.transcript].
    trace = [{"kind": e.kind, "text": e.text} for e in result.transcript]
    # Print 'Trace:', json.dumps(trace, indent=2).
    print("Trace:", json.dumps(trace, indent=2))
    # Check whether args.save_screenshots.
    if args.save_screenshots:
        # Keep the outcome beside the exact images the model saw, pass or fail.
        # Build record from the entries below.
        record = {"model": model.model, "status": result.status, "answer": result.answer,
                  # Include expected_target, expected_top in this dictionary.
                  "expected_target": target_code, "expected_top": top_code,
                  # Include denied, trace in this dictionary.
                  "denied": len(result.denied), "trace": trace}
        # Call (directory / 'result.json').write_text with json.dumps(record, indent=2) plus '\n'.
        (directory / "result.json").write_text(json.dumps(record, indent=2) + "\n")
        # Print 'Saved result:', (directory / 'result.json').resolve().
        print("Saved result:", (directory / "result.json").resolve())
    # Check whether result.status does not equal 'finished' or target_code does not equal
    # (result.answer or '').strip().upper().
    if result.status != "finished" or target_code != (result.answer or "").strip().upper():
        # Raise SystemExit('FAIL: agent did not finish with the target code.') to stop the normal
        # path.
        raise SystemExit("FAIL: agent did not finish with the target code.")
    # Print 'PASS: agent finished with the target code supplied only through screenshots'.
    print("PASS: agent finished with the target code supplied only through screenshots")
    # Print 'Cleanup returned without exception; provider termination not independently checked.'.
    print("Cleanup returned without exception; provider termination not independently checked.")


# Check whether __name__ equals '__main__'.
if __name__ == "__main__":
    # Call main with no arguments.
    main()
