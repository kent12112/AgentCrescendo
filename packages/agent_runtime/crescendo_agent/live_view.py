"""Loopback HTTP/WebSocket proxy for one private E2B noVNC stream."""
# Import asyncio: runs concurrent async tasks for streaming and coordination.
import asyncio
# Import from contextlib: contextmanager (turns a generator into a with-block resource lifetime).
from contextlib import asynccontextmanager, contextmanager
# Import from dataclasses: dataclass (generates data-container initialization and comparison
# methods); field (configures a dataclass field, including per-instance factories and repr hiding).
from dataclasses import dataclass, field
# Import from secrets: compare_digest (compares credential bytes without an early exit on a matching
# prefix); token_urlsafe (generates unpredictable URL-safe tokens from secure random bytes).
from secrets import compare_digest, token_urlsafe
# Import select: waits for file/socket readiness without polling continuously.
import select
# Import socket: creates or probes network sockets.
import socket
# Import sys: provides process details and standard input/output streams.
import sys
# Import threading: runs the viewer server separately and communicates with thread-safe events.
import threading
# Import time: measures monotonic elapsed time and provides bounded pauses.
import time
# Import from urllib.parse: urlencode (encodes query-string parameters safely); urlsplit (parses
# scheme, hostname, port, and path instead of guessing from substrings).
from urllib.parse import urlencode, urlsplit

# Import httpx: makes HTTP requests or supplies mock HTTP transports in tests.
import httpx
# Import anyio: provides bounded, shielded cancellation during cleanup.
import anyio
# Import from fastapi: FastAPI (creates the ASGI application and its schema-aware routing); Request
# (exposes HTTP headers, cookies, query parameters, and request data); WebSocket (represents the
# browser streaming connection).
from fastapi import FastAPI, Request, WebSocket
# Import from fastapi.responses: RedirectResponse (redirects the authorized viewer to the noVNC
# page); Response (constructs an explicit HTTP response, including empty deletion responses).
from fastapi.responses import RedirectResponse, Response
# Import from starlette.middleware.trustedhost: TrustedHostMiddleware (rejects requests with
# unapproved Host headers).
from starlette.middleware.trustedhost import TrustedHostMiddleware
# Import uvicorn: serves an ASGI app such as FastAPI.
import uvicorn
# Import from websockets.asyncio.client: connect (opens the upstream async WebSocket with explicit
# authentication/timeouts).
from websockets.asyncio.client import connect
# Import from websockets.exceptions: InvalidStatus (identifies a failed HTTP WebSocket handshake
# without logging its raw message).
from websockets.exceptions import InvalidStatus


# Decorate the class with generated data-container methods.
@dataclass
# Define LiveViewHandle.
class LiveViewHandle:
    # Declare url with type str.
    url: str
    # Set connected to field(default_factory=threading.Event, repr=False).
    connected: threading.Event = field(default_factory=threading.Event, repr=False)
    # Set errors to field(default_factory=list, repr=False).
    errors: list[str] = field(default_factory=list, repr=False)

    # Define wait_connected with parameters self, timeout.
    def wait_connected(self, timeout=30):
        # Set deadline to time.monotonic() plus timeout.
        deadline = time.monotonic() + timeout
        # Repeat this block while not (self.connected.wait(0.1)).
        while not self.connected.wait(0.1):
            # Check whether self.errors.
            if self.errors:
                # Raise RuntimeError('Live viewer connection failed: ' + self.errors[-1]) to stop
                # the normal path.
                raise RuntimeError("Live viewer connection failed: " + self.errors[-1])
            # Check whether time.monotonic() is at least deadline.
            if time.monotonic() >= deadline:
                # Raise TimeoutError('Live viewer did not connect within 30 seconds. Agent was not
                # started.') to stop the normal path.
                raise TimeoutError("Live viewer did not connect within 30 seconds. Agent was not started.")


