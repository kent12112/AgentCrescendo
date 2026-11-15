# Learn: From http.client, import RemoteDisconnected (a dependency used below).
from http.client import RemoteDisconnected
# Learn: From unittest.mock, import Mock (supplies configurable fake attributes and call recording);
# mock_open (a dependency used below).
from unittest.mock import Mock, mock_open

# Learn: Import pytest: provides test discovery, fixtures, parametrization, and exception assertions.
import pytest

# Learn: From crescendo_agent.e2b_desktop, import E2BDesktop (a dependency used below); RELAY (the fixed
# remote CDP TCP relay program); START_BROWSER (the fixed remote Chrome launch/readiness program);
# WAIT_READY (the fixed remote relay-readiness check); open_e2b_desktop (owns restricted sandbox setup,
# browser connection, and cleanup).
from crescendo_agent.e2b_desktop import E2BDesktop, RELAY, START_BROWSER, WAIT_READY, open_e2b_desktop
# Learn: From crescendo_security.policy, import TaskGrant (holds the task identity and immutable tool/host
# allowlists).
from crescendo_security.policy import TaskGrant

# Learn: Set GRANT to TaskGrant('test', frozenset({'navigate', 'finish'}), frozenset({'en.wikipedia.org'})).
GRANT = TaskGrant("test", frozenset({"navigate", "finish"}), frozenset({"en.wikipedia.org"}))


# Learn: Test blocked redirect becomes observation and agent chooses another source. pytest supplies named
# fixtures and checks assertions below.
def test_blocked_redirect_becomes_observation_and_agent_chooses_another_source():
    # Learn: From playwright.sync_api, import Error (the SDK browser exception used to distinguish policy
    # navigation failures).
    from playwright.sync_api import Error
    # Learn: From crescendo_agent.loop, import run_agent (runs the bounded text observation/action loop).
    from crescendo_agent.loop import run_agent
    # Learn: From crescendo_agent.model, import ScriptedModel (a dependency used below).
    from crescendo_agent.model import ScriptedModel
    # Learn: From crescendo_security.policy, import ToolCall (holds an untrusted proposed tool name and
    # argument mapping).
    from crescendo_security.policy import ToolCall

    # Learn: Set (page, session) to the tuple (Mock(), Mock()) (positional values).
    page, session = Mock(), Mock()
    # Learn: Set page.url to 'about:blank'; the destination or current page address.
    page.url = "about:blank"
    # Learn: Set session.send.return_value to a new dictionary with keys 'frameTree'.
    session.send.return_value = {"frameTree": {"frame": {"id": "main"}}}
    # Learn: Set desktop to E2BDesktop(page, session, GRANT).
    desktop = E2BDesktop(page, session, GRANT)
    # Learn: Set first to 'https://en.wikipedia.org/redirect'.
    first = "https://en.wikipedia.org/redirect"
    # Learn: Set second to 'https://en.wikipedia.org/wiki/Boston'.
    second = "https://en.wikipedia.org/wiki/Boston"

    # Learn: Define goto(url). The body runs when called, not when defined.
    def goto(url, **kwargs):
        # Learn: Take this branch only if url equals first.
        if url == first:
            # Learn: Call desktop._request_paused with the arguments shown.
            desktop._request_paused({
                # Learn: Define this named mapping field: "requestId": "redirect", "frameId": "main",
                # "resourceType": "Document",. The key selects the schema/configuration value.
                "requestId": "redirect", "frameId": "main", "resourceType": "Document",
                # Learn: Define this named mapping field: "request": {"url": "https://evil.example/",
                # "method": "GET"},. The key selects the schema/configuration value.
                "request": {"url": "https://evil.example/", "method": "GET"},
            # Learn: Close this dict literal; delimiters group the values into one object.
            })
            # Learn: Raise Error('net::ERR_BLOCKED_BY_CLIENT') to stop the normal path.
            raise Error("net::ERR_BLOCKED_BY_CLIENT")
        # The model gets a safe observation without reading the failed page.
        # Learn: Verify the denied/error path never invoked this fake dependency on page.locator.
        page.locator.assert_not_called()
        # Learn: Set page.url to second; the destination or current page address.
        page.url = second

    # Learn: Set page.goto.side_effect to goto.
    page.goto.side_effect = goto
    # Learn: Set page.locator.return_value.count.return_value to 0.
    page.locator.return_value.count.return_value = 0
    # Learn: Set page.locator.return_value.inner_text.return_value to 'Boston facts'.
    page.locator.return_value.inner_text.return_value = "Boston facts"
    # Learn: Set page.locator.return_value.locator.return_value.evaluate_all.return_value to a new list
    # (empty).
    page.locator.return_value.locator.return_value.evaluate_all.return_value = []
    # Learn: Set model to ScriptedModel([ToolCall('navigate', {'url': first}), ToolCall('navigate', {'url':
    # second}), ToolCall('finish', {'answer': 'Boston fa...; the provider adapter or scripted test model
    # used to propose actions.
    model = ScriptedModel([
        # Learn: Call ToolCall with the arguments shown.
        ToolCall("navigate", {"url": first}),
        # Learn: Call ToolCall with the arguments shown.
        ToolCall("navigate", {"url": second}),
        # Learn: Call ToolCall with the arguments shown.
        ToolCall("finish", {"answer": "Boston facts", "sources": [second]}),
    # Learn: Close this list literal; delimiters group the values into one object.
    ])

    # Learn: Set result to run_agent('Research Boston', GRANT, desktop, model); the operation outcome for
    # subsequent checks or reporting.
    result = run_agent("Research Boston", GRANT, desktop, model)

    # Learn: Assert that result.status equals 'finished'. If false, this check fails with AssertionError.
    assert result.status == "finished"
    # Learn: Assert that desktop.visited equals a new list containing second. If false, this check fails
    # with AssertionError.
    assert desktop.visited == [second]
    # Learn: Assert that desktop.blocked_requests equals a new list containing 'https://evil.example/'. If
    # false, this check fails with AssertionError.
    assert desktop.blocked_requests == ["https://evil.example/"]
    # Learn: Assert that any(('Navigation blocked by browser policy' in e.text for e in model.seen[1])). If
    # false, this check fails with AssertionError.
    assert any("Navigation blocked by browser policy" in e.text for e in model.seen[1])
    # Learn: Assert that any(('Boston facts' in e.text for e in model.seen[2] if e.kind == 'observation')).
    # If false, this check fails with AssertionError.
    assert any("Boston facts" in e.text for e in model.seen[2] if e.kind == "observation")
    # Learn: Assert that desktop.observe().url equals second. If false, this check fails with
    # AssertionError.
    assert desktop.observe().url == second
    # Learn: Call session.send.assert_any_call with the arguments shown.
    session.send.assert_any_call("Fetch.failRequest", {
        # Learn: Define this named mapping field: "requestId": "redirect", "errorReason":
        # "BlockedByClient",. The key selects the schema/configuration value.
        "requestId": "redirect", "errorReason": "BlockedByClient",
    # Learn: Close this dict literal; delimiters group the values into one object.
    })


