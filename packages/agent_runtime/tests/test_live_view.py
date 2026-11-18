# Import asyncio: runs concurrent async tasks for streaming and coordination.
import asyncio
# Import from contextlib: asynccontextmanager (turns an async generator into an async with-block
# resource lifetime); contextmanager (turns a generator into a with-block resource lifetime).
from contextlib import asynccontextmanager, contextmanager
# Import from pathlib: Path (represents filesystem paths and explicit file operations).
from pathlib import Path
# Import runpy: use this module through its namespace.
import runpy
# Import sys: provides process details and standard input/output streams.
import sys
# Import from types: SimpleNamespace (builds a small object with named attributes for test
# fixtures).
from types import SimpleNamespace
# Import from unittest.mock: Mock (supplies configurable fake attributes and call recording).
from unittest.mock import Mock

# Import from fastapi.testclient: TestClient (drives the real ASGI app locally without a live HTTP
# server).
from fastapi.testclient import TestClient
# Import httpx: makes HTTP requests or supplies mock HTTP transports in tests.
import httpx
# Import pytest: provides test discovery, fixtures, parametrization, and exception assertions.
import pytest
# Import from starlette.websockets: WebSocketDisconnect (a dependency used below).
from starlette.websockets import WebSocketDisconnect

# Import from crescendo_agent.live_view: LiveViewHandle (a dependency used below); create_viewer_app
# (a dependency used below); open_live_view (owns the authenticated loopback viewer and VNC stream
# lifetime).
from crescendo_agent.live_view import LiveViewHandle, create_viewer_app, open_live_view
# Import from crescendo_agent.e2b_desktop: E2BDesktop (a dependency used below).
from crescendo_agent.e2b_desktop import E2BDesktop
# Import from crescendo_security.policy: TaskGrant (holds the task identity and immutable tool/host
# allowlists).
from crescendo_security.policy import TaskGrant

# Set ORIGIN to 'http://127.0.0.1:34567'.
ORIGIN = "http://127.0.0.1:34567"


def test_concurrent_viewer_cookies_are_isolated_on_the_same_local_host():
    upstream = httpx.MockTransport(lambda request: httpx.Response(200, content=b"viewer"))
    first = create_viewer_app("stream.e2b.app", "traffic", "vnc", "first-secret", ORIGIN,
                              transport=upstream, cookie_name="viewer_one", cookie_max_age=600)
    second = create_viewer_app("stream.e2b.app", "traffic", "vnc", "second-secret", ORIGIN,
                               transport=upstream, cookie_name="viewer_two", cookie_max_age=600)
    with TestClient(first, base_url=ORIGIN) as a, TestClient(second, base_url=ORIGIN) as b:
        response = a.get("/watch/first-secret", follow_redirects=False)
        assert "Max-Age=600" in response.headers["set-cookie"]
        b.get("/watch/second-secret", follow_redirects=False)
        # A browser shares both cookies across localhost ports.
        a.cookies.update(b.cookies)
        b.cookies.update(a.cookies)
        assert a.get("/vnc.html").status_code == 200
        assert b.get("/vnc.html").status_code == 200


def test_reloaded_connection_survives_old_connections_delayed_close(monkeypatch):
    captured = {}
    listener = Mock()
    listener.getsockname.return_value = ("127.0.0.1", 34567)
    monkeypatch.setattr("crescendo_agent.live_view.socket.socket", Mock(return_value=listener))

    def viewer_app(*args, **kwargs):
        captured.update(kwargs)
        return Mock()

    monkeypatch.setattr("crescendo_agent.live_view.create_viewer_app", viewer_app)
    monkeypatch.setattr("crescendo_agent.live_view.uvicorn.Server", lambda config: SimpleNamespace(
        started=True, should_exit=False, run=lambda **kwargs: None))
    sandbox = Mock()
    sandbox.stream.get_url.return_value = "https://stream.e2b.app"
    with open_live_view(sandbox, cookie_max_age=600) as handle:
        captured["on_connected"]()  # original frame
        captured["on_connected"]()  # reloaded frame connected before the old one closes
        captured["on_disconnected"]()
        assert handle.connected.is_set()
        captured["on_disconnected"]()
        assert not handle.connected.is_set()
        assert captured["cookie_name"] == "crescendo_viewer_34567"
        assert captured["cookie_max_age"] == 600


