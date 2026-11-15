# Learn: Document this module, class, or function with a docstring; it is not an action or a model
# instruction.
"""Model-selected scrolling on a controlled E2B page; at most five model calls."""
# Learn: Import argparse: parses the explicit command-line options for this demo.
import argparse
# Learn: From contextlib, import nullcontext (supplies a no-op with-block when optional viewing is
# disabled).
from contextlib import nullcontext
# Learn: Import json: encodes/decodes JSON for tool arguments, transcripts, or HTTP payloads.
import json
# Learn: Import os: reads process environment/configuration and OS facilities.
import os
# Learn: From pathlib, import Path (represents filesystem paths and explicit file operations).
from pathlib import Path
# Learn: Import re: matches bounded text patterns such as query words or answer formats.
import re
# Learn: Import webbrowser: opens the local viewer in the user browser.
import webbrowser
# Learn: From uuid, import uuid4 (generates independent random UUID identifiers).
from uuid import uuid4
# Learn: From secrets, import token_hex (generates random bytes encoded as hexadecimal text).
from secrets import token_hex

# Learn: From crescendo_agent.local_env, import load_local_env (loads root .env values without replacing
# existing process values).
from crescendo_agent.local_env import load_local_env
# Learn: From crescendo_agent.e2b_desktop, import open_e2b_desktop (owns restricted sandbox setup, browser
# connection, and cleanup).
from crescendo_agent.e2b_desktop import open_e2b_desktop
# Learn: From crescendo_agent.vision, import GroqVision (adapts screenshot observations to Groq vision
# requests).
from crescendo_agent.vision import GroqVision
# Learn: From crescendo_agent.vision_loop, import run_vision_agent (runs the bounded
# screenshot/proposal/authorization/action loop).
from crescendo_agent.vision_loop import run_vision_agent
# Learn: From crescendo_security.policy, import TaskGrant (holds the task identity and immutable tool/host
# allowlists).
from crescendo_security.policy import TaskGrant


# Learn: Define validate_code_answer(answer). The body runs when called, not when defined.
def validate_code_answer(answer):
    # Learn: Take this branch only if re.fullmatch('[0-9A-Fa-f]{6}', answer.strip()) is None (no value).
    if re.fullmatch(r"[0-9A-Fa-f]{6}", answer.strip()) is None:
        # Learn: Return 'Return exactly six hexadecimal characters read from the target section, without
        # labels or c... to the caller and stop this function.
        return "Return exactly six hexadecimal characters read from the target section, without labels or coordinates. Inspect the screenshot again."
    # Learn: Return None (no value) to the caller and stop this function.
    return None


