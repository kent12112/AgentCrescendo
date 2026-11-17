"""Live, model-free check of clicking (plan W1X-F01). Creates one metered desktop.

Each case loads a small fixture page (page.set_content, no network) and clicks a
box on it with the REAL desktop pointer through desktop.click(), the same path the
agent uses. Expected results:

  permitted link     opens https://en.wikipedia.org/wiki/Massachusetts
  blocked-host link  request failed by the request filter (example.com)
  POST form          request failed by the request filter (only GET allowed)
  new-tab link/form  refused before the button is pressed (no new tab)
  download link      refused before the button is pressed
  address bar, dock  refused by the gateway: outside the page area

Two "second layer" cases then bypass desktop.click() with a raw E2B click, to show
what still holds if the first check were wrong: Chrome's download block, and the
new-tab backstop that closes any tab that opens.
"""
import os
from uuid import uuid4

from crescendo_agent.desktop import ActionDenied
from crescendo_agent.e2b_desktop import PAGE_AREA, open_e2b_desktop
from crescendo_agent.local_env import load_local_env
from crescendo_security.policy import TaskGrant

TARGET = "https://en.wikipedia.org/wiki/Massachusetts"
# Fixture boxes: (left, top) in page pixels; each is 300x80.
BOXES = {"ok": (40, 40), "bad": (400, 40), "post": (40, 160), "blank": (400, 160),
         "form_blank": (40, 280), "download": (400, 280)}
STYLE = "position:absolute;left:{}px;top:{}px;width:300px;height:80px;display:block;background:#cde;font:20px Arial"
FIXTURE = (
    '<body style="margin:0">'
    f'<a href="{TARGET}" style="{STYLE.format(*BOXES["ok"])}">permitted link</a>'
    f'<a href="https://example.com/" style="{STYLE.format(*BOXES["bad"])}">blocked host</a>'
    '<form method="post" action="https://en.wikipedia.org/w/index.php"><input type="hidden" name="q" value="x">'
    f'<button style="{STYLE.format(*BOXES["post"])}">POST form</button></form>'
    f'<a target="_blank" href="https://en.wikipedia.org/wiki/Boston" style="{STYLE.format(*BOXES["blank"])}">new tab</a>'
    '<form target="_blank" action="https://en.wikipedia.org/wiki/Boston">'
    f'<button style="{STYLE.format(*BOXES["form_blank"])}">form, new tab</button></form>'
    f'<a download="x.txt" href="data:text/plain,hello" style="{STYLE.format(*BOXES["download"])}">download</a>'
    '</body>')


def screen_point(name):
    """Center of a fixture box, in real screen pixels."""
    left, top = BOXES[name]
    return PAGE_AREA.left + left + 150, PAGE_AREA.top + top + 40


def check(condition, message):
    if not condition:
        raise RuntimeError("FAIL: " + message)
    print("PASS:", message, flush=True)


def reset(desktop):
    desktop.page.set_content(FIXTURE, wait_until="domcontentloaded")


def expect_refused(desktop, x, y, words, label):
    try:
        desktop.click(x, y)
    except ActionDenied as denied:
        check(words in str(denied), f"{label}: refused ({denied})")
    else:
        raise RuntimeError(f"FAIL: {label}: click was not refused")


def expect_stale(desktop, target_id, label):
    try:
        desktop.resolve_link(target_id)
    except ActionDenied:
        check(True, label)
    else:
        raise RuntimeError("FAIL: " + label)


