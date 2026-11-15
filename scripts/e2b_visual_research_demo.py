# Learn: Document this module, class, or function with a docstring; it is not an action or a model
# instruction.
"""Visual research on a permitted public page: navigate, screenshots, model-selected scrolling, cited answer."""
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
# Learn: Import time: measures monotonic elapsed time and provides bounded pauses.
import time
# Learn: From urllib.parse, import urlsplit (parses scheme, hostname, port, and path instead of guessing
# from substrings).
from urllib.parse import urlsplit
# Learn: From uuid, import uuid4 (generates independent random UUID identifiers).
from uuid import uuid4
# Learn: Import webbrowser: opens the local viewer in the user browser.
import webbrowser

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

# Learn: Set SOURCE_URL to 'https://en.wikipedia.org/wiki/Boston'.
SOURCE_URL = "https://en.wikipedia.org/wiki/Boston"
# An obscure infobox value: a model is unlikely to know it without reading the screen.
# Learn: Set QUESTION to "What is Boston's GNIS feature ID, as listed in this article's infobox?".
QUESTION = "What is Boston's GNIS feature ID, as listed in this article's infobox?"
# Learn: Set EXPECTED to '617565'.
EXPECTED = "617565"
# Learn: Set DESKTOP_LIFETIME_SECONDS to 300.
DESKTOP_LIFETIME_SECONDS = 300
# Learn: Set ARTICLE_SELECTOR to '#mw-content-text'.
ARTICLE_SELECTOR = "#mw-content-text"  # Wikipedia's article body; absent on error pages.

# Fixed expression run by automation (page scripts stay disabled). The needle is passed
# as data, never as code. True when the text is drawn inside the current viewport.
# Learn: Set VISIBLE_IN_VIEWPORT to 'needle => {\n const walker = document.createTreeWalker(document.body,
# NodeFilter.SHOW_TEXT)....
# Learn string line 1: Literal prompt, documentation, or fixture content: needle => {. It remains unchanged
# at runtime.
# Learn string line 2: Walk text nodes in the selected document without executing page-supplied code.
# Learn string line 3: Literal prompt, documentation, or fixture content: while (walker.nextNode()) {. It
# remains unchanged at runtime.
# Learn string line 4: Declare a JavaScript binding for node = walker.currentNode;.
# Learn string line 5: Declare a JavaScript binding for index = node.textContent.indexOf(needle);.
# Learn string line 6: Literal prompt, documentation, or fixture content: if (index < 0) continue;. It
# remains unchanged at runtime.
# Learn string line 7: Declare a JavaScript binding for range = document.createRange();.
# Learn string line 8: Bound the DOM Range around the expected text for visibility grading.
# Learn string line 9: Bound the DOM Range around the expected text for visibility grading.
# Learn string line 10: Read rendered text rectangles to grade whether evidence is on screen.
# Learn string line 11: Accept a nonempty text rectangle intersecting the viewport vertically.
# Learn string line 12: Close this embedded-language block or expression.
# Learn string line 13: Close this embedded-language block or expression.
# Learn string line 14: Report that no qualifying visible match was found.
# Learn string line 15: Close this embedded-language block or expression.
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


# Learn: Define validate_short_answer(answer). The body runs when called, not when defined.
def validate_short_answer(answer):
    # Learn: Take this branch only if the number of items/characters in answer.strip() is greater than 200.
    if len(answer.strip()) > 200:
        # Learn: Return 'Answer in at most 200 characters with only the requested value. Inspect the
        # screenshot again.' to the caller and stop this function.
        return "Answer in at most 200 characters with only the requested value. Inspect the screenshot again."
    # Learn: Return None (no value) to the caller and stop this function.
    return None


# Learn: Define grade(answer, expected, page_text, visible_at_finish). The body runs when called, not when
# defined.
def grade(answer, expected, page_text, visible_at_finish):
    # Learn: Document this module, class, or function with a docstring; it is not an action or a model
    # instruction.
    """Return (passed, reason). Text reading is for grading only; the model never saw it."""
    # Learn: Take this branch only if expected is not in page_text.
    if expected not in page_text:
        # Learn: Return the tuple (False, 'FIXTURE CHANGED: the source page no longer contains the expected
        # value.') (positional values) to the caller and stop this function.
        return False, "FIXTURE CHANGED: the source page no longer contains the expected value."
    # Learn: Take this branch only if answer is None (no value) OR expected is not in answer.
    if answer is None or expected not in answer:
        # Learn: Return the tuple (False, 'FAIL: the answer does not contain the expected value.')
        # (positional values) to the caller and stop this function.
        return False, "FAIL: the answer does not contain the expected value."
    # Learn: Take this branch only if not (visible_at_finish).
    if not visible_at_finish:
        # Learn: Return the tuple (False, 'FAIL: the expected value was not on screen when the model
        # finished.') (positional values) to the caller and stop this function.
        return False, "FAIL: the expected value was not on screen when the model finished."
    # Learn: Return the tuple (True, 'PASS: correct answer, supported by the cited page and visible on
    # screen at finish.') (positional values) to the caller and stop this function.
    return True, "PASS: correct answer, supported by the cited page and visible on screen at finish."


