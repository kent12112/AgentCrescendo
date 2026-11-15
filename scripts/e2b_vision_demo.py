# Learn: Document this module, class, or function with a docstring; it is not an action or a model
# instruction.
"""One metered E2B desktop; optional host-driven scroll and second vision request."""
# Learn: Import argparse: parses the explicit command-line options for this demo.
import argparse
# Learn: Import os: reads process environment/configuration and OS facilities.
import os
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
# Learn: From crescendo_security.policy, import TaskGrant (holds the task identity and immutable tool/host
# allowlists).
from crescendo_security.policy import TaskGrant


# Learn: Define main(). The body runs when called, not when defined.
def main():
    # Learn: Call load_local_env with no arguments.
    load_local_env()
    # Learn: Set parser to argparse.ArgumentParser(description=__doc__); the command-line argument parser.
    parser = argparse.ArgumentParser(description=__doc__)
    # Learn: Declare this CLI option, its type/default, and help text on parser; inputs: '--model'.
    parser.add_argument("--model", default=os.environ.get("GROQ_VISION_MODEL", "qwen/qwen3.8-27b"))
    # Learn: Declare this CLI option, its type/default, and help text on parser; inputs: '--scroll'.
    parser.add_argument("--scroll", action="store_true", help="Read a second visual code after one bounded scroll (two model calls).")
    # Learn: Set args to parser.parse_args(); the arguments for the current operation. Parse command-line
    # values and reject unsupported argument syntax.
    args = parser.parse_args()
    # Learn: Iterate over the tuple ('E2B_API_KEY', 'GROQ_API_KEY') (positional values), binding name for
    # each item.
    for name in ("E2B_API_KEY", "GROQ_API_KEY"):
        # Learn: Take this branch only if not (os.environ[name] with None as the missing-key default).
        if not os.environ.get(name):
            # Learn: Raise SystemExit(f'Set {name} in this terminal first.') to stop the normal path.
            raise SystemExit(f"Set {name} in this terminal first.")
    # Learn: Set code to token_hex(3).upper().
    code = token_hex(3).upper()
    # Learn: Set second_code to token_hex(3).upper() when args.scroll, otherwise None (no value).
    second_code = token_hex(3).upper() if args.scroll else None
    # Learn: Set grant to TaskGrant('vision-observation-demo', frozenset({'screenshot', 'scroll'} if
    # args.scroll else {'screenshot'}), frozenset()); the task identity and fixed tool/host permissions;
    # model output cannot expand these.
    grant = TaskGrant("vision-observation-demo", frozenset({"screenshot", "scroll"} if args.scroll else {"screenshot"}), frozenset())
    # Learn: Set model to GroqVision(args.model); the provider adapter or scripted test model used to
    # propose actions.
    model = GroqVision(args.model)
    # Learn: Enter open_e2b_desktop(grant) as desktop. The context manager controls setup/exit; inspect it
    # for the actual cleanup behavior.
    with open_e2b_desktop(grant) as desktop:
        # A fixed trusted fixture, not model-generated HTML. No external assets.
        # Learn: Call desktop.page.set_content with the arguments shown.
        desktop.page.set_content(
            # Learn: Supply literal text '<main style="font:28px
            # Arial;padding:32px;background:#eef4ee;color:#183c2d"><section
            # style="height:650px"><h1>Crescendo vision...; adjacent string literals are concatenated
            # without adding whitespace.
            '<main style="font:28px Arial;padding:32px;background:#eef4ee;color:#183c2d">'
            # Learn: Supply the next argument to desktop.page.set_content: '<section
            # style="height:650px"><h1>Crescendo vision check</h1><p>Remote desktop observation</p>'.
            '<section style="height:650px"><h1>Crescendo vision check</h1><p>Remote desktop observation</p>'
            # Learn: Supply the next argument to desktop.page.set_content: f'<p
            # style="font-size:48px">Visual code: <strong>{code}</strong></p>'.
            f'<p style="font-size:48px">Visual code: <strong>{code}</strong></p>'
            # Learn: Supply the next argument to desktop.page.set_content: '<p>Status: Ready</p></section>'.
            '<p>Status: Ready</p></section>'
            # Learn: Supply the next argument to desktop.page.set_content: + (f'<section
            # style="height:650px"><h2>After scrolling</h2><p style="font-size:48px">'.
            + (f'<section style="height:650px"><h2>After scrolling</h2><p style="font-size:48px">'
               # Learn: Supply literal text ''; adjacent string literals are concatenated without adding
               # whitespace.
               f'Visual code: <strong>{second_code}</strong></p></section>' if args.scroll else '')
            # Learn: Pass keyword wait_until = 'domcontentloaded'.
            + '</main>', wait_until="domcontentloaded")
        # Learn: Set screenshot to desktop.capture_screen(); the current PNG observation supplied to the
        # vision model. Capture a fresh whole-desktop PNG through the permission-checked adapter.
        screenshot = desktop.capture_screen()
        # Learn: Set description to model.describe(screenshot).
        description = model.describe(screenshot)
        # Learn: Take this branch only if args.scroll.
        if args.scroll:
            # Learn: Execute the already-checked wheel action; the next screenshot shows its effect on
            # desktop; inputs: 'down', 5.
            desktop.scroll("down", 5)
            # Learn: Set second_screenshot to desktop.capture_screen(). Capture a fresh whole-desktop PNG
            # through the permission-checked adapter.
            second_screenshot = desktop.capture_screen()
            # Learn: Set second_description to model.describe(second_screenshot).
            second_description = model.describe(second_screenshot)
    # Print only after browser/sandbox cleanup succeeds. Never print image data.
    # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
    # 'Model:', model.model.
    print("Model:", model.model)
    # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
    # 'Screenshot pixels:', screenshot.size.
    print("Screenshot pixels:", screenshot.size)
    # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
    # 'Expected visual code:', code.
    print("Expected visual code:", code)
    # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
    # 'Description:', description.
    print("Description:", description)
    # Learn: Take this branch only if code is not in description.upper().
    if code not in description.upper():
        # Learn: Raise SystemExit('FAIL: vision response did not contain the displayed code. Inspect the
        # screenshot capture path.') to stop the normal path.
        raise SystemExit("FAIL: vision response did not contain the displayed code. Inspect the screenshot capture path.")
    # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs: 'PASS:
    # model read the code sent only in the image'.
    print("PASS: model read the code sent only in the image")
    # Learn: Take this branch only if args.scroll.
    if args.scroll:
        # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
        # 'Expected code after scroll:', second_code.
        print("Expected code after scroll:", second_code)
        # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
        # 'Description after scroll:', second_description.
        print("Description after scroll:", second_description)
        # Learn: Take this branch only if second_code is not in second_description.upper() OR second_code is
        # in description.upper() OR code is in second_description.upper().
        if (second_code not in second_description.upper() or second_code in description.upper()
                # Learn: Call second_description.upper with no arguments.
                or code in second_description.upper()):
            # Learn: Raise SystemExit('FAIL: could not verify distinct visible codes before and after
            # scroll.') to stop the normal path.
            raise SystemExit("FAIL: could not verify distinct visible codes before and after scroll.")
        # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
        # 'PASS: one bounded scroll revealed a different visual code'.
        print("PASS: one bounded scroll revealed a different visual code")
    # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs: 'Desktop
    # cleanup completed without an exception; provider termination was not independently ....
    print("Desktop cleanup completed without an exception; provider termination was not independently checked.")


# Learn: Take this branch only if __name__ equals '__main__'. The __main__ guard keeps imports from
# launching the CLI.
if __name__ == "__main__":
    # Learn: Call main with no arguments.
    main()
