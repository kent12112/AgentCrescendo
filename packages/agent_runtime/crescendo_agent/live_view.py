"""Loopback HTTP/WebSocket proxy for one private E2B noVNC stream."""
import asyncio
from contextlib import contextmanager
from dataclasses import dataclass, field
from secrets import compare_digest, token_urlsafe
import socket
import threading
import time
from urllib.parse import urlencode, urlsplit

import httpx
import anyio
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import RedirectResponse, Response
from starlette.middleware.trustedhost import TrustedHostMiddleware
import uvicorn
from websockets.asyncio.client import connect
from websockets.exceptions import InvalidStatus


@dataclass
class LiveViewHandle:
    url: str
    connected: threading.Event = field(default_factory=threading.Event, repr=False)
    errors: list[str] = field(default_factory=list, repr=False)

    def wait_connected(self, timeout=30):
        deadline = time.monotonic() + timeout
        while not self.connected.wait(0.1):
            if self.errors:
                raise RuntimeError("Live viewer connection failed: " + self.errors[-1])
            if time.monotonic() >= deadline:
                raise TimeoutError("Live viewer did not connect within 30 seconds. Agent was not started.")


def create_viewer_app(host, traffic_token, vnc_password, secret, local_origin, *, transport=None,
                      on_connected=None, on_disconnected=None, on_error=None):
    if not host or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-" for character in host):
        raise ValueError("Invalid desktop stream host.")
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1"])
    headers = {"e2b-traffic-access-token": traffic_token}
    private_headers = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}

    def authorized(cookies):
        return compare_digest(cookies.get("crescendo_viewer", "").encode(), secret.encode())

    @app.get("/watch/{capability}")
    async def bootstrap(capability: str):
        if not compare_digest(capability.encode(), secret.encode()):
            return Response(status_code=403, headers=private_headers)
        query = urlencode({"autoconnect": "true", "view_only": "true", "resize": "scale",
                           "password": vnc_password, "path": "websockify"})
        response = RedirectResponse("/vnc.html?" + query, headers=private_headers)
        response.set_cookie("crescendo_viewer", secret, httponly=True, samesite="strict", max_age=180)
        return response

    @app.websocket("/websockify")
    async def relay(browser: WebSocket):
        if not authorized(browser.cookies) or browser.headers.get("origin") != local_origin:
            await browser.close(code=1008)
            return
        tasks = []
        try:
            protocols = [p for p in browser.scope.get("subprotocols", []) if p == "binary"]
            async with connect("wss://" + host + "/websockify", additional_headers=headers,
                               subprotocols=protocols or None, open_timeout=10, close_timeout=2,
                               max_size=4_000_000, compression=None) as upstream:
                await browser.accept(subprotocol=upstream.subprotocol)
                if on_connected:
                    on_connected()

                async def to_remote():
                    while True:
                        message = await browser.receive()
                        if message["type"] == "websocket.disconnect":
                            return
                        await upstream.send(message.get("bytes") if message.get("bytes") is not None else message["text"])

                async def to_browser():
                    async for message in upstream:
                        if isinstance(message, bytes):
                            await browser.send_bytes(message)
                        else:
                            await browser.send_text(message)

                tasks = [asyncio.create_task(to_remote()), asyncio.create_task(to_browser())]
                await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        except asyncio.CancelledError:
            pass
        except Exception as error:
            # Report fixed categories/status numbers, never exception messages,
            # which may include connection credentials or internal details.
            code = "WEBSOCKET_TRANSPORT_ERROR"
            if isinstance(error, InvalidStatus):
                code = "UPSTREAM_WEBSOCKET_HTTP_" + str(error.response.status_code)
            elif isinstance(error, TimeoutError):
                code = "UPSTREAM_WEBSOCKET_TIMEOUT"
            if on_error:
                on_error(code)
        finally:
            if on_disconnected:
                on_disconnected()
            with anyio.move_on_after(2, shield=True):
                for task in tasks:
                    task.cancel()
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                try:
                    await browser.close(code=1000)
                except RuntimeError:
                    pass

    @app.get("/{path:path}")
    async def assets(path: str, request: Request):
        if not authorized(request.cookies):
            return Response(status_code=403, headers=private_headers)
        # The host is fixed from this sandbox's SDK. Browser input can select
        # only a path on that host; no browser cookies or auth headers are forwarded.
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=False, transport=transport) as client:
                upstream = await client.get("https://" + host + "/" + path,
                                            params=request.query_params, headers=headers)
            if upstream.status_code != 200:
                if on_error and (path == "vnc.html" or path.endswith(".js")):
                    on_error("UPSTREAM_ASSET_HTTP_" + str(upstream.status_code))
                return Response("Desktop viewer asset unavailable.", status_code=502, headers=private_headers)
            response_headers = {**private_headers, "Content-Type": upstream.headers.get("content-type", "application/octet-stream")}
            return Response(upstream.content, headers=response_headers)
        except httpx.HTTPError:
            if on_error:
                on_error("UPSTREAM_ASSET_CONNECTION_ERROR")
            return Response("Cannot reach desktop viewer.", status_code=502, headers=private_headers)

    return app


@contextmanager
def open_live_view(sandbox):
    """Own the VNC stream and local server; sandbox cleanup belongs to caller."""
    listener = socket.socket()
    server = None
    thread = None
    started_stream = False
    try:
        listener.bind(("127.0.0.1", 0))
        listener.listen(32)
        port = listener.getsockname()[1]
        origin = f"http://127.0.0.1:{port}"
        sandbox.stream.start(require_auth=True)
        started_stream = True
        host = urlsplit(sandbox.stream.get_url()).hostname
        secret = token_urlsafe(32)
        handle = LiveViewHandle(origin + "/watch/" + secret)
        def report_error(code):
            handle.errors.append(code)
            print("Live viewer connection error:", code, flush=True)
        app = create_viewer_app(host, sandbox.traffic_access_token, sandbox.stream.get_auth_key(), secret, origin,
                               on_connected=handle.connected.set, on_disconnected=handle.connected.clear,
                               on_error=report_error)
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port,
            access_log=False, log_level="critical", ws="websockets-sansio", timeout_graceful_shutdown=1))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        deadline = time.monotonic() + 5
        while not server.started:
            if not thread.is_alive() or time.monotonic() >= deadline:
                raise RuntimeError("Local desktop viewer failed to start.")
            time.sleep(0.01)
        yield handle
    finally:
        if server is not None:
            server.should_exit = True
        if thread is not None:
            thread.join(timeout=3)
        listener.close()
        if started_stream:
            sandbox.stream.stop()