# Learn: Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("kind,frame,message", [
    # Learn: Add this item to the surrounding list: (None, None, "net::ERR_BLOCKED_BY_CLIENT"),.
    (None, None, "net::ERR_BLOCKED_BY_CLIENT"),
    # Learn: Add this item to the surrounding list: ("Image", "main", "net::ERR_BLOCKED_BY_CLIENT"),.
    ("Image", "main", "net::ERR_BLOCKED_BY_CLIENT"),
    # Learn: Add this item to the surrounding list: ("Document", "iframe", "net::ERR_BLOCKED_BY_CLIENT"),.
    ("Document", "iframe", "net::ERR_BLOCKED_BY_CLIENT"),
    # Learn: Add this item to the surrounding list: ("Document", "main", "Connection failed"),.
    ("Document", "main", "Connection failed"),
# Learn: Close this list literal; delimiters group the values into one object.
])
# Learn: Test unrelated navigation errors still propagate. pytest supplies named fixtures and checks
# assertions below.
def test_unrelated_navigation_errors_still_propagate(kind, frame, message):
    # Learn: From playwright.sync_api, import Error (the SDK browser exception used to distinguish policy
    # navigation failures).
    from playwright.sync_api import Error

    # Learn: Set (page, session) to the tuple (Mock(), Mock()) (positional values).
    page, session = Mock(), Mock()
    # Learn: Set session.send.return_value to a new dictionary with keys 'frameTree'.
    session.send.return_value = {"frameTree": {"frame": {"id": "main"}}}
    # Learn: Set desktop to E2BDesktop(page, session, GRANT).
    desktop = E2BDesktop(page, session, GRANT)

    # Learn: Define goto(). The body runs when called, not when defined.
    def goto(*args, **kwargs):
        # Learn: Take this branch only if kind.
        if kind:
            # Learn: Call desktop._request_paused with the arguments shown.
            desktop._request_paused({
                # Learn: Define this named mapping field: "requestId": "other", "frameId": frame,
                # "resourceType": kind,. The key selects the schema/configuration value.
                "requestId": "other", "frameId": frame, "resourceType": kind,
                # Learn: Define this named mapping field: "request": {"url": "https://evil.example/",
                # "method": "GET"},. The key selects the schema/configuration value.
                "request": {"url": "https://evil.example/", "method": "GET"},
            # Learn: Close this dict literal; delimiters group the values into one object.
            })
        # Learn: Raise Error(message) to stop the normal path.
        raise Error(message)

    # Learn: Set page.goto.side_effect to goto.
    page.goto.side_effect = goto
    # Learn: Enter pytest.raises(Error, match=message). The context manager controls setup/exit; inspect it
    # for the actual cleanup behavior.
    with pytest.raises(Error, match=message):
        # Learn: Open the requested destination through the desktop adapter on desktop; inputs:
        # 'https://en.wikipedia.org/'.
        desktop.navigate("https://en.wikipedia.org/")
    # Learn: Assert that desktop.visited equals a new list (empty). If false, this check fails with
    # AssertionError.
    assert desktop.visited == []