def test_failed_upstream_handshake_does_not_disconnect_an_existing_viewer(monkeypatch):
    events = []

    @asynccontextmanager
    async def fail(*args, **kwargs):
        raise RuntimeError("private-upstream-details")
        yield

    monkeypatch.setattr("crescendo_agent.live_view.connect", fail)
    app = create_viewer_app("stream.e2b.app", "traffic", "vnc", "secret", ORIGIN,
        on_connected=lambda: events.append("connected"), on_disconnected=lambda: events.append("disconnected"),
        on_error=lambda code: events.append("safe-error"))
    with TestClient(app, base_url=ORIGIN) as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(ORIGIN.replace("http://", "ws://") + "/websockify", headers={"origin": ORIGIN, "cookie": "crescendo_viewer=secret"}):
                pass
    assert events == ["safe-error"]


# Define app_with_transport with parameters handler.
def app_with_transport(handler):
    return create_viewer_app("stream.e2b.app", "private-traffic-token", "vnc-password",
                             # Pass keyword transport = httpx.MockTransport(handler).
                             "local-secret", ORIGIN, transport=httpx.MockTransport(handler))


# Define test_viewer_authentication_and_fixed_host_proxy with no parameters.
def test_viewer_authentication_and_fixed_host_proxy():
    # Set requests to an empty list.
    requests = []
    # Define upstream with parameters request.
    def upstream(request):
        # Append request to requests.
        requests.append(request)
        # Return httpx.Response(200, content=b'viewer asset', headers={'content-type':
        # 'text/javascript'}).
        return httpx.Response(200, content=b"viewer asset", headers={"content-type": "text/javascript"})
    # Use TestClient(app_with_transport(upstream), base_url=ORIGIN) as client; leave the context and
    # run its cleanup when this block ends.
    with TestClient(app_with_transport(upstream), base_url=ORIGIN) as client:
        # Assert that client.get('/vnc.html').status_code equals 403. If false, this check fails
        # with AssertionError.
        assert client.get("/vnc.html").status_code == 403
        # Assert that client.get('/watch/wrong').status_code equals 403. If false, this check fails
        # with AssertionError.
        assert client.get("/watch/wrong").status_code == 403
        # Assert that requests equals a new list (empty). If false, this check fails with
        # AssertionError.
        assert requests == []
        # Set response to client.get('/watch/local-secret', follow_redirects=False).
        response = client.get("/watch/local-secret", follow_redirects=False)
        # Assert that response.status_code equals 307. If false, this check fails with
        # AssertionError.
        assert response.status_code == 307
        # Assert that 'password=vnc-password' is in response.headers['location']. If false, this
        # check fails with AssertionError.
        assert "password=vnc-password" in response.headers["location"]
        # Assert that 'HttpOnly' is in response.headers['set-cookie']. If false, this check fails
        # with AssertionError.
        assert "HttpOnly" in response.headers["set-cookie"]
        # Assert that 'SameSite=strict' is in response.headers['set-cookie']. If false, this check
        # fails with AssertionError.
        assert "SameSite=strict" in response.headers["set-cookie"]
        # Assert that response.headers['referrer-policy'] equals 'no-referrer'. If false, this check
        # fails with AssertionError.
        assert response.headers["referrer-policy"] == "no-referrer"
        # Set response to client.get('/app/ui.js', headers={'Authorization': 'Bearer user-header'}).
        response = client.get("/app/ui.js", headers={"Authorization": "Bearer user-header"})
        # Assert that response.status_code equals 200. If false, this check fails with
        # AssertionError.
        assert response.status_code == 200
        # Assert that response.content equals b'viewer asset'. If false, this check fails with
        # AssertionError.
        assert response.content == b"viewer asset"
        # Assert that response.headers['cache-control'] equals 'no-store'. If false, this check
        # fails with AssertionError.
        assert response.headers["cache-control"] == "no-store"
        # Assert that 'private-traffic-token' is not in response.text. If false, this check fails
        # with AssertionError.
        assert "private-traffic-token" not in response.text
        # Assert that requests[0].url.host equals 'stream.e2b.app'. If false, this check fails with
        # AssertionError.
        assert requests[0].url.host == "stream.e2b.app"
        # Assert that requests[0].headers['e2b-traffic-access-token'] equals
        # 'private-traffic-token'. If false, this check fails with AssertionError.
        assert requests[0].headers["e2b-traffic-access-token"] == "private-traffic-token"
        # Assert that 'cookie' is not in requests[0].headers. If false, this check fails with
        # AssertionError.
        assert "cookie" not in requests[0].headers
        # Assert that 'authorization' is not in requests[0].headers. If false, this check fails with
        # AssertionError.
        assert "authorization" not in requests[0].headers
        # Assert that client.get('/vnc.html', headers={'Host': 'evil.example'}).status_code equals
        # 400. If false, this check fails with AssertionError.
        assert client.get("/vnc.html", headers={"Host": "evil.example"}).status_code == 400


# Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("status", [302, 401, 500])
# Define test_upstream_errors_and_redirects_do_not_leak_details with parameters status.
def test_upstream_errors_and_redirects_do_not_leak_details(status):
    # Define upstream with parameters request.
    def upstream(request):
        # Return httpx.Response(status, text='private-traffic-token', headers={'location':
        # 'https://evil.example/'}).
        return httpx.Response(status, text="private-traffic-token", headers={"location": "https://evil.example/"})
    # Use TestClient(app_with_transport(upstream), base_url=ORIGIN) as client; leave the context and
    # run its cleanup when this block ends.
    with TestClient(app_with_transport(upstream), base_url=ORIGIN) as client:
        # Call client.get with '/watch/local-secret'.
        client.get("/watch/local-secret", follow_redirects=False)
        # Set response to client.get('/vnc.html').
        response = client.get("/vnc.html")
        # Assert that response.status_code equals 502. If false, this check fails with
        # AssertionError.
        assert response.status_code == 502
        # Assert that 'private-traffic-token' is not in response.text. If false, this check fails
        # with AssertionError.
        assert "private-traffic-token" not in response.text
        # Assert that 'location' is not in response.headers. If false, this check fails with
        # AssertionError.
        assert "location" not in response.headers


# Define test_websocket_requires_cookie_and_same_origin with parameters monkeypatch.
def test_websocket_requires_cookie_and_same_origin(monkeypatch):
    # Set connect to Mock().
    connect = Mock()
    # Call monkeypatch.setattr with 'crescendo_agent.live_view.connect', connect.
    monkeypatch.setattr("crescendo_agent.live_view.connect", connect)
    # Use TestClient(app_with_transport(lambda r: httpx.Response(200)), base_url=ORIGIN) as client;
    # leave the context and run its cleanup when this block ends.
    with TestClient(app_with_transport(lambda r: httpx.Response(200)), base_url=ORIGIN) as client:
        # Use pytest.raises(WebSocketDisconnect); leave the context and run its cleanup when this
        # block ends.
        with pytest.raises(WebSocketDisconnect):
            # Use client.websocket_connect(ORIGIN.replace('http://', 'ws://') + '/websockify',
            # headers={'origin': ORIGIN}); leave the context and run its cleanup when this block
            # ends.
            with client.websocket_connect(ORIGIN.replace("http://", "ws://") + "/websockify", headers={"origin": ORIGIN}):
                pass
        # Call client.get with '/watch/local-secret'.
        client.get("/watch/local-secret", follow_redirects=False)
        # Use pytest.raises(WebSocketDisconnect); leave the context and run its cleanup when this
        # block ends.
        with pytest.raises(WebSocketDisconnect):
            # Use client.websocket_connect(ORIGIN.replace('http://', 'ws://') + '/websockify',
            # headers={'origin': 'http://evil.example'}); leave the context and run its cleanup when
            # this block ends.
            with client.websocket_connect(ORIGIN.replace("http://", "ws://") + "/websockify", headers={"origin": "http://evil.example"}):
                pass
    # Call connect.assert_not_called with no arguments.
    connect.assert_not_called()


