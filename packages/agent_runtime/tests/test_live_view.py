# Learn: Import asyncio: runs concurrent async tasks for streaming and coordination.
import asyncio
# Learn: From contextlib, import asynccontextmanager (turns an async generator into an async with-block
# resource lifetime); contextmanager (turns a generator into a with-block resource lifetime).
from contextlib import asynccontextmanager, contextmanager
# Learn: From pathlib, import Path (represents filesystem paths and explicit file operations).
from pathlib import Path
# Learn: Import runpy: use this module through its namespace.
import runpy
# Learn: Import sys: provides process details and standard input/output streams.
import sys
# Learn: From types, import SimpleNamespace (builds a small object with named attributes for test fixtures).
from types import SimpleNamespace
# Learn: From unittest.mock, import Mock (supplies configurable fake attributes and call recording).
from unittest.mock import Mock

# Learn: From fastapi.testclient, import TestClient (drives the real ASGI app locally without a live HTTP
# server).
from fastapi.testclient import TestClient
# Learn: Import httpx: makes HTTP requests or supplies mock HTTP transports in tests.
import httpx
# Learn: Import pytest: provides test discovery, fixtures, parametrization, and exception assertions.
import pytest
# Learn: From starlette.websockets, import WebSocketDisconnect (a dependency used below).
from starlette.websockets import WebSocketDisconnect

# Learn: From crescendo_agent.live_view, import LiveViewHandle (a dependency used below); create_viewer_app
# (a dependency used below); open_live_view (owns the authenticated loopback viewer and VNC stream
# lifetime).
from crescendo_agent.live_view import LiveViewHandle, create_viewer_app, open_live_view
# Learn: From crescendo_agent.e2b_desktop, import E2BDesktop (a dependency used below).
from crescendo_agent.e2b_desktop import E2BDesktop
# Learn: From crescendo_security.policy, import TaskGrant (holds the task identity and immutable tool/host
# allowlists).
from crescendo_security.policy import TaskGrant

# Learn: Set ORIGIN to 'http://127.0.0.1:34567'.
ORIGIN = "http://127.0.0.1:34567"


# Learn: Define app_with_transport(handler). The body runs when called, not when defined.
def app_with_transport(handler):
    # Learn: Return create_viewer_app('stream.e2b.app', 'private-traffic-token', 'vnc-password',
    # 'local-secret', ORIGIN, transport=httpx.MockTransport(h... to the caller and stop this function.
    return create_viewer_app("stream.e2b.app", "private-traffic-token", "vnc-password",
                             # Learn: Pass keyword transport = httpx.MockTransport(handler).
                             "local-secret", ORIGIN, transport=httpx.MockTransport(handler))