# Learn: Test previous document block does not hide later navigation error. pytest supplies named fixtures
# and checks assertions below.
def test_previous_document_block_does_not_hide_later_navigation_error():
    # Learn: From playwright.sync_api, import Error (the SDK browser exception used to distinguish policy
    # navigation failures).
    from playwright.sync_api import Error

    # Learn: Set (page, session) to the tuple (Mock(), Mock()) (positional values).
    page, session = Mock(), Mock()
    # Learn: Set session.send.return_value to a new dictionary with keys 'frameTree'.
    session.send.return_value = {"frameTree": {"frame": {"id": "main"}}}
    # Learn: Set desktop to E2BDesktop(page, session, GRANT).
    desktop = E2BDesktop(page, session, GRANT)
    # Learn: Call desktop._request_paused with the arguments shown.
    desktop._request_paused({
        # Learn: Define this named mapping field: "requestId": "old", "frameId": "main", "resourceType":
        # "Document",. The key selects the schema/configuration value.
        "requestId": "old", "frameId": "main", "resourceType": "Document",
        # Learn: Define this named mapping field: "request": {"url": "https://evil.example/", "method":
        # "GET"},. The key selects the schema/configuration value.
        "request": {"url": "https://evil.example/", "method": "GET"},
    # Learn: Close this dict literal; delimiters group the values into one object.
    })
    # Learn: Set page.goto.side_effect to Error('Connection failed').
    page.goto.side_effect = Error("Connection failed")
    # Learn: Enter pytest.raises(Error, match='Connection failed'). The context manager controls setup/exit;
    # inspect it for the actual cleanup behavior.
    with pytest.raises(Error, match="Connection failed"):
        # Learn: Open the requested destination through the desktop adapter on desktop; inputs:
        # 'https://en.wikipedia.org/'.
        desktop.navigate("https://en.wikipedia.org/")


# Learn: Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("websocket", [False, True])
# Learn: Test relay translates external host and preserves websocket upgrade. pytest supplies named fixtures
# and checks assertions below.
def test_relay_translates_external_host_and_preserves_websocket_upgrade(websocket):
    # Learn: Set namespace to a new dictionary with keys '__name__'.
    namespace = {"__name__": "relay_test"}
    # Learn: Call exec with the arguments shown.
    exec(compile(RELAY, "<relay>", "exec"), namespace)
    # Learn: Set upgrade to b'Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: test-key\r\n'
    # when websocket, otherwise b''.
    upgrade = b"Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: test-key\r\n" if websocket else b""
    # Learn: Set request to b'GET /json/version HTTP/1.1\r\nhOsT:
    # private.e2b.app\r\ne2b-traffic-access-token: secret-te... plus upgrade plus b'\r\n' plus
    # b'trailing-bytes'.
    request = (b"GET /json/version HTTP/1.1\r\nhOsT: private.e2b.app\r\n"
               # Learn: Continue the expression b"e2b-traffic-access-token: secret-test\r\n" + upgrade +
               # b"\r\n" + b"trailing-bytes"); brackets keep it part of the statement above.
               b"e2b-traffic-access-token: secret-test\r\n" + upgrade + b"\r\n" + b"trailing-bytes")
    # Learn: Set forwarded to namespace['chrome_request'](request).
    forwarded = namespace["chrome_request"](request)
    # Learn: Assert that b'Host: 127.0.0.1:9222\r\n' is in forwarded. If false, this check fails with
    # AssertionError.
    assert b"Host: 127.0.0.1:9222\r\n" in forwarded
    # Learn: Assert that b'private.e2b.app' is not in forwarded. If false, this check fails with
    # AssertionError.
    assert b"private.e2b.app" not in forwarded
    # Learn: Assert that b'secret-test' is not in forwarded. If false, this check fails with AssertionError.
    assert b"secret-test" not in forwarded
    # Learn: Assert that upgrade is in forwarded. If false, this check fails with AssertionError.
    assert upgrade in forwarded
    # Learn: Assert that forwarded.endswith(b'\r\n\r\ntrailing-bytes'). If false, this check fails with
    # AssertionError.
    assert forwarded.endswith(b"\r\n\r\ntrailing-bytes")


