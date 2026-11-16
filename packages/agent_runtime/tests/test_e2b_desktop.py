# Import from http.client: RemoteDisconnected (a dependency used below).
from http.client import RemoteDisconnected
# Import from unittest.mock: Mock (supplies configurable fake attributes and call recording);
# mock_open (a dependency used below).
from unittest.mock import Mock, mock_open

# Import pytest: provides test discovery, fixtures, parametrization, and exception assertions.
import pytest

# Import from crescendo_agent.e2b_desktop: E2BDesktop (a dependency used below); RELAY (the fixed
# remote CDP TCP relay program); START_BROWSER (the fixed remote Chrome launch/readiness program);
# WAIT_READY (the fixed remote relay-readiness check); open_e2b_desktop (owns restricted sandbox
# setup, browser connection, and cleanup).
from crescendo_agent.e2b_desktop import E2BDesktop, RELAY, START_BROWSER, WAIT_READY, open_e2b_desktop
# Import from crescendo_security.policy: TaskGrant (holds the task identity and immutable tool/host
# allowlists).
from crescendo_security.policy import TaskGrant

# Set GRANT to TaskGrant('test', frozenset({'navigate', 'finish'}),
# frozenset({'en.wikipedia.org'})).
GRANT = TaskGrant("test", frozenset({"navigate", "finish"}), frozenset({"en.wikipedia.org"}))


# Define test_blocked_redirect_becomes_observation_and_agent_chooses_another_source with no
# parameters.
def test_blocked_redirect_becomes_observation_and_agent_chooses_another_source():
    # Import from playwright.sync_api: Error (the SDK browser exception used to distinguish policy
    # navigation failures).
    from playwright.sync_api import Error
    # Import from crescendo_agent.loop: run_agent (runs the bounded text observation/action loop).
    from crescendo_agent.loop import run_agent
    # Import from crescendo_agent.model: ScriptedModel (a dependency used below).
    from crescendo_agent.model import ScriptedModel
    # Import from crescendo_security.policy: ToolCall (holds an untrusted proposed tool name and
    # argument mapping).
    from crescendo_security.policy import ToolCall

    # Set (page, session) to (Mock(), Mock()).
    page, session = Mock(), Mock()
    # Set page.url to 'about:blank'.
    page.url = "about:blank"
    # Set session.send.return_value to {'frameTree': {'frame': {'id': 'main'}}}.
    session.send.return_value = {"frameTree": {"frame": {"id": "main"}}}
    # Set desktop to E2BDesktop(page, session, GRANT).
    desktop = E2BDesktop(page, session, GRANT)
    # Set first to 'https://en.wikipedia.org/redirect'.
    first = "https://en.wikipedia.org/redirect"
    # Set second to 'https://en.wikipedia.org/wiki/Boston'.
    second = "https://en.wikipedia.org/wiki/Boston"

    # Define goto with parameters url.
    def goto(url, **kwargs):
        # Check whether url equals first.
        if url == first:
            # Call desktop._request_paused with {'requestId': 'redirect', 'frameId': 'main',
            # 'resourceType': 'Document', 'request': {'url': 'https://evil.example/', 'method':
            # 'GET'}}.
            desktop._request_paused({
                # Include requestId, frameId, resourceType in this dictionary.
                "requestId": "redirect", "frameId": "main", "resourceType": "Document",
                # Include request, url, method in this dictionary.
                "request": {"url": "https://evil.example/", "method": "GET"},
            })
            # Raise Error('net::ERR_BLOCKED_BY_CLIENT') to stop the normal path.
            raise Error("net::ERR_BLOCKED_BY_CLIENT")
        # The model gets a safe observation without reading the failed page.
        # Call page.locator.assert_not_called with no arguments.
        page.locator.assert_not_called()
        # Set page.url to second.
        page.url = second

    # Set page.goto.side_effect to goto.
    page.goto.side_effect = goto
    # Set page.locator.return_value.count.return_value to 0.
    page.locator.return_value.count.return_value = 0
    # Set page.locator.return_value.inner_text.return_value to 'Boston facts'.
    page.locator.return_value.inner_text.return_value = "Boston facts"
    # Set page.locator.return_value.locator.return_value.evaluate_all.return_value to an empty list.
    page.locator.return_value.locator.return_value.evaluate_all.return_value = []
    # Set model to ScriptedModel([ToolCall('navigate', {'url': first}), ToolCall('navigate', {'url':
    # second}), ToolCall('finish', {'answer': 'Boston facts', 'sources': [second]})]).
    model = ScriptedModel([
        # Call ToolCall with the arguments shown.
        ToolCall("navigate", {"url": first}),
        # Call ToolCall with the arguments shown.
        ToolCall("navigate", {"url": second}),
        # Call ToolCall with the arguments shown.
        ToolCall("finish", {"answer": "Boston facts", "sources": [second]}),
    ])

    # Set result to run_agent('Research Boston', GRANT, desktop, model).
    result = run_agent("Research Boston", GRANT, desktop, model)

    # Assert that result.status equals 'finished'. If false, this check fails with AssertionError.
    assert result.status == "finished"
    # Assert that desktop.visited equals a new list containing second. If false, this check fails
    # with AssertionError.
    assert desktop.visited == [second]
    # Assert that desktop.blocked_requests equals a new list containing 'https://evil.example/'. If
    # false, this check fails with AssertionError.
    assert desktop.blocked_requests == ["https://evil.example/"]
    # Assert that any(('Navigation blocked by browser policy' in e.text for e in model.seen[1])). If
    # false, this check fails with AssertionError.
    assert any("Navigation blocked by browser policy" in e.text for e in model.seen[1])
    # Assert that any(('Boston facts' in e.text for e in model.seen[2] if e.kind == 'observation')).
    # If false, this check fails with AssertionError.
    assert any("Boston facts" in e.text for e in model.seen[2] if e.kind == "observation")
    # Assert that desktop.observe().url equals second. If false, this check fails with
    # AssertionError.
    assert desktop.observe().url == second
    # Call session.send.assert_any_call with 'Fetch.failRequest', {'requestId': 'redirect',
    # 'errorReason': 'BlockedByClient'}.
    session.send.assert_any_call("Fetch.failRequest", {
        # Include requestId, errorReason in this dictionary.
        "requestId": "redirect", "errorReason": "BlockedByClient",
    })


# Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("kind,frame,message", [
    # Add this item to the surrounding list: (None, None, "net::ERR_BLOCKED_BY_CLIENT"),.
    (None, None, "net::ERR_BLOCKED_BY_CLIENT"),
    # Add this item to the surrounding list: ("Image", "main", "net::ERR_BLOCKED_BY_CLIENT"),.
    ("Image", "main", "net::ERR_BLOCKED_BY_CLIENT"),
    # Add this item to the surrounding list: ("Document", "iframe", "net::ERR_BLOCKED_BY_CLIENT"),.
    ("Document", "iframe", "net::ERR_BLOCKED_BY_CLIENT"),
    # Add this item to the surrounding list: ("Document", "main", "Connection failed"),.
    ("Document", "main", "Connection failed"),
])
# Define test_unrelated_navigation_errors_still_propagate with parameters kind, frame, message.
def test_unrelated_navigation_errors_still_propagate(kind, frame, message):
    # Import from playwright.sync_api: Error (the SDK browser exception used to distinguish policy
    # navigation failures).
    from playwright.sync_api import Error

    # Set (page, session) to (Mock(), Mock()).
    page, session = Mock(), Mock()
    # Set session.send.return_value to {'frameTree': {'frame': {'id': 'main'}}}.
    session.send.return_value = {"frameTree": {"frame": {"id": "main"}}}
    # Set desktop to E2BDesktop(page, session, GRANT).
    desktop = E2BDesktop(page, session, GRANT)

    # Define goto with no parameters.
    def goto(*args, **kwargs):
        # Check whether kind.
        if kind:
            # Call desktop._request_paused with {'requestId': 'other', 'frameId': frame,
            # 'resourceType': kind, 'request': {'url': 'https://evil.example/', 'method': 'GET'}}.
            desktop._request_paused({
                # Include requestId, frameId, resourceType in this dictionary.
                "requestId": "other", "frameId": frame, "resourceType": kind,
                # Include request, url, method in this dictionary.
                "request": {"url": "https://evil.example/", "method": "GET"},
            })
        # Raise Error(message) to stop the normal path.
        raise Error(message)

    # Set page.goto.side_effect to goto.
    page.goto.side_effect = goto
    # Use pytest.raises(Error, match=message); leave the context and run its cleanup when this block
    # ends.
    with pytest.raises(Error, match=message):
        # Call desktop.navigate with 'https://en.wikipedia.org/'.
        desktop.navigate("https://en.wikipedia.org/")
    # Assert that desktop.visited equals a new list (empty). If false, this check fails with
    # AssertionError.
    assert desktop.visited == []