# Learn: Define model_tools(transcript). The body runs when called, not when defined.
def model_tools(transcript):
    # Learn: Document this module, class, or function with a docstring; it is not an action or a model
    # instruction.
    """Tools the model actually proposed, in order (its only evidence channel is screenshots)."""
    # Learn: Return a list built from transcript by the comprehension with its filter to the caller and stop
    # this function.
    return [json.loads(entry.text)["tool"] for entry in transcript if entry.kind == "action"]


# Learn: Define decision_lines(transcript). The body runs when called, not when defined.
def decision_lines(transcript):
    # Learn: Document this module, class, or function with a docstring; it is not an action or a model
    # instruction.
    """One readable line per proposal. Reasons are the model's own, untrusted account."""
    # Learn: Set lines to a new list (empty).
    lines = []
    # Learn: Iterate over enumerate((json.loads(e.text) for e in transcript if e.kind == 'action'),
    # start=1), binding (number, action) for each item.
    for number, action in enumerate((json.loads(e.text) for e in transcript if e.kind == "action"), start=1):
        # Learn: Set args to ', '.join((f'{key}={value!r}' for (key, value) in action['args'].items())); the
        # arguments for the current operation.
        args = ", ".join(f"{key}={value!r}" for key, value in action["args"].items())
        # Learn: Append one item to the ordered collection on lines; inputs: an f-string that substitutes
        # the expressions in {...} into the text.
        lines.append(f"  {number}. {action['tool']}({args}) — reason: {action.get('reason', '(none given)')!r}")
    # Learn: Return lines to the caller and stop this function.
    return lines