# Learn: Test browser exiting early reports log. pytest supplies named fixtures and checks assertions below.
def test_browser_exiting_early_reports_log(monkeypatch):
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/chromium" if name == "chromium" else None)
    # Learn: Set process to Mock().
    process = Mock()
    # Learn: Set process.poll.return_value to 1.
    process.poll.return_value = 1
    # Learn: Set launch to Mock(return_value=process).
    launch = Mock(return_value=process)
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("subprocess.Popen", launch)
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("builtins.open", mock_open())
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("pathlib.Path.read_text", lambda *args, **kwargs: "Missing X server")
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("time.sleep", lambda seconds: None)
    # Learn: Enter pytest.raises(RuntimeError, match='Missing X server'). The context manager controls
    # setup/exit; inspect it for the actual cleanup behavior.
    with pytest.raises(RuntimeError, match="Missing X server"):
        # Learn: Call exec with the arguments shown.
        exec(compile(START_BROWSER, "<browser-startup>", "exec"), {})
    # Learn: Assert that launch.call_args.args[0][0] equals '/usr/bin/chromium'. If false, this check fails
    # with AssertionError.
    assert launch.call_args.args[0][0] == "/usr/bin/chromium"


# Learn: Test readiness disconnect reports browser and relay logs. pytest supplies named fixtures and checks
# assertions below.
def test_readiness_disconnect_reports_browser_and_relay_logs(monkeypatch):
    # Learn: Set opener to Mock().
    opener = Mock()
    # Learn: Set opener.open.side_effect to RemoteDisconnected('Remote end closed connection').
    opener.open.side_effect = RemoteDisconnected("Remote end closed connection")
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("urllib.request.build_opener", lambda *args: opener)
    # Learn: Set times to iter([0, 21]).
    times = iter([0, 21])
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("time.monotonic", lambda: next(times))
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("pathlib.Path.exists", lambda self: True)
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("pathlib.Path.read_text", lambda self, **kwargs: "startup diagnostic")
    # Learn: Enter pytest.raises(RuntimeError) as error. The context manager controls setup/exit; inspect it
    # for the actual cleanup behavior.
    with pytest.raises(RuntimeError) as error:
        # Learn: Call exec with the arguments shown.
        exec(compile(WAIT_READY, "<browser-readiness>", "exec"), {})
    # Learn: Assert that 'RemoteDisconnected' is in str(error.value). If false, this check fails with
    # AssertionError.
    assert "RemoteDisconnected" in str(error.value)
    # Learn: Assert that 'chrome: startup diagnostic' is in str(error.value). If false, this check fails
    # with AssertionError.
    assert "chrome: startup diagnostic" in str(error.value)
    # Learn: Assert that 'relay: startup diagnostic' is in str(error.value). If false, this check fails with
    # AssertionError.
    assert "relay: startup diagnostic" in str(error.value)


# Learn: Test browser startup waits for direct debugger after slow launch. pytest supplies named fixtures
# and checks assertions below.
def test_browser_startup_waits_for_direct_debugger_after_slow_launch(monkeypatch):
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/chromium")
    # Learn: Set child to Mock().
    child = Mock()
    # Learn: Set child.poll.return_value to None (no value).
    child.poll.return_value = None
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("subprocess.Popen", Mock(return_value=child))
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("builtins.open", mock_open())
    # Learn: Set opener to Mock().
    opener = Mock()
    # Learn: Set response to Mock(); the returned HTTP or model-provider response.
    response = Mock()
    # Learn: Set response.__enter__ to Mock(return_value=response).
    response.__enter__ = Mock(return_value=response)
    # Learn: Set response.__exit__ to Mock(return_value=False).
    response.__exit__ = Mock(return_value=False)
    # Learn: Set opener.open.side_effect to a new list containing ConnectionRefusedError('starting'),
    # ConnectionRefusedError('still starting'), response.
    opener.open.side_effect = [ConnectionRefusedError("starting"), ConnectionRefusedError("still starting"), response]
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("urllib.request.build_opener", lambda *args: opener)
    # Learn: Set seconds to iter([0, 1, 30]).
    seconds = iter([0, 1, 30])
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("time.monotonic", lambda: next(seconds))
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("time.sleep", lambda seconds: None)

    # Learn: Call exec with the arguments shown.
    exec(compile(START_BROWSER, "<browser-startup>", "exec"), {})

    # Learn: Assert that opener.open.call_count equals 3. If false, this check fails with AssertionError.
    assert opener.open.call_count == 3
    # Learn: Call opener.open.assert_called_with with the arguments shown.
    opener.open.assert_called_with("http://127.0.0.1:9222/json/version", timeout=1)