# Define test_previous_document_block_does_not_hide_later_navigation_error with no parameters.
def test_previous_document_block_does_not_hide_later_navigation_error():
    # Import from playwright.sync_api: Error (the SDK browser exception used to distinguish policy
    # navigation failures).
    from playwright.sync_api import Error

    # Set (page, session) to (Mock(), Mock()).
    page, session = Mock(), Mock()
    # Set session.send.return_value to {'frameTree': {'frame': {'id': 'main'}}}.
    session.send.return_value = {"frameTree": {"frame": {"id": "main"}}}
    # Set desktop to E2BDesktop(page, session, GRANT).
    desktop = E2BDesktop(page, session, GRANT)
    # Call desktop._request_paused with {'requestId': 'old', 'frameId': 'main', 'resourceType':
    # 'Document', 'request': {'url': 'https://evil.example/', 'method': 'GET'}}.
    desktop._request_paused({
        # Include requestId, frameId, resourceType in this dictionary.
        "requestId": "old", "frameId": "main", "resourceType": "Document",
        # Include request, url, method in this dictionary.
        "request": {"url": "https://evil.example/", "method": "GET"},
    })
    # Set page.goto.side_effect to Error('Connection failed').
    page.goto.side_effect = Error("Connection failed")
    # Use pytest.raises(Error, match='Connection failed'); leave the context and run its cleanup
    # when this block ends.
    with pytest.raises(Error, match="Connection failed"):
        # Call desktop.navigate with 'https://en.wikipedia.org/'.
        desktop.navigate("https://en.wikipedia.org/")


# Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("websocket", [False, True])
# Define test_relay_translates_external_host_and_preserves_websocket_upgrade with parameters
# websocket.
def test_relay_translates_external_host_and_preserves_websocket_upgrade(websocket):
    # Set namespace to {'__name__': 'relay_test'}.
    namespace = {"__name__": "relay_test"}
    # Call exec with compile(RELAY, '<relay>', 'exec'), namespace.
    exec(compile(RELAY, "<relay>", "exec"), namespace)
    # Set upgrade to b'Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: test-key\r\n'
    # if websocket, otherwise b''.
    upgrade = b"Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: test-key\r\n" if websocket else b""
    # Set request to b'GET /json/version HTTP/1.1\r\nhOsT:
    # private.e2b.app\r\ne2b-traffic-access-token: secret-test\r\n' plus upgrade plus b'\r\n' plus
    # b'trailing-bytes'.
    request = (b"GET /json/version HTTP/1.1\r\nhOsT: private.e2b.app\r\n"
               # Continue the expression b"e2b-traffic-access-token: secret-test\r\n" + upgrade +
               # b"\r\n" + b"trailing-bytes"); brackets keep it part of the statement above.
               b"e2b-traffic-access-token: secret-test\r\n" + upgrade + b"\r\n" + b"trailing-bytes")
    # Set forwarded to namespace['chrome_request'](request).
    forwarded = namespace["chrome_request"](request)
    # Assert that b'Host: 127.0.0.1:9222\r\n' is in forwarded. If false, this check fails with
    # AssertionError.
    assert b"Host: 127.0.0.1:9222\r\n" in forwarded
    # Assert that b'private.e2b.app' is not in forwarded. If false, this check fails with
    # AssertionError.
    assert b"private.e2b.app" not in forwarded
    # Assert that b'secret-test' is not in forwarded. If false, this check fails with
    # AssertionError.
    assert b"secret-test" not in forwarded
    # Assert that upgrade is in forwarded. If false, this check fails with AssertionError.
    assert upgrade in forwarded
    # Assert that forwarded.endswith(b'\r\n\r\ntrailing-bytes'). If false, this check fails with
    # AssertionError.
    assert forwarded.endswith(b"\r\n\r\ntrailing-bytes")