# Define test_websocket_forwards_binary_data_and_authenticates_upstream with parameters monkeypatch.
def test_websocket_forwards_binary_data_and_authenticates_upstream(monkeypatch):
    # Set connections to an empty list.
    connections = []
    # Define Remote.
    class Remote:
        # Set subprotocol to 'binary'.
        subprotocol = "binary"
        # Define __init__ with parameters self.
        def __init__(self):
            # Set self.messages to asyncio.Queue().
            self.messages = asyncio.Queue()
            # Call self.messages.put_nowait with b'RFB fixture'.
            self.messages.put_nowait(b"RFB fixture")
        # Define send with parameters self, message.
        async def send(self, message):
            # Await completion without blocking the event loop: Call self.messages.put with the
            # arguments shown.
            await self.messages.put(message)
        # Define __aiter__ with parameters self.
        def __aiter__(self):
            # Return self.
            return self
        # Define __anext__ with parameters self.
        async def __anext__(self):
            # Return await self.messages.get().
            return await self.messages.get()

    # Wrap the generator as a context manager: yield enters the with-block and exit resumes cleanup.
    @asynccontextmanager
    # Define connect with parameters url.
    async def connect(url, **kwargs):
        # Append (url, kwargs) to connections.
        connections.append((url, kwargs))
        # Give Remote() to the caller and pause here until execution resumes.
        yield Remote()
    # Call monkeypatch.setattr with 'crescendo_agent.live_view.connect', connect.
    monkeypatch.setattr("crescendo_agent.live_view.connect", connect)
    # Use TestClient(app_with_transport(lambda r: httpx.Response(200)), base_url=ORIGIN) as client;
    # leave the context and run its cleanup when this block ends.
    with TestClient(app_with_transport(lambda r: httpx.Response(200)), base_url=ORIGIN) as client:
        # Call client.get with '/watch/local-secret'.
        client.get("/watch/local-secret", follow_redirects=False)
        # Use client.websocket_connect(ORIGIN.replace('http://', 'ws://') + '/websockify',
        # headers={'origin': ORIGIN}, subprotocols=['binary']) as ws; leave the context and run its
        # cleanup when this block ends.
        with client.websocket_connect(ORIGIN.replace("http://", "ws://") + "/websockify", headers={"origin": ORIGIN}, subprotocols=["binary"]) as ws:
            # Assert that ws.receive_bytes() equals b'RFB fixture'. If false, this check fails with
            # AssertionError.
            assert ws.receive_bytes() == b"RFB fixture"
            # Call ws.send_bytes with b'client message'.
            ws.send_bytes(b"client message")
            # Assert that ws.receive_bytes() equals b'client message'. If false, this check fails
            # with AssertionError.
            assert ws.receive_bytes() == b"client message"
    # Assert that connections[0][0] equals 'wss://stream.e2b.app/websockify'. If false, this check
    # fails with AssertionError.
    assert connections[0][0] == "wss://stream.e2b.app/websockify"
    # Assert that connections[0][1]['additional_headers'] equals a new dictionary with keys
    # 'e2b-traffic-access-token'. If false, this check fails with AssertionError.
    assert connections[0][1]["additional_headers"] == {"e2b-traffic-access-token": "private-traffic-token"}


# Define test_viewer_grant_is_required_before_provider_call with no parameters.
def test_viewer_grant_is_required_before_provider_call():
    # Set provider to Mock().
    provider = Mock()
    # Set desktop to E2BDesktop(Mock(), Mock(), TaskGrant('no-view', frozenset(), frozenset()),
    # viewer_provider=provider).
    desktop = E2BDesktop(Mock(), Mock(), TaskGrant("no-view", frozenset(), frozenset()), viewer_provider=provider)
    # Use pytest.raises(ValueError, match='not permitted'); leave the context and run its cleanup
    # when this block ends.
    with pytest.raises(ValueError, match="not permitted"):
        # Call desktop.live_view with no arguments.
        desktop.live_view()
    # Call provider.assert_not_called with no arguments.
    provider.assert_not_called()