# Learn: Test browser startup timeout reports direct port and log. pytest supplies named fixtures and checks
# assertions below.
def test_browser_startup_timeout_reports_direct_port_and_log(monkeypatch):
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/chromium")
    # Learn: Set child to Mock().
    child = Mock()
    # Learn: Set child.poll.return_value to None (no value).
    child.poll.return_value = None
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("subprocess.Popen", Mock(return_value=child))
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("builtins.open", mock_open())
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("pathlib.Path.read_text", lambda *args, **kwargs: "browser startup diagnostic")
    # Learn: Set opener to Mock().
    opener = Mock()
    # Learn: Set opener.open.side_effect to ConnectionRefusedError('not listening').
    opener.open.side_effect = ConnectionRefusedError("not listening")
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("urllib.request.build_opener", lambda *args: opener)
    # Learn: Set seconds to iter([0, 46]).
    seconds = iter([0, 46])
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("time.monotonic", lambda: next(seconds))

    # Learn: Enter pytest.raises(RuntimeError, match='port 9222') as error. The context manager controls
    # setup/exit; inspect it for the actual cleanup behavior.
    with pytest.raises(RuntimeError, match="port 9222") as error:
        # Learn: Call exec with the arguments shown.
        exec(compile(START_BROWSER, "<browser-startup>", "exec"), {})
    # Learn: Assert that 'browser startup diagnostic' is in str(error.value). If false, this check fails
    # with AssertionError.
    assert "browser startup diagnostic" in str(error.value)


# Learn: Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("url,kind,method,allowed", [
    # Learn: Add this item to the surrounding list: ("https://en.wikipedia.org/wiki/Boston", "Document",
    # "GET", True),.
    ("https://en.wikipedia.org/wiki/Boston", "Document", "GET", True),
    # Learn: Add this item to the surrounding list: ("https://127.0.0.1:8000/runs", "Document", "GET",
    # False),.
    ("https://127.0.0.1:8000/runs", "Document", "GET", False),
    # Learn: Add this item to the surrounding list: ("http://169.254.169.254/", "Document", "GET", False),.
    ("http://169.254.169.254/", "Document", "GET", False),
    # Learn: Add this item to the surrounding list: ("https://en.wikipedia.org@evil.com/", "Document",
    # "GET", False),.
    ("https://en.wikipedia.org@evil.com/", "Document", "GET", False),
    # Stylesheets: only GET, only from a permitted host.
    # Learn: Add this item to the surrounding list: ("https://en.wikipedia.org/w/load.php?only=styles",
    # "Stylesheet", "GET", True),.
    ("https://en.wikipedia.org/w/load.php?only=styles", "Stylesheet", "GET", True),
    # Learn: Add this item to the surrounding list: ("https://evil.com/style.css", "Stylesheet", "GET",
    # False),.
    ("https://evil.com/style.css", "Stylesheet", "GET", False),
    # Learn: Add this item to the surrounding list: ("https://en.wikipedia.org/w/load.php?only=styles",
    # "Stylesheet", "POST", False),.
    ("https://en.wikipedia.org/w/load.php?only=styles", "Stylesheet", "POST", False),
    # Everything else stays blocked, even from a permitted host.
    # Learn: Add this item to the surrounding list: ("https://en.wikipedia.org/w/load.php?only=scripts",
    # "Script", "GET", False),.
    ("https://en.wikipedia.org/w/load.php?only=scripts", "Script", "GET", False),
    # Learn: Add this item to the surrounding list: ("https://en.wikipedia.org/logo.png", "Image", "GET",
    # False),.
    ("https://en.wikipedia.org/logo.png", "Image", "GET", False),
    # Learn: Add this item to the surrounding list: ("https://en.wikipedia.org/font.woff2", "Font", "GET",
    # False),.
    ("https://en.wikipedia.org/font.woff2", "Font", "GET", False),
    # Learn: Add this item to the surrounding list: ("https://en.wikipedia.org/api", "XHR", "GET", False),.
    ("https://en.wikipedia.org/api", "XHR", "GET", False),
    # Learn: Add this item to the surrounding list: ("https://en.wikipedia.org/", "Document", "POST",
    # False),.
    ("https://en.wikipedia.org/", "Document", "POST", False),
    # Learn: Add this item to the surrounding list: ("https://[invalid/", "Document", "GET", False),.
    ("https://[invalid/", "Document", "GET", False),