def grounded_checks(desktop):
    """Exercise the browser's real DOM, without relying on a model's account."""
    page = desktop.page
    page.set_content(FIXTURE + '''
        <a href="/hidden" style="display:none">hidden link</a>
        <div style="opacity:0"><a href="/transparent" style="position:absolute;top:500px">transparent link</a></div>
        <a href="/below" style="position:absolute;top:650px">below safe page area</a>
        <a href="/covered" style="position:absolute;left:800px;top:40px;width:100px;height:80px">covered link</a>
        <div style="position:absolute;left:800px;top:40px;width:100px;height:80px;background:white;z-index:9"></div>
        ''', wait_until="domcontentloaded")
    targets = desktop.visible_links()
    by_label = {target["label"]: target["id"] for target in targets}
    check(not {"hidden link", "transparent link", "below safe page area", "covered link"}.intersection(by_label),
          "link grounding excludes hidden, transparent, covered, and below-safe-area links")
    check(desktop.resolve_link(by_label["permitted link"]) == screen_point("ok"),
          "grounded link resolves to the measured real screen point")
    old_id = by_label["permitted link"]
    targets = desktop.visible_links()
    check(not {target["id"] for target in targets}.intersection(by_label.values()),
          "new observation does not reuse old link IDs")
    expect_stale(desktop, old_id, "expired observation ID refused")
    current = next(target["id"] for target in targets if target["label"] == "permitted link")
    page.evaluate("() => document.querySelector('a').href = 'https://en.wikipedia.org/wiki/Boston'")
    expect_stale(desktop, current, "link with changed destination refused")

    reset(desktop)
    current = desktop.visible_links()[0]["id"]
    page.evaluate("() => document.querySelector('a').style.top = '500px'")
    expect_stale(desktop, current, "link moved away from its saved point refused")
    reset(desktop)
    current = desktop.visible_links()[0]["id"]
    page.evaluate("() => document.querySelector('a').textContent = 'changed label'")
    expect_stale(desktop, current, "link with changed label refused")
    reset(desktop)
    expect_stale(desktop, current, "replaced document elements refused")

    targets = {target["label"]: target["id"] for target in desktop.visible_links()}
    for label, words in (("new tab", "new tab"), ("download", "Download")):
        expect_refused(desktop, *desktop.resolve_link(targets[label]), words, "grounded " + label)
    outcome = desktop.click(*desktop.resolve_link(targets["permitted link"]))
    check(page.url == TARGET and "click opened" in outcome,
          "grounded selection opens permitted destination through the real pointer")


def run(sandbox_type):
    created = []

    class Tracked:
        @staticmethod
        def create(**kwargs):
            sandbox = sandbox_type.create(**kwargs)
            created.append(sandbox)
            return sandbox

    grant = TaskGrant(str(uuid4()), frozenset({"navigate", "screenshot", "read_visible_links", "click"}),
                      frozenset({"en.wikipedia.org"}))
    with open_e2b_desktop(grant, sandbox_type=Tracked) as desktop:
        sandbox, page = created[0], desktop.page
        check(desktop.click_area() == PAGE_AREA, "Chrome geometry matches the measured page area")

        reset(desktop)
        outcome = desktop.click(*screen_point("ok"))
        check(page.url == TARGET and desktop.visited == [TARGET], f"permitted link: {outcome}")

        grounded_checks(desktop)

        reset(desktop)
        outcome = desktop.click(*screen_point("bad"))
        check("blocked" in outcome and "https://example.com/" in desktop.blocked_requests,
              f"blocked-host link: {outcome}")

        reset(desktop)
        outcome = desktop.click(*screen_point("post"))
        check("blocked" in outcome and "https://en.wikipedia.org/w/index.php" in desktop.blocked_requests,
              f"POST form: {outcome}")

        for name, words in (("blank", "new tab"), ("form_blank", "new tab"), ("download", "Download")):
            reset(desktop)
            expect_refused(desktop, *screen_point(name), words, name)
        check(len(page.context.pages) == 1 and desktop.closed_pages == [], "no new tab was opened")

        expect_refused(desktop, 512, 90, "outside", "address bar (512, 90)")
        expect_refused(desktop, 512, 740, "outside", "dock (512, 740)")

        # Second layer: bypass desktop.click() on purpose.
        reset(desktop)
        sandbox.move_mouse(*screen_point("download"))
        sandbox.left_click()
        page.wait_for_timeout(3000)  # Playwright wait, so browser events are processed.
        files = sandbox.commands.run("ls -A ~/Downloads", timeout=10).stdout.split()
        check(files == [], "raw click on download link saved no file (Chrome download block)")

        reset(desktop)
        sandbox.move_mouse(*screen_point("blank"))
        sandbox.left_click()
        page.wait_for_timeout(3000)
        check(desktop.closed_pages != [] and len(page.context.pages) == 1,
              f"raw click on new-tab link: backstop closed {desktop.closed_pages}")
    print("All click checks passed. No model calls were made.")


def main():
    load_local_env()
    if not os.environ.get("E2B_API_KEY"):
        raise SystemExit("Set E2B_API_KEY in this terminal. This check uses E2B resources.")
    from e2b_desktop import Sandbox

    run(Sandbox)


if __name__ == "__main__":
    main()