# Learn: Test viewer authentication and fixed host proxy. pytest supplies named fixtures and checks
# assertions below.
def test_viewer_authentication_and_fixed_host_proxy():
    # Learn: Set requests to a new list (empty).
    requests = []
    # Learn: Define upstream(request). The body runs when called, not when defined.
    def upstream(request):
        # Learn: Append one item to the ordered collection on requests; inputs: request.
        requests.append(request)
        # Learn: Return httpx.Response(200, content=b'viewer asset', headers={'content-type':
        # 'text/javascript'}) to the caller and stop this function.
        return httpx.Response(200, content=b"viewer asset", headers={"content-type": "text/javascript"})
    # Learn: Enter TestClient(app_with_transport(upstream), base_url=ORIGIN) as client. The context manager
    # controls setup/exit; inspect it for the actual cleanup behavior.
    with TestClient(app_with_transport(upstream), base_url=ORIGIN) as client:
        # Learn: Assert that client.get('/vnc.html').status_code equals 403. If false, this check fails with
        # AssertionError.
        assert client.get("/vnc.html").status_code == 403
        # Learn: Assert that client.get('/watch/wrong').status_code equals 403. If false, this check fails
        # with AssertionError.
        assert client.get("/watch/wrong").status_code == 403
        # Learn: Assert that requests equals a new list (empty). If false, this check fails with
        # AssertionError.
        assert requests == []
        # Learn: Set response to client['/watch/local-secret'] with None as the missing-key default; the
        # returned HTTP or model-provider response. Read a key/row, using the supplied default when
        # applicable.
        response = client.get("/watch/local-secret", follow_redirects=False)
        # Learn: Assert that response.status_code equals 307. If false, this check fails with
        # AssertionError.
        assert response.status_code == 307
        # Learn: Assert that 'password=vnc-password' is in response.headers['location']. If false, this
        # check fails with AssertionError.
        assert "password=vnc-password" in response.headers["location"]
        # Learn: Assert that 'HttpOnly' is in response.headers['set-cookie']. If false, this check fails
        # with AssertionError.
        assert "HttpOnly" in response.headers["set-cookie"]
        # Learn: Assert that 'SameSite=strict' is in response.headers['set-cookie']. If false, this check
        # fails with AssertionError.
        assert "SameSite=strict" in response.headers["set-cookie"]
        # Learn: Assert that response.headers['referrer-policy'] equals 'no-referrer'. If false, this check
        # fails with AssertionError.
        assert response.headers["referrer-policy"] == "no-referrer"
        # Learn: Set response to client['/app/ui.js'] with None as the missing-key default; the returned
        # HTTP or model-provider response. Read a key/row, using the supplied default when applicable.
        response = client.get("/app/ui.js", headers={"Authorization": "Bearer user-header"})
        # Learn: Assert that response.status_code equals 200. If false, this check fails with
        # AssertionError.
        assert response.status_code == 200
        # Learn: Assert that response.content equals b'viewer asset'. If false, this check fails with
        # AssertionError.
        assert response.content == b"viewer asset"
        # Learn: Assert that response.headers['cache-control'] equals 'no-store'. If false, this check fails
        # with AssertionError.
        assert response.headers["cache-control"] == "no-store"
        # Learn: Assert that 'private-traffic-token' is not in response.text. If false, this check fails
        # with AssertionError.
        assert "private-traffic-token" not in response.text
        # Learn: Assert that requests[0].url.host equals 'stream.e2b.app'. If false, this check fails with
        # AssertionError.
        assert requests[0].url.host == "stream.e2b.app"
        # Learn: Assert that requests[0].headers['e2b-traffic-access-token'] equals 'private-traffic-token'.
        # If false, this check fails with AssertionError.
        assert requests[0].headers["e2b-traffic-access-token"] == "private-traffic-token"
        # Learn: Assert that 'cookie' is not in requests[0].headers. If false, this check fails with
        # AssertionError.
        assert "cookie" not in requests[0].headers
        # Learn: Assert that 'authorization' is not in requests[0].headers. If false, this check fails with
        # AssertionError.
        assert "authorization" not in requests[0].headers
        # Learn: Assert that client.get('/vnc.html', headers={'Host': 'evil.example'}).status_code equals
        # 400. If false, this check fails with AssertionError.
        assert client.get("/vnc.html", headers={"Host": "evil.example"}).status_code == 400


# Learn: Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("status", [302, 401, 500])
# Learn: Test upstream errors and redirects do not leak details. pytest supplies named fixtures and checks
# assertions below.
def test_upstream_errors_and_redirects_do_not_leak_details(status):
    # Learn: Define upstream(request). The body runs when called, not when defined.
    def upstream(request):
        # Learn: Return httpx.Response(status, text='private-traffic-token', headers={'location':
        # 'https://evil.example/'}) to the caller and stop this function.
        return httpx.Response(status, text="private-traffic-token", headers={"location": "https://evil.example/"})
    # Learn: Enter TestClient(app_with_transport(upstream), base_url=ORIGIN) as client. The context manager
    # controls setup/exit; inspect it for the actual cleanup behavior.
    with TestClient(app_with_transport(upstream), base_url=ORIGIN) as client:
        # Learn: Read a key/row, using the supplied default when applicable on client; inputs:
        # '/watch/local-secret'.
        client.get("/watch/local-secret", follow_redirects=False)
        # Learn: Set response to client['/vnc.html'] with None as the missing-key default; the returned HTTP
        # or model-provider response. Read a key/row, using the supplied default when applicable.
        response = client.get("/vnc.html")
        # Learn: Assert that response.status_code equals 502. If false, this check fails with
        # AssertionError.
        assert response.status_code == 502
        # Learn: Assert that 'private-traffic-token' is not in response.text. If false, this check fails
        # with AssertionError.
        assert "private-traffic-token" not in response.text
        # Learn: Assert that 'location' is not in response.headers. If false, this check fails with
        # AssertionError.
        assert "location" not in response.headers


