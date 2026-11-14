"""One metered E2B desktop; optional host-driven scroll and second vision request."""
import argparse
import os
from secrets import token_hex

from crescendo_agent.e2b_desktop import open_e2b_desktop
from crescendo_agent.vision import GroqVision
from crescendo_security.policy import TaskGrant


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=os.environ.get("GROQ_VISION_MODEL", "qwen/qwen3.8-27b"))
    parser.add_argument("--scroll", action="store_true", help="Read a second visual code after one bounded scroll (two model calls).")
    args = parser.parse_args()
    for name in ("E2B_API_KEY", "GROQ_API_KEY"):
        if not os.environ.get(name):
            raise SystemExit(f"Set {name} in this terminal first.")
    code = token_hex(3).upper()
    second_code = token_hex(3).upper() if args.scroll else None
    grant = TaskGrant("vision-observation-demo", frozenset({"screenshot", "scroll"} if args.scroll else {"screenshot"}), frozenset())
    model = GroqVision(args.model)
    with open_e2b_desktop(grant) as desktop:
        # A fixed trusted fixture, not model-generated HTML. No external assets.
        desktop.page.set_content(
            '<main style="font:28px Arial;padding:32px;background:#eef4ee;color:#183c2d">'
            '<section style="height:650px"><h1>Crescendo vision check</h1><p>Remote desktop observation</p>'
            f'<p style="font-size:48px">Visual code: <strong>{code}</strong></p>'
            '<p>Status: Ready</p></section>'
            + (f'<section style="height:650px"><h2>After scrolling</h2><p style="font-size:48px">'
               f'Visual code: <strong>{second_code}</strong></p></section>' if args.scroll else '')
            + '</main>', wait_until="domcontentloaded")
        screenshot = desktop.capture_screen()
        description = model.describe(screenshot)
        if args.scroll:
            desktop.scroll("down", 5)
            second_screenshot = desktop.capture_screen()
            second_description = model.describe(second_screenshot)
    # Print only after browser/sandbox cleanup succeeds. Never print image data.
    print("Model:", model.model)
    print("Screenshot pixels:", screenshot.size)
    print("Expected visual code:", code)
    print("Description:", description)
    if code not in description.upper():
        raise SystemExit("FAIL: vision response did not contain the displayed code. Inspect the screenshot capture path.")
    print("PASS: model read the code sent only in the image")
    if args.scroll:
        print("Expected code after scroll:", second_code)
        print("Description after scroll:", second_description)
        if (second_code not in second_description.upper() or second_code in description.upper()
                or code in second_description.upper()):
            raise SystemExit("FAIL: could not verify distinct visible codes before and after scroll.")
        print("PASS: one bounded scroll revealed a different visual code")
    print("Desktop cleanup completed without an exception; provider termination was not independently checked.")


if __name__ == "__main__":
    main()