# Define test_stream_stops_when_local_server_setup_fails with parameters monkeypatch.
def test_stream_stops_when_local_server_setup_fails(monkeypatch):
    # Set sandbox to Mock().
    sandbox = Mock()
    # Set sandbox.stream.get_url.return_value to 'https://stream.e2b.app/vnc.html'.
    sandbox.stream.get_url.return_value = "https://stream.e2b.app/vnc.html"
    # Set sandbox.stream.get_auth_key.return_value to 'vnc-password'.
    sandbox.stream.get_auth_key.return_value = "vnc-password"
    # Set sandbox.traffic_access_token to 'traffic-token'.
    sandbox.traffic_access_token = "traffic-token"
    # Set listener to Mock().
    listener = Mock()
    # Set listener.getsockname.return_value to ('127.0.0.1', 34567).
    listener.getsockname.return_value = ("127.0.0.1", 34567)
    # Call monkeypatch.setattr with 'crescendo_agent.live_view.socket.socket',
    # Mock(return_value=listener).
    monkeypatch.setattr("crescendo_agent.live_view.socket.socket", Mock(return_value=listener))
    # Call monkeypatch.setattr with 'crescendo_agent.live_view.uvicorn.Config',
    # Mock(side_effect=RuntimeError('bad config')).
    monkeypatch.setattr("crescendo_agent.live_view.uvicorn.Config", Mock(side_effect=RuntimeError("bad config")))
    # Use pytest.raises(RuntimeError, match='bad config'); leave the context and run its cleanup
    # when this block ends.
    with pytest.raises(RuntimeError, match="bad config"):
        # Use open_live_view(sandbox); leave the context and run its cleanup when this block ends.
        with open_live_view(sandbox):
            # Call pytest.fail with 'Must not yield'.
            pytest.fail("Must not yield")
    # Call sandbox.stream.start.assert_called_once_with with no arguments.
    sandbox.stream.start.assert_called_once_with(require_auth=True)
    # Call sandbox.stream.stop.assert_called_once_with with no arguments.
    sandbox.stream.stop.assert_called_once_with()
    # Call listener.close.assert_called_once_with with no arguments.
    listener.close.assert_called_once_with()


# Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("wait_fails", [False, True])
# Define test_watch_demo_waits_before_agent_and_cleans_up with parameters monkeypatch, wait_fails.
def test_watch_demo_waits_before_agent_and_cleans_up(monkeypatch, wait_fails):
    # Call monkeypatch.setenv with 'E2B_API_KEY', 'offline-key'.
    monkeypatch.setenv("E2B_API_KEY", "offline-key")
    # Call monkeypatch.setenv with 'GROQ_API_KEY', 'offline-key'.
    monkeypatch.setenv("GROQ_API_KEY", "offline-key")
    # Call monkeypatch.setattr with sys, 'argv', ['e2b_vision_agent_demo.py', '--watch'].
    monkeypatch.setattr(sys, "argv", ["e2b_vision_agent_demo.py", "--watch"])
    # Call monkeypatch.setattr with 'secrets.token_hex', a function that returns 'abc123' when
    # called.
    monkeypatch.setattr("secrets.token_hex", lambda n: "abc123")
    # Set events to an empty list.
    events = []
    # Set desktop to Mock().
    desktop = Mock()

    # Wrap the generator as a context manager: yield enters the with-block and exit resumes cleanup.
    @contextmanager
    # Define viewer with no parameters.
    def viewer():
        # Append 'viewer started' to events.
        events.append("viewer started")
        # Try the following operations; matching except clauses handle failures. The finally block
        # runs on every exit.
        try:
            # Give SimpleNamespace(url="http://127.0.0.1:34567/watch/fixture") to the caller and
            # pause here until execution resumes.
            yield SimpleNamespace(url="http://127.0.0.1:34567/watch/fixture")
        # Always run cleanup, whether the operation succeeds, returns, or raises.
        finally:
            # Append 'viewer stopped' to events.
            events.append("viewer stopped")

    # Wrap the generator as a context manager: yield enters the with-block and exit resumes cleanup.
    @contextmanager
    # Define open_desktop with parameters grant.
    def open_desktop(grant):
        # Assert that 'view_desktop' is in grant.allowed_tools. If false, this check fails with
        # AssertionError.
        assert "view_desktop" in grant.allowed_tools
        # Try the following operations; matching except clauses handle failures. The finally block
        # runs on every exit.
        try:
            # Give desktop to the caller and pause here until execution resumes.
            yield desktop
        # Always run cleanup, whether the operation succeeds, returns, or raises.
        finally:
            # Append 'desktop stopped' to events.
            events.append("desktop stopped")

    # Set desktop.live_view.side_effect to viewer.
    desktop.live_view.side_effect = viewer
    # Call monkeypatch.setattr with 'crescendo_agent.e2b_desktop.open_e2b_desktop', open_desktop.
    monkeypatch.setattr("crescendo_agent.e2b_desktop.open_e2b_desktop", open_desktop)
    # Call monkeypatch.setattr with 'crescendo_agent.vision.GroqVision', a function that returns
    # SimpleNamespace(model=name) when called.
    monkeypatch.setattr("crescendo_agent.vision.GroqVision", lambda name: SimpleNamespace(model=name))
    # Define run with no parameters.
    def run(*args, **kwargs):
        # Append 'agent started' to events.
        events.append("agent started")
        # Return SimpleNamespace(status='finished', answer='ABC123', denied=[], transcript=[]).
        return SimpleNamespace(status="finished", answer="ABC123", denied=[], transcript=[])
    # Call monkeypatch.setattr with 'crescendo_agent.vision_loop.run_vision_agent', run.
    monkeypatch.setattr("crescendo_agent.vision_loop.run_vision_agent", run)
    # Call monkeypatch.setattr with 'webbrowser.open', a function that returns
    # events.append('browser opened') when called.
    monkeypatch.setattr("webbrowser.open", lambda url: events.append("browser opened"))
    # Set script to Path(__file__).resolve().parents[3] divided by 'scripts' divided by
    # 'e2b_vision_agent_demo.py'.
    script = Path(__file__).resolve().parents[3] / "scripts" / "e2b_vision_agent_demo.py"
    # Set main to runpy.run_path(str(script))['main'].
    main = runpy.run_path(str(script))["main"]
    # Define wait with parameters viewer.
    def wait(viewer):
        # Append 'waited for user' to events.
        events.append("waited for user")
        # Check whether wait_fails.
        if wait_fails:
            # Raise TimeoutError('expired') to stop the normal path.
            raise TimeoutError("expired")
    # The script imports the shared helper inside its --watch branch, at call time.
    # Call monkeypatch.setattr with 'crescendo_agent.live_view.wait_for_viewer', wait.
    monkeypatch.setattr("crescendo_agent.live_view.wait_for_viewer", wait)
    # Check whether wait_fails.
    if wait_fails:
        # Use pytest.raises(TimeoutError, match='expired'); leave the context and run its cleanup
        # when this block ends.
        with pytest.raises(TimeoutError, match="expired"):
            # Call main with no arguments.
            main()
    # Run this alternative only when the preceding conditional did not select its first branch.
    else:
        # Call main with no arguments.
        main()
    # Set expected to ['viewer started', 'browser opened', 'waited for user'].
    expected = ["viewer started", "browser opened", "waited for user"]
    # Check whether not (wait_fails).
    if not wait_fails:
        # Append 'agent started' to expected.
        expected.append("agent started")
    # Assert that events equals expected plus a new list containing 'viewer stopped', 'desktop
    # stopped'. If false, this check fails with AssertionError.
    assert events == expected + ["viewer stopped", "desktop stopped"]


# Define test_viewer_connection_gate_reports_error_without_waiting_for_model with no parameters.
def test_viewer_connection_gate_reports_error_without_waiting_for_model():
    # Set handle to LiveViewHandle('http://127.0.0.1/viewer').
    handle = LiveViewHandle("http://127.0.0.1/viewer")
    # Append 'UPSTREAM_WEBSOCKET_HTTP_401' to handle.errors.
    handle.errors.append("UPSTREAM_WEBSOCKET_HTTP_401")
    # Use pytest.raises(RuntimeError, match='UPSTREAM_WEBSOCKET_HTTP_401'); leave the context and
    # run its cleanup when this block ends.
    with pytest.raises(RuntimeError, match="UPSTREAM_WEBSOCKET_HTTP_401"):
        # Call handle.wait_connected with no arguments.
        handle.wait_connected()
    # Call handle.errors.clear with no arguments.
    handle.errors.clear()
    # Call handle.connected.set with no arguments.
    handle.connected.set()
    # Call handle.wait_connected with no arguments.
    handle.wait_connected()


