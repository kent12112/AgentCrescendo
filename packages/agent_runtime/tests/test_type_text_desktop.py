"""type_text in the desktop adapter (W1X-F03). Fakes replace Chrome and E2B.

The order of real-desktop actions matters: nothing may be typed until the field
under the point is checked and has real keyboard focus, so a key never reaches
the address bar or another window.
"""
from unittest.mock import Mock, call

import pytest

from crescendo_agent.desktop import ActionDenied
from crescendo_agent.e2b_desktop import (EXPECTED_WINDOW, FIELD_TARGET, FOCUSED_FIELD, PAGE_AREA,
                                         E2BDesktop, field_target_problem)
from crescendo_security.policy import TaskGrant

GRANT = TaskGrant("type", frozenset({"type_text", "read_visible_links", "screenshot", "finish"}),
                  frozenset(), public_web=True)
FIELD = {"kind": "field", "target": ""}


def fake_browser(*, target=FIELD, focused=(True, True)):
    """A page whose field check returns `target` and whose focus checks return `focused` in turn."""
    page, session = Mock(), Mock()
    page.url = "https://en.wikipedia.org/wiki/Main_Page"
    focus = list(focused)

    def send(method, params=None):
        if method == "Browser.getWindowForTarget":
            return {"windowId": 1, "bounds": dict(EXPECTED_WINDOW)}
        if method == "Page.getFrameTree":
            return {"frameTree": {"frame": {"id": "main"}}}
        return {}

    def evaluate(script, arg=None):
        if "innerWidth" in script:
            return [1280, 720]
        if script == FIELD_TARGET:
            return target
        if script == FOCUSED_FIELD:
            return focus.pop(0)
        raise AssertionError("unexpected script")

    session.send.side_effect = send
    page.evaluate.side_effect = evaluate
    return page, session


def desktop_for(page, session, grant=GRANT):
    """Record every real-desktop action in one ordered log."""
    log = Mock()
    desktop = E2BDesktop(page, session, grant, pointer_provider=log.pointer, click_provider=log.click,
                         write_provider=log.write, key_provider=log.key)
    return desktop, log


def frame_navigated(page):
    return [c.args[1] for c in page.on.call_args_list if c.args[0] == "framenavigated"][0]


def test_types_into_a_focused_field_without_submitting():
    page, session = fake_browser(focused=(True,))
    desktop, log = desktop_for(page, session)
    outcome = desktop.type_text(300, 200, "Boston Common", False)
    assert log.mock_calls == [call.pointer(300, 200), call.click(),
                              call.key(["ctrl", "a"]), call.write("Boston Common")]
    assert outcome.startswith("Typed into the field.")
    # The field was checked in page coordinates, and focus emulation was turned off first.
    field_check = [c for c in page.evaluate.call_args_list if c.args[0] == FIELD_TARGET][0]
    assert field_check.args[1] == [300 - PAGE_AREA.left, 200 - PAGE_AREA.top]
    session.send.assert_any_call("Emulation.setFocusEmulationEnabled", {"enabled": False})


def test_submit_presses_enter_and_reports_the_page_it_opened():
    page, session = fake_browser()
    desktop, log = desktop_for(page, session)
    results = "https://en.wikipedia.org/w/index.php?search=Boston+Common"

    def key(keys):
        if keys == "enter":  # a GET form submission loads a new document in this tab
            desktop._request_paused({"requestId": "r", "resourceType": "Document", "frameId": "main",
                                     "request": {"url": results, "method": "GET"}})
            page.url = results
            frame_navigated(page)(page.main_frame)
    log.key.side_effect = key
    outcome = desktop.type_text(300, 200, "Boston Common", True)
    assert [c for c in log.mock_calls if c[0] == "key"] == [call.key(["ctrl", "a"]), call.key("enter")]
    assert outcome == f"The submission opened {results}."
    assert desktop.visited == [results]


def test_submission_to_internal_host_is_blocked_by_the_request_filter():
    page, session = fake_browser()
    desktop, log = desktop_for(page, session)

    def key(keys):
        if keys == "enter":
            desktop._request_paused({"requestId": "r", "resourceType": "Document", "frameId": "main",
                                     "request": {"url": "https://10.0.0.1/?q=x", "method": "GET"}})
            page.url = "chrome-error://chromewebdata/"
            frame_navigated(page)(page.main_frame)
    log.key.side_effect = key
    assert "blocked by browser policy" in desktop.type_text(300, 200, "x", True)
    assert desktop.blocked_requests == ["https://10.0.0.1/?q=x"]
    assert desktop.visited == []