# Define create_viewer_app with parameters host, traffic_token, vnc_password, secret, local_origin,
# transport, on_connected, on_disconnected, on_error.
def create_viewer_app(host, traffic_token, vnc_password, secret, local_origin, *, transport=None,
                      on_connected=None, on_disconnected=None, on_error=None,
                      cookie_name="crescendo_viewer", cookie_max_age=180):
    # Check whether not (host) or any((character not in
    # 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-' for character in host)).
    if not host or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-" for character in host):
        # Raise ValueError('Invalid desktop stream host.') to stop the normal path.
        raise ValueError("Invalid desktop stream host.")
    @asynccontextmanager
    async def lifespan(app):
        # noVNC loads dozens of modules/icons. Reuse this session's connections,
        # and close them with the loopback server rather than per browser request.
        async with httpx.AsyncClient(timeout=10, follow_redirects=False, transport=transport,
                                     limits=httpx.Limits(max_connections=8, max_keepalive_connections=8)) as client:
            app.state.asset_client = client
            yield

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    # Call app.add_middleware with TrustedHostMiddleware.
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1"])
    # Set headers to {'e2b-traffic-access-token': traffic_token}.
    headers = {"e2b-traffic-access-token": traffic_token}
    # Set private_headers to {'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer'}.
    private_headers = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}

    # Define authorized with parameters cookies.
    def authorized(cookies):
        # Return compare_digest(cookies.get('crescendo_viewer', '').encode(), secret.encode()).
        return compare_digest(cookies.get(cookie_name, "").encode(), secret.encode())

    # Register this function as the route for the indicated HTTP method or WebSocket path;
    # dependencies enforce the configured boundary.
    @app.get("/watch/{capability}")
    # Define bootstrap with parameters capability.
    async def bootstrap(capability: str):
        # Check whether not (compare_digest(capability.encode(), secret.encode())).
        if not compare_digest(capability.encode(), secret.encode()):
            # Return Response(status_code=403, headers=private_headers).
            return Response(status_code=403, headers=private_headers)
        # Set query to urlencode({'autoconnect': 'true', 'view_only': 'true', 'resize': 'scale',
        # 'password': vnc_password, 'path': 'websockify'}).
        query = urlencode({"autoconnect": "true", "view_only": "true", "resize": "scale",
                           # Include password, path in this dictionary.
                           "password": vnc_password, "path": "websockify"})
        # Set response to RedirectResponse('/vnc.html?' + query, headers=private_headers).
        response = RedirectResponse("/vnc.html?" + query, headers=private_headers)
        # Call response.set_cookie with 'crescendo_viewer', secret.
        response.set_cookie(cookie_name, secret, httponly=True, samesite="strict", max_age=cookie_max_age)
        # Return response.
        return response

    # Register this function as the route for the indicated HTTP method or WebSocket path;
    # dependencies enforce the configured boundary.
    @app.websocket("/websockify")
    # Define relay with parameters browser.
    async def relay(browser: WebSocket):
        # Check whether not (authorized(browser.cookies)) or browser.headers['origin'], or None if
        # absent does not equal local_origin.
        if not authorized(browser.cookies) or browser.headers.get("origin") != local_origin:
            # Await completion without blocking the event loop: Close this owned connection, stream,
            # file, or browser resource on browser.
            await browser.close(code=1008)
            # Return without a value.
            return
        # Set tasks to an empty list.
        tasks = []
        connected = False
        # Try the following operations; matching except clauses handle failures. The finally block
        # runs on every exit.
        try:
            # Set protocols to [p for p in browser.scope.get('subprotocols', []) if p == 'binary'].
            protocols = [p for p in browser.scope.get("subprotocols", []) if p == "binary"]
            # Asynchronously enter connect('wss://' + host + '/websockify',
            # additional_headers=headers, subprotocols=protocols or None, open_timeout=10,
            # close_timeout=2, max_size=4000000, compression=None) as upstream. The context manager
            # controls setup/exit; inspect it for the actual cleanup behavior.
            async with connect("wss://" + host + "/websockify", additional_headers=headers,
                               # Pass keyword subprotocols = protocols OR None (no value).
                               subprotocols=protocols or None, open_timeout=10, close_timeout=2,
                               # Pass keyword max_size = 4000000.
                               max_size=4_000_000, compression=None) as upstream:
                # Await completion without blocking the event loop: Call browser.accept with the
                # arguments shown.
                await browser.accept(subprotocol=upstream.subprotocol)
                connected = True
                # Check whether on_connected.
                if on_connected:
                    # Call on_connected with no arguments.
                    on_connected()

                # Define to_remote with no parameters.
                async def to_remote():
                    # Repeat this block while True.
                    while True:
                        # Set message to await browser.receive().
                        message = await browser.receive()
                        # Check whether message['type'] equals 'websocket.disconnect'.
                        if message["type"] == "websocket.disconnect":
                            # Return without a value.
                            return
                        await upstream.send(message.get("bytes") if message.get("bytes") is not None else message["text"])

                # Define to_browser with no parameters.
                async def to_browser():
                    # Asynchronously iterate over upstream, binding message for each item.
                    async for message in upstream:
                        # Check whether whether message is an instance of bytes.
                        if isinstance(message, bytes):
                            # Await completion without blocking the event loop: Call
                            # browser.send_bytes with the arguments shown.
                            await browser.send_bytes(message)
                        # Run this alternative only when the preceding conditional did not select
                        # its first branch.
                        else:
                            # Await completion without blocking the event loop: Call
                            # browser.send_text with the arguments shown.
                            await browser.send_text(message)

                # Set tasks to [asyncio.create_task(to_remote()),
                # asyncio.create_task(to_browser())].
                tasks = [asyncio.create_task(to_remote()), asyncio.create_task(to_browser())]
                # Await completion without blocking the event loop: Call asyncio.wait with the
                # arguments shown.
                await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        # Handle asyncio.CancelledError; unmatched errors propagate.
        except asyncio.CancelledError:
            pass
        # Handle Exception as error; unmatched errors propagate.
        except Exception as error:
            # Report fixed categories/status numbers, never exception messages,
            # which may include connection credentials or internal details.
            # Set code to 'WEBSOCKET_TRANSPORT_ERROR'.
            code = "WEBSOCKET_TRANSPORT_ERROR"
            # Check whether whether error is an instance of InvalidStatus.
            if isinstance(error, InvalidStatus):
                # Set code to 'UPSTREAM_WEBSOCKET_HTTP_' plus error.response.status_code converted
                # to a string.
                code = "UPSTREAM_WEBSOCKET_HTTP_" + str(error.response.status_code)
            # Otherwise, check whether whether error is an instance of TimeoutError.
            elif isinstance(error, TimeoutError):
                # Set code to 'UPSTREAM_WEBSOCKET_TIMEOUT'.
                code = "UPSTREAM_WEBSOCKET_TIMEOUT"
            # Check whether on_error.
            if on_error:
                # Call on_error with code.
                on_error(code)
        # Always run cleanup, whether the operation succeeds, returns, or raises.
        finally:
            # Check whether on_disconnected.
            if connected and on_disconnected:
                # Call on_disconnected with no arguments.
                on_disconnected()
            # Use anyio.move_on_after(2, shield=True); leave the context and run its cleanup when
            # this block ends.
            with anyio.move_on_after(2, shield=True):
                # Iterate over tasks, binding task for each item.
                for task in tasks:
                    # Call task.cancel with no arguments.
                    task.cancel()
                # Check whether tasks.
                if tasks:
                    # Await completion without blocking the event loop: Call asyncio.gather with the
                    # arguments shown.
                    await asyncio.gather(*tasks, return_exceptions=True)
                # Try the following operations; matching except clauses handle failures.
                try:
                    # Await completion without blocking the event loop: Close this owned connection,
                    # stream, file, or browser resource on browser.
                    await browser.close(code=1000)
                # Handle RuntimeError; unmatched errors propagate.
                except RuntimeError:
                    pass

    # Register this function as the route for the indicated HTTP method or WebSocket path;
    # dependencies enforce the configured boundary.
    @app.get("/{path:path}")
    # Define assets with parameters path, request.
    async def assets(path: str, request: Request):
        # Check whether not (authorized(request.cookies)).
        if not authorized(request.cookies):
            # Return Response(status_code=403, headers=private_headers).
            return Response(status_code=403, headers=private_headers)
        essential = path == "vnc.html" or path.endswith((".js", ".css"))
        # The host is fixed from this sandbox's SDK. Browser input can select
        # only a path on that host; no browser cookies or auth headers are forwarded.
        # Try the following operations; matching except clauses handle failures.
        try:
            for attempt in range(2):
                try:
                    upstream = await app.state.asset_client.get("https://" + host + "/" + path,
                                                               params=request.query_params, headers=headers)
                except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError):
                    if attempt == 1:
                        raise
                    await asyncio.sleep(0.25)
                else:
                    break
            # Check whether upstream.status_code does not equal 200.
            if upstream.status_code != 200:
                # Check whether on_error and path equals 'vnc.html' or path.endswith('.js').
                if on_error and essential:
                    # Call on_error with 'UPSTREAM_ASSET_HTTP_' plus upstream.status_code converted
                    # to a string.
                    on_error("UPSTREAM_ASSET_HTTP_" + str(upstream.status_code))
                # Return Response('Desktop viewer asset unavailable.', status_code=502,
                # headers=private_headers).
                return Response("Desktop viewer asset unavailable.", status_code=502, headers=private_headers)
            # Set response_headers to {**private_headers, 'Content-Type':
            # upstream.headers.get('content-type', 'application/octet-stream')}.
            response_headers = {**private_headers, "Content-Type": upstream.headers.get("content-type", "application/octet-stream")}
            # Return Response(upstream.content, headers=response_headers).
            return Response(upstream.content, headers=response_headers)
        # Handle httpx.HTTPError; unmatched errors propagate.
        except httpx.HTTPError as error:
            # Check whether on_error.
            if on_error and essential:
                # Fixed categories only; raw exceptions may include credentials.
                category = "CONNECTION_ERROR"
                for error_type, name in ((httpx.ConnectTimeout, "CONNECT_TIMEOUT"),
                                         (httpx.ReadTimeout, "READ_TIMEOUT"),
                                         (httpx.PoolTimeout, "POOL_TIMEOUT"),
                                         (httpx.ProxyError, "PROXY_ERROR"),
                                         (httpx.ConnectError, "CONNECT_ERROR"),
                                         (httpx.RemoteProtocolError, "PROTOCOL_ERROR")):
                    if isinstance(error, error_type):
                        category = name
                        break
                on_error("UPSTREAM_ASSET_" + category)
            # Return Response('Cannot reach desktop viewer.', status_code=502,
            # headers=private_headers).
            return Response("Cannot reach desktop viewer.", status_code=502, headers=private_headers)

    # Return app.
    return app