# Define test_browser_exiting_early_reports_log with parameters monkeypatch.
def test_browser_exiting_early_reports_log(monkeypatch):
    # Call monkeypatch.setattr with 'shutil.which', a function that returns '/usr/bin/chromium' if
    # name equals 'chromium', otherwise None when called.
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/chromium" if name == "chromium" else None)
    # Set process to Mock().
    process = Mock()
    # Set process.poll.return_value to 1.
    process.poll.return_value = 1
    # Set launch to Mock(return_value=process).
    launch = Mock(return_value=process)
    # Call monkeypatch.setattr with 'subprocess.Popen', launch.
    monkeypatch.setattr("subprocess.Popen", launch)
    # Call monkeypatch.setattr with 'builtins.open', mock_open().
    monkeypatch.setattr("builtins.open", mock_open())
    # Call monkeypatch.setattr with 'pathlib.Path.read_text', a function that returns 'Missing X
    # server' when called.
    monkeypatch.setattr("pathlib.Path.read_text", lambda *args, **kwargs: "Missing X server")
    # Call monkeypatch.setattr with 'time.sleep', a function that returns None when called.
    monkeypatch.setattr("time.sleep", lambda seconds: None)
    # Use pytest.raises(RuntimeError, match='Missing X server'); leave the context and run its
    # cleanup when this block ends.
    with pytest.raises(RuntimeError, match="Missing X server"):
        # Call exec with compile(START_BROWSER, '<browser-startup>', 'exec'), an empty dictionary.
        exec(compile(START_BROWSER, "<browser-startup>", "exec"), {})
    # Assert that launch.call_args.args[0][0] equals '/usr/bin/chromium'. If false, this check fails
    # with AssertionError.
    assert launch.call_args.args[0][0] == "/usr/bin/chromium"


# Define test_readiness_disconnect_reports_browser_and_relay_logs with parameters monkeypatch.
def test_readiness_disconnect_reports_browser_and_relay_logs(monkeypatch):
    # Set opener to Mock().
    opener = Mock()
    # Set opener.open.side_effect to RemoteDisconnected('Remote end closed connection').
    opener.open.side_effect = RemoteDisconnected("Remote end closed connection")
    # Call monkeypatch.setattr with 'urllib.request.build_opener', a function that returns opener
    # when called.
    monkeypatch.setattr("urllib.request.build_opener", lambda *args: opener)
    # Set times to iter([0, 21]).
    times = iter([0, 21])
    # Call monkeypatch.setattr with 'time.monotonic', a function that returns next(times) when
    # called.
    monkeypatch.setattr("time.monotonic", lambda: next(times))
    # Call monkeypatch.setattr with 'pathlib.Path.exists', a function that returns True when called.
    monkeypatch.setattr("pathlib.Path.exists", lambda self: True)
    # Call monkeypatch.setattr with 'pathlib.Path.read_text', a function that returns 'startup
    # diagnostic' when called.
    monkeypatch.setattr("pathlib.Path.read_text", lambda self, **kwargs: "startup diagnostic")
    # Use pytest.raises(RuntimeError) as error; leave the context and run its cleanup when this
    # block ends.
    with pytest.raises(RuntimeError) as error:
        # Call exec with compile(WAIT_READY, '<browser-readiness>', 'exec'), an empty dictionary.
        exec(compile(WAIT_READY, "<browser-readiness>", "exec"), {})
    # Assert that 'RemoteDisconnected' is in str(error.value). If false, this check fails with
    # AssertionError.
    assert "RemoteDisconnected" in str(error.value)
    # Assert that 'chrome: startup diagnostic' is in str(error.value). If false, this check fails
    # with AssertionError.
    assert "chrome: startup diagnostic" in str(error.value)
    # Assert that 'relay: startup diagnostic' is in str(error.value). If false, this check fails
    # with AssertionError.
    assert "relay: startup diagnostic" in str(error.value)