# Learn: Define main(). The body runs when called, not when defined.
def main():
    # Learn: Call load_local_env with no arguments.
    load_local_env()
    # Learn: Set parser to argparse.ArgumentParser(description=__doc__); the command-line argument parser.
    parser = argparse.ArgumentParser(description=__doc__)
    # Learn: Declare this CLI option, its type/default, and help text on parser; inputs: '--model'.
    parser.add_argument("--model", default=os.environ.get("GROQ_VISION_MODEL", "qwen/qwen3.8-27b"))
    # Learn: Declare this CLI option, its type/default, and help text on parser; inputs: '--max-steps'.
    parser.add_argument("--max-steps", type=int, default=8, help="Model decisions allowed (1-10).")
    # Learn: Declare this CLI option, its type/default, and help text on parser; inputs: '--image-width'.
    parser.add_argument("--image-width", type=int, default=768,
                        # Learn: Pass keyword help = 'Downscale model screenshots to this width to reduce
                        # input tokens (default 768).'.
                        help="Downscale model screenshots to this width to reduce input tokens (default 768).")
    # Learn: Declare this CLI option, its type/default, and help text on parser; inputs: '--watch'.
    parser.add_argument("--watch", action="store_true", help="Open the real desktop in a local live viewer before starting.")
    # Learn: Declare this CLI option, its type/default, and help text on parser; inputs:
    # '--save-screenshots'.
    parser.add_argument("--save-screenshots", action="store_true", help="Save model-input PNGs and result.json under ignored .demo-artifacts/.")
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
    # Learn: Set host to urlsplit(SOURCE_URL).hostname; the parsed destination hostname rather than a
    # substring of the URL.
    host = urlsplit(SOURCE_URL).hostname
    # The model may only scroll and finish; "navigate" is used by this host code alone.
    # Learn: Set tools to a set of 'navigate', 'screenshot', 'scroll', 'finish' (unique members).
    tools = {"navigate", "screenshot", "scroll", "finish"}
    # Learn: Take this branch only if args.watch.
    if args.watch:
        # Learn: Stage an object or add a value to this collection on tools; inputs: 'view_desktop'.
        tools.add("view_desktop")
    # Learn: Set grant to TaskGrant('visual-research-demo', frozenset(tools), frozenset({host})); the task
    # identity and fixed tool/host permissions; model output cannot expand these.
    grant = TaskGrant("visual-research-demo", frozenset(tools), frozenset({host}))
    # Learn: Set model to GroqVision(args.model); the provider adapter or scripted test model used to
    # propose actions.
    model = GroqVision(args.model)
    # Learn: Set directory to None (no value); the optional local diagnostic artifact directory.
    directory = None
    # Learn: Set record_screenshot to None (no value).
    record_screenshot = None
    # Learn: Set rate_waits to a new list (empty); the retry delays recorded for the demo report.
    rate_waits = []
    # Learn: Take this branch only if args.save_screenshots.
    if args.save_screenshots:
        # Learn: Set directory to Path('.demo-artifacts') divided by 'research-' plus uuid4().hex; the
        # optional local diagnostic artifact directory.
        directory = Path(".demo-artifacts") / ("research-" + uuid4().hex)
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
    # Longer than the 180 s default: setup + optional viewer wait + up to 120 s of
    # agent time, which rate-limit pauses can fill. The agent deadline is unchanged.
    # Learn: Enter open_e2b_desktop(grant, lifetime_seconds=DESKTOP_LIFETIME_SECONDS) as desktop. The
    # context manager controls setup/exit; inspect it for the actual cleanup behavior.
    with open_e2b_desktop(grant, lifetime_seconds=DESKTOP_LIFETIME_SECONDS) as desktop:
        # Learn: Open the requested destination through the desktop adapter on desktop; inputs: SOURCE_URL.
        desktop.navigate(SOURCE_URL)  # Authorized by the grant; blocked pages raise or become an observation.
        # The site can answer with an error page (e.g. "Too many requests"). Stop before
        # spending model calls rather than grading an agent on a page without the source.
        # Learn: Take this branch only if desktop.page.locator(ARTICLE_SELECTOR).count() equals 0.
        if desktop.page.locator(ARTICLE_SELECTOR).count() == 0:
            # Learn: Raise SystemExit(f'SOURCE UNAVAILABLE: {SOURCE_URL} did not show the article (page
            # title: {desktop.page.title()!r}). No model calls were m... to stop the normal path.
            raise SystemExit(f"SOURCE UNAVAILABLE: {SOURCE_URL} did not show the article "
                             # Learn: Call desktop.page.title with no arguments.
                             f"(page title: {desktop.page.title()!r}). No model calls were made.")
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
            # Learn: Set started to time.monotonic(); the monotonic timestamp used to measure elapsed time.
            started = time.monotonic()
            # Learn: Set result to run_vision_agent(f'You are viewing a Wikipedia article in Chrome.
            # {QUESTION} Scroll as needed and read the value from the screen. Fi...; the operation outcome
            # for subsequent checks or reporting.
            result = run_vision_agent(
                # Learn: Supply literal text 'You are viewing a Wikipedia article in Chrome. '; adjacent
                # string literals are concatenated without adding whitespace.
                f"You are viewing a Wikipedia article in Chrome. {QUESTION} "
                # Learn: Supply the next argument to run_vision_agent: "Scroll as needed and read the value
                # from the screen. ".
                "Scroll as needed and read the value from the screen. "
                # Learn: Supply the next argument to run_vision_agent: "Finish with only the value, no
                # labels or explanation.",.
                "Finish with only the value, no labels or explanation.",
                # Learn: Pass keyword max_steps = args.max_steps.
                grant, desktop, model, max_steps=args.max_steps,
                # Learn: Pass keyword on_screenshot = record_screenshot.
                on_screenshot=record_screenshot, finish_validator=validate_short_answer,
                # Learn: Pass keyword max_image_width = args.image_width.
                max_image_width=args.image_width,
                # Learn: Parameters: step is provided/defaulted by the caller; seconds is provided/defaulted
                # by the caller. Type hints do not enforce types by themselves.
                on_rate_limit=lambda step, seconds: (rate_waits.append(seconds), print(
                    # Learn: Pass keyword flush = True.
                    f"Model provider rate limit at step {step}; waiting {seconds:.1f} s.", flush=True)))
            # Learn: Set agent_seconds to round(time.monotonic() - started, 1).
            agent_seconds = round(time.monotonic() - started, 1)
            # Grading evidence, gathered after the model finished and never shown to it.
            # Learn: Set source to desktop.page.url.
            source = desktop.page.url
            # Learn: Set visible to the truth value of desktop.page.evaluate(VISIBLE_IN_VIEWPORT, EXPECTED).
            visible = bool(desktop.page.evaluate(VISIBLE_IN_VIEWPORT, EXPECTED))
            # Learn: Set article to desktop.page.locator(ARTICLE_SELECTOR).
            article = desktop.page.locator(ARTICLE_SELECTOR)
            # Learn: Set page_text to article.inner_text(timeout=10000) when article.count(), otherwise ''.
            page_text = article.inner_text(timeout=10000) if article.count() else ""
            # Learn: Set blocked to the number of items/characters in desktop.blocked_requests.
            blocked = len(desktop.blocked_requests)
    # Learn: Take this branch only if urlsplit(source).hostname does not equal host.
    if urlsplit(source).hostname != host:
        # Learn: Raise SystemExit(f'FAIL: finished on an unexpected page: {source}') to stop the normal
        # path.
        raise SystemExit(f"FAIL: finished on an unexpected page: {source}")
    # Learn: Set (passed, reason) to grade(result.answer, EXPECTED, page_text, visible).
    passed, reason = grade(result.answer, EXPECTED, page_text, visible)
    # Learn: Set tools_used to model_tools(result.transcript).
    tools_used = model_tools(result.transcript)
    # Learn: Set trace to a list built from result.transcript by the comprehension.
    trace = [{"kind": e.kind, "text": e.text} for e in result.transcript]
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
    # 'Source:', source.
    print("Source:", source)
    # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
    # 'Expected:', EXPECTED, '| visible on screen at finish:', visible.
    print("Expected:", EXPECTED, "| visible on screen at finish:", visible)
    # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs: 'Model
    # tools (evidence came only from screenshots):', tools_used.
    print("Model tools (evidence came only from screenshots):", tools_used)
    # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs: "Model
    # decisions (reasons are the model's own account, not verified):".
    print("Model decisions (reasons are the model's own account, not verified):")
    # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
    # '\n'.join(decision_lines(result.transcript)).
    print("\n".join(decision_lines(result.transcript)))
    # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs: 'Denied
    # proposals:', the number of items/characters in result.denied, '| blocked browser requests:', blocked.
    print("Denied proposals:", len(result.denied), "| blocked browser requests:", blocked)
    # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs: an
    # f-string that substitutes the expressions in {...} into the text.
    print(f"Agent time: {agent_seconds} s (deadline 120 s) | rate-limit waits: {len(rate_waits)}"
          # Learn: Call sum with the arguments shown.
          f" totalling {sum(rate_waits):.1f} s")
    # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
    # 'Trace:', json.dumps(trace, indent=2).
    print("Trace:", json.dumps(trace, indent=2))
    # Learn: Take this branch only if directory is not None (no value).
    if directory is not None:
        # Learn: Set record to a new dictionary with keys 'model', 'image_width', 'status', 'answer',
        # 'source', 'question', 'expected', 'visible_at_finish', 'page_contains_expected', 'model_....
        record = {"model": model.model, "image_width": args.image_width,
                  # Learn: Define this named mapping field: "status": result.status, "answer":
                  # result.answer,. The key selects the schema/configuration value.
                  "status": result.status, "answer": result.answer,
                  # Learn: Define this named mapping field: "source": source, "question": QUESTION,
                  # "expected": EXPECTED,. The key selects the schema/configuration value.
                  "source": source, "question": QUESTION, "expected": EXPECTED,
                  # Learn: Define this named mapping field: "visible_at_finish": visible,
                  # "page_contains_expected": EXPECTED in page_text,. The key selects the
                  # schema/configuration value.
                  "visible_at_finish": visible, "page_contains_expected": EXPECTED in page_text,
                  # Learn: Define this named mapping field: "model_tools": tools_used, "denied":
                  # len(result.denied),. The key selects the schema/configuration value.
                  "model_tools": tools_used, "denied": len(result.denied),
                  # Learn: Define this named mapping field: "blocked_requests": blocked, "agent_seconds":
                  # agent_seconds,. The key selects the schema/configuration value.
                  "blocked_requests": blocked, "agent_seconds": agent_seconds,
                  # Learn: Define this named mapping field: "rate_limit_waits_seconds": rate_waits,
                  # "result": reason, "trace": trace}. The key selects the schema/configuration value.
                  "rate_limit_waits_seconds": rate_waits, "result": reason, "trace": trace}
        # Learn: Write text to the selected file, replacing existing contents on directory / 'result.json';
        # inputs: json.dumps(record, indent=2) plus '\n'.
        (directory / "result.json").write_text(json.dumps(record, indent=2) + "\n")
        # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
        # 'Saved result:', (directory / 'result.json').resolve().
        print("Saved result:", (directory / "result.json").resolve())
    # Learn: Take this branch only if result.status does not equal 'finished' OR not (passed).
    if result.status != "finished" or not passed:
        # Learn: Raise SystemExit(reason if result.status == 'finished' else f'FAIL: run ended with status
        # {result.status}.') to stop the normal path.
        raise SystemExit(reason if result.status == "finished" else f"FAIL: run ended with status {result.status}.")
    # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs: an
    # f-string that substitutes the expressions in {...} into the text.
    print(f"{reason}\nCited answer: {result.answer.strip()} [{source}]")
    # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs: 'Cleanup
    # returned without exception; provider termination not independently checked.'.
    print("Cleanup returned without exception; provider termination not independently checked.")


# Learn: Take this branch only if __name__ equals '__main__'. The __main__ guard keeps imports from
# launching the CLI.
if __name__ == "__main__":
    # Learn: Call main with no arguments.
    main()
