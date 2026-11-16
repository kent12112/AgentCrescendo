"""Visual research on a permitted public page: navigate, screenshots, model-selected scrolling, cited answer."""
# Load the library for reading command-line options.
import argparse
# Import a do-nothing context manager for runs without a live viewer.
from contextlib import nullcontext
# Load JSON parsing and formatting functions.
import json
# Load access to environment variables.
import os
# Import the class used to build file and directory paths.
from pathlib import Path
# Load the clock used to measure elapsed time.
import time
# Import the function that separates a URL into its components.
from urllib.parse import urlsplit
# Import the function that generates random unique IDs.
from uuid import uuid4
# Load the helper for opening a URL in your local browser.
import webbrowser

# Import our helper that loads local .env configuration.
from crescendo_agent.local_env import load_local_env
# Import our context manager that creates, connects to, and cleans up an E2B desktop.
from crescendo_agent.e2b_desktop import open_e2b_desktop
# Import our adapter for sending screenshots to a Groq vision model.
from crescendo_agent.vision import GroqVision
# Import the agent loop that observes screenshots and executes allowed model actions.
from crescendo_agent.vision_loop import run_vision_agent
# Import the class describing a task’s allowed tools and hosts.
from crescendo_security.policy import TaskGrant

# Store the article URL the demo will open.
SOURCE_URL = "https://en.wikipedia.org/wiki/Boston"
# An obscure infobox value: a model is unlikely to know it without reading the screen.
# Store the question the model must answer from the screen.
QUESTION = "What is Boston's GNIS feature ID, as listed in this article's infobox?"
# Store the correct value used to grade the answer afterward.
EXPECTED = "617565"
# Allow the remote desktop to exist for up to 300 seconds.
DESKTOP_LIFETIME_SECONDS = 300
# Store the CSS selector identifying Wikipedia’s article content.
ARTICLE_SELECTOR = "#mw-content-text"  # Wikipedia's article body; absent on error pages.

# Fixed expression run by automation (page scripts stay disabled). The needle is passed
# as data, never as code. True when the text is drawn inside the current viewport.
# Store a JavaScript function that checks whether the expected text is on screen.
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


# Define a function that checks the model’s proposed final answer length.
def validate_short_answer(answer):
    # Remove surrounding whitespace and check whether the answer exceeds 200 characters.
    if len(answer.strip()) > 200:
        # Return feedback asking the model to try again with a shorter answer.
        return "Answer in at most 200 characters with only the requested value. Inspect the screenshot again."
    # Return no feedback, meaning this length check accepts the answer.
    return None


# Define a function returning a pass/fail boolean and an explanation.
def grade(answer, expected, page_text, visible_at_finish):
    """Return (passed, reason). Text reading is for grading only; the model never saw it."""
    # Check whether the source page is missing the known correct value.
    if expected not in page_text:
        # Report that the source page no longer matches this demo’s expected content.
        return False, "FIXTURE CHANGED: the source page no longer contains the expected value."
    # Check whether the answer is missing or does not contain the correct value.
    if answer is None or expected not in answer:
        # Report that the answer failed the correctness check.
        return False, "FAIL: the answer does not contain the expected value."
    # Check whether the correct value was absent from the final screen.
    if not visible_at_finish:
        # Report that the final screen did not support the answer.
        return False, "FAIL: the expected value was not on screen when the model finished."
    # Report success: the answer is correct and the value was visible on the source page.
    return True, "PASS: correct answer, supported by the cited page and visible on screen at finish."


# Define a function that extracts the model’s proposed tool names from its transcript.
def model_tools(transcript):
    """Tools the model actually proposed, in order (its only evidence channel is screenshots)."""
    # Keep action entries, parse their JSON, and collect each action’s tool name.
    return [json.loads(entry.text)["tool"] for entry in transcript if entry.kind == "action"]


# Define a function that formats model proposals as readable numbered lines.
def decision_lines(transcript):
    """One readable line per proposal. Reasons are the model's own, untrusted account."""
    # Start an empty list of formatted decision lines.
    lines = []
    # Parse action entries and loop through them with numbering starting at 1.
    for number, action in enumerate((json.loads(e.text) for e in transcript if e.kind == "action"), start=1):
        # Format each argument as key=value and join the arguments with commas.
        args = ", ".join(f"{key}={value!r}" for key, value in action["args"].items())
        # Add a line containing the action number, tool, arguments, and model-provided reason.
        lines.append(f"  {number}. {action['tool']}({args}) — reason: {action.get('reason', '(none given)')!r}")
    # Return the collected decision lines.
    return lines