# Define test_browser_startup_waits_for_direct_debugger_after_slow_launch with parameters
# monkeypatch.
def test_browser_startup_waits_for_direct_debugger_after_slow_launch(monkeypatch):
    # Call monkeypatch.setattr with 'shutil.which', a function that returns '/usr/bin/chromium' when
    # called.
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/chromium")
    # Set child to Mock().
    child = Mock()
    # Set child.poll.return_value to None.
    child.poll.return_value = None
    # Call monkeypatch.setattr with 'subprocess.Popen', Mock(return_value=child).
    monkeypatch.setattr("subprocess.Popen", Mock(return_value=child))
    # Call monkeypatch.setattr with 'builtins.open', mock_open().
    monkeypatch.setattr("builtins.open", mock_open())
    # Set opener to Mock().
    opener = Mock()
    # Set response to Mock().
    response = Mock()
    # Set response.__enter__ to Mock(return_value=response).
    response.__enter__ = Mock(return_value=response)
    # Set response.__exit__ to Mock(return_value=False).
    response.__exit__ = Mock(return_value=False)
    # Set opener.open.side_effect to [ConnectionRefusedError('starting'),
    # ConnectionRefusedError('still starting'), response].
    opener.open.side_effect = [ConnectionRefusedError("starting"), ConnectionRefusedError("still starting"), response]
    # Call monkeypatch.setattr with 'urllib.request.build_opener', a function that returns opener
    # when called.
    monkeypatch.setattr("urllib.request.build_opener", lambda *args: opener)
    # Set seconds to iter([0, 1, 30]).
    seconds = iter([0, 1, 30])
    # Call monkeypatch.setattr with 'time.monotonic', a function that returns next(seconds) when
    # called.
    monkeypatch.setattr("time.monotonic", lambda: next(seconds))
    # Call monkeypatch.setattr with 'time.sleep', a function that returns None when called.
    monkeypatch.setattr("time.sleep", lambda seconds: None)

    # Call exec with compile(START_BROWSER, '<browser-startup>', 'exec'), an empty dictionary.
    exec(compile(START_BROWSER, "<browser-startup>", "exec"), {})

    # Assert that opener.open.call_count equals 3. If false, this check fails with AssertionError.
    assert opener.open.call_count == 3
    # Call opener.open.assert_called_with with 'http://127.0.0.1:9222/json/version'.
    opener.open.assert_called_with("http://127.0.0.1:9222/json/version", timeout=1)


# Define test_browser_startup_timeout_reports_direct_port_and_log with parameters monkeypatch.
def test_browser_startup_timeout_reports_direct_port_and_log(monkeypatch):
    # Call monkeypatch.setattr with 'shutil.which', a function that returns '/usr/bin/chromium' when
    # called.
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/chromium")
    # Set child to Mock().
    child = Mock()
    # Set child.poll.return_value to None.
    child.poll.return_value = None
    # Call monkeypatch.setattr with 'subprocess.Popen', Mock(return_value=child).
    monkeypatch.setattr("subprocess.Popen", Mock(return_value=child))
    # Call monkeypatch.setattr with 'builtins.open', mock_open().
    monkeypatch.setattr("builtins.open", mock_open())
    # Call monkeypatch.setattr with 'pathlib.Path.read_text', a function that returns 'browser
    # startup diagnostic' when called.
    monkeypatch.setattr("pathlib.Path.read_text", lambda *args, **kwargs: "browser startup diagnostic")
    # Set opener to Mock().
    opener = Mock()
    # Set opener.open.side_effect to ConnectionRefusedError('not listening').
    opener.open.side_effect = ConnectionRefusedError("not listening")
    # Call monkeypatch.setattr with 'urllib.request.build_opener', a function that returns opener
    # when called.
    monkeypatch.setattr("urllib.request.build_opener", lambda *args: opener)
    # Set seconds to iter([0, 46]).
    seconds = iter([0, 46])
    # Call monkeypatch.setattr with 'time.monotonic', a function that returns next(seconds) when
    # called.
    monkeypatch.setattr("time.monotonic", lambda: next(seconds))

    # Use pytest.raises(RuntimeError, match='port 9222') as error; leave the context and run its
    # cleanup when this block ends.
    with pytest.raises(RuntimeError, match="port 9222") as error:
        # Call exec with compile(START_BROWSER, '<browser-startup>', 'exec'), an empty dictionary.
        exec(compile(START_BROWSER, "<browser-startup>", "exec"), {})
    # Assert that 'browser startup diagnostic' is in str(error.value). If false, this check fails
    # with AssertionError.
    assert "browser startup diagnostic" in str(error.value)


# Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("url,kind,method,allowed", [
    # Add this item to the surrounding list: ("https://en.wikipedia.org/wiki/Boston", "Document",
    # "GET", True),.
    ("https://en.wikipedia.org/wiki/Boston", "Document", "GET", True),
    # Add this item to the surrounding list: ("https://127.0.0.1:8000/runs", "Document", "GET",
    # False),.
    ("https://127.0.0.1:8000/runs", "Document", "GET", False),
    # Add this item to the surrounding list: ("http://169.254.169.254/", "Document", "GET", False),.
    ("http://169.254.169.254/", "Document", "GET", False),
    # Add this item to the surrounding list: ("https://en.wikipedia.org@evil.com/", "Document",
    # "GET", False),.
    ("https://en.wikipedia.org@evil.com/", "Document", "GET", False),
    # Stylesheets: only GET, only from a permitted host.
    # Add this item to the surrounding list: ("https://en.wikipedia.org/w/load.php?only=styles",
    # "Stylesheet", "GET", True),.
    ("https://en.wikipedia.org/w/load.php?only=styles", "Stylesheet", "GET", True),
    # Add this item to the surrounding list: ("https://evil.com/style.css", "Stylesheet", "GET",
    # False),.
    ("https://evil.com/style.css", "Stylesheet", "GET", False),
    # Add this item to the surrounding list: ("https://en.wikipedia.org/w/load.php?only=styles",
    # "Stylesheet", "POST", False),.
    ("https://en.wikipedia.org/w/load.php?only=styles", "Stylesheet", "POST", False),
    # Everything else stays blocked, even from a permitted host.
    # Add this item to the surrounding list: ("https://en.wikipedia.org/w/load.php?only=scripts",
    # "Script", "GET", False),.
    ("https://en.wikipedia.org/w/load.php?only=scripts", "Script", "GET", False),
    # Add this item to the surrounding list: ("https://en.wikipedia.org/logo.png", "Image", "GET",
    # False),.
    ("https://en.wikipedia.org/logo.png", "Image", "GET", False),
    # Add this item to the surrounding list: ("https://en.wikipedia.org/font.woff2", "Font", "GET",
    # False),.
    ("https://en.wikipedia.org/font.woff2", "Font", "GET", False),
    # Add this item to the surrounding list: ("https://en.wikipedia.org/api", "XHR", "GET", False),.
    ("https://en.wikipedia.org/api", "XHR", "GET", False),
    # Add this item to the surrounding list: ("https://en.wikipedia.org/", "Document", "POST",
    # False),.
    ("https://en.wikipedia.org/", "Document", "POST", False),
    # Add this item to the surrounding list: ("https://[invalid/", "Document", "GET", False),.
    ("https://[invalid/", "Document", "GET", False),
])
# Define test_browser_requests_checked_before_continuation with parameters url, kind, method,
# allowed.
def test_browser_requests_checked_before_continuation(url, kind, method, allowed):
    # Set (page, session) to (Mock(), Mock()).
    page, session = Mock(), Mock()
    # Set desktop to E2BDesktop(page, session, GRANT).
    desktop = E2BDesktop(page, session, GRANT)
    # Call desktop._request_paused with {'requestId': 'one', 'resourceType': kind, 'request':
    # {'url': url, 'method': method}}.
    desktop._request_paused({"requestId": "one", "resourceType": kind,
                             # Include request, url, method in this dictionary.
                             "request": {"url": url, "method": method}})
    # Check whether allowed.
    if allowed:
        # Call session.send.assert_called_with with 'Fetch.continueRequest', {'requestId': 'one'}.
        session.send.assert_called_with("Fetch.continueRequest", {"requestId": "one"})
        # Assert that desktop.blocked_requests equals a new list (empty). If false, this check fails
        # with AssertionError.
        assert desktop.blocked_requests == []
    # Run this alternative only when the preceding conditional did not select its first branch.
    else:
        # Call session.send.assert_called_with with 'Fetch.failRequest', {'requestId': 'one',
        # 'errorReason': 'BlockedByClient'}.
        session.send.assert_called_with("Fetch.failRequest", {
            # Include requestId, errorReason in this dictionary.
            "requestId": "one", "errorReason": "BlockedByClient"})
        # Assert that desktop.blocked_requests equals a new list containing url. If false, this
        # check fails with AssertionError.
        assert desktop.blocked_requests == [url]


# Define test_redirect_destination_is_checked_as_another_paused_request with no parameters.
def test_redirect_destination_is_checked_as_another_paused_request():
    # Set session to Mock().
    session = Mock()
    # Set desktop to E2BDesktop(Mock(), session, GRANT).
    desktop = E2BDesktop(Mock(), session, GRANT)
    for identifier, url in [("first", "https://en.wikipedia.org/"),
                            # Add this item to the surrounding list: ("redirect",
                            # "http://169.254.169.254/")]:.
                            ("redirect", "http://169.254.169.254/")]:
        # Call desktop._request_paused with {'requestId': identifier, 'resourceType': 'Document',
        # 'request': {'url': url, 'method': 'GET'}}.
        desktop._request_paused({"requestId": identifier, "resourceType": "Document",
                                 # Include request, url, method in this dictionary.
                                 "request": {"url": url, "method": "GET"}})
    # Assert that desktop.blocked_requests equals a new list containing 'http://169.254.169.254/'.
    # If false, this check fails with AssertionError.
    assert desktop.blocked_requests == ["http://169.254.169.254/"]
    # Call session.send.assert_called_with with 'Fetch.failRequest', {'requestId': 'redirect',
    # 'errorReason': 'BlockedByClient'}.
    session.send.assert_called_with("Fetch.failRequest", {
        # Include requestId, errorReason in this dictionary.
        "requestId": "redirect", "errorReason": "BlockedByClient"})


