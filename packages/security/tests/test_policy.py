# Learn: Import pytest: provides test discovery, fixtures, parametrization, and exception assertions.
import pytest

# Learn: From crescendo_security.policy, import TaskGrant (holds the task identity and immutable tool/host
# allowlists); ToolCall (holds an untrusted proposed tool name and argument mapping); authorize (checks task
# grants and argument bounds before a proposed tool can execute).
from crescendo_security.policy import TaskGrant, ToolCall, authorize

# Learn: Set GRANT to TaskGrant(task_id='task-1', allowed_tools=frozenset({'navigate', 'finish'}),
# allowed_hosts=frozenset({'en.wikipedia.org'})).
GRANT = TaskGrant(
    # Learn: Pass keyword task_id = 'task-1'.
    task_id="task-1",
    # Learn: Pass keyword allowed_tools = frozenset({'navigate', 'finish'}).
    allowed_tools=frozenset({"navigate", "finish"}),
    # Learn: Pass keyword allowed_hosts = frozenset({'en.wikipedia.org'}).
    allowed_hosts=frozenset({"en.wikipedia.org"}),
# Learn: Close the argument list for TaskGrant; the grouped expression remains one call.
)


# Learn: Define navigate(url). The body runs when called, not when defined.
def navigate(url):
    # Learn: Return ToolCall('navigate', {'url': url}) to the caller and stop this function.
    return ToolCall("navigate", {"url": url})


# Learn: Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("call", [
    # Learn: Open the requested destination through the desktop adapter; inputs:
    # 'https://en.wikipedia.org/wiki/Boston'.
    navigate("https://en.wikipedia.org/wiki/Boston"),
    # Learn: Open the requested destination through the desktop adapter; inputs:
    # 'https://EN.WIKIPEDIA.ORG/wiki/Boston'.
    navigate("https://EN.WIKIPEDIA.ORG/wiki/Boston"),  # hostnames are case-insensitive
    # Learn: Call ToolCall with the arguments shown.
    ToolCall("finish", {"answer": "done", "sources": []}),
# Learn: Close this list literal; delimiters group the values into one object.
])
# Learn: Test permitted calls are allowed. pytest supplies named fixtures and checks assertions below.
def test_permitted_calls_are_allowed(call):
    # Learn: Assert that authorize(GRANT, call).allowed. If false, this check fails with AssertionError.
    assert authorize(GRANT, call).allowed


# Learn: Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("call", [
    # Learn: Call ToolCall with the arguments shown.
    ToolCall("type_text", {"text": "hello"}),                 # tool not granted
    # Learn: Call ToolCall with the arguments shown.
    ToolCall("navigate", {}),                                 # missing url
    # Learn: Call ToolCall with the arguments shown.
    ToolCall("navigate", {"url": 42}),                        # url is not a string
    # Learn: Open the requested destination through the desktop adapter; inputs:
    # 'http://en.wikipedia.org/wiki/Boston'.
    navigate("http://en.wikipedia.org/wiki/Boston"),          # not https
    # Learn: Open the requested destination through the desktop adapter; inputs: 'file:///etc/passwd'.
    navigate("file:///etc/passwd"),                           # local file scheme
    # Learn: Open the requested destination through the desktop adapter; inputs: 'https://evil.com/'.
    navigate("https://evil.com/"),                            # host not granted
    # Learn: Open the requested destination through the desktop adapter; inputs:
    # 'https://en.wikipedia.org.evil.com/'.
    navigate("https://en.wikipedia.org.evil.com/"),           # suffix trick
    # Learn: Open the requested destination through the desktop adapter; inputs:
    # 'https://en.wikipedia.org@evil.com/'.
    navigate("https://en.wikipedia.org@evil.com/"),           # userinfo trick: host is evil.com
    # Learn: Open the requested destination through the desktop adapter; inputs:
    # 'https://127.0.0.1:8000/runs'.
    navigate("https://127.0.0.1:8000/runs"),                  # our own backend API
    # Learn: Open the requested destination through the desktop adapter; inputs: 'https://localhost/'.
    navigate("https://localhost/"),
    # Learn: Open the requested destination through the desktop adapter; inputs:
    # 'https://169.254.169.254/latest/meta-data/'.
    navigate("https://169.254.169.254/latest/meta-data/"),    # cloud metadata service
    # Learn: Open the requested destination through the desktop adapter; inputs:
    # 'https://en.wikipedia.org:8443/'.
    navigate("https://en.wikipedia.org:8443/"),               # explicit port
    # Learn: Open the requested destination through the desktop adapter; inputs:
    # 'https://en.wikipedia.org:notaport/'.
    navigate("https://en.wikipedia.org:notaport/"),           # malformed port must not crash
    # Learn: Open the requested destination through the desktop adapter; inputs: 'https://[invalid/'.
    navigate("https://[invalid/"),                          # unmatched IPv6 bracket
    # Learn: Open the requested destination through the desktop adapter; inputs: 'https://[not-an-ip]/'.
    navigate("https://[not-an-ip]/"),                       # invalid bracketed address
    # Learn: Open the requested destination through the desktop adapter; inputs:
    # 'https://en.wikipedia.org／evil.com/'.
    navigate("https://en.wikipedia.org\uff0fevil.com/"),       # unsafe Unicode host delimiter
# Learn: Close this list literal; delimiters group the values into one object.
])
# Learn: Test everything else is denied with a reason. pytest supplies named fixtures and checks assertions
# below.
def test_everything_else_is_denied_with_a_reason(call):
    # Learn: Set decision to authorize(GRANT, call); the gateway allow/deny result and its explanation.
    # Check the proposed action against the fixed task grant before any effect.
    decision = authorize(GRANT, call)
    # Learn: Assert that not (decision.allowed). If false, this check fails with AssertionError.
    assert not decision.allowed
    # Learn: Assert that decision.reason. If false, this check fails with AssertionError.
    assert decision.reason
