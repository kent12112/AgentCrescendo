from http.client import RemoteDisconnected
from unittest.mock import Mock, mock_open

import pytest

from crescendo_agent.e2b_desktop import E2BDesktop, RELAY, START_BROWSER, WAIT_READY, open_e2b_desktop
from crescendo_security.policy import TaskGrant

GRANT = TaskGrant("test", frozenset({"navigate", "finish"}), frozenset({"en.wikipedia.org"}))


def test_blocked_redirect_becomes_observation_and_agent_chooses_another_source():
    from playwright.sync_api import Error
    from crescendo_agent.loop import run_agent
    from crescendo_agent.model import ScriptedModel
    from crescendo_security.policy import ToolCall

    page, session = Mock(), Mock()
    page.url = "about:blank"
    session.send.return_value = {"frameTree": {"frame": {"id": "main"}}}
    desktop = E2BDesktop(page, session, GRANT)
    first = "https://en.wikipedia.org/redirect"
    second = "https://en.wikipedia.org/wiki/Boston"

    def goto(url, **kwargs):
        if url == first:
            desktop._request_paused({
                "requestId": "redirect", "frameId": "main", "resourceType": "Document",
                "request": {"url": "https://evil.example/", "method": "GET"},
            })
            raise Error("net::ERR_BLOCKED_BY_CLIENT")
        # The model gets a safe observation without reading the failed page.
        page.locator.assert_not_called()
        page.url = second

    page.goto.side_effect = goto
    page.locator.return_value.count.return_value = 0
    page.locator.return_value.inner_text.return_value = "Boston facts"
    page.locator.return_value.locator.return_value.evaluate_all.return_value = []
    model = ScriptedModel([
        ToolCall("navigate", {"url": first}),
        ToolCall("navigate", {"url": second}),
        ToolCall("finish", {"answer": "Boston facts", "sources": [second]}),
    ])

    result = run_agent("Research Boston", GRANT, desktop, model)

    assert result.status == "finished"
    assert desktop.visited == [second]
    assert desktop.blocked_requests == ["https://evil.example/"]
    assert any("Navigation blocked by browser policy" in e.text for e in model.seen[1])
    assert any("Boston facts" in e.text for e in model.seen[2] if e.kind == "observation")
    assert desktop.observe().url == second
    session.send.assert_any_call("Fetch.failRequest", {
        "requestId": "redirect", "errorReason": "BlockedByClient",
    })


@pytest.mark.parametrize("kind,frame,message", [
    (None, None, "net::ERR_BLOCKED_BY_CLIENT"),
    ("Image", "main", "net::ERR_BLOCKED_BY_CLIENT"),
    ("Document", "iframe", "net::ERR_BLOCKED_BY_CLIENT"),
    ("Document", "main", "Connection failed"),
])
def test_unrelated_navigation_errors_still_propagate(kind, frame, message):
    from playwright.sync_api import Error

    page, session = Mock(), Mock()
    session.send.return_value = {"frameTree": {"frame": {"id": "main"}}}
    desktop = E2BDesktop(page, session, GRANT)

    def goto(*args, **kwargs):
        if kind:
            desktop._request_paused({
                "requestId": "other", "frameId": frame, "resourceType": kind,
                "request": {"url": "https://evil.example/", "method": "GET"},
            })
        raise Error(message)

    page.goto.side_effect = goto
    with pytest.raises(Error, match=message):
        desktop.navigate("https://en.wikipedia.org/")
    assert desktop.visited == []


def test_previous_document_block_does_not_hide_later_navigation_error():
    from playwright.sync_api import Error

    page, session = Mock(), Mock()
    session.send.return_value = {"frameTree": {"frame": {"id": "main"}}}
    desktop = E2BDesktop(page, session, GRANT)
    desktop._request_paused({
        "requestId": "old", "frameId": "main", "resourceType": "Document",
        "request": {"url": "https://evil.example/", "method": "GET"},
    })
    page.goto.side_effect = Error("Connection failed")
    with pytest.raises(Error, match="Connection failed"):
        desktop.navigate("https://en.wikipedia.org/")