# Learn: Test websocket requires cookie and same origin. pytest supplies named fixtures and checks
# assertions below.
def test_websocket_requires_cookie_and_same_origin(monkeypatch):
    # Learn: Set connect to Mock().
    connect = Mock()
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("crescendo_agent.live_view.connect", connect)
    # Learn: Enter TestClient(app_with_transport(lambda r: httpx.Response(200)), base_url=ORIGIN) as client.
    # The context manager controls setup/exit; inspect it for the actual cleanup behavior.
    with TestClient(app_with_transport(lambda r: httpx.Response(200)), base_url=ORIGIN) as client:
        # Learn: Enter pytest.raises(WebSocketDisconnect). The context manager controls setup/exit; inspect
        # it for the actual cleanup behavior.
        with pytest.raises(WebSocketDisconnect):
            # Learn: Enter client.websocket_connect(ORIGIN.replace('http://', 'ws://') + '/websockify',
            # headers={'origin': ORIGIN}). The context manager controls setup/exit; inspect it for the
            # actual cleanup behavior.
            with client.websocket_connect(ORIGIN.replace("http://", "ws://") + "/websockify", headers={"origin": ORIGIN}):
                # Learn: No operation: this body intentionally needs no executable statement.
                pass
        # Learn: Read a key/row, using the supplied default when applicable on client; inputs:
        # '/watch/local-secret'.
        client.get("/watch/local-secret", follow_redirects=False)
        # Learn: Enter pytest.raises(WebSocketDisconnect). The context manager controls setup/exit; inspect
        # it for the actual cleanup behavior.
        with pytest.raises(WebSocketDisconnect):
            # Learn: Enter client.websocket_connect(ORIGIN.replace('http://', 'ws://') + '/websockify',
            # headers={'origin': 'http://evil.example'}). The context manager controls setup/exit; inspect
            # it for the actual cleanup behavior.
            with client.websocket_connect(ORIGIN.replace("http://", "ws://") + "/websockify", headers={"origin": "http://evil.example"}):
                # Learn: No operation: this body intentionally needs no executable statement.
                pass
    # Learn: Verify the denied/error path never invoked this fake dependency on connect.
    connect.assert_not_called()


# Learn: Test websocket forwards binary data and authenticates upstream. pytest supplies named fixtures and
# checks assertions below.
def test_websocket_forwards_binary_data_and_authenticates_upstream(monkeypatch):
    # Learn: Set connections to a new list (empty).
    connections = []
    # Learn: Define Remote. This test double replaces an external dependency.
    class Remote:
        # Learn: Set subprotocol to 'binary'.
        subprotocol = "binary"
        # Learn: Define __init__(). This initializes or validates each new instance.
        def __init__(self):
            # Learn: Set self.messages to asyncio.Queue().
            self.messages = asyncio.Queue()
            # Learn: Call self.messages.put_nowait with the arguments shown.
            self.messages.put_nowait(b"RFB fixture")
        # Learn: Define an async function send(message). Awaited calls can yield control to other work. The
        # body runs when called, not when defined.
        async def send(self, message):
            # Learn: Await completion without blocking the event loop: Call self.messages.put with the
            # arguments shown.
            await self.messages.put(message)
        # Learn: Define __aiter__(). The body runs when called, not when defined.
        def __aiter__(self):
            # Learn: Return self to the caller and stop this function.
            return self
        # Learn: Define an async function __anext__(). Awaited calls can yield control to other work. The
        # body runs when called, not when defined.
        async def __anext__(self):
            # Learn: Return await self.messages.get() to the caller and stop this function.
            return await self.messages.get()

    # Learn: Wrap the generator as a context manager: yield enters the with-block and exit resumes cleanup.
    @asynccontextmanager
    # Learn: Define an async function connect(url). Awaited calls can yield control to other work. The body
    # runs when called, not when defined.
    async def connect(url, **kwargs):
        # Learn: Append one item to the ordered collection on connections; inputs: the tuple (url, kwargs)
        # (positional values).
        connections.append((url, kwargs))
        # Learn: Yield Remote() to the with-block/request; resume here for cleanup afterward.
        yield Remote()
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("crescendo_agent.live_view.connect", connect)
    # Learn: Enter TestClient(app_with_transport(lambda r: httpx.Response(200)), base_url=ORIGIN) as client.
    # The context manager controls setup/exit; inspect it for the actual cleanup behavior.
    with TestClient(app_with_transport(lambda r: httpx.Response(200)), base_url=ORIGIN) as client:
        # Learn: Read a key/row, using the supplied default when applicable on client; inputs:
        # '/watch/local-secret'.
        client.get("/watch/local-secret", follow_redirects=False)
        # Learn: Enter client.websocket_connect(ORIGIN.replace('http://', 'ws://') + '/websockify',
        # headers={'origin': ORIGIN}, subprotocols=['binary']) as ws. The context manager controls
        # setup/exit; inspect it for the actual cleanup behavior.
        with client.websocket_connect(ORIGIN.replace("http://", "ws://") + "/websockify", headers={"origin": ORIGIN}, subprotocols=["binary"]) as ws:
            # Learn: Assert that ws.receive_bytes() equals b'RFB fixture'. If false, this check fails with
            # AssertionError.
            assert ws.receive_bytes() == b"RFB fixture"
            # Learn: Call ws.send_bytes with the arguments shown.
            ws.send_bytes(b"client message")
            # Learn: Assert that ws.receive_bytes() equals b'client message'. If false, this check fails
            # with AssertionError.
            assert ws.receive_bytes() == b"client message"
    # Learn: Assert that connections[0][0] equals 'wss://stream.e2b.app/websockify'. If false, this check
    # fails with AssertionError.
    assert connections[0][0] == "wss://stream.e2b.app/websockify"
    # Learn: Assert that connections[0][1]['additional_headers'] equals a new dictionary with keys
    # 'e2b-traffic-access-token'. If false, this check fails with AssertionError.
    assert connections[0][1]["additional_headers"] == {"e2b-traffic-access-token": "private-traffic-token"}