# Define the function that sets up, runs, and reports this demo.
def main():
    # Load local environment settings without replacing existing environment values.
    load_local_env()
    # Create a CLI parser; __doc__ supplies this module’s top docstring as its description.
    parser = argparse.ArgumentParser(description=__doc__)
    # Accept --model; otherwise use GROQ_VISION_MODEL or the specified fallback model.
    parser.add_argument("--model", default=os.environ.get("GROQ_VISION_MODEL", "qwen/qwen3.8-27b"))
    # Accept an integer decision limit, defaulting to 8.
    parser.add_argument("--max-steps", type=int, default=8, help="Model decisions allowed (1-10).")
    # Accept a screenshot width in pixels, defaulting to 768.
    parser.add_argument("--image-width", type=int, default=768,
                        # Set the help message displayed for the screenshot-width option.
                        help="Downscale model screenshots to this width to reduce input tokens (default 768).")
    # Make --watch a boolean flag that enables the local live viewer.
    parser.add_argument("--watch", action="store_true", help="Open the real desktop in a local live viewer before starting.")
    # Make --save-screenshots a boolean flag that enables diagnostic file saving.
    parser.add_argument("--save-screenshots", action="store_true", help="Save model-input PNGs and result.json under ignored .demo-artifacts/.")
    # Read the CLI options into args; invalid option syntax stops the program.
    args = parser.parse_args()
    # Run this block only when --watch was supplied.
    if args.watch:
        # Load the optional viewer dependency before creating a metered desktop.
        # Import the helper that waits for viewer connection and user confirmation.
        from crescendo_agent.live_view import wait_for_viewer
    # Check each required API-key environment variable in turn.
    for name in ("E2B_API_KEY", "GROQ_API_KEY"):
        # Check whether this API key is missing or empty.
        if not os.environ.get(name):
            # Stop the demo and tell the user which API key to configure.
            raise SystemExit(f"Set {name} in this terminal first.")
    # Extract the hostname from the source URL.
    host = urlsplit(SOURCE_URL).hostname
    # The model may only scroll and finish; "navigate" is used by this host code alone.
    # Create the set of tool permissions available to this demo.
    tools = {"navigate", "screenshot", "scroll", "finish"}
    # Run this block only when --watch was supplied.
    if args.watch:
        # Also permit desktop viewing when watch mode is enabled.
        tools.add("view_desktop")
    # Create a task grant with a task ID and immutable tool and hostname allowlists.
    grant = TaskGrant("visual-research-demo", frozenset(tools), frozenset({host}))
    # Create the vision-model adapter using the chosen model name.
    model = GroqVision(args.model)
    # Start with no diagnostic output directory.
    directory = None
    # Start with no screenshot-saving callback.
    record_screenshot = None
    # Start an empty list of provider rate-limit wait durations.
    rate_waits = []
    # Set up diagnostic saving only when --save-screenshots was supplied.
    if args.save_screenshots:
        # Build a unique output path under .demo-artifacts; / joins path components.
        directory = Path(".demo-artifacts") / ("research-" + uuid4().hex)
        # Create the output directory and any missing parent directories.
        directory.mkdir(parents=True)
        # Print the absolute screenshot directory path immediately.
        print("Diagnostic screenshots:", directory.resolve(), flush=True)
        # Define the callback that saves each model-input screenshot.
        def record_screenshot(step, screenshot):
            # Open a numbered PNG file for binary writing; xb refuses to overwrite an existing file.
            with (directory / f"step-{step:02d}.png").open("xb") as output:
                # Write the screenshot’s PNG bytes to the file.
                output.write(screenshot.png)
    # Longer than the 180 s default: setup + optional viewer wait + up to 120 s of
    # agent time, which rate-limit pauses can fill. The agent deadline is unchanged.
    # Create the permitted desktop, name it desktop, and clean it up when this block exits.
    with open_e2b_desktop(grant, lifetime_seconds=DESKTOP_LIFETIME_SECONDS) as desktop:
        # Navigate the remote browser to the source URL through the desktop adapter.
        desktop.navigate(SOURCE_URL)  # Authorized by the grant; blocked pages raise or become an observation.
        # The site can answer with an error page (e.g. "Too many requests"). Stop before
        # spending model calls rather than grading an agent on a page without the source.
        # Check whether the expected article element is missing.
        if desktop.page.locator(ARTICLE_SELECTOR).count() == 0:
            # Stop before calling the model if the source article did not load.
            raise SystemExit(f"SOURCE UNAVAILABLE: {SOURCE_URL} did not show the article "
                             # Include the actual page title and explain that no model calls were made.
                             f"(page title: {desktop.page.title()!r}). No model calls were made.")
        # Open a live viewer in watch mode; otherwise enter a do-nothing context.
        with desktop.live_view() if args.watch else nullcontext() as viewer:
            # Run this block only when --watch was supplied.
            if args.watch:
                # Print the local viewer URL immediately.
                print("Local live viewer:", viewer.url, flush=True)
                # Open that viewer URL in the local browser.
                webbrowser.open(viewer.url)
                # Wait for the viewer connection and user confirmation before starting the agent.
                wait_for_viewer(viewer)
            # Record a monotonic start time for measuring the agent’s duration.
            started = time.monotonic()
            # Run the agent with the following prompt, permissions, desktop, model, and limits.
            result = run_vision_agent(
                # Begin the prompt with the page context and the research question.
                f"You are viewing a Wikipedia article in Chrome. {QUESTION} "
                # Continue the same prompt by asking the model to scroll and read the screen.
                "Scroll as needed and read the value from the screen. "
                # Finish the prompt by requiring only the requested value as the answer.
                "Finish with only the value, no labels or explanation.",
                # Pass the permission grant, desktop, model adapter, and maximum decision count.
                grant, desktop, model, max_steps=args.max_steps,
                # Supply the optional screenshot saver and the final-answer length validator.
                on_screenshot=record_screenshot, finish_validator=validate_short_answer,
                # Limit screenshot width using the selected CLI setting.
                max_image_width=args.image_width,
                # Define a callback that records each retry wait and prints its duration.
                on_rate_limit=lambda step, seconds: (rate_waits.append(seconds), print(
                    # Print the step and wait time immediately; :.1f shows one decimal place.
                    f"Model provider rate limit at step {step}; waiting {seconds:.1f} s.", flush=True)))
            # Calculate elapsed agent time and round it to one decimal place.
            agent_seconds = round(time.monotonic() - started, 1)
            # Grading evidence, gathered after the model finished and never shown to it.
            # Read the browser’s final URL.
            source = desktop.page.url
            # Run the fixed visibility check with EXPECTED as data and convert the result to a boolean.
            visible = bool(desktop.page.evaluate(VISIBLE_IN_VIEWPORT, EXPECTED))
            # Locate the article element for post-run grading.
            article = desktop.page.locator(ARTICLE_SELECTOR)
            # Read article text with a 10-second timeout, or use an empty string if no article exists.
            page_text = article.inner_text(timeout=10000) if article.count() else ""
            # Count the browser requests blocked by the desktop adapter.
            blocked = len(desktop.blocked_requests)
    # Check whether the browser finished on a different hostname.
    if urlsplit(source).hostname != host:
        # Stop with an error if the final hostname is unexpected.
        raise SystemExit(f"FAIL: finished on an unexpected page: {source}")
    # Grade the answer and unpack the pass/fail boolean and explanation.
    passed, reason = grade(result.answer, EXPECTED, page_text, visible)
    # Extract the tool names proposed in the transcript.
    tools_used = model_tools(result.transcript)
    # Copy each transcript entry’s kind and text into a list of dictionaries.
    trace = [{"kind": e.kind, "text": e.text} for e in result.transcript]
    # Print the model name used for this run.
    print("Model:", model.model)
    # Print the agent’s final status.
    print("Status:", result.status)
    # Print the answer returned by the agent.
    print("Answer:", result.answer)
    # Print the browser’s final URL as the source.
    print("Source:", source)
    # Print the correct value and whether it was on screen when the agent finished.
    print("Expected:", EXPECTED, "| visible on screen at finish:", visible)
    # Print the model’s proposed tool names.
    print("Model tools (evidence came only from screenshots):", tools_used)
    # Print a heading noting that model reasons are unverified.
    print("Model decisions (reasons are the model's own account, not verified):")
    # Join the formatted decision lines with newlines and print them.
    print("\n".join(decision_lines(result.transcript)))
    # Print the counts of denied proposals and blocked browser requests.
    print("Denied proposals:", len(result.denied), "| blocked browser requests:", blocked)
    # Print elapsed agent time and the number of rate-limit waits.
    print(f"Agent time: {agent_seconds} s (deadline 120 s) | rate-limit waits: {len(rate_waits)}"
          # Continue the same output line with the sum of all wait durations.
          f" totalling {sum(rate_waits):.1f} s")
    # Print the transcript as indented JSON.
    print("Trace:", json.dumps(trace, indent=2))
    # Save a report only if an output directory was created.
    if directory is not None:
        # Start a report dictionary with the model name and screenshot width.
        record = {"model": model.model, "image_width": args.image_width,
                  # Include the final status and answer.
                  "status": result.status, "answer": result.answer,
                  # Include the source URL, question, and expected answer.
                  "source": source, "question": QUESTION, "expected": EXPECTED,
                  # Include whether the answer was on screen and present in the article text.
                  "visible_at_finish": visible, "page_contains_expected": EXPECTED in page_text,
                  # Include proposed tool names and the number of denied proposals.
                  "model_tools": tools_used, "denied": len(result.denied),
                  # Include blocked-request count and elapsed agent time.
                  "blocked_requests": blocked, "agent_seconds": agent_seconds,
                  # Include retry wait durations, grading explanation, and transcript.
                  "rate_limit_waits_seconds": rate_waits, "result": reason, "trace": trace}
        # Write the report as indented JSON followed by a newline.
        (directory / "result.json").write_text(json.dumps(record, indent=2) + "\n")
        # Print the absolute path of the saved report.
        print("Saved result:", (directory / "result.json").resolve())
    # Check whether the agent failed to finish or the answer failed grading.
    if result.status != "finished" or not passed:
        # Exit with the grading explanation or the unfinished-run status.
        raise SystemExit(reason if result.status == "finished" else f"FAIL: run ended with status {result.status}.")
    # Print the success explanation and answer with its source URL.
    print(f"{reason}\nCited answer: {result.answer.strip()} [{source}]")
    # Report that cleanup completed without an exception, while termination remains unverified.
    print("Cleanup returned without exception; provider termination not independently checked.")


# Run the following block only when this file is executed directly, not imported.
if __name__ == "__main__":
    # Start the demo.
    main()
