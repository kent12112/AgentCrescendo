"""Open browsing in the model and the vision loop (W1X-F03): type_text and navigate.

The loop turns a field ID into a checked screen point exactly as click_link does,
then the gateway and the desktop adapter each check again. Fakes replace E2B.
"""
import json
from unittest.mock import Mock

import pytest

from crescendo_agent.desktop import ActionDenied
from crescendo_agent.e2b_desktop import PAGE_AREA
from crescendo_agent.vision import GroqVision
from crescendo_agent.vision_loop import run_vision_agent
from crescendo_security.policy import TaskGrant, ToolCall

from test_click import Script, png, tool_response

GRANT = TaskGrant("open", frozenset({"screenshot", "scroll", "click", "read_visible_links",
                                     "type_text", "navigate", "finish"}), frozenset(), public_web=True)
SEARCH = {"target_id": 2, "text": "Boston Common", "submit": True}


class BrowseDesktop:
    """Shows one link (ID 1) and one search field (ID 2) on every step."""

    def __init__(self, refuse=None):
        self.typed, self.navigated, self.refuse = [], [], refuse

    def capture_screen(self):
        return png(1024, 768)

    def click_area(self):
        return PAGE_AREA

    def visible_links(self):
        return [{"id": 1, "label": "Massachusetts"},
                {"id": 2, "label": "Search Wikipedia", "kind": "field"}]

    def resolve_link(self, target_id):
        if target_id != 1:
            raise ActionDenied("Choose a link ID from the current visible_links observation.")
        return 317, 601

    def resolve_field(self, target_id):
        if target_id != 2:
            raise ActionDenied("Choose a field ID from the current visible_links observation.")
        return 640, 160

    def type_text(self, x, y, text, submit):
        if self.refuse:
            raise ActionDenied(self.refuse)
        self.typed.append((x, y, text, submit))
        return "The submission opened https://en.wikipedia.org/w/index.php?search=Boston+Common."

    def navigate_and_report(self, url):
        from crescendo_security.policy import authorize
        decision = authorize(GRANT, ToolCall("navigate", {"url": url}))
        if not decision.allowed:
            raise ValueError(decision.reason)
        self.navigated.append(url)
        return f"The tab now shows {url}."


def run(calls, desktop=None, grant=GRANT, **kwargs):
    desktop = desktop or BrowseDesktop()
    model = Script(calls + [ToolCall("finish", {"answer": "done"})])
    result = run_vision_agent("Find it", grant, desktop, model, link_grounding=True, **kwargs)
    return result, desktop, model


def test_type_text_resolves_the_field_and_types_there():
    result, desktop, model = run([ToolCall("type_text", SEARCH)])
    assert desktop.typed == [(640, 160, "Boston Common", True)]
    action = json.loads(next(e.text for e in result.transcript if e.kind == "action"))
    assert action["args"] == SEARCH
    assert action["screen"] == {"x": 640, "y": 160, "text": "Boston Common", "submit": True}
    outcomes = [e.text for e in model.seen[1][1] if e.text.startswith("Authorized")]
    assert outcomes == ["Authorized type_text completed. The submission opened "
                        "https://en.wikipedia.org/w/index.php?search=Boston+Common."]
    assert result.status == "finished"


def test_fields_are_listed_for_a_typing_only_grant():
    grant = TaskGrant("t", GRANT.allowed_tools - {"click"}, frozenset(), public_web=True)
    result, desktop, model = run([ToolCall("type_text", SEARCH)], grant=grant)
    assert desktop.typed and any(e.kind == "visible_links" for e in model.seen[0][1])


@pytest.mark.parametrize("args", [
    {"target_id": 1, "text": "x", "submit": True},       # a link ID, not a field
    {"target_id": True, "text": "x", "submit": True},
    {"target_id": 2, "text": "x"},                       # missing submit
    {"target_id": 2, "text": "x", "submit": True, "x": 1},
    {"target_id": 2, "text": "a\nb", "submit": True},     # gateway: not one line
    {"target_id": 2, "text": "x", "submit": "yes"},
])
def test_invalid_typing_never_reaches_the_keyboard(args):
    result, desktop, _ = run([ToolCall("type_text", args)])
    assert desktop.typed == [] and len(result.denied) == 1


