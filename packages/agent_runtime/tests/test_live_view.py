import asyncio
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace
from unittest.mock import Mock

from fastapi.testclient import TestClient
import httpx
import pytest
from starlette.websockets import WebSocketDisconnect

from crescendo_agent.live_view import LiveViewHandle, create_viewer_app, open_live_view
from crescendo_agent.e2b_desktop import E2BDesktop
from crescendo_security.policy import TaskGrant

ORIGIN = "http://127.0.0.1:34567"


def app_with_transport(handler):
    return create_viewer_app("stream.e2b.app", "private-traffic-token", "vnc-password",
                             "local-secret", ORIGIN, transport=httpx.MockTransport(handler))


def test_viewer_authentication_and_fixed_host_proxy():
    requests = []
    def upstream(request):
        requests.append(request)
        return httpx.Response(200, content=b"viewer asset", headers={"content-type": "text/javascript"})
    with TestClient(app_with_transport(upstream), base_url=ORIGIN) as client:
        assert client.get("/vnc.html").status_code == 403
        assert client.get("/watch/wrong").status_code == 403
        assert requests == []
        response = client.get("/watch/local-secret", follow_redirects=False)
        assert response.status_code == 307
        assert "password=vnc-password" in response.headers["location"]
        assert "HttpOnly" in response.headers["set-cookie"]
        assert "SameSite=strict" in response.headers["set-cookie"]
        assert response.headers["referrer-policy"] == "no-referrer"
        response = client.get("/app/ui.js", headers={"Authorization": "Bearer user-header"})
        assert response.status_code == 200
        assert response.content == b"viewer asset"
        assert response.headers["cache-control"] == "no-store"
        assert "private-traffic-token" not in response.text
        assert requests[0].url.host == "stream.e2b.app"
        assert requests[0].headers["e2b-traffic-access-token"] == "private-traffic-token"
        assert "cookie" not in requests[0].headers
        assert "authorization" not in requests[0].headers
        assert client.get("/vnc.html", headers={"Host": "evil.example"}).status_code == 400


@pytest.mark.parametrize("status", [302, 401, 500])
def test_upstream_errors_and_redirects_do_not_leak_details(status):
    def upstream(request):
        return httpx.Response(status, text="private-traffic-token", headers={"location": "https://evil.example/"})
    with TestClient(app_with_transport(upstream), base_url=ORIGIN) as client:
        client.get("/watch/local-secret", follow_redirects=False)
        response = client.get("/vnc.html")
        assert response.status_code == 502
        assert "private-traffic-token" not in response.text
        assert "location" not in response.headers


def test_websocket_requires_cookie_and_same_origin(monkeypatch):
    connect = Mock()
    monkeypatch.setattr("crescendo_agent.live_view.connect", connect)
    with TestClient(app_with_transport(lambda r: httpx.Response(200)), base_url=ORIGIN) as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(ORIGIN.replace("http://", "ws://") + "/websockify", headers={"origin": ORIGIN}):
                pass
        client.get("/watch/local-secret", follow_redirects=False)
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(ORIGIN.replace("http://", "ws://") + "/websockify", headers={"origin": "http://evil.example"}):
                pass
    connect.assert_not_called()


def test_websocket_forwards_binary_data_and_authenticates_upstream(monkeypatch):
    connections = []
    class Remote:
        subprotocol = "binary"
        def __init__(self):
            self.messages = asyncio.Queue()
            self.messages.put_nowait(b"RFB fixture")
        async def send(self, message):
            await self.messages.put(message)
        def __aiter__(self):
            return self
        async def __anext__(self):
            return await self.messages.get()

    @asynccontextmanager
    async def connect(url, **kwargs):
        connections.append((url, kwargs))
        yield Remote()
    monkeypatch.setattr("crescendo_agent.live_view.connect", connect)
    with TestClient(app_with_transport(lambda r: httpx.Response(200)), base_url=ORIGIN) as client:
        client.get("/watch/local-secret", follow_redirects=False)
        with client.websocket_connect(ORIGIN.replace("http://", "ws://") + "/websockify", headers={"origin": ORIGIN}, subprotocols=["binary"]) as ws:
            assert ws.receive_bytes() == b"RFB fixture"
            ws.send_bytes(b"client message")
            assert ws.receive_bytes() == b"client message"
    assert connections[0][0] == "wss://stream.e2b.app/websockify"
    assert connections[0][1]["additional_headers"] == {"e2b-traffic-access-token": "private-traffic-token"}


