import pytest

from crescendo_security.policy import TaskGrant, ToolCall, authorize

GRANT = TaskGrant(
    task_id="task-1",
    allowed_tools=frozenset({"navigate", "finish"}),
    allowed_hosts=frozenset({"en.wikipedia.org"}),
)


def navigate(url):
    return ToolCall("navigate", {"url": url})


@pytest.mark.parametrize("call", [
    navigate("https://en.wikipedia.org/wiki/Boston"),
    navigate("https://EN.WIKIPEDIA.ORG/wiki/Boston"),  # hostnames are case-insensitive
    ToolCall("finish", {"answer": "done", "sources": []}),
])
def test_permitted_calls_are_allowed(call):
    assert authorize(GRANT, call).allowed


@pytest.mark.parametrize("call", [
    ToolCall("type_text", {"text": "hello"}),                 # tool not granted
    ToolCall("navigate", {}),                                 # missing url
    ToolCall("navigate", {"url": 42}),                        # url is not a string
    navigate("http://en.wikipedia.org/wiki/Boston"),          # not https
    navigate("file:///etc/passwd"),                           # local file scheme
    navigate("https://evil.com/"),                            # host not granted
    navigate("https://en.wikipedia.org.evil.com/"),           # suffix trick
    navigate("https://en.wikipedia.org@evil.com/"),           # userinfo trick: host is evil.com
    navigate("https://127.0.0.1:8000/runs"),                  # our own backend API
    navigate("https://localhost/"),
    navigate("https://169.254.169.254/latest/meta-data/"),    # cloud metadata service
    navigate("https://en.wikipedia.org:8443/"),               # explicit port
    navigate("https://en.wikipedia.org:notaport/"),           # malformed port must not crash
    navigate("https://[invalid/"),                          # unmatched IPv6 bracket
    navigate("https://[not-an-ip]/"),                       # invalid bracketed address
    navigate("https://en.wikipedia.org\uff0fevil.com/"),       # unsafe Unicode host delimiter
])
def test_everything_else_is_denied_with_a_reason(call):
    decision = authorize(GRANT, call)
    assert not decision.allowed
    assert decision.reason