def test_post_form_submission_is_blocked():
    # A login-style POST form never sends what was typed: the filter passes only GET.
    page, session = fake_browser()
    desktop, log = desktop_for(page, session)

    def key(keys):
        if keys == "enter":
            desktop._request_paused({"requestId": "r", "resourceType": "Document", "frameId": "main",
                                     "request": {"url": "https://example.com/login", "method": "POST"}})
            page.url = "chrome-error://chromewebdata/"
            frame_navigated(page)(page.main_frame)
    log.key.side_effect = key
    assert "blocked by browser policy" in desktop.type_text(300, 200, "x", True)


def test_nothing_is_typed_if_the_field_does_not_get_focus():
    # E.g. the address bar or another window holds the keyboard.
    page, session = fake_browser(focused=(False,))
    desktop, log = desktop_for(page, session)
    with pytest.raises(ActionDenied, match="keyboard focus"):
        desktop.type_text(300, 200, "Boston", True)
    assert [c[0] for c in log.mock_calls] == ["pointer", "click"]  # no key, no write


def test_enter_is_not_pressed_if_focus_moved_while_typing():
    page, session = fake_browser(focused=(True, False))
    desktop, log = desktop_for(page, session)
    assert "Enter was not pressed" in desktop.type_text(300, 200, "Boston", True)
    assert call.key("enter") not in log.mock_calls


@pytest.mark.parametrize("target, words", [
    ({"kind": "other"}, "no permitted text field"),       # e.g. a password field or plain text
    ({"kind": "none"}, "no permitted text field"),
    ({"kind": "frame"}, "embedded frames"),
    ({"kind": "field", "target": "_blank"}, "new tab"),
    ("garbage", "no permitted text field"),
])
def test_refused_targets_touch_nothing(target, words):
    page, session = fake_browser(target=target)
    desktop, log = desktop_for(page, session)
    with pytest.raises(ActionDenied, match=words):
        desktop.type_text(300, 200, "Boston", False)
    assert log.mock_calls == []


def test_gateway_refuses_before_any_desktop_action():
    page, session = fake_browser()
    desktop, log = desktop_for(page, session)
    with pytest.raises(ActionDenied, match="outside"):
        desktop.type_text(300, 60, "Boston", False)  # the address bar row
    with pytest.raises(ActionDenied, match="printable"):
        desktop.type_text(300, 200, "two\nlines", False)
    no_tool = TaskGrant("n", frozenset({"click"}), frozenset(), public_web=True)
    with pytest.raises(ActionDenied, match="not permitted"):
        desktop_for(page, session, no_tool)[0].type_text(300, 200, "Boston", False)
    assert log.mock_calls == []


def test_field_target_problem_accepts_only_same_tab_fields():
    assert field_target_problem(FIELD) is None
    assert field_target_problem({"kind": "field", "target": "_self"}) is None
    assert field_target_problem({"kind": "field", "target": None}) is not None
    assert field_target_problem({"kind": "link"}) is not None


def test_field_ids_and_link_ids_are_not_interchangeable():
    page, session = fake_browser()
    desktop, _ = desktop_for(page, session, TaskGrant(
        "both", GRANT.allowed_tools | {"click"}, frozenset(), public_web=True))
    snapshot = Mock()
    snapshot.evaluate.return_value = [{"id": 1, "label": "Massachusetts"},
                                      {"id": 2, "label": "Search Wikipedia", "kind": "field"}]
    page.evaluate_handle.return_value = snapshot
    labels = desktop.visible_links()
    assert labels[1] == {"id": 2, "label": "Search Wikipedia", "kind": "field"}
    # Fields were requested because type_text is granted.
    assert page.evaluate_handle.call_args.args[1]["fieldLimit"] > 0
    with pytest.raises(ActionDenied, match="link ID"):
        desktop.resolve_link(2)
    with pytest.raises(ActionDenied, match="field ID"):
        desktop.resolve_field(1)
    snapshot.evaluate.return_value = {"x": 300, "y": 200}
    assert desktop.resolve_field(2) == (300, 200)


def test_fields_are_not_listed_without_type_text():
    page, session = fake_browser()
    click_only = TaskGrant("c", frozenset({"click", "read_visible_links"}), frozenset(), public_web=True)
    desktop, _ = desktop_for(page, session, click_only)
    page.evaluate_handle.return_value.evaluate.return_value = []
    desktop.visible_links()
    assert page.evaluate_handle.call_args.args[1]["fieldLimit"] == 0