# Learn: Define main(). The body runs when called, not when defined.
def main():
    # Learn: Call load_local_env with no arguments.
    load_local_env()
    # Learn: Set parser to argparse.ArgumentParser(description=__doc__); the command-line argument parser.
    parser = argparse.ArgumentParser(description=__doc__)
    # Learn: Declare this CLI option, its type/default, and help text on parser; inputs: '--model'.
    parser.add_argument("--model", default=os.environ.get("GROQ_VISION_MODEL", "qwen/qwen3.8-27b"))
    # Learn: Declare this CLI option, its type/default, and help text on parser; inputs: '--watch'.
    parser.add_argument("--watch", action="store_true", help="Open the real desktop in a local live viewer before starting.")
    # Learn: Declare this CLI option, its type/default, and help text on parser; inputs:
    # '--save-screenshots'.
    parser.add_argument("--save-screenshots", action="store_true", help="Save the exact model-input PNGs under ignored .demo-artifacts/ for diagnosis.")
    # Learn: Set args to parser.parse_args(); the arguments for the current operation. Parse command-line
    # values and reject unsupported argument syntax.
    args = parser.parse_args()
    # Learn: Take this branch only if args.watch.
    if args.watch:
        # Load the optional viewer dependency before creating a metered desktop.
        # Learn: From crescendo_agent.live_view, import wait_for_viewer (waits for transport connection and
        # the user confirmation before agent actions).
        from crescendo_agent.live_view import wait_for_viewer
    # Learn: Iterate over the tuple ('E2B_API_KEY', 'GROQ_API_KEY') (positional values), binding name for
    # each item.
    for name in ("E2B_API_KEY", "GROQ_API_KEY"):
        # Learn: Take this branch only if not (os.environ[name] with None as the missing-key default).
        if not os.environ.get(name):
            # Learn: Raise SystemExit(f'Set {name} in this terminal first.') to stop the normal path.
            raise SystemExit(f"Set {name} in this terminal first.")
    # Learn: Set (top_code, target_code) to the tuple (token_hex(3).upper(), token_hex(3).upper())
    # (positional values).
    top_code, target_code = token_hex(3).upper(), token_hex(3).upper()
    # Learn: Set tools to a set of 'screenshot', 'scroll', 'finish' (unique members).
    tools = {"screenshot", "scroll", "finish"}
    # Learn: Take this branch only if args.watch.
    if args.watch:
        # Learn: Stage an object or add a value to this collection on tools; inputs: 'view_desktop'.
        tools.add("view_desktop")
    # Learn: Set grant to TaskGrant('vision-agent-demo', frozenset(tools), frozenset()); the task identity
    # and fixed tool/host permissions; model output cannot expand these.
    grant = TaskGrant("vision-agent-demo", frozenset(tools), frozenset())
    # Learn: Set model to GroqVision(args.model); the provider adapter or scripted test model used to
    # propose actions.
    model = GroqVision(args.model)
    # Learn: Set record_screenshot to None (no value).
    record_screenshot = None
    # Learn: Take this branch only if args.save_screenshots.
    if args.save_screenshots:
        # Learn: Set directory to Path('.demo-artifacts') divided by 'vision-' plus uuid4().hex; the
        # optional local diagnostic artifact directory.
        directory = Path(".demo-artifacts") / ("vision-" + uuid4().hex)
        # Learn: Create the artifact directory with the explicitly supplied parent/existence options on
        # directory.
        directory.mkdir(parents=True)
        # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
        # 'Diagnostic screenshots:', directory.resolve().
        print("Diagnostic screenshots:", directory.resolve(), flush=True)
        # Learn: Define record_screenshot(step, screenshot). The body runs when called, not when defined.
        def record_screenshot(step, screenshot):
            # Learn: Enter (directory / f'step-{step:02d}.png').open('xb') as output. The context manager
            # controls setup/exit; inspect it for the actual cleanup behavior.
            with (directory / f"step-{step:02d}.png").open("xb") as output:
                # Learn: Write this text or byte sequence to the already-open output on output; inputs:
                # screenshot.png.
                output.write(screenshot.png)
    # Learn: Enter open_e2b_desktop(grant) as desktop. The context manager controls setup/exit; inspect it
    # for the actual cleanup behavior.
    with open_e2b_desktop(grant) as desktop:
        # Learn: Call desktop.page.set_content with the arguments shown.
        desktop.page.set_content(
            # Learn: Supply literal text '<main style="font:28px
            # Arial;padding:32px;background:#eef4ee;color:#183c2d"><section
            # style="height:650px"><h1>Crescendo vision...; adjacent string literals are concatenated
            # without adding whitespace.
            '<main style="font:28px Arial;padding:32px;background:#eef4ee;color:#183c2d">'
            # Learn: Supply the next argument to desktop.page.set_content: '<section
            # style="height:650px"><h1>Crescendo vision check</h1>'.
            '<section style="height:650px"><h1>Crescendo vision check</h1>'
            # Learn: Supply the next argument to desktop.page.set_content: f'<p
            # style="font-size:48px">Visual code: <strong>{top_code}</strong></p>'.
            f'<p style="font-size:48px">Visual code: <strong>{top_code}</strong></p>'
            # Learn: Supply the next argument to desktop.page.set_content: '<p>The After scrolling section
            # is below.</p></section>'.
            '<p>The After scrolling section is below.</p></section>'
            # Learn: Supply the next argument to desktop.page.set_content: '<section
            # style="height:650px"><h2>After scrolling</h2>'.
            '<section style="height:650px"><h2>After scrolling</h2>'
            # Learn: Supply the next argument to desktop.page.set_content: f'<p
            # style="font-size:48px">Visual code: <strong>{target_code}</strong></p></section></main>',.
            f'<p style="font-size:48px">Visual code: <strong>{target_code}</strong></p></section></main>',
            # Learn: Pass keyword wait_until = 'domcontentloaded'.
            wait_until="domcontentloaded")
        # Learn: Foreground the controlled tab before screenshot or wheel input on desktop.page.
        desktop.page.bring_to_front()
        # Learn: Enter desktop.live_view() if args.watch else nullcontext() as viewer. The context manager
        # controls setup/exit; inspect it for the actual cleanup behavior.
        with desktop.live_view() if args.watch else nullcontext() as viewer:
            # Learn: Take this branch only if args.watch.
            if args.watch:
                # Learn: Display diagnostic/result text without treating it as verified model evidence;
                # inputs: 'Local live viewer:', viewer.url.
                print("Local live viewer:", viewer.url, flush=True)
                # Learn: Call webbrowser.open with the arguments shown.
                webbrowser.open(viewer.url)
                # Learn: Call wait_for_viewer with the arguments shown.
                wait_for_viewer(viewer)
            # Learn: Set result to run_vision_agent("Find the section headed 'After scrolling'. Scroll down
            # as needed. Report exactly the six hexadecimal characters of...; the operation outcome for
            # subsequent checks or reporting.
            result = run_vision_agent(
                # Learn: Supply literal text "Find the section headed 'After scrolling'. Scroll down as
                # needed. Report exactly the six hexadecimal characters of the Visual ...; adjacent string
                # literals are concatenated without adding whitespace.
                "Find the section headed 'After scrolling'. Scroll down as needed. "
                # Learn: Supply the next argument to run_vision_agent: "Report exactly the six hexadecimal
                # characters of the Visual code visible in that section, ".
                "Report exactly the six hexadecimal characters of the Visual code visible in that section, "
                # Learn: Supply the next argument to run_vision_agent: "not the code in the first section.
                # Do not report coordinates or add labels.",.
                "not the code in the first section. Do not report coordinates or add labels.",
                # Learn: Pass keyword on_screenshot = record_screenshot.
                grant, desktop, model, on_screenshot=record_screenshot, finish_validator=validate_code_answer)
    # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
    # 'Model:', model.model.
    print("Model:", model.model)
    # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
    # 'Status:', result.status.
    print("Status:", result.status)
    # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
    # 'Answer:', result.answer.
    print("Answer:", result.answer)
    # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
    # 'Expected target code:', target_code.
    print("Expected target code:", target_code)
    # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs: 'Denied
    # proposals:', the number of items/characters in result.denied.
    print("Denied proposals:", len(result.denied))
    # Learn: Set trace to a list built from result.transcript by the comprehension.
    trace = [{"kind": e.kind, "text": e.text} for e in result.transcript]
    # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
    # 'Trace:', json.dumps(trace, indent=2).
    print("Trace:", json.dumps(trace, indent=2))
    # Learn: Take this branch only if args.save_screenshots.
    if args.save_screenshots:
        # Keep the outcome beside the exact images the model saw, pass or fail.
        # Learn: Set record to a new dictionary with keys 'model', 'status', 'answer', 'expected_target',
        # 'expected_top', 'denied', 'trace'.
        record = {"model": model.model, "status": result.status, "answer": result.answer,
                  # Learn: Define this named mapping field: "expected_target": target_code, "expected_top":
                  # top_code,. The key selects the schema/configuration value.
                  "expected_target": target_code, "expected_top": top_code,
                  # Learn: Define this named mapping field: "denied": len(result.denied), "trace": trace}.
                  # The key selects the schema/configuration value.
                  "denied": len(result.denied), "trace": trace}
        # Learn: Write text to the selected file, replacing existing contents on directory / 'result.json';
        # inputs: json.dumps(record, indent=2) plus '\n'.
        (directory / "result.json").write_text(json.dumps(record, indent=2) + "\n")
        # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
        # 'Saved result:', (directory / 'result.json').resolve().
        print("Saved result:", (directory / "result.json").resolve())
    # Learn: Take this branch only if result.status does not equal 'finished' OR target_code does not equal
    # (result.answer or '').strip().upper().
    if result.status != "finished" or target_code != (result.answer or "").strip().upper():
        # Learn: Raise SystemExit('FAIL: agent did not finish with the target code.') to stop the normal
        # path.
        raise SystemExit("FAIL: agent did not finish with the target code.")
    # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs: 'PASS:
    # agent finished with the target code supplied only through screenshots'.
    print("PASS: agent finished with the target code supplied only through screenshots")
    # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs: 'Cleanup
    # returned without exception; provider termination not independently checked.'.
    print("Cleanup returned without exception; provider termination not independently checked.")


# Learn: Take this branch only if __name__ equals '__main__'. The __main__ guard keeps imports from
# launching the CLI.
if __name__ == "__main__":
    # Learn: Call main with no arguments.
    main()
