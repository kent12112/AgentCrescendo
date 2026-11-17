"""Offline tests for clicking (W1X-F01): adapter checks, model tool, and loop mapping.

The fake browser imitates what the live probes showed (docs/e2b-clicking.md): a
navigating click produces a main-frame Document request that the request filter
sees, and a blocked one leaves the tab on Chrome's error page.
"""
from io import BytesIO
import json
from types import SimpleNamespace as NS
from unittest.mock import Mock

import pytest
from PIL import Image

from crescendo_agent.desktop import ActionDenied
from crescendo_agent.e2b_desktop import (EXPECTED_WINDOW, PAGE_AREA, E2BDesktop,
                                         click_target_problem)
from crescendo_agent.model import Entry
from crescendo_agent.vision import GroqVision, Screenshot
from crescendo_agent.vision_loop import run_vision_agent
from crescendo_security.policy import TaskGrant, ToolCall

# navigate is granted because the request filter checks hosts through the navigate rule;
# without it every page load a click starts would be blocked (see docs/e2b-clicking.md).
GRANT = TaskGrant("click-task", frozenset({"navigate", "click", "screenshot", "read_visible_links", "scroll", "finish"}),
                  frozenset({"en.wikipedia.org"}))
LINK = {"kind": "link", "target": "", "download": False}


def fake_browser(*, target=LINK, window=EXPECTED_WINDOW, viewport=(1280, 720)):
    page, session = Mock(), Mock()
    page.url = "https://en.wikipedia.org/wiki/Boston"

    def send(method, params=None):
        if method == "Browser.getWindowForTarget":
            return {"windowId": 1, "bounds": dict(window)}
        if method == "Page.getFrameTree":
            return {"frameTree": {"frame": {"id": "main"}}}
        return {}

    def evaluate(script, arg=None):
        return list(viewport) if "innerWidth" in script else target

    session.send.side_effect = send
    page.evaluate.side_effect = evaluate
    return page, session


def desktop_for(page, session, press=None):
    pointer, clicker = Mock(), Mock(side_effect=press)
    desktop = E2BDesktop(page, session, GRANT, pointer_provider=pointer, click_provider=clicker)
    return desktop, pointer, clicker


def navigation(desktop, page, url, *, landed=None):
    """A press that requests `url` in the main frame, as a real link click does."""
    def press():
        desktop._request_paused({"requestId": "r1", "resourceType": "Document", "frameId": "main",
                                 "request": {"url": url, "method": "GET"}})
        page.url = landed or url
        # Chrome then shows the new document (or its error page) in the tab.
        frame_navigated(page)(page.main_frame)
    return press


def frame_navigated(page):
    """The adapter's framenavigated handler, as registered on the fake page."""
    return [c.args[1] for c in page.on.call_args_list if c.args[0] == "framenavigated"][0]


def test_click_on_permitted_link_moves_real_pointer_and_reports_new_page():
    page, session = fake_browser()
    desktop, pointer, clicker = desktop_for(page, session)
    clicker.side_effect = navigation(desktop, page, "https://en.wikipedia.org/wiki/Massachusetts")
    outcome = desktop.click(190, 194)
    pointer.assert_called_once_with(190, 194)
    clicker.assert_called_once_with()
    # The page was asked about the point in page coordinates (screen minus page origin).
    target_call = [c for c in page.evaluate.call_args_list if "elementFromPoint" in c.args[0]][0]
    assert target_call.args[1] == [190 - PAGE_AREA.left, 194 - PAGE_AREA.top]
    assert outcome == "The click opened https://en.wikipedia.org/wiki/Massachusetts."
    assert desktop.visited == ["https://en.wikipedia.org/wiki/Massachusetts"]


def test_click_to_blocked_host_is_failed_by_request_filter_and_reported():
    page, session = fake_browser()
    desktop, _, clicker = desktop_for(page, session)
    clicker.side_effect = navigation(desktop, page, "https://example.com/",
                                     landed="chrome-error://chromewebdata/")
    outcome = desktop.click(550, 194)
    assert "blocked by browser policy" in outcome
    assert desktop.blocked_requests == ["https://example.com/"]
    session.send.assert_any_call("Fetch.failRequest", {"requestId": "r1", "errorReason": "BlockedByClient"})
    assert desktop.visited == []
    assert "blocked" in desktop.observe().text


