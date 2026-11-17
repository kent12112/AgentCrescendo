"""Local Chromium run of the type_text field checks (W1X-F03): no E2B, no model, no internet.

Loads a fixture page into real Microsoft Edge with page scripts disabled, as in
E2B, then runs the real field JavaScript: listing (READ_LINK_TARGETS with fields),
resolving (RESOLVE_FIELD_TARGET), what is under a point (FIELD_TARGET), and the
keyboard-focus check (FOCUSED_FIELD) with Playwright's focus emulation turned off.
It does not press real keys or prove anything about Chrome's address bar on E2B.

Requires Playwright and installed Microsoft Edge. Run from the repository root.
"""
from playwright.sync_api import sync_playwright

from crescendo_agent.e2b_desktop import FIELD_TARGET, FOCUSED_FIELD, field_target_problem
from crescendo_agent.link_grounding import LINK_LABELS, READ_LINK_TARGETS, RESOLVE_FIELD_TARGET

FIXTURE = """<!doctype html><body style="margin:0;font:16px sans-serif">
<a href="https://example.com/a" style="position:absolute;left:10px;top:10px">A link</a>
<label style="position:absolute;left:10px;top:50px">City <input id="city" type="text"></label>
<input id="search" type="search" placeholder="Search Wikipedia" style="position:absolute;left:10px;top:90px">
<input id="bare" style="position:absolute;left:10px;top:130px">
<textarea id="notes" aria-label="Notes" style="position:absolute;left:10px;top:170px"></textarea>
<input id="password" type="password" placeholder="pw" style="position:absolute;left:300px;top:50px">
<input id="disabled" disabled placeholder="off" style="position:absolute;left:300px;top:90px">
<input id="readonly" readonly placeholder="ro" style="position:absolute;left:300px;top:130px">
<input id="check" type="checkbox" style="position:absolute;left:300px;top:170px">
<input id="hidden" type="hidden" name="h">
<input id="invisible" placeholder="ghost" style="position:absolute;left:300px;top:210px;opacity:0">
<input id="covered" placeholder="under" style="position:absolute;left:300px;top:250px">
<div style="position:absolute;left:290px;top:240px;width:300px;height:40px;background:#fff"></div>
<form target="_blank" action="https://example.com/s"><input id="newtab" placeholder="new tab"
  style="position:absolute;left:10px;top:250px"></form>
<iframe srcdoc="<input placeholder='framed'>" style="position:absolute;left:10px;top:300px;width:300px;height:60px"></iframe>
</body>"""

PAGE = {"left": 0, "top": 0, "right": 1280, "bottom": 720}


def main():
    failures = []

    def check(ok, label):
        print(("PASS " if ok else "FAIL ") + label)
        if not ok:
            failures.append(label)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=False)
        try:
            context = browser.new_context(java_script_enabled=False, viewport={"width": 1280, "height": 720})
            page = context.new_page()
            session = context.new_cdp_session(page)
            page.set_content(FIXTURE)

            snapshot = page.evaluate_handle(READ_LINK_TARGETS, {
                "page": PAGE, "firstId": 1, "limit": 120, "fieldLimit": 10})
            labels = snapshot.evaluate(LINK_LABELS)
            fields = {t["label"]: t["id"] for t in labels if t.get("kind") == "field"}
            links = [t for t in labels if t.get("kind") != "field"]
            check(links == [{"id": 1, "label": "A link"}], f"links keep their shape: {links}")
            # "text field" is the fallback label of #bare, which has no label attributes.
            check(set(fields) == {"City", "Search Wikipedia", "text field", "Notes", "new tab"},
                  f"only usable text fields are listed: {sorted(fields)}")
            none_listed = page.evaluate_handle(READ_LINK_TARGETS, {
                "page": PAGE, "firstId": 50, "limit": 120, "fieldLimit": 0}).evaluate(LINK_LABELS)
            check(all(t.get("kind") != "field" for t in none_listed), "fieldLimit 0 lists no fields")

            point = snapshot.evaluate(RESOLVE_FIELD_TARGET, fields["Search Wikipedia"])
            check(point is not None, f"search field resolves to a point: {point}")
            check(snapshot.evaluate(RESOLVE_FIELD_TARGET, 1) is None, "a link ID does not resolve as a field")
            target = page.evaluate(FIELD_TARGET, [point["x"], point["y"]])
            check(field_target_problem(target) is None, f"FIELD_TARGET accepts the search field: {target}")
            newtab = snapshot.evaluate(RESOLVE_FIELD_TARGET, fields["new tab"])
            problem = field_target_problem(page.evaluate(FIELD_TARGET, [newtab["x"], newtab["y"]]))
            check(problem is not None and "new tab" in problem, f"target=_blank form is refused: {problem}")

            for element_id, words in (("password", "no permitted"), ("check", "no permitted"),
                                      ("covered", "no permitted")):
                box = page.locator("#" + element_id).bounding_box()
                at = [int(box["x"] + box["width"] / 2), int(box["y"] + box["height"] / 2)]
                problem = field_target_problem(page.evaluate(FIELD_TARGET, at))
                check(problem is not None and words in problem, f"{element_id} is refused: {problem}")
            box = page.locator("iframe").bounding_box()
            problem = field_target_problem(page.evaluate(FIELD_TARGET, [int(box["x"] + 20), int(box["y"] + 20)]))
            check(problem is not None and "frames" in problem, f"framed field is refused: {problem}")

            # Playwright's default focus emulation makes the page claim focus even when its
            # window does not have it: exactly what would hide an address-bar focus.
            check(page.evaluate("() => document.hasFocus()") is True,
                  "with Playwright's focus emulation on, the page always claims focus")
            # Focus: with emulation off, the check must follow the real focused element.
            session.send("Emulation.setFocusEmulationEnabled", {"enabled": False})
            check(page.evaluate("() => document.hasFocus()") is False,
                  "with emulation off, an unfocused window reports no focus")
            at = [point["x"], point["y"]]
            page.locator("#city").focus()
            check(page.evaluate(FOCUSED_FIELD, at) is False, "focus on another field fails the check")
            page.locator("#search").focus()
            has_focus = page.evaluate("() => document.hasFocus()")
            check(page.evaluate(FOCUSED_FIELD, at) is has_focus,
                  f"focus on the search field passes when the window has focus (hasFocus={has_focus})")
        finally:
            browser.close()
    if failures:
        raise SystemExit(f"{len(failures)} check(s) failed.")
    print("All local field checks passed.")


if __name__ == "__main__":
    main()