# Learn: Close this list literal; delimiters group the values into one object.
])
# Learn: Test browser requests checked before continuation. pytest supplies named fixtures and checks
# assertions below.
def test_browser_requests_checked_before_continuation(url, kind, method, allowed):
    # Learn: Set (page, session) to the tuple (Mock(), Mock()) (positional values).
    page, session = Mock(), Mock()
    # Learn: Set desktop to E2BDesktop(page, session, GRANT).
    desktop = E2BDesktop(page, session, GRANT)
    # Learn: Call desktop._request_paused with the arguments shown.
    desktop._request_paused({"requestId": "one", "resourceType": kind,
                             # Learn: Define this named mapping field: "request": {"url": url, "method":
                             # method}}). The key selects the schema/configuration value.
                             "request": {"url": url, "method": method}})
    # Learn: Take this branch only if allowed.
    if allowed:
        # Learn: Call session.send.assert_called_with with the arguments shown.
        session.send.assert_called_with("Fetch.continueRequest", {"requestId": "one"})
        # Learn: Assert that desktop.blocked_requests equals a new list (empty). If false, this check fails
        # with AssertionError.
        assert desktop.blocked_requests == []
    # Learn: Run this alternative only when the preceding conditional did not select its first branch.
    else:
        # Learn: Call session.send.assert_called_with with the arguments shown.
        session.send.assert_called_with("Fetch.failRequest", {
            # Learn: Define this named mapping field: "requestId": "one", "errorReason":
            # "BlockedByClient"}). The key selects the schema/configuration value.
            "requestId": "one", "errorReason": "BlockedByClient"})
        # Learn: Assert that desktop.blocked_requests equals a new list containing url. If false, this check
        # fails with AssertionError.
        assert desktop.blocked_requests == [url]


# Learn: Test redirect destination is checked as another paused request. pytest supplies named fixtures and
# checks assertions below.
def test_redirect_destination_is_checked_as_another_paused_request():
    # Learn: Set session to Mock(); the database unit of work or browser CDP session, as selected by this
    # function.
    session = Mock()
    # Learn: Set desktop to E2BDesktop(Mock(), session, GRANT).
    desktop = E2BDesktop(Mock(), session, GRANT)
    # Learn: Iterate over a new list containing the tuple ('first', 'https://en.wikipedia.org/') (positional
    # values), the tuple ('redirect', 'http://169.254.1..., binding (identifier, url) for each item.
    for identifier, url in [("first", "https://en.wikipedia.org/"),
                            # Learn: Add this item to the surrounding list: ("redirect",
                            # "http://169.254.169.254/")]:.
                            ("redirect", "http://169.254.169.254/")]:
        # Learn: Call desktop._request_paused with the arguments shown.
        desktop._request_paused({"requestId": identifier, "resourceType": "Document",
                                 # Learn: Define this named mapping field: "request": {"url": url, "method":
                                 # "GET"}}). The key selects the schema/configuration value.
                                 "request": {"url": url, "method": "GET"}})
    # Learn: Assert that desktop.blocked_requests equals a new list containing 'http://169.254.169.254/'. If
    # false, this check fails with AssertionError.
    assert desktop.blocked_requests == ["http://169.254.169.254/"]
    # Learn: Call session.send.assert_called_with with the arguments shown.
    session.send.assert_called_with("Fetch.failRequest", {
        # Learn: Define this named mapping field: "requestId": "redirect", "errorReason":
        # "BlockedByClient"}). The key selects the schema/configuration value.
        "requestId": "redirect", "errorReason": "BlockedByClient"})


# Learn: Test navigation and observation are bounded. pytest supplies named fixtures and checks assertions
# below.
def test_navigation_and_observation_are_bounded():
    # Learn: Set page to Mock(); the browser tab controlled by Playwright.
    page = Mock()
    # Learn: Set page.url to 'about:blank'; the destination or current page address.
    page.url = "about:blank"
    # Learn: Set desktop to E2BDesktop(page, Mock(), GRANT, max_chars=5).
    desktop = E2BDesktop(page, Mock(), GRANT, max_chars=5)
    # Learn: Assert that desktop.observe().url is None (no value). If false, this check fails with
    # AssertionError.
    assert desktop.observe().url is None
    # Learn: Enter pytest.raises(ValueError). The context manager controls setup/exit; inspect it for the
    # actual cleanup behavior.
    with pytest.raises(ValueError):
        # Learn: Open the requested destination through the desktop adapter on desktop; inputs:
        # 'https://evil.com/'.
        desktop.navigate("https://evil.com/")
    # Learn: Verify the denied/error path never invoked this fake dependency on page.goto.
    page.goto.assert_not_called()
    # Learn: Set page.url to 'https://en.wikipedia.org/wiki/Boston'; the destination or current page
    # address.
    page.url = "https://en.wikipedia.org/wiki/Boston"
    # Learn: Open the requested destination through the desktop adapter on desktop; inputs: page.url.
    desktop.navigate(page.url)
    # Learn: Set page.locator.return_value.count.return_value to 0.
    page.locator.return_value.count.return_value = 0
    # Learn: Set page.locator.return_value.inner_text.return_value to 'Boston is the capital'.
    page.locator.return_value.inner_text.return_value = "Boston is the capital"
    # Learn: Set page.locator.return_value.locator.return_value.evaluate_all.return_value to a new list
    # (empty).
    page.locator.return_value.locator.return_value.evaluate_all.return_value = []
    # Learn: Assert that desktop.observe().text equals 'Bosto\n[Page text truncated]'. If false, this check
    # fails with AssertionError.
    assert desktop.observe().text == "Bosto\n[Page text truncated]"
    # Learn: Assert that desktop.visited equals a new list containing page.url. If false, this check fails
    # with AssertionError.
    assert desktop.visited == [page.url]