def test_post_form_request_is_failed_by_request_filter():
    page, session = fake_browser(target={"kind": "form", "target": ""})
    desktop, _, clicker = desktop_for(page, session)

    def press():
        desktop._request_paused({"requestId": "r2", "resourceType": "Document", "frameId": "main",
                                 "request": {"url": "https://en.wikipedia.org/w/index.php", "method": "POST"}})
        page.url = "chrome-error://chromewebdata/"
        frame_navigated(page)(page.main_frame)
    clicker.side_effect = press
    assert "blocked by browser policy" in desktop.click(190, 314)
    assert desktop.blocked_requests == ["https://en.wikipedia.org/w/index.php"]


def test_click_that_loads_nothing_reports_no_page_load():
    page, session = fake_browser(target={"kind": "other"})
    desktop, _, clicker = desktop_for(page, session)
    assert "did not start a page load" in desktop.click(512, 400)
    clicker.assert_called_once_with()
    page.wait_for_load_state.assert_not_called()


def test_navigation_to_same_url_still_completes():
    # Two error pages in a row share one URL; completion must not depend on URL change.
    page, session = fake_browser()
    page.url = "chrome-error://chromewebdata/"
    desktop, _, clicker = desktop_for(page, session)
    clicker.side_effect = navigation(desktop, page, "https://en.wikipedia.org/wiki/Boston",
                                     landed="chrome-error://chromewebdata/")
    assert "click opened" in desktop.click(512, 400)


def test_navigation_that_never_shows_a_document_times_out_honestly():
    page, session = fake_browser()
    desktop, _, clicker = desktop_for(page, session)

    def press():  # A request starts, but the tab never switches documents.
        desktop._request_paused({"requestId": "r3", "resourceType": "Document", "frameId": "main",
                                 "request": {"url": "https://en.wikipedia.org/wiki/Boston", "method": "GET"}})
    clicker.side_effect = press
    assert "did not finish within 20 seconds" in desktop.click(512, 400)
    assert desktop.visited == []


@pytest.mark.parametrize("target, reason", [
    ({"kind": "link", "target": "_blank", "download": False}, "new tab"),
    ({"kind": "link", "target": "Named-Window", "download": False}, "new tab"),
    ({"kind": "form", "target": "_blank"}, "new tab"),
    ({"kind": "link", "target": "", "download": True}, "Download"),
    ({"kind": "frame"}, "frames"),
    ({"kind": "imagemap"}, "image maps"),
    ({"kind": "surprise"}, "could not be checked"),
    (None, "could not be checked"),
])
def test_risky_click_targets_are_refused_before_the_button_is_pressed(target, reason):
    page, session = fake_browser(target=target)
    desktop, pointer, clicker = desktop_for(page, session)
    with pytest.raises(ActionDenied, match=reason):
        desktop.click(512, 400)
    pointer.assert_not_called()
    clicker.assert_not_called()


@pytest.mark.parametrize("target", [LINK, {"kind": "link", "target": "_self", "download": False},
                                    {"kind": "link", "target": "_TOP", "download": False},
                                    {"kind": "form", "target": ""}, {"kind": "other"}, {"kind": "none"}])
def test_same_tab_targets_are_accepted(target):
    assert click_target_problem(target) is None


@pytest.mark.parametrize("x, y", [(512, 90), (512, 740), (2000, 400)])
def test_click_outside_page_area_never_reaches_the_desktop(x, y):
    page, session = fake_browser()
    desktop, pointer, clicker = desktop_for(page, session)
    with pytest.raises(ActionDenied, match="outside the browser page area|integer"):
        desktop.click(x, y)
    pointer.assert_not_called()
    clicker.assert_not_called()


@pytest.mark.parametrize("change", [
    {"window": {**EXPECTED_WINDOW, "top": 60}},
    {"window": {**EXPECTED_WINDOW, "windowState": "maximized"}},
    {"viewport": (1024, 640)},
])
def test_unexpected_browser_geometry_refuses_clicks(change):
    page, session = fake_browser(**change)
    desktop, pointer, clicker = desktop_for(page, session)
    assert desktop.click_area() is None
    with pytest.raises(ActionDenied, match="unknown"):
        desktop.click(512, 400)
    clicker.assert_not_called()


def test_click_requires_grant():
    page, session = fake_browser()
    grant = TaskGrant("no-click", frozenset({"navigate", "scroll"}), frozenset({"en.wikipedia.org"}))
    clicker = Mock()
    desktop = E2BDesktop(page, session, grant, pointer_provider=Mock(), click_provider=clicker)
    with pytest.raises(ActionDenied, match="not permitted"):
        desktop.click(512, 400)
    clicker.assert_not_called()