# Learn: Test viewer grant is required before provider call. pytest supplies named fixtures and checks
# assertions below.
def test_viewer_grant_is_required_before_provider_call():
    # Learn: Set provider to Mock().
    provider = Mock()
    # Learn: Set desktop to E2BDesktop(Mock(), Mock(), TaskGrant('no-view', frozenset(), frozenset()),
    # viewer_provider=provider).
    desktop = E2BDesktop(Mock(), Mock(), TaskGrant("no-view", frozenset(), frozenset()), viewer_provider=provider)
    # Learn: Enter pytest.raises(ValueError, match='not permitted'). The context manager controls
    # setup/exit; inspect it for the actual cleanup behavior.
    with pytest.raises(ValueError, match="not permitted"):
        # Learn: Call desktop.live_view with no arguments.
        desktop.live_view()
    # Learn: Verify the denied/error path never invoked this fake dependency on provider.
    provider.assert_not_called()


# Learn: Test stream stops when local server setup fails. pytest supplies named fixtures and checks
# assertions below.
def test_stream_stops_when_local_server_setup_fails(monkeypatch):
    # Learn: Set sandbox to Mock(); the E2B desktop instance; its owner must attempt cleanup.
    sandbox = Mock()
    # Learn: Set sandbox.stream.get_url.return_value to 'https://stream.e2b.app/vnc.html'.
    sandbox.stream.get_url.return_value = "https://stream.e2b.app/vnc.html"
    # Learn: Set sandbox.stream.get_auth_key.return_value to 'vnc-password'.
    sandbox.stream.get_auth_key.return_value = "vnc-password"
    # Learn: Set sandbox.traffic_access_token to 'traffic-token'.
    sandbox.traffic_access_token = "traffic-token"
    # Learn: Set listener to Mock(); the loopback socket owned by the local live-view server.
    listener = Mock()
    # Learn: Set listener.getsockname.return_value to the tuple ('127.0.0.1', 34567) (positional values).
    listener.getsockname.return_value = ("127.0.0.1", 34567)
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("crescendo_agent.live_view.socket.socket", Mock(return_value=listener))
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("crescendo_agent.live_view.uvicorn.Config", Mock(side_effect=RuntimeError("bad config")))
    # Learn: Enter pytest.raises(RuntimeError, match='bad config'). The context manager controls setup/exit;
    # inspect it for the actual cleanup behavior.
    with pytest.raises(RuntimeError, match="bad config"):
        # Learn: Enter open_live_view(sandbox). The context manager controls setup/exit; inspect it for the
        # actual cleanup behavior.
        with open_live_view(sandbox):
            # Learn: Call pytest.fail with the arguments shown.
            pytest.fail("Must not yield")
    # Learn: Verify the fake dependency ran exactly once with these arguments on sandbox.stream.start.
    sandbox.stream.start.assert_called_once_with(require_auth=True)
    # Learn: Verify the fake dependency ran exactly once with these arguments on sandbox.stream.stop.
    sandbox.stream.stop.assert_called_once_with()
    # Learn: Verify the fake dependency ran exactly once with these arguments on listener.close.
    listener.close.assert_called_once_with()