def test_field_point_outside_the_page_area_is_refused():
    desktop = BrowseDesktop()
    desktop.resolve_field = lambda target_id: (640, 60)  # the address bar row
    result, _, _ = run([ToolCall("type_text", SEARCH)], desktop=desktop)
    assert desktop.typed == [] and "outside" in result.denied[0][1].reason


def test_typing_requires_grant_and_loop_opt_in():
    grant = TaskGrant("n", GRANT.allowed_tools - {"type_text"}, frozenset(), public_web=True)
    result, desktop, _ = run([ToolCall("type_text", SEARCH)], grant=grant)
    assert desktop.typed == [] and "not permitted" in result.denied[0][1].reason
    desktop = BrowseDesktop()
    model = Script([ToolCall("type_text", SEARCH), ToolCall("finish", {"answer": "x"})])
    result = run_vision_agent("Find it", GRANT, desktop, model)  # link_grounding off
    assert desktop.typed == [] and "not enabled" in result.denied[0][1].reason


def test_adapter_refusal_reaches_the_model_as_a_denial():
    desktop = BrowseDesktop(refuse="The text field did not receive keyboard focus, so nothing was typed.")
    result, _, model = run([ToolCall("type_text", SEARCH)], desktop=desktop)
    assert "keyboard focus" in result.denied[0][1].reason
    assert any(e.kind == "denied" and "keyboard focus" in e.text for e in model.seen[1][1])


def test_navigate_opens_public_sites_and_refuses_internal_ones():
    result, desktop, model = run([ToolCall("navigate", {"url": "https://www.boston.gov/"}),
                                  ToolCall("navigate", {"url": "https://169.254.169.254/"})])
    assert desktop.navigated == ["https://www.boston.gov/"]
    assert "IP addresses" in result.denied[0][1].reason
    assert any(e.text == "Authorized navigate completed. The tab now shows https://www.boston.gov/."
               for e in model.seen[1][1])


def test_navigate_needs_the_tool():
    grant = TaskGrant("n", GRANT.allowed_tools - {"navigate"}, frozenset(), public_web=True)
    result, desktop, _ = run([ToolCall("navigate", {"url": "https://www.boston.gov/"})], grant=grant)
    assert desktop.navigated == [] and "not permitted" in result.denied[0][1].reason


# --- model tool offering and parsing -------------------------------------------------

def test_typing_and_navigate_tools_are_offered_only_when_enabled():
    client = Mock()
    client.chat.completions.create.return_value = tool_response("type_text", {**SEARCH, "reason": "search box"})
    with pytest.raises(ValueError, match="unknown tool"):
        GroqVision(client=client, allow_click=True, click_mode="links").decide(png(8, 8), [])
    model = GroqVision(client=client, allow_click=True, click_mode="links", allow_typing=True)
    assert model.decide(png(8, 8), []).call == ToolCall("type_text", SEARCH)
    request = client.chat.completions.create.call_args.kwargs
    assert {t["function"]["name"] for t in request["tools"]} == {"scroll", "finish", "click_link", "type_text"}
    assert "kind 'field'" in request["messages"][0]["content"]

    client.chat.completions.create.return_value = tool_response(
        "navigate", {"url": "https://www.boston.gov/", "reason": "named site"})
    with pytest.raises(ValueError, match="unknown tool"):
        model.decide(png(8, 8), [])
    navigating = GroqVision(client=client, allow_navigate=True)
    assert navigating.decide(png(8, 8), []).call == ToolCall("navigate", {"url": "https://www.boston.gov/"})


def test_typing_needs_link_mode_for_field_ids():
    with pytest.raises(ValueError, match="allow_typing"):
        GroqVision(client=Mock(), allow_typing=True)
    with pytest.raises(ValueError, match="allow_typing"):
        GroqVision(client=Mock(), allow_click=True, allow_typing=True)  # coordinates mode