# Wrap the generator as a context manager: yield enters the with-block and exit resumes cleanup.
@contextmanager
# Define open_live_view with parameters sandbox.
def open_live_view(sandbox, *, cookie_max_age=180):
    """Own the VNC stream and local server; sandbox cleanup belongs to caller."""
    # Set listener to socket.socket().
    listener = socket.socket()
    # Set server to None.
    server = None
    # Set thread to None.
    thread = None
    # Set started_stream to False.
    started_stream = False
    # Try the following operations; matching except clauses handle failures. The finally block runs
    # on every exit.
    try:
        # Call listener.bind with ('127.0.0.1', 0).
        listener.bind(("127.0.0.1", 0))
        # Call listener.listen with 32.
        listener.listen(32)
        # Set port to listener.getsockname()[1].
        port = listener.getsockname()[1]
        # Set origin to f'http://127.0.0.1:{port}'.
        origin = f"http://127.0.0.1:{port}"
        # Call sandbox.stream.start with no arguments.
        sandbox.stream.start(require_auth=True)
        # Set started_stream to True.
        started_stream = True
        # Set host to urlsplit(sandbox.stream.get_url()).hostname.
        host = urlsplit(sandbox.stream.get_url()).hostname
        # Set secret to token_urlsafe(32).
        secret = token_urlsafe(32)
        # Set handle to LiveViewHandle(origin + '/watch/' + secret).
        handle = LiveViewHandle(origin + "/watch/" + secret)
        connection_lock = threading.Lock()
        connections = 0

        def viewer_connected():
            nonlocal connections
            with connection_lock:
                connections += 1
                handle.connected.set()

        def viewer_disconnected():
            nonlocal connections
            with connection_lock:
                connections = max(0, connections - 1)
                if connections == 0:
                    handle.connected.clear()
        # Define report_error with parameters code.
        def report_error(code):
            # Append code to handle.errors.
            handle.errors.append(code)
            # Print 'Live viewer connection error:', code.
            print("Live viewer connection error:", code, flush=True)
        # Set app to the result of create_viewer_app using the arguments below.
        app = create_viewer_app(host, sandbox.traffic_access_token, sandbox.stream.get_auth_key(), secret, origin,
                               # Set on_connected to (handle.connected.clear,).
                               on_connected=viewer_connected, on_disconnected=viewer_disconnected,
                               # Pass keyword on_error = report_error.
                               on_error=report_error,
                               # Cookies ignore ports: isolate concurrent localhost viewers.
                               cookie_name=f"crescendo_viewer_{port}", cookie_max_age=cookie_max_age)
        # Set server to uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=port,
        # access_log=False, log_level='critical', ws='websockets-sansio',
        # timeout_graceful_shutdown=1)).
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port,
            # Pass keyword access_log = False.
            access_log=False, log_level="critical", ws="websockets-sansio", timeout_graceful_shutdown=1))
        # Set thread to threading.Thread(target=server.run, kwargs={'sockets': [listener]},
        # daemon=True).
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        # Call thread.start with no arguments.
        thread.start()
        # Set deadline to time.monotonic() plus 5.
        deadline = time.monotonic() + 5
        # Repeat this block while not (server.started).
        while not server.started:
            # Check whether not (thread.is_alive()) or time.monotonic() is at least deadline.
            if not thread.is_alive() or time.monotonic() >= deadline:
                # Raise RuntimeError('Local desktop viewer failed to start.') to stop the normal
                # path.
                raise RuntimeError("Local desktop viewer failed to start.")
            # Call time.sleep with 0.01.
            time.sleep(0.01)
        # Give handle to the caller and pause here until execution resumes.
        yield handle
    # Always run cleanup, whether the operation succeeds, returns, or raises.
    finally:
        # Check whether server is not None.
        if server is not None:
            # Set server.should_exit to True.
            server.should_exit = True
        # Check whether thread is not None.
        if thread is not None:
            # Call thread.join with no arguments.
            thread.join(timeout=3)
        listener.close()
        # Check whether started_stream.
        if started_stream:
            # Call sandbox.stream.stop with no arguments.
            sandbox.stream.stop()