def test_new_tab_that_opens_anyway_is_closed_and_recorded():
    page, session = fake_browser()
    desktop, _, _ = desktop_for(page, session)
    event, handler = page.context.on.call_args.args
    assert event == "page"
    popup = Mock(url="https://en.wikipedia.org/wiki/Boston")
    handler(popup)
    popup.close.assert_called_once_with()
    assert desktop.closed_pages == ["https://en.wikipedia.org/wiki/Boston"]


# --- model tool ----------------------------------------------------------------------

def tool_response(name, args):
    return NS(choices=[NS(finish_reason="tool_calls", message=NS(tool_calls=[
        NS(type="function", function=NS(name=name, arguments=json.dumps(args)))]))])


def png(width, height):
    output = BytesIO()
    Image.new("RGB", (width, height), "white").save(output, format="PNG")
    return Screenshot(output.getvalue())


def test_click_tool_is_offered_and_accepted_only_when_enabled():
    client = Mock()
    client.chat.completions.create.return_value = tool_response("click", {"x": 10, "y": 20, "reason": "link"})
    with pytest.raises(ValueError, match="unknown tool"):
        GroqVision(client=client).decide(png(4, 4), [Entry("goal", "g")])
    proposal = GroqVision(client=client, allow_click=True).decide(png(4, 4), [Entry("goal", "g")])
    assert proposal.call == ToolCall("click", {"x": 10, "y": 20})
    offered = {t["function"]["name"] for t in client.chat.completions.create.call_args.kwargs["tools"]}
    assert offered == {"scroll", "finish", "click"}


# --- loop ----------------------------------------------------------------------------

class Script:
    def __init__(self, calls):
        self.calls = iter(calls)
        self.seen = []

    def decide(self, screenshot, transcript):
        self.seen.append((screenshot.size, list(transcript)))
        return next(self.calls)


class ClickDesktop:
    def __init__(self, refuse=None):
        self.clicks = []
        self.refuse = refuse

    def capture_screen(self):
        return png(1024, 768)

    def click_area(self):
        return PAGE_AREA

    def click(self, x, y):
        if self.refuse:
            raise ActionDenied(self.refuse)
        self.clicks.append((x, y))
        return "The click opened https://en.wikipedia.org/wiki/Massachusetts."


def test_loop_maps_click_from_downscaled_image_to_screen_pixels():
    desktop = ClickDesktop()
    model = Script([ToolCall("click", {"x": 384, "y": 300}), ToolCall("finish", {"answer": "done"})])
    result = run_vision_agent("Open the link", GRANT, desktop, model, max_image_width=768)
    assert model.seen[0][0] == (768, 576)
    # 768/1024 = 0.75, so (384, 300) in the image is (512, 400) on the screen.
    assert desktop.clicks == [(512, 400)]
    assert result.status == "finished"
    action = json.loads([e.text for e in result.transcript if e.kind == "action"][0])
    assert action["args"] == {"x": 384, "y": 300} and action["screen"] == {"x": 512, "y": 400}
    assert any("click opened" in e.text for e in result.transcript if e.kind == "observation")


def test_loop_denies_click_outside_page_area_without_clicking():
    desktop = ClickDesktop()
    model = Script([ToolCall("click", {"x": 512, "y": 60}), ToolCall("finish", {"answer": "done"})])
    result = run_vision_agent("Open the link", GRANT, desktop, model)
    assert desktop.clicks == []
    assert "outside the browser page area" in result.denied[0][1].reason
    assert result.status == "finished"


def test_loop_turns_desktop_refusal_into_denial_the_model_sees():
    desktop = ClickDesktop(refuse="That link or form would open a new tab or window, which is not permitted.")
    model = Script([ToolCall("click", {"x": 512, "y": 400}), ToolCall("finish", {"answer": "done"})])
    result = run_vision_agent("Open the link", GRANT, desktop, model)
    assert "new tab" in result.denied[0][1].reason
    assert ("denied", result.denied[0][1].reason) in [(e.kind, e.text) for e in model.seen[1][1]]


def test_grid_keeps_image_size_and_is_announced_only_when_enabled():
    from crescendo_agent.vision import add_grid
    plain = png(768, 576)
    gridded = add_grid(plain)
    assert gridded.size == plain.size and gridded.png != plain.png
    for grid in (False, True):
        model = Script([ToolCall("finish", {"answer": "done"})])
        run_vision_agent("g", GRANT, ClickDesktop(), model, grid=grid)
        observation = [e.text for e in model.seen[0][1] if e.kind == "observation"][0]
        assert ("coordinate grid" in observation) is grid


