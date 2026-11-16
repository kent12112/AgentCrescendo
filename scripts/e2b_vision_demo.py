"""One metered E2B desktop; optional host-driven scroll and second vision request."""
# Import argparse: parses the explicit command-line options for this demo.
import argparse
# Import os: reads process environment/configuration and OS facilities.
import os
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
# Import from crescendo_security.policy: TaskGrant (holds the task identity and immutable tool/host
# allowlists).
from crescendo_security.policy import TaskGrant


# Define main with no parameters.
def main():
    # Call load_local_env with no arguments.
    load_local_env()
    # Set parser to argparse.ArgumentParser(description=__doc__).
    parser = argparse.ArgumentParser(description=__doc__)
    # Call parser.add_argument with '--model'.
    parser.add_argument("--model", default=os.environ.get("GROQ_VISION_MODEL", "qwen/qwen3.8-27b"))
    # Call parser.add_argument with '--scroll'.
    parser.add_argument("--scroll", action="store_true", help="Read a second visual code after one bounded scroll (two model calls).")
    # Set args to parser.parse_args().
    args = parser.parse_args()
    # Iterate over the tuple ('E2B_API_KEY', 'GROQ_API_KEY') (positional values), binding name for
    # each item.
    for name in ("E2B_API_KEY", "GROQ_API_KEY"):
        # Check whether not (os.environ[name], or None if absent).
        if not os.environ.get(name):
            # Raise SystemExit(f'Set {name} in this terminal first.') to stop the normal path.
            raise SystemExit(f"Set {name} in this terminal first.")
    # Set code to token_hex(3).upper().
    code = token_hex(3).upper()
    # Set second_code to token_hex(3).upper() if args.scroll, otherwise None.
    second_code = token_hex(3).upper() if args.scroll else None
    # Set grant to TaskGrant('vision-observation-demo', frozenset({'screenshot', 'scroll'} if
    # args.scroll else {'screenshot'}), frozenset()).
    grant = TaskGrant("vision-observation-demo", frozenset({"screenshot", "scroll"} if args.scroll else {"screenshot"}), frozenset())
    # Set model to GroqVision(args.model).
    model = GroqVision(args.model)
    # Use open_e2b_desktop(grant) as desktop; leave the context and run its cleanup when this block
    # ends.
    with open_e2b_desktop(grant) as desktop:
        # A fixed trusted fixture, not model-generated HTML. No external assets.
        # Call desktop.page.set_content with f'<main style="font:28px
        # Arial;padding:32px;background:#eef4ee;color:#183c2d"><section
        # style="height:650px"><h1>Crescendo vision check</h1><p>Remote desktop observation</p><p
        # style="font-size:48px">Visual code: <strong>{code}</strong></p><p>Status:
        # Ready</p></section>' plus f'<section style="height:650px"><h2>After scrolling</h2><p
        # style="font-size:48px">Visual code: <strong>{second_code}</strong></p></section>' if
        # args.scroll, otherwise '' plus '</main>'.
        desktop.page.set_content(
            '<main style="font:28px Arial;padding:32px;background:#eef4ee;color:#183c2d">'
            '<section style="height:650px"><h1>Crescendo vision check</h1><p>Remote desktop observation</p>'
            f'<p style="font-size:48px">Visual code: <strong>{code}</strong></p>'
            '<p>Status: Ready</p></section>'
            + (f'<section style="height:650px"><h2>After scrolling</h2><p style="font-size:48px">'
               f'Visual code: <strong>{second_code}</strong></p></section>' if args.scroll else '')
            # Pass keyword wait_until = 'domcontentloaded'.
            + '</main>', wait_until="domcontentloaded")
        # Set screenshot to desktop.capture_screen().
        screenshot = desktop.capture_screen()
        # Set description to model.describe(screenshot).
        description = model.describe(screenshot)
        # Check whether args.scroll.
        if args.scroll:
            # Call desktop.scroll with 'down', 5.
            desktop.scroll("down", 5)
            # Set second_screenshot to desktop.capture_screen().
            second_screenshot = desktop.capture_screen()
            # Set second_description to model.describe(second_screenshot).
            second_description = model.describe(second_screenshot)
    # Print only after browser/sandbox cleanup succeeds. Never print image data.
    # Print 'Model:', model.model.
    print("Model:", model.model)
    # Print 'Screenshot pixels:', screenshot.size.
    print("Screenshot pixels:", screenshot.size)
    # Print 'Expected visual code:', code.
    print("Expected visual code:", code)
    # Print 'Description:', description.
    print("Description:", description)
    # Check whether code is not in description.upper().
    if code not in description.upper():
        # Raise SystemExit('FAIL: vision response did not contain the displayed code. Inspect the
        # screenshot capture path.') to stop the normal path.
        raise SystemExit("FAIL: vision response did not contain the displayed code. Inspect the screenshot capture path.")
    # Print 'PASS: model read the code sent only in the image'.
    print("PASS: model read the code sent only in the image")
    # Check whether args.scroll.
    if args.scroll:
        # Print 'Expected code after scroll:', second_code.
        print("Expected code after scroll:", second_code)
        # Print 'Description after scroll:', second_description.
        print("Description after scroll:", second_description)
        # Check whether second_code is not in second_description.upper() OR second_code is in
        # description.upper() OR code is in second_description.upper().
        if (second_code not in second_description.upper() or second_code in description.upper()
                # Call second_description.upper with no arguments.
                or code in second_description.upper()):
            # Raise SystemExit('FAIL: could not verify distinct visible codes before and after
            # scroll.') to stop the normal path.
            raise SystemExit("FAIL: could not verify distinct visible codes before and after scroll.")
        # Print 'PASS: one bounded scroll revealed a different visual code'.
        print("PASS: one bounded scroll revealed a different visual code")
    # Print 'Desktop cleanup completed without an exception; provider termination was not
    # independently checked.'.
    print("Desktop cleanup completed without an exception; provider termination was not independently checked.")


# Check whether __name__ equals '__main__'.
if __name__ == "__main__":
    # Call main with no arguments.
    main()
