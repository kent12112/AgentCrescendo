# Import pytest: provides test discovery, fixtures, parametrization, and exception assertions.
import pytest

# Import from crescendo_security.policy: TaskGrant (holds the task identity and immutable tool/host
# allowlists); ToolCall (holds an untrusted proposed tool name and argument mapping); authorize
# (checks task grants and argument bounds before a proposed tool can execute).
from crescendo_security.policy import TaskGrant, ToolCall, authorize

# Set GRANT to TaskGrant(task_id='task-1', allowed_tools=frozenset({'navigate', 'finish'}),
# allowed_hosts=frozenset({'en.wikipedia.org'})).
GRANT = TaskGrant(
    # Set task_id to ('task-1',).
    task_id="task-1",
    # Set allowed_tools to (frozenset({'navigate', 'finish'}),).
    allowed_tools=frozenset({"navigate", "finish"}),
    # Set allowed_hosts to (frozenset({'en.wikipedia.org'}),).
    allowed_hosts=frozenset({"en.wikipedia.org"}),
)


@pytest.mark.parametrize("tools, allowed", [
    ({"screenshot"}, False),
    ({"click"}, False),
    ({"read_visible_links"}, True),
])
def test_read_visible_links_requires_explicit_permission(tools, allowed):
    grant = TaskGrant("links", frozenset(tools), frozenset())
    assert authorize(grant, ToolCall("read_visible_links")).allowed is allowed


def test_read_visible_links_refuses_arguments():
    grant = TaskGrant("links", frozenset({"read_visible_links"}), frozenset())
    decision = authorize(grant, ToolCall("read_visible_links", {"url": "https://example.com"}))
    assert not decision.allowed and "no arguments" in decision.reason


# Define navigate with parameters url.
def navigate(url):
    # Return ToolCall('navigate', {'url': url}).
    return ToolCall("navigate", {"url": url})


# Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("call", [
    # Open the requested destination through the desktop adapter; inputs:
    # 'https://en.wikipedia.org/wiki/Boston'.
    navigate("https://en.wikipedia.org/wiki/Boston"),
    # Open the requested destination through the desktop adapter; inputs:
    # 'https://EN.WIKIPEDIA.ORG/wiki/Boston'.
    navigate("https://EN.WIKIPEDIA.ORG/wiki/Boston"),  # hostnames are case-insensitive
    # Call ToolCall with the arguments shown.
    ToolCall("finish", {"answer": "done", "sources": []}),
])
# Define test_permitted_calls_are_allowed with parameters call.
def test_permitted_calls_are_allowed(call):
    # Assert that authorize(GRANT, call).allowed. If false, this check fails with AssertionError.
    assert authorize(GRANT, call).allowed


# Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("call", [
    # Call ToolCall with the arguments shown.
    ToolCall("type_text", {"text": "hello"}),                 # tool not granted
    # Call ToolCall with the arguments shown.
    ToolCall("navigate", {}),                                 # missing url
    # Call ToolCall with the arguments shown.
    ToolCall("navigate", {"url": 42}),                        # url is not a string
    # Open the requested destination through the desktop adapter; inputs:
    # 'http://en.wikipedia.org/wiki/Boston'.
    navigate("http://en.wikipedia.org/wiki/Boston"),          # not https
    # Open the requested destination through the desktop adapter; inputs: 'file:///etc/passwd'.
    navigate("file:///etc/passwd"),                           # local file scheme
    # Open the requested destination through the desktop adapter; inputs: 'https://evil.com/'.
    navigate("https://evil.com/"),                            # host not granted
    # Open the requested destination through the desktop adapter; inputs:
    # 'https://en.wikipedia.org.evil.com/'.
    navigate("https://en.wikipedia.org.evil.com/"),           # suffix trick
    # Open the requested destination through the desktop adapter; inputs:
    # 'https://en.wikipedia.org@evil.com/'.
    navigate("https://en.wikipedia.org@evil.com/"),           # userinfo trick: host is evil.com
    # Open the requested destination through the desktop adapter; inputs:
    # 'https://127.0.0.1:8000/runs'.
    navigate("https://127.0.0.1:8000/runs"),                  # our own backend API
    # Open the requested destination through the desktop adapter; inputs: 'https://localhost/'.
    navigate("https://localhost/"),
    # Open the requested destination through the desktop adapter; inputs:
    # 'https://169.254.169.254/latest/meta-data/'.
    navigate("https://169.254.169.254/latest/meta-data/"),    # cloud metadata service
    # Open the requested destination through the desktop adapter; inputs:
    # 'https://en.wikipedia.org:8443/'.
    navigate("https://en.wikipedia.org:8443/"),               # explicit port
    # Open the requested destination through the desktop adapter; inputs:
    # 'https://en.wikipedia.org:notaport/'.
    navigate("https://en.wikipedia.org:notaport/"),           # malformed port must not crash
    # Open the requested destination through the desktop adapter; inputs: 'https://[invalid/'.
    navigate("https://[invalid/"),                          # unmatched IPv6 bracket
    # Open the requested destination through the desktop adapter; inputs: 'https://[not-an-ip]/'.
    navigate("https://[not-an-ip]/"),                       # invalid bracketed address
    # Open the requested destination through the desktop adapter; inputs:
    # 'https://en.wikipedia.org／evil.com/'.
    navigate("https://en.wikipedia.org\uff0fevil.com/"),       # unsafe Unicode host delimiter
])
# Define test_everything_else_is_denied_with_a_reason with parameters call.
def test_everything_else_is_denied_with_a_reason(call):
    # Set decision to authorize(GRANT, call).
    decision = authorize(GRANT, call)
    # Assert that not (decision.allowed). If false, this check fails with AssertionError.
    assert not decision.allowed
    # Assert that decision.reason. If false, this check fails with AssertionError.
    assert decision.reason


# --- click (W1X-F01) ---------------------------------------------------------------

from crescendo_security.policy import ScreenArea

CLICK_GRANT = TaskGrant("task-click", frozenset({"click"}), frozenset())
AREA = ScreenArea(left=0, top=114, right=1024, bottom=700)


def click(x, y):
    return ToolCall("click", {"x": x, "y": y})


@pytest.mark.parametrize("call", [click(0, 114), click(512, 400), click(1023, 699)])
def test_click_inside_page_area_is_allowed(call):
    assert authorize(CLICK_GRANT, call, click_area=AREA).allowed


@pytest.mark.parametrize("call, reason", [
    (click(512, 90), "outside"),       # Chrome address bar
    (click(512, 20), "outside"),       # desktop taskbar
    (click(512, 740), "outside"),      # dock at the bottom edge
    (click(1024, 400), "outside"),     # right/bottom edges are exclusive
    (click(512, 700), "outside"),
    (click(True, 400), "integer"),     # bool is not a coordinate
    (click(512.0, 400), "integer"),
    (click("512", 400), "integer"),
    (click(-1, 400), "integer"),
    (click(9000, 400), "integer"),
    (ToolCall("click", {"x": 512}), "integer"),
    (ToolCall("click", {"x": 512, "y": 400, "button": "right"}), "integer"),
])
def test_click_outside_area_or_malformed_is_denied(call, reason):
    decision = authorize(CLICK_GRANT, call, click_area=AREA)
    assert not decision.allowed
    assert reason in decision.reason


def test_click_without_known_page_area_is_denied():
    decision = authorize(CLICK_GRANT, click(512, 400))
    assert not decision.allowed and "unknown" in decision.reason


def test_click_requires_grant_even_inside_area():
    assert not authorize(GRANT, click(512, 400), click_area=AREA).allowed