# Define test_navigation_and_observation_are_bounded with no parameters.
def test_navigation_and_observation_are_bounded():
    # Set page to Mock().
    page = Mock()
    # Set page.url to 'about:blank'.
    page.url = "about:blank"
    # Set desktop to E2BDesktop(page, Mock(), GRANT, max_chars=5).
    desktop = E2BDesktop(page, Mock(), GRANT, max_chars=5)
    # Assert that desktop.observe().url is None (no value). If false, this check fails with
    # AssertionError.
    assert desktop.observe().url is None
    # Use pytest.raises(ValueError); leave the context and run its cleanup when this block ends.
    with pytest.raises(ValueError):
        # Call desktop.navigate with 'https://evil.com/'.
        desktop.navigate("https://evil.com/")
    # Call page.goto.assert_not_called with no arguments.
    page.goto.assert_not_called()
    # Set page.url to 'https://en.wikipedia.org/wiki/Boston'.
    page.url = "https://en.wikipedia.org/wiki/Boston"
    # Call desktop.navigate with page.url.
    desktop.navigate(page.url)
    # Set page.locator.return_value.count.return_value to 0.
    page.locator.return_value.count.return_value = 0
    # Set page.locator.return_value.inner_text.return_value to 'Boston is the capital'.
    page.locator.return_value.inner_text.return_value = "Boston is the capital"
    # Set page.locator.return_value.locator.return_value.evaluate_all.return_value to an empty list.
    page.locator.return_value.locator.return_value.evaluate_all.return_value = []
    # Assert that desktop.observe().text equals 'Bosto\n[Page text truncated]'. If false, this check
    # fails with AssertionError.
    assert desktop.observe().text == "Bosto\n[Page text truncated]"
    # Assert that desktop.visited equals a new list containing page.url. If false, this check fails
    # with AssertionError.
    assert desktop.visited == [page.url]


# Define test_remote_setup_failure_still_destroys_sandbox with no parameters.
def test_remote_setup_failure_still_destroys_sandbox():
    # Set factory to Mock().
    factory = Mock()
    # Set factory.create.return_value.commands.run.side_effect to RuntimeError('Chrome failed').
    factory.create.return_value.commands.run.side_effect = RuntimeError("Chrome failed")
    # Use pytest.raises(RuntimeError, match='Chrome failed'); leave the context and run its cleanup
    # when this block ends.
    with pytest.raises(RuntimeError, match="Chrome failed"):
        # Use open_e2b_desktop(GRANT, sandbox_type=factory, playwright_factory=Mock()); leave the
        # context and run its cleanup when this block ends.
        with open_e2b_desktop(GRANT, sandbox_type=factory, playwright_factory=Mock()):
            # Call pytest.fail with 'Setup should fail before yielding'.
            pytest.fail("Setup should fail before yielding")
    # Call factory.create.return_value.kill.assert_called_once_with with no arguments.
    factory.create.return_value.kill.assert_called_once_with()
    # Assert that factory.create.call_args.kwargs['network'] equals a new dictionary with keys
    # 'deny_out', 'allow_out', 'allow_public_traffic'. If false, this check fails with
    # AssertionError.
    assert factory.create.call_args.kwargs["network"] == {
        # Include deny_out, allow_out in this dictionary.
        "deny_out": ["0.0.0.0/0"], "allow_out": ["en.wikipedia.org"],
        # Include allow_public_traffic in this dictionary.
        "allow_public_traffic": False,
    }
    # Assert that factory.create.call_args.kwargs['timeout'] equals 180. If false, this check fails
    # with AssertionError.
    assert factory.create.call_args.kwargs["timeout"] == 180