def test_link_tool_is_offered_and_accepted_only_in_link_mode():
    client = Mock()
    client.chat.completions.create.return_value = tool_response(
        "click_link", {"target_id": 17, "reason": "Massachusetts"})
    for settings in ({}, {"allow_click": True}):
        with pytest.raises(ValueError, match="unknown tool"):
            GroqVision(client=client, **settings).decide(png(768, 576), [])
    model = GroqVision(client=client, allow_click=True, click_mode="links")
    proposal = model.decide(png(768, 576), [])
    assert proposal.call == ToolCall("click_link", {"target_id": 17})
    request = client.chat.completions.create.call_args.kwargs
    assert "untrusted visible link labels" in request["messages"][0]["content"]
    assert {t["function"]["name"] for t in request["tools"]} == {"scroll", "finish", "click_link"}


class LinkDesktop(ClickDesktop):
    def __init__(self, refuse=None):
        super().__init__(refuse)
        self.resolved = []
        self.observations = 0

    def visible_links(self):
        self.observations += 1
        return [{"id": self.observations, "label": "Massachusetts"}]

    def resolve_link(self, target_id):
        self.resolved.append(target_id)
        if target_id != self.observations:
            raise ActionDenied("Choose a link ID from the current observation.")
        return 317, 601


@pytest.mark.parametrize("image_width", [768, 1024])
def test_link_selection_resolves_to_screen_point_without_downscaling_it_twice(image_width):
    desktop = LinkDesktop()
    model = Script([ToolCall("click_link", {"target_id": 1}),
                    ToolCall("finish", {"answer": "done"})])
    result = run_vision_agent("Open link", GRANT, desktop, model, max_image_width=image_width,
                              link_grounding=True)
    # The target is around (238,451) in the 768x576 image; screen is 1024x768.
    assert desktop.clicks == [(317, 601)]
    action = json.loads(next(e.text for e in result.transcript if e.kind == "action"))
    assert action["tool"] == "click_link" and action["resolved_tool"] == "click"
    assert action["args"] == {"target_id": 1}
    assert action["screen"] == {"x": 317, "y": 601}


@pytest.mark.parametrize("args", [
    {"target_id": True}, {"target_id": "1"}, {"target_id": 1.0},
    {"target_id": 1, "x": 317}, {}, {"target_id": -1}, {"target_id": 999},
])
def test_invalid_link_selections_never_press_the_button(args):
    desktop = LinkDesktop()
    model = Script([ToolCall("click_link", args)])
    result = run_vision_agent("Open link", GRANT, desktop, model, max_steps=1, link_grounding=True)
    assert desktop.clicks == []
    assert len(result.denied) == 1


@pytest.mark.parametrize("point", [(500, 90), (500, 740), (1024, 500)])
def test_link_selection_preserves_page_area_guard(point):
    desktop = LinkDesktop()
    desktop.resolve_link = lambda target_id: point
    model = Script([ToolCall("click_link", {"target_id": 1})])
    result = run_vision_agent("Open link", GRANT, desktop, model, max_steps=1, link_grounding=True)
    assert not desktop.clicks
    assert "outside the browser page area" in result.denied[0][1].reason


def test_link_selection_cannot_enable_ungranted_click():
    grant = TaskGrant("no-click", GRANT.allowed_tools - {"click"}, GRANT.allowed_hosts)
    desktop = LinkDesktop()
    model = Script([ToolCall("click_link", {"target_id": 1})])
    result = run_vision_agent("Open link", grant, desktop, model, max_steps=1, link_grounding=True)
    assert not desktop.clicks
    assert "not permitted" in result.denied[0][1].reason


def test_old_link_id_is_denied_and_new_snapshot_reaches_the_model():
    desktop = LinkDesktop()
    model = Script([ToolCall("click_link", {"target_id": 1}),
                    ToolCall("click_link", {"target_id": 1}),
                    ToolCall("click_link", {"target_id": 3})])
    result = run_vision_agent("Open link", GRANT, desktop, model, max_steps=3, link_grounding=True)
    assert desktop.clicks == [(317, 601), (317, 601)]
    assert len(result.denied) == 1
    links = [json.loads(e.text) for e in model.seen[2][1] if e.kind == "visible_links"]
    assert [items[0]["id"] for items in links] == [1, 2, 3]