# Learn: Test remote setup failure still destroys sandbox. pytest supplies named fixtures and checks
# assertions below.
def test_remote_setup_failure_still_destroys_sandbox():
    # Learn: Set factory to Mock().
    factory = Mock()
    # Learn: Set factory.create.return_value.commands.run.side_effect to RuntimeError('Chrome failed').
    factory.create.return_value.commands.run.side_effect = RuntimeError("Chrome failed")
    # Learn: Enter pytest.raises(RuntimeError, match='Chrome failed'). The context manager controls
    # setup/exit; inspect it for the actual cleanup behavior.
    with pytest.raises(RuntimeError, match="Chrome failed"):
        # Learn: Enter open_e2b_desktop(GRANT, sandbox_type=factory, playwright_factory=Mock()). The context
        # manager controls setup/exit; inspect it for the actual cleanup behavior.
        with open_e2b_desktop(GRANT, sandbox_type=factory, playwright_factory=Mock()):
            # Learn: Call pytest.fail with the arguments shown.
            pytest.fail("Setup should fail before yielding")
    # Learn: Verify the fake dependency ran exactly once with these arguments on
    # factory.create.return_value.kill.
    factory.create.return_value.kill.assert_called_once_with()
    # Learn: Assert that factory.create.call_args.kwargs['network'] equals a new dictionary with keys
    # 'deny_out', 'allow_out', 'allow_public_traffic'. If false, this check fails with AssertionError.
    assert factory.create.call_args.kwargs["network"] == {
        # Learn: Define this named mapping field: "deny_out": ["0.0.0.0/0"], "allow_out":
        # ["en.wikipedia.org"],. The key selects the schema/configuration value.
        "deny_out": ["0.0.0.0/0"], "allow_out": ["en.wikipedia.org"],
        # Learn: Define this named mapping field: "allow_public_traffic": False,. The key selects the
        # schema/configuration value.
        "allow_public_traffic": False,
    # Learn: Close this dict literal; delimiters group the values into one object.
    }
    # Learn: Assert that factory.create.call_args.kwargs['timeout'] equals 180. If false, this check fails
    # with AssertionError.
    assert factory.create.call_args.kwargs["timeout"] == 180


# Learn: Test desktop lifetime is configurable within bounds. pytest supplies named fixtures and checks
# assertions below.
def test_desktop_lifetime_is_configurable_within_bounds():
    # Learn: Set factory to Mock().
    factory = Mock()
    # Learn: Set factory.create.return_value.commands.run.side_effect to RuntimeError('stop after create').
    factory.create.return_value.commands.run.side_effect = RuntimeError("stop after create")
    # Learn: Enter pytest.raises(RuntimeError). The context manager controls setup/exit; inspect it for the
    # actual cleanup behavior.
    with pytest.raises(RuntimeError):
        # Learn: Enter open_e2b_desktop(GRANT, sandbox_type=factory, playwright_factory=Mock(),
        # lifetime_seconds=300). The context manager controls setup/exit; inspect it for the actual cleanup
        # behavior.
        with open_e2b_desktop(GRANT, sandbox_type=factory, playwright_factory=Mock(), lifetime_seconds=300):
            # Learn: No operation: this body intentionally needs no executable statement.
            pass
    # Learn: Assert that factory.create.call_args.kwargs['timeout'] equals 300. If false, this check fails
    # with AssertionError.
    assert factory.create.call_args.kwargs["timeout"] == 300
    # Learn: Iterate over the tuple (59, 601, 300.0, True) (positional values), binding bad for each item.
    for bad in (59, 601, 300.0, True):
        # Learn: Enter pytest.raises(ValueError, match='lifetime_seconds'). The context manager controls
        # setup/exit; inspect it for the actual cleanup behavior.
        with pytest.raises(ValueError, match="lifetime_seconds"):
            # Learn: Enter open_e2b_desktop(GRANT, sandbox_type=factory, playwright_factory=Mock(),
            # lifetime_seconds=bad). The context manager controls setup/exit; inspect it for the actual
            # cleanup behavior.
            with open_e2b_desktop(GRANT, sandbox_type=factory, playwright_factory=Mock(), lifetime_seconds=bad):
                # Learn: No operation: this body intentionally needs no executable statement.
                pass
    # Learn: Assert that factory.create.call_count equals 1. If false, this check fails with AssertionError.
    assert factory.create.call_count == 1