# Define test_desktop_lifetime_is_configurable_within_bounds with no parameters.
def test_desktop_lifetime_is_configurable_within_bounds():
    # Set factory to Mock().
    factory = Mock()
    # Set factory.create.return_value.commands.run.side_effect to RuntimeError('stop after create').
    factory.create.return_value.commands.run.side_effect = RuntimeError("stop after create")
    # Use pytest.raises(RuntimeError); leave the context and run its cleanup when this block ends.
    with pytest.raises(RuntimeError):
        # Use open_e2b_desktop(GRANT, sandbox_type=factory, playwright_factory=Mock(),
        # lifetime_seconds=300); leave the context and run its cleanup when this block ends.
        with open_e2b_desktop(GRANT, sandbox_type=factory, playwright_factory=Mock(), lifetime_seconds=300):
            pass
    # Assert that factory.create.call_args.kwargs['timeout'] equals 300. If false, this check fails
    # with AssertionError.
    assert factory.create.call_args.kwargs["timeout"] == 300
    # Iterate over the tuple (59, 601, 300.0, True) (positional values), binding bad for each item.
    for bad in (59, 601, 300.0, True):
        # Use pytest.raises(ValueError, match='lifetime_seconds'); leave the context and run its
        # cleanup when this block ends.
        with pytest.raises(ValueError, match="lifetime_seconds"):
            # Use open_e2b_desktop(GRANT, sandbox_type=factory, playwright_factory=Mock(),
            # lifetime_seconds=bad); leave the context and run its cleanup when this block ends.
            with open_e2b_desktop(GRANT, sandbox_type=factory, playwright_factory=Mock(), lifetime_seconds=bad):
                pass
    # Assert that factory.create.call_count equals 1. If false, this check fails with
    # AssertionError.
    assert factory.create.call_count == 1


# Define test_body_failure_closes_browser_and_sandbox with parameters monkeypatch.
def test_body_failure_closes_browser_and_sandbox(monkeypatch):
    # Set (factory, playwright_factory) to (Mock(), Mock()).
    factory, playwright_factory = Mock(), Mock()
    # Set sandbox to factory.create.return_value.
    sandbox = factory.create.return_value
    # Set sandbox.get_host.return_value to 'private.e2b.app'.
    sandbox.get_host.return_value = "private.e2b.app"
    # Set sandbox.traffic_access_token to 'test-token'.
    sandbox.traffic_access_token = "test-token"
    # Set response to Mock().
    response = Mock()
    # Set response.json.return_value to {'webSocketDebuggerUrl':
    # 'ws://localhost:9222/devtools/browser/test'}.
    response.json.return_value = {"webSocketDebuggerUrl": "ws://localhost:9222/devtools/browser/test"}
    # Set get to Mock(return_value=response).
    get = Mock(return_value=response)
    # Call monkeypatch.setattr with 'httpx.get', get.
    monkeypatch.setattr("httpx.get", get)
    # Set playwright to Mock().
    playwright = Mock()
    # Mock context-manager magic methods explicitly.
    # Set manager to Mock().
    manager = Mock()
    # Set manager.__enter__ to Mock(return_value=playwright).
    manager.__enter__ = Mock(return_value=playwright)
    # Set manager.__exit__ to Mock(return_value=False).
    manager.__exit__ = Mock(return_value=False)
    # Set playwright_factory.return_value to manager.
    playwright_factory.return_value = manager
    # Set browser to playwright.chromium.connect_over_cdp.return_value.
    browser = playwright.chromium.connect_over_cdp.return_value
    # Use pytest.raises(RuntimeError, match='model failed'); leave the context and run its cleanup
    # when this block ends.
    with pytest.raises(RuntimeError, match="model failed"):
        # Use open_e2b_desktop(GRANT, sandbox_type=factory, playwright_factory=playwright_factory)
        # as desktop; leave the context and run its cleanup when this block ends.
        with open_e2b_desktop(GRANT, sandbox_type=factory, playwright_factory=playwright_factory) as desktop:
            # Call desktop._screenshot_provider with no arguments.
            desktop._screenshot_provider()
            # Call sandbox.screenshot.assert_called_once_with with no arguments.
            sandbox.screenshot.assert_called_once_with(format="bytes")
            # Raise RuntimeError('model failed') to stop the normal path.
            raise RuntimeError("model failed")
    # Call browser.close.assert_called_once_with with no arguments.
    browser.close.assert_called_once_with()
    # Call sandbox.kill.assert_called_once_with with no arguments.
    sandbox.kill.assert_called_once_with()
    # Call playwright.chromium.connect_over_cdp.assert_called_once_with with
    # 'wss://private.e2b.app/devtools/browser/test'.
    playwright.chromium.connect_over_cdp.assert_called_once_with(
        "wss://private.e2b.app/devtools/browser/test",
        # Pass keyword headers = a new dictionary with keys 'e2b-traffic-access-token'.
        headers={"e2b-traffic-access-token": "test-token"}, timeout=20000,
    )