@pytest.mark.parametrize("websocket", [False, True])
def test_relay_translates_external_host_and_preserves_websocket_upgrade(websocket):
    namespace = {"__name__": "relay_test"}
    exec(compile(RELAY, "<relay>", "exec"), namespace)
    upgrade = b"Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: test-key\r\n" if websocket else b""
    request = (b"GET /json/version HTTP/1.1\r\nhOsT: private.e2b.app\r\n"
               b"e2b-traffic-access-token: secret-test\r\n" + upgrade + b"\r\n" + b"trailing-bytes")
    forwarded = namespace["chrome_request"](request)
    assert b"Host: 127.0.0.1:9222\r\n" in forwarded
    assert b"private.e2b.app" not in forwarded
    assert b"secret-test" not in forwarded
    assert upgrade in forwarded
    assert forwarded.endswith(b"\r\n\r\ntrailing-bytes")


def test_browser_exiting_early_reports_log(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/chromium" if name == "chromium" else None)
    process = Mock()
    process.poll.return_value = 1
    launch = Mock(return_value=process)
    monkeypatch.setattr("subprocess.Popen", launch)
    monkeypatch.setattr("builtins.open", mock_open())
    monkeypatch.setattr("pathlib.Path.read_text", lambda *args, **kwargs: "Missing X server")
    monkeypatch.setattr("time.sleep", lambda seconds: None)
    with pytest.raises(RuntimeError, match="Missing X server"):
        exec(compile(START_BROWSER, "<browser-startup>", "exec"), {})
    assert launch.call_args.args[0][0] == "/usr/bin/chromium"


def test_readiness_disconnect_reports_browser_and_relay_logs(monkeypatch):
    opener = Mock()
    opener.open.side_effect = RemoteDisconnected("Remote end closed connection")
    monkeypatch.setattr("urllib.request.build_opener", lambda *args: opener)
    times = iter([0, 21])
    monkeypatch.setattr("time.monotonic", lambda: next(times))
    monkeypatch.setattr("pathlib.Path.exists", lambda self: True)
    monkeypatch.setattr("pathlib.Path.read_text", lambda self, **kwargs: "startup diagnostic")
    with pytest.raises(RuntimeError) as error:
        exec(compile(WAIT_READY, "<browser-readiness>", "exec"), {})
    assert "RemoteDisconnected" in str(error.value)
    assert "chrome: startup diagnostic" in str(error.value)
    assert "relay: startup diagnostic" in str(error.value)


def test_browser_startup_waits_for_direct_debugger_after_slow_launch(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/chromium")
    child = Mock()
    child.poll.return_value = None
    monkeypatch.setattr("subprocess.Popen", Mock(return_value=child))
    monkeypatch.setattr("builtins.open", mock_open())
    opener = Mock()
    response = Mock()
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    opener.open.side_effect = [ConnectionRefusedError("starting"), ConnectionRefusedError("still starting"), response]
    monkeypatch.setattr("urllib.request.build_opener", lambda *args: opener)
    seconds = iter([0, 1, 30])
    monkeypatch.setattr("time.monotonic", lambda: next(seconds))
    monkeypatch.setattr("time.sleep", lambda seconds: None)

    exec(compile(START_BROWSER, "<browser-startup>", "exec"), {})

    assert opener.open.call_count == 3
    opener.open.assert_called_with("http://127.0.0.1:9222/json/version", timeout=1)


def test_browser_startup_timeout_reports_direct_port_and_log(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/chromium")
    child = Mock()
    child.poll.return_value = None
    monkeypatch.setattr("subprocess.Popen", Mock(return_value=child))
    monkeypatch.setattr("builtins.open", mock_open())
    monkeypatch.setattr("pathlib.Path.read_text", lambda *args, **kwargs: "browser startup diagnostic")
    opener = Mock()
    opener.open.side_effect = ConnectionRefusedError("not listening")
    monkeypatch.setattr("urllib.request.build_opener", lambda *args: opener)
    seconds = iter([0, 46])
    monkeypatch.setattr("time.monotonic", lambda: next(seconds))

    with pytest.raises(RuntimeError, match="port 9222") as error:
        exec(compile(START_BROWSER, "<browser-startup>", "exec"), {})
    assert "browser startup diagnostic" in str(error.value)


@pytest.mark.parametrize("url,kind,method,allowed", [
    ("https://en.wikipedia.org/wiki/Boston", "Document", "GET", True),
    ("https://127.0.0.1:8000/runs", "Document", "GET", False),
    ("http://169.254.169.254/", "Document", "GET", False),
    ("https://en.wikipedia.org@evil.com/", "Document", "GET", False),
    ("https://en.wikipedia.org/style.css", "Stylesheet", "GET", False),
    ("https://en.wikipedia.org/", "Document", "POST", False),
    ("https://[invalid/", "Document", "GET", False),
])
def test_browser_requests_checked_before_continuation(url, kind, method, allowed):
    page, session = Mock(), Mock()
    desktop = E2BDesktop(page, session, GRANT)
    desktop._request_paused({"requestId": "one", "resourceType": kind,
                             "request": {"url": url, "method": method}})
    if allowed:
        session.send.assert_called_with("Fetch.continueRequest", {"requestId": "one"})
        assert desktop.blocked_requests == []
    else:
        session.send.assert_called_with("Fetch.failRequest", {
            "requestId": "one", "errorReason": "BlockedByClient"})
        assert desktop.blocked_requests == [url]


def test_redirect_destination_is_checked_as_another_paused_request():
    session = Mock()
    desktop = E2BDesktop(Mock(), session, GRANT)
    for identifier, url in [("first", "https://en.wikipedia.org/"),
                            ("redirect", "http://169.254.169.254/")]:
        desktop._request_paused({"requestId": identifier, "resourceType": "Document",
                                 "request": {"url": url, "method": "GET"}})
    assert desktop.blocked_requests == ["http://169.254.169.254/"]
    session.send.assert_called_with("Fetch.failRequest", {
        "requestId": "redirect", "errorReason": "BlockedByClient"})


def test_navigation_and_observation_are_bounded():
    page = Mock()
    page.url = "about:blank"
    desktop = E2BDesktop(page, Mock(), GRANT, max_chars=5)
    assert desktop.observe().url is None
    with pytest.raises(ValueError):
        desktop.navigate("https://evil.com/")
    page.goto.assert_not_called()
    page.url = "https://en.wikipedia.org/wiki/Boston"
    desktop.navigate(page.url)
    page.locator.return_value.count.return_value = 0
    page.locator.return_value.inner_text.return_value = "Boston is the capital"
    page.locator.return_value.locator.return_value.evaluate_all.return_value = []
    assert desktop.observe().text == "Bosto\n[Page text truncated]"
    assert desktop.visited == [page.url]


def test_remote_setup_failure_still_destroys_sandbox():
    factory = Mock()
    factory.create.return_value.commands.run.side_effect = RuntimeError("Chrome failed")
    with pytest.raises(RuntimeError, match="Chrome failed"):
        with open_e2b_desktop(GRANT, sandbox_type=factory, playwright_factory=Mock()):
            pytest.fail("Setup should fail before yielding")
    factory.create.return_value.kill.assert_called_once_with()
    assert factory.create.call_args.kwargs["network"] == {
        "deny_out": ["0.0.0.0/0"], "allow_out": ["en.wikipedia.org"],
        "allow_public_traffic": False,
    }


def test_body_failure_closes_browser_and_sandbox(monkeypatch):
    factory, playwright_factory = Mock(), Mock()
    sandbox = factory.create.return_value
    sandbox.get_host.return_value = "private.e2b.app"
    sandbox.traffic_access_token = "test-token"
    response = Mock()
    response.json.return_value = {"webSocketDebuggerUrl": "ws://localhost:9222/devtools/browser/test"}
    get = Mock(return_value=response)
    monkeypatch.setattr("httpx.get", get)
    playwright = Mock()
    # Mock context-manager magic methods explicitly.
    manager = Mock()
    manager.__enter__ = Mock(return_value=playwright)
    manager.__exit__ = Mock(return_value=False)
    playwright_factory.return_value = manager
    browser = playwright.chromium.connect_over_cdp.return_value
    with pytest.raises(RuntimeError, match="model failed"):
        with open_e2b_desktop(GRANT, sandbox_type=factory, playwright_factory=playwright_factory) as desktop:
            desktop._screenshot_provider()
            sandbox.screenshot.assert_called_once_with(format="bytes")
            raise RuntimeError("model failed")
    browser.close.assert_called_once_with()
    sandbox.kill.assert_called_once_with()
    playwright.chromium.connect_over_cdp.assert_called_once_with(
        "wss://private.e2b.app/devtools/browser/test",
        headers={"e2b-traffic-access-token": "test-token"}, timeout=20000,
    )