# Define test_proxy_reports_sanitized_upstream_connection_failure with parameters monkeypatch.
def test_proxy_reports_sanitized_upstream_connection_failure(monkeypatch):
    # Set errors to an empty list.
    errors = []
    # Wrap the generator as a context manager: yield enters the with-block and exit resumes cleanup.
    @asynccontextmanager
    # Define connect with no parameters.
    async def connect(*args, **kwargs):
        # Raise OSError('sensitive-traffic-token should not be logged') to stop the normal path.
        raise OSError("sensitive-traffic-token should not be logged")
        # Yield None (no value) to the with-block/request; resume here for cleanup afterward.
        yield
    # Call monkeypatch.setattr with 'crescendo_agent.live_view.connect', connect.
    monkeypatch.setattr("crescendo_agent.live_view.connect", connect)
    # Set app to create_viewer_app('stream.e2b.app', 'traffic-token', 'vnc-password',
    # 'local-secret', ORIGIN, on_error=errors.append).
    app = create_viewer_app("stream.e2b.app", "traffic-token", "vnc-password", "local-secret", ORIGIN,
                            # Pass keyword on_error = errors.append.
                            on_error=errors.append)
    # Use TestClient(app, base_url=ORIGIN) as client; leave the context and run its cleanup when
    # this block ends.
    with TestClient(app, base_url=ORIGIN) as client:
        # Call client.get with '/watch/local-secret'.
        client.get("/watch/local-secret", follow_redirects=False)
        # Use pytest.raises(WebSocketDisconnect); leave the context and run its cleanup when this
        # block ends.
        with pytest.raises(WebSocketDisconnect):
            # Use client.websocket_connect(ORIGIN.replace('http://', 'ws://') + '/websockify',
            # headers={'origin': ORIGIN}); leave the context and run its cleanup when this block
            # ends.
            with client.websocket_connect(ORIGIN.replace("http://", "ws://") + "/websockify", headers={"origin": ORIGIN}):
                pass
    # Assert that errors equals a new list containing 'WEBSOCKET_TRANSPORT_ERROR'. If false, this
    # check fails with AssertionError.
    assert errors == ["WEBSOCKET_TRANSPORT_ERROR"]


# Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("typed,close,error", [
    # Add this item to the surrounding list: (b"\n", False, None), # user pressed Enter.
    (b"\n", False, None),                       # user pressed Enter
    # Add this item to the surrounding list: (b"", False, TimeoutError), # nobody pressed Enter in
    # time.
    (b"", False, TimeoutError),                 # nobody pressed Enter in time
    # Add this item to the surrounding list: (b"", True, RuntimeError), # no interactive terminal
    # (input closed).
    (b"", True, RuntimeError),                  # no interactive terminal (input closed)
])
# Define test_shared_wait_for_viewer with parameters typed, close, error.
def test_shared_wait_for_viewer(typed, close, error):
    # Import os: reads process environment/configuration and OS facilities.
    import os
    # Import from crescendo_agent.live_view: wait_for_viewer (waits for transport connection and the
    # user confirmation before agent actions).
    from crescendo_agent.live_view import wait_for_viewer
    # Set (read_fd, write_fd) to os.pipe().
    read_fd, write_fd = os.pipe()
    # Call os.write with write_fd, typed.
    os.write(write_fd, typed)
    # Check whether close.
    if close:
        os.close(write_fd)
    # Set viewer to LiveViewHandle('http://127.0.0.1/viewer').
    viewer = LiveViewHandle("http://127.0.0.1/viewer")
    # Call viewer.connected.set with no arguments.
    viewer.connected.set()
    # Use os.fdopen(read_fd) as stream; leave the context and run its cleanup when this block ends.
    with os.fdopen(read_fd) as stream:
        # Check whether error is None.
        if error is None:
            # Call wait_for_viewer with viewer.
            wait_for_viewer(viewer, timeout=1, stream=stream)
        # Run this alternative only when the preceding conditional did not select its first branch.
        else:
            # Use pytest.raises(error); leave the context and run its cleanup when this block ends.
            with pytest.raises(error):
                # Call wait_for_viewer with viewer.
                wait_for_viewer(viewer, timeout=0.05, stream=stream)
    # Check whether not (close).
    if not close:
        os.close(write_fd)
