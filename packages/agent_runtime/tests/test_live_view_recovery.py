"""Recover viewer asset transport without letting optional icons fail the gate."""
from contextlib import contextmanager
import json
from pathlib import Path
import runpy
import sys
from unittest.mock import Mock

from fastapi.testclient import TestClient
import httpx
import pytest

from crescendo_agent import live_view
from crescendo_agent.vision import Screenshot


ORIGIN = "http://127.0.0.1:34567"


def app_for(handler, errors):
    return live_view.create_viewer_app("stream.e2b.app", "traffic-secret", "vnc-secret",
                                       "local-secret", ORIGIN, transport=httpx.MockTransport(handler),
                                       on_error=errors.append)


def authenticate(client):
    client.get("/watch/local-secret", follow_redirects=False)


def test_required_module_recovers_one_transport_failure_without_failing_gate():
    requests, errors = [], []

    def upstream(request):
        requests.append(request)
        if len(requests) == 1:
            raise httpx.ReadTimeout("private connection details", request=request)
        return httpx.Response(200, text="module loaded")

    with TestClient(app_for(upstream, errors), base_url=ORIGIN) as client:
        authenticate(client)
        response = client.get("/core/rfb.js")
    assert response.status_code == 200 and response.text == "module loaded"
    assert len(requests) == 2 and errors == []
    assert all(request.url.host == "stream.e2b.app" for request in requests)
    assert all(request.headers["e2b-traffic-access-token"] == "traffic-secret" for request in requests)


@pytest.mark.parametrize("path", ["/favicon.ico", "/app/images/keyboard.svg", "/app/images/icon.png"])
def test_optional_asset_failure_does_not_poison_connection_gate(path):
    requests, errors = [], []

    def upstream(request):
        requests.append(request)
        raise httpx.ConnectError("private connection details", request=request)

    with TestClient(app_for(upstream, errors), base_url=ORIGIN) as client:
        authenticate(client)
        response = client.get(path)
    assert response.status_code == 502 and len(requests) == 2
    assert errors == [] and "private" not in response.text


@pytest.mark.parametrize("error_type, suffix", [
    (httpx.ConnectTimeout, "CONNECT_TIMEOUT"),
    (httpx.ReadTimeout, "READ_TIMEOUT"),
    (httpx.PoolTimeout, "POOL_TIMEOUT"),
    (httpx.ConnectError, "CONNECT_ERROR"),
    (httpx.RemoteProtocolError, "PROTOCOL_ERROR"),
])
def test_persistent_required_asset_failure_has_safe_category_and_bounded_retry(error_type, suffix):
    requests, errors = [], []

    def upstream(request):
        requests.append(request)
        raise error_type("private connection details", request=request)

    with TestClient(app_for(upstream, errors), base_url=ORIGIN) as client:
        authenticate(client)
        response = client.get("/core/rfb.js")
    assert response.status_code == 502 and len(requests) == 2
    assert errors == ["UPSTREAM_ASSET_" + suffix]
    assert "private" not in response.text


@pytest.mark.parametrize("path", ["/vnc.html", "/core/rfb.js", "/app/styles/base.css"])
def test_required_file_refusal_remains_fatal_and_is_not_retried(path):
    requests, errors = [], []

    def upstream(request):
        requests.append(request)
        return httpx.Response(401, text="traffic-secret")

    with TestClient(app_for(upstream, errors), base_url=ORIGIN) as client:
        authenticate(client)
        response = client.get(path)
    assert response.status_code == 502 and len(requests) == 1
    assert errors == ["UPSTREAM_ASSET_HTTP_401"]
    assert "traffic-secret" not in response.text


def test_one_upstream_client_is_reused_and_closed_with_app(monkeypatch):
    instances = []
    real_client = httpx.AsyncClient

    class TrackedClient(real_client):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            instances.append(self)

    monkeypatch.setattr(live_view.httpx, "AsyncClient", TrackedClient)
    with TestClient(app_for(lambda request: httpx.Response(200), []), base_url=ORIGIN) as client:
        authenticate(client)
        for path in ("/vnc.html", "/core/rfb.js", "/app/styles/base.css"):
            assert client.get(path).status_code == 200
        assert len(instances) == 1 and not instances[0].is_closed
    assert instances[0].is_closed


def test_click_demo_saves_viewer_failure_and_closes_without_model_calls(tmp_path, monkeypatch, capsys):
    script = Path(__file__).resolve().parents[3] / "scripts" / "e2b_click_demo.py"
    main = runpy.run_path(str(script))["main"]
    desktop, model, cleanup = Mock(), Mock(), []
    desktop.last_navigation_status, desktop.last_navigation_retry_after = 200, None
    desktop.page.title.return_value = "Boston - Wikipedia"
    desktop.page.locator.return_value.count.return_value = 1
    desktop.capture_screen.return_value = Screenshot(bytes.fromhex(
        "89504e470d0a1a0a0000000d4948445200000001000000010804000000b51c0c02"
        "0000000b4944415478da63fcff1f0003030200efa3875b0000000049454e44ae426082"))
    model.model = "test-model"
    viewer = live_view.LiveViewHandle("http://127.0.0.1/private-viewer")
    viewer.errors.append("UPSTREAM_ASSET_READ_TIMEOUT")

    @contextmanager
    def open_desktop(*args, **kwargs):
        try:
            yield desktop
        finally:
            cleanup.append("desktop closed")

    @contextmanager
    def open_viewer():
        try:
            yield viewer
        finally:
            cleanup.append("viewer closed")

    desktop.live_view.side_effect = open_viewer
    monkeypatch.setitem(main.__globals__, "load_local_env", lambda: None)
    monkeypatch.setitem(main.__globals__, "open_e2b_desktop", open_desktop)
    monkeypatch.setitem(main.__globals__, "GroqVision", lambda *args, **kwargs: model)
    monkeypatch.setattr(main.__globals__["webbrowser"], "open", lambda url: None)
    monkeypatch.setenv("E2B_API_KEY", "test-only")
    monkeypatch.setenv("GROQ_API_KEY", "test-only")
    monkeypatch.setattr(sys, "argv", [str(script), "--watch", "--save-screenshots"])
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit, match="VIEWER UNAVAILABLE.*No model calls"):
        main()
    assert cleanup == ["viewer closed", "desktop closed"]
    model.decide.assert_not_called()
    result_file, = tmp_path.glob(".demo-artifacts/click-*/result.json")
    result = json.loads(result_file.read_text())
    assert result["status"] == "viewer_unavailable" and result["model_calls"] == 0
    assert result["viewer_errors"] == ["UPSTREAM_ASSET_READ_TIMEOUT"]
    assert "private-viewer" not in result_file.read_text()
    assert result_file.with_name("viewer-desktop.png").exists()