# Learn: Test body failure closes browser and sandbox. pytest supplies named fixtures and checks assertions
# below.
def test_body_failure_closes_browser_and_sandbox(monkeypatch):
    # Learn: Set (factory, playwright_factory) to the tuple (Mock(), Mock()) (positional values).
    factory, playwright_factory = Mock(), Mock()
    # Learn: Set sandbox to factory.create.return_value; the E2B desktop instance; its owner must attempt
    # cleanup.
    sandbox = factory.create.return_value
    # Learn: Set sandbox.get_host.return_value to 'private.e2b.app'.
    sandbox.get_host.return_value = "private.e2b.app"
    # Learn: Set sandbox.traffic_access_token to 'test-token'.
    sandbox.traffic_access_token = "test-token"
    # Learn: Set response to Mock(); the returned HTTP or model-provider response.
    response = Mock()
    # Learn: Set response.json.return_value to a new dictionary with keys 'webSocketDebuggerUrl'.
    response.json.return_value = {"webSocketDebuggerUrl": "ws://localhost:9222/devtools/browser/test"}
    # Learn: Set get to Mock(return_value=response).
    get = Mock(return_value=response)
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("httpx.get", get)
    # Learn: Set playwright to Mock().
    playwright = Mock()
    # Mock context-manager magic methods explicitly.
    # Learn: Set manager to Mock().
    manager = Mock()
    # Learn: Set manager.__enter__ to Mock(return_value=playwright).
    manager.__enter__ = Mock(return_value=playwright)
    # Learn: Set manager.__exit__ to Mock(return_value=False).
    manager.__exit__ = Mock(return_value=False)
    # Learn: Set playwright_factory.return_value to manager.
    playwright_factory.return_value = manager
    # Learn: Set browser to playwright.chromium.connect_over_cdp.return_value; the browser connection or
    # WebSocket peer used in this scope.
    browser = playwright.chromium.connect_over_cdp.return_value
    # Learn: Enter pytest.raises(RuntimeError, match='model failed'). The context manager controls
    # setup/exit; inspect it for the actual cleanup behavior.
    with pytest.raises(RuntimeError, match="model failed"):
        # Learn: Enter open_e2b_desktop(GRANT, sandbox_type=factory, playwright_factory=playwright_factory)
        # as desktop. The context manager controls setup/exit; inspect it for the actual cleanup behavior.
        with open_e2b_desktop(GRANT, sandbox_type=factory, playwright_factory=playwright_factory) as desktop:
            # Learn: Call desktop._screenshot_provider with no arguments.
            desktop._screenshot_provider()
            # Learn: Verify the fake dependency ran exactly once with these arguments on sandbox.screenshot.
            sandbox.screenshot.assert_called_once_with(format="bytes")
            # Learn: Raise RuntimeError('model failed') to stop the normal path.
            raise RuntimeError("model failed")
    # Learn: Verify the fake dependency ran exactly once with these arguments on browser.close.
    browser.close.assert_called_once_with()
    # Learn: Verify the fake dependency ran exactly once with these arguments on sandbox.kill.
    sandbox.kill.assert_called_once_with()
    # Learn: Verify the fake dependency ran exactly once with these arguments on
    # playwright.chromium.connect_over_cdp; inputs: 'wss://private.e2b.app/devtools/browser/test'.
    playwright.chromium.connect_over_cdp.assert_called_once_with(
        # Learn: Supply literal text 'wss://private.e2b.app/devtools/browser/test'; adjacent string literals
        # are concatenated without adding whitespace.
        "wss://private.e2b.app/devtools/browser/test",
        # Learn: Pass keyword headers = a new dictionary with keys 'e2b-traffic-access-token'.
        headers={"e2b-traffic-access-token": "test-token"}, timeout=20000,
    # Learn: Close the argument list for playwright.chromium.connect_over_cdp.assert_called_once_with; the
    # grouped expression remains one call.
    )