# Learn: Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("wait_fails", [False, True])
# Learn: Test watch demo waits before agent and cleans up. pytest supplies named fixtures and checks
# assertions below.
def test_watch_demo_waits_before_agent_and_cleans_up(monkeypatch, wait_fails):
    # Learn: Temporarily set an environment variable for this test on monkeypatch; inputs: 'E2B_API_KEY',
    # 'offline-key'.
    monkeypatch.setenv("E2B_API_KEY", "offline-key")
    # Learn: Temporarily set an environment variable for this test on monkeypatch; inputs: 'GROQ_API_KEY',
    # 'offline-key'.
    monkeypatch.setenv("GROQ_API_KEY", "offline-key")
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr(sys, "argv", ["e2b_vision_agent_demo.py", "--watch"])
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("secrets.token_hex", lambda n: "abc123")
    # Learn: Set events to a new list (empty).
    events = []
    # Learn: Set desktop to Mock().
    desktop = Mock()

    # Learn: Wrap the generator as a context manager: yield enters the with-block and exit resumes cleanup.
    @contextmanager
    # Learn: Define viewer(). The body runs when called, not when defined.
    def viewer():
        # Learn: Append one item to the ordered collection on events; inputs: 'viewer started'.
        events.append("viewer started")
        # Learn: Try the following operations; matching except clauses handle failures. The finally block
        # runs on every exit.
        try:
            # Learn: Yield SimpleNamespace(url='http://127.0.0.1:34567/watch/fixture') to the
            # with-block/request; resume here for cleanup afterward.
            yield SimpleNamespace(url="http://127.0.0.1:34567/watch/fixture")
        # Learn: Always run cleanup, whether the operation succeeds, returns, or raises.
        finally:
            # Learn: Append one item to the ordered collection on events; inputs: 'viewer stopped'.
            events.append("viewer stopped")

    # Learn: Wrap the generator as a context manager: yield enters the with-block and exit resumes cleanup.
    @contextmanager
    # Learn: Define open_desktop(grant). The body runs when called, not when defined.
    def open_desktop(grant):
        # Learn: Assert that 'view_desktop' is in grant.allowed_tools. If false, this check fails with
        # AssertionError.
        assert "view_desktop" in grant.allowed_tools
        # Learn: Try the following operations; matching except clauses handle failures. The finally block
        # runs on every exit.
        try:
            # Learn: Yield desktop to the with-block/request; resume here for cleanup afterward.
            yield desktop
        # Learn: Always run cleanup, whether the operation succeeds, returns, or raises.
        finally:
            # Learn: Append one item to the ordered collection on events; inputs: 'desktop stopped'.
            events.append("desktop stopped")

    # Learn: Set desktop.live_view.side_effect to viewer.
    desktop.live_view.side_effect = viewer
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("crescendo_agent.e2b_desktop.open_e2b_desktop", open_desktop)
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("crescendo_agent.vision.GroqVision", lambda name: SimpleNamespace(model=name))
    # Learn: Define run(). The body runs when called, not when defined.
    def run(*args, **kwargs):
        # Learn: Append one item to the ordered collection on events; inputs: 'agent started'.
        events.append("agent started")
        # Learn: Return SimpleNamespace(status='finished', answer='ABC123', denied=[], transcript=[]) to the
        # caller and stop this function.
        return SimpleNamespace(status="finished", answer="ABC123", denied=[], transcript=[])
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("crescendo_agent.vision_loop.run_vision_agent", run)
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("webbrowser.open", lambda url: events.append("browser opened"))
    # Learn: Set script to Path(__file__).resolve().parents[3] divided by 'scripts' divided by
    # 'e2b_vision_agent_demo.py'.
    script = Path(__file__).resolve().parents[3] / "scripts" / "e2b_vision_agent_demo.py"
    # Learn: Set main to runpy.run_path(str(script))['main'].
    main = runpy.run_path(str(script))["main"]
    # Learn: Define wait(viewer). The body runs when called, not when defined.
    def wait(viewer):
        # Learn: Append one item to the ordered collection on events; inputs: 'waited for user'.
        events.append("waited for user")
        # Learn: Take this branch only if wait_fails.
        if wait_fails:
            # Learn: Raise TimeoutError('expired') to stop the normal path.
            raise TimeoutError("expired")
    # The script imports the shared helper inside its --watch branch, at call time.
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("crescendo_agent.live_view.wait_for_viewer", wait)
    # Learn: Take this branch only if wait_fails.
    if wait_fails:
        # Learn: Enter pytest.raises(TimeoutError, match='expired'). The context manager controls
        # setup/exit; inspect it for the actual cleanup behavior.
        with pytest.raises(TimeoutError, match="expired"):
            # Learn: Call main with no arguments.
            main()
    # Learn: Run this alternative only when the preceding conditional did not select its first branch.
    else:
        # Learn: Call main with no arguments.
        main()
    # Learn: Set expected to a new list containing 'viewer started', 'browser opened', 'waited for user';
    # the expected credential or fixture result used in this comparison.
    expected = ["viewer started", "browser opened", "waited for user"]
    # Learn: Take this branch only if not (wait_fails).
    if not wait_fails:
        # Learn: Append one item to the ordered collection on expected; inputs: 'agent started'.
        expected.append("agent started")
    # Learn: Assert that events equals expected plus a new list containing 'viewer stopped', 'desktop
    # stopped'. If false, this check fails with AssertionError.
    assert events == expected + ["viewer stopped", "desktop stopped"]


