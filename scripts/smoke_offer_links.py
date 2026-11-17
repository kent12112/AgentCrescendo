"""Local Edge check of offer-link recognition (JOB-F01): no E2B, no model; public page loads.

Loads real company boards in Microsoft Edge with page scripts disabled and only
GET Document/Stylesheet requests allowed (as the E2B request filter does), then
runs the real READ_LINK_TARGETS and LINK_RECORDS JavaScript and classifies every
visible link with offers.posting_company. A board passes when its first screen
shows at least one posting link for that company and no Apply link counts as one.

It does not prove E2B rendering (fonts/images are blocked there too, but the
window and Chrome build differ). Requires Playwright and installed Microsoft Edge.
Usage: python scripts/smoke_offer_links.py [BOARD_URL ...]
"""
import sys

from playwright.sync_api import sync_playwright

from crescendo_agent.link_grounding import LINK_RECORDS, READ_LINK_TARGETS
from crescendo_agent.offers import board_from_url, is_generic_label, posting_company

DEFAULT_BOARDS = ["https://job-boards.greenhouse.io/anthropic", "https://jobs.lever.co/palantir"]
PAGE = {"left": 0, "top": 0, "right": 1280, "bottom": 720}


def main(urls):
    failures = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        try:
            for url in urls:
                board = board_from_url(url)
                if board is None:
                    failures.append(f"{url}: not a supported board URL")
                    continue
                context = browser.new_context(java_script_enabled=False,
                                              viewport={"width": 1280, "height": 720})
                context.route("**/*", lambda route: route.continue_()
                              if route.request.method == "GET"
                              and route.request.resource_type in {"document", "stylesheet"}
                              else route.abort())
                try:
                    page = context.new_page()
                    page.goto(url, wait_until="load", timeout=20000)
                    snapshot = page.evaluate_handle(READ_LINK_TARGETS, {
                        "page": PAGE, "firstId": 1, "limit": 120, "fieldLimit": 0})
                    count = snapshot.evaluate("targets => targets.length")
                    records = snapshot.evaluate(LINK_RECORDS, list(range(1, count + 1)))
                finally:
                    context.close()
                postings = [r for r in records if posting_company(r["href"]) == (board.platform, board.company)
                            and not is_generic_label(r["label"])]
                applies = [r for r in records if r["label"].strip().lower() == "apply"]
                print(f"\n{url}: {len(records)} visible links, {len(postings)} postings")
                for record in records:
                    kind = "POSTING" if record in postings else "other  "
                    print(f"  {kind} {record['label'][:70]!r} -> {record['href'][:100]}")
                if not postings:
                    failures.append(f"{url}: no posting links on the first screen")
                if any(r in postings for r in applies):
                    failures.append(f"{url}: an Apply link was accepted as an offer title")
        finally:
            browser.close()
    print()
    for failure in failures:
        print("FAIL", failure)
    if failures:
        raise SystemExit(f"{len(failures)} check(s) failed.")
    print("All boards show recognizable posting links.")


if __name__ == "__main__":
    main(sys.argv[1:] or DEFAULT_BOARDS)