def test_link_selection_keeps_adapter_target_refusals():
    desktop = LinkDesktop(refuse="Download links are not permitted.")
    model = Script([ToolCall("click_link", {"target_id": 1})])
    result = run_vision_agent("Open link", GRANT, desktop, model, max_steps=1, link_grounding=True)
    assert not desktop.clicks
    assert "Download" in result.denied[0][1].reason


def test_link_selection_requires_explicit_loop_opt_in():
    desktop = LinkDesktop()
    model = Script([ToolCall("click_link", {"target_id": 1})])
    result = run_vision_agent("Open link", GRANT, desktop, model, max_steps=1)
    assert not desktop.clicks and not desktop.resolved
    assert "not enabled" in result.denied[0][1].reason


def test_model_receives_only_the_latest_link_list_but_keeps_prior_actions():
    client = Mock()
    client.chat.completions.create.return_value = tool_response("finish", {"answer": "done"})
    transcript = [Entry("goal", "g"), Entry("visible_links", '[{"id": 1, "label": "old"}]'),
                  Entry("action", "prior click"), Entry("visible_links", '[{"id": 2, "label": "new"}]')]
    GroqVision(client=client, allow_click=True, click_mode="links").decide(png(10, 10), transcript)
    content = client.chat.completions.create.call_args.kwargs["messages"][1]["content"][0]["text"]
    entries = json.loads(content)
    assert [e["text"] for e in entries if e["kind"] == "visible_links"] == [transcript[-1].text]
    assert {"kind": "action", "text": "prior click"} in entries
    assert len(transcript) == 4  # The complete audit trace remains intact.


@pytest.mark.parametrize("missing, reason", [
    ("read_visible_links", "read_visible_links.*not permitted"),
    ("click", "Click is not permitted"),
])
def test_visible_links_requires_read_and_click_permissions_before_inspecting_page(missing, reason):
    page, session = fake_browser()
    grant = TaskGrant("missing-permission", GRANT.allowed_tools - {missing}, GRANT.allowed_hosts)
    desktop = E2BDesktop(page, session, grant)
    desktop._link_snapshot = old = Mock()
    desktop._visible_link_ids = {1}
    with pytest.raises(ActionDenied, match=reason):
        desktop.visible_links()
    old.dispose.assert_called_once_with()
    page.evaluate_handle.assert_not_called()
    page.evaluate.assert_not_called()
    with pytest.raises(ActionDenied, match="current visible_links"):
        desktop.resolve_link(1)


def test_visible_links_reads_metadata_without_screenshot_permission_or_capture():
    page, session = fake_browser()
    grant = TaskGrant("links-only", frozenset({"read_visible_links", "click"}), GRANT.allowed_hosts)
    screenshot = Mock()
    desktop = E2BDesktop(page, session, grant, screenshot_provider=screenshot)
    page.evaluate_handle.return_value.evaluate.return_value = [{"id": 1, "label": "Massachusetts"}]
    assert desktop.visible_links() == [{"id": 1, "label": "Massachusetts"}]
    screenshot.assert_not_called()


def test_adapter_expires_previous_snapshot_and_rejects_old_or_changed_targets():
    page, session = fake_browser()
    desktop, pointer, clicker = desktop_for(page, session)
    first, second = Mock(), Mock()
    page.evaluate_handle.side_effect = [first, second]
    first.evaluate.return_value = [{"id": 1, "label": "Massachusetts"}]
    second.evaluate.side_effect = [[{"id": 2, "label": "Massachusetts"}], None]
    assert desktop.visible_links() == [{"id": 1, "label": "Massachusetts"}]
    desktop.visible_links()
    first.dispose.assert_called_once_with()
    with pytest.raises(ActionDenied, match="current visible_links"):
        desktop.resolve_link(1)
    with pytest.raises(ActionDenied, match="selected link changed"):
        desktop.resolve_link(2)
    pointer.assert_not_called()
    clicker.assert_not_called()


def test_unknown_geometry_clears_previous_link_ids_without_inspecting_the_page():
    page, session = fake_browser()
    desktop, _, _ = desktop_for(page, session)
    desktop._link_snapshot = old = Mock()
    desktop._visible_link_ids = {1}
    desktop.click_area = lambda: None
    assert desktop.visible_links() == []
    old.dispose.assert_called_once_with()
    page.evaluate_handle.assert_not_called()
    with pytest.raises(ActionDenied):
        desktop.resolve_link(1)