# Define wait_for_viewer with parameters viewer, timeout, stream.
def wait_for_viewer(viewer, *, timeout=45, stream=None):
    """Block until the viewer connects and the user presses Enter, so the agent
    never starts before the person can see the desktop. Shared by the demos."""
    # Set stream to sys.stdin if stream is None, otherwise stream.
    stream = sys.stdin if stream is None else stream
    # Call viewer.wait_connected with no arguments.
    viewer.wait_connected()
    # Print 'Viewer stream transport connected. Confirm that the remote desktop and page are
    # visible.'.
    print("Viewer stream transport connected. Confirm that the remote desktop and page are visible.", flush=True)
    # Print f'When the desktop is visible, press Enter here to start the agent ({timeout}-second
    # limit).'.
    print(f"When the desktop is visible, press Enter here to start the agent ({timeout}-second limit).", flush=True)
    # Check whether not (select.select([stream], [], [], timeout)[0]).
    if not select.select([stream], [], [], timeout)[0]:
        # Raise TimeoutError('Viewer wait expired; desktop will be cleaned up.') to stop the normal
        # path.
        raise TimeoutError("Viewer wait expired; desktop will be cleaned up.")
    # Check whether not (stream.readline()).
    if not stream.readline():
        # Raise RuntimeError('Interactive terminal required for --watch.') to stop the normal path.
        raise RuntimeError("Interactive terminal required for --watch.")