# Learn: Test viewer connection gate reports error without waiting for model. pytest supplies named fixtures
# and checks assertions below.
def test_viewer_connection_gate_reports_error_without_waiting_for_model():
    # Learn: Set handle to LiveViewHandle('http://127.0.0.1/viewer').
    handle = LiveViewHandle("http://127.0.0.1/viewer")
    # Learn: Append one item to the ordered collection on handle.errors; inputs:
    # 'UPSTREAM_WEBSOCKET_HTTP_401'.
    handle.errors.append("UPSTREAM_WEBSOCKET_HTTP_401")
    # Learn: Enter pytest.raises(RuntimeError, match='UPSTREAM_WEBSOCKET_HTTP_401'). The context manager
    # controls setup/exit; inspect it for the actual cleanup behavior.
    with pytest.raises(RuntimeError, match="UPSTREAM_WEBSOCKET_HTTP_401"):
        # Learn: Call handle.wait_connected with no arguments.
        handle.wait_connected()
    # Learn: Call handle.errors.clear with no arguments.
    handle.errors.clear()
    # Learn: Call handle.connected.set with no arguments.
    handle.connected.set()
    # Learn: Call handle.wait_connected with no arguments.
    handle.wait_connected()


# Learn: Test proxy reports sanitized upstream connection failure. pytest supplies named fixtures and checks
# assertions below.
def test_proxy_reports_sanitized_upstream_connection_failure(monkeypatch):
    # Learn: Set errors to a new list (empty); the safe connection error categories retained for diagnosis.
    errors = []
    # Learn: Wrap the generator as a context manager: yield enters the with-block and exit resumes cleanup.
    @asynccontextmanager
    # Learn: Define an async function connect(). Awaited calls can yield control to other work. The body
    # runs when called, not when defined.
    async def connect(*args, **kwargs):
        # Learn: Raise OSError('sensitive-traffic-token should not be logged') to stop the normal path.
        raise OSError("sensitive-traffic-token should not be logged")
        # Learn: Yield None (no value) to the with-block/request; resume here for cleanup afterward.
        yield
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("crescendo_agent.live_view.connect", connect)
    # Learn: Set app to create_viewer_app('stream.e2b.app', 'traffic-token', 'vnc-password', 'local-secret',
    # ORIGIN, on_error=errors.append).
    app = create_viewer_app("stream.e2b.app", "traffic-token", "vnc-password", "local-secret", ORIGIN,
                            # Learn: Pass keyword on_error = errors.append.
                            on_error=errors.append)
    # Learn: Enter TestClient(app, base_url=ORIGIN) as client. The context manager controls setup/exit;
    # inspect it for the actual cleanup behavior.
    with TestClient(app, base_url=ORIGIN) as client:
        # Learn: Read a key/row, using the supplied default when applicable on client; inputs:
        # '/watch/local-secret'.
        client.get("/watch/local-secret", follow_redirects=False)
        # Learn: Enter pytest.raises(WebSocketDisconnect). The context manager controls setup/exit; inspect
        # it for the actual cleanup behavior.
        with pytest.raises(WebSocketDisconnect):
            # Learn: Enter client.websocket_connect(ORIGIN.replace('http://', 'ws://') + '/websockify',
            # headers={'origin': ORIGIN}). The context manager controls setup/exit; inspect it for the
            # actual cleanup behavior.
            with client.websocket_connect(ORIGIN.replace("http://", "ws://") + "/websockify", headers={"origin": ORIGIN}):
                # Learn: No operation: this body intentionally needs no executable statement.
                pass
    # Learn: Assert that errors equals a new list containing 'WEBSOCKET_TRANSPORT_ERROR'. If false, this
    # check fails with AssertionError.
    assert errors == ["WEBSOCKET_TRANSPORT_ERROR"]