def test_viewer_grant_is_required_before_provider_call():
    provider = Mock()
    desktop = E2BDesktop(Mock(), Mock(), TaskGrant("no-view", frozenset(), frozenset()), viewer_provider=provider)
    with pytest.raises(ValueError, match="not permitted"):
        desktop.live_view()
    provider.assert_not_called()


def test_stream_stops_when_local_server_setup_fails(monkeypatch):
    sandbox = Mock()
    sandbox.stream.get_url.return_value = "https://stream.e2b.app/vnc.html"
    sandbox.stream.get_auth_key.return_value = "vnc-password"
    sandbox.traffic_access_token = "traffic-token"
    listener = Mock()
    listener.getsockname.return_value = ("127.0.0.1", 34567)
    monkeypatch.setattr("crescendo_agent.live_view.socket.socket", Mock(return_value=listener))
    monkeypatch.setattr("crescendo_agent.live_view.uvicorn.Config", Mock(side_effect=RuntimeError("bad config")))
    with pytest.raises(RuntimeError, match="bad config"):
        with open_live_view(sandbox):
            pytest.fail("Must not yield")
    sandbox.stream.start.assert_called_once_with(require_auth=True)
    sandbox.stream.stop.assert_called_once_with()
    listener.close.assert_called_once_with()


@pytest.mark.parametrize("wait_fails", [False, True])
def test_watch_demo_waits_before_agent_and_cleans_up(monkeypatch, wait_fails):
    monkeypatch.setenv("E2B_API_KEY", "offline-key")
    monkeypatch.setenv("GROQ_API_KEY", "offline-key")
    monkeypatch.setattr(sys, "argv", ["e2b_vision_agent_demo.py", "--watch"])
    monkeypatch.setattr("secrets.token_hex", lambda n: "abc123")
    events = []
    desktop = Mock()

    @contextmanager
    def viewer():
        events.append("viewer started")
        try:
            yield SimpleNamespace(url="http://127.0.0.1:34567/watch/fixture")
        finally:
            events.append("viewer stopped")

    @contextmanager
    def open_desktop(grant):
        assert "view_desktop" in grant.allowed_tools
        try:
            yield desktop
        finally:
            events.append("desktop stopped")

    desktop.live_view.side_effect = viewer
    monkeypatch.setattr("crescendo_agent.e2b_desktop.open_e2b_desktop", open_desktop)
    monkeypatch.setattr("crescendo_agent.vision.GroqVision", lambda name: SimpleNamespace(model=name))
    def run(*args, **kwargs):
        events.append("agent started")
        return SimpleNamespace(status="finished", answer="ABC123", denied=[], transcript=[])
    monkeypatch.setattr("crescendo_agent.vision_loop.run_vision_agent", run)
    monkeypatch.setattr("webbrowser.open", lambda url: events.append("browser opened"))
    script = Path(__file__).resolve().parents[3] / "scripts" / "e2b_vision_agent_demo.py"
    main = runpy.run_path(str(script))["main"]
    def wait(viewer):
        events.append("waited for user")
        if wait_fails:
            raise TimeoutError("expired")
    main.__globals__["wait_for_viewer"] = wait
    if wait_fails:
        with pytest.raises(TimeoutError, match="expired"):
            main()
    else:
        main()
    expected = ["viewer started", "browser opened", "waited for user"]
    if not wait_fails:
        expected.append("agent started")
    assert events == expected + ["viewer stopped", "desktop stopped"]


def test_viewer_connection_gate_reports_error_without_waiting_for_model():
    handle = LiveViewHandle("http://127.0.0.1/viewer")
    handle.errors.append("UPSTREAM_WEBSOCKET_HTTP_401")
    with pytest.raises(RuntimeError, match="UPSTREAM_WEBSOCKET_HTTP_401"):
        handle.wait_connected()
    handle.errors.clear()
    handle.connected.set()
    handle.wait_connected()


def test_proxy_reports_sanitized_upstream_connection_failure(monkeypatch):
    errors = []
    @asynccontextmanager
    async def connect(*args, **kwargs):
        raise OSError("sensitive-traffic-token should not be logged")
        yield
    monkeypatch.setattr("crescendo_agent.live_view.connect", connect)
    app = create_viewer_app("stream.e2b.app", "traffic-token", "vnc-password", "local-secret", ORIGIN,
                            on_error=errors.append)
    with TestClient(app, base_url=ORIGIN) as client:
        client.get("/watch/local-secret", follow_redirects=False)
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(ORIGIN.replace("http://", "ws://") + "/websockify", headers={"origin": ORIGIN}):
                pass
    assert errors == ["WEBSOCKET_TRANSPORT_ERROR"]