# Learn: Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("typed,close,error", [
    # Learn: Add this item to the surrounding list: (b"\n", False, None), # user pressed Enter.
    (b"\n", False, None),                       # user pressed Enter
    # Learn: Add this item to the surrounding list: (b"", False, TimeoutError), # nobody pressed Enter in
    # time.
    (b"", False, TimeoutError),                 # nobody pressed Enter in time
    # Learn: Add this item to the surrounding list: (b"", True, RuntimeError), # no interactive terminal
    # (input closed).
    (b"", True, RuntimeError),                  # no interactive terminal (input closed)
# Learn: Close this list literal; delimiters group the values into one object.
])
# Learn: Test shared wait for viewer. pytest supplies named fixtures and checks assertions below.
def test_shared_wait_for_viewer(typed, close, error):
    # Learn: Import os: reads process environment/configuration and OS facilities.
    import os
    # Learn: From crescendo_agent.live_view, import wait_for_viewer (waits for transport connection and the
    # user confirmation before agent actions).
    from crescendo_agent.live_view import wait_for_viewer
    # Learn: Set (read_fd, write_fd) to os.pipe().
    read_fd, write_fd = os.pipe()
    # Learn: Write this text or byte sequence to the already-open output on os; inputs: write_fd, typed.
    os.write(write_fd, typed)
    # Learn: Take this branch only if close.
    if close:
        # Learn: Close this owned connection, stream, file, or browser resource on os; inputs: write_fd.
        os.close(write_fd)
    # Learn: Set viewer to LiveViewHandle('http://127.0.0.1/viewer'); the live-view handle, separate from
    # the screenshots sent to the model.
    viewer = LiveViewHandle("http://127.0.0.1/viewer")
    # Learn: Call viewer.connected.set with no arguments.
    viewer.connected.set()
    # Learn: Enter os.fdopen(read_fd) as stream. The context manager controls setup/exit; inspect it for the
    # actual cleanup behavior.
    with os.fdopen(read_fd) as stream:
        # Learn: Take this branch only if error is None (no value).
        if error is None:
            # Learn: Call wait_for_viewer with the arguments shown.
            wait_for_viewer(viewer, timeout=1, stream=stream)
        # Learn: Run this alternative only when the preceding conditional did not select its first branch.
        else:
            # Learn: Enter pytest.raises(error). The context manager controls setup/exit; inspect it for the
            # actual cleanup behavior.
            with pytest.raises(error):
                # Learn: Call wait_for_viewer with the arguments shown.
                wait_for_viewer(viewer, timeout=0.05, stream=stream)
    # Learn: Take this branch only if not (close).
    if not close:
        # Learn: Close this owned connection, stream, file, or browser resource on os; inputs: write_fd.
        os.close(write_fd)
