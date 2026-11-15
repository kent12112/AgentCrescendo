# Learn: Document this module, class, or function with a docstring; it is not an action or a model
# instruction.
"""Loopback HTTP/WebSocket proxy for one private E2B noVNC stream."""
# Learn: Import asyncio: runs concurrent async tasks for streaming and coordination.
import asyncio
# Learn: From contextlib, import contextmanager (turns a generator into a with-block resource lifetime).
from contextlib import contextmanager
# Learn: From dataclasses, import dataclass (generates data-container initialization and comparison
# methods); field (configures a dataclass field, including per-instance factories and repr hiding).
from dataclasses import dataclass, field
# Learn: From secrets, import compare_digest (compares credential bytes without an early exit on a matching
# prefix); token_urlsafe (generates unpredictable URL-safe tokens from secure random bytes).
from secrets import compare_digest, token_urlsafe
# Learn: Import select: waits for file/socket readiness without polling continuously.
import select
# Learn: Import socket: creates or probes network sockets.
import socket
# Learn: Import sys: provides process details and standard input/output streams.
import sys
# Learn: Import threading: runs the viewer server separately and communicates with thread-safe events.
import threading
# Learn: Import time: measures monotonic elapsed time and provides bounded pauses.
import time
# Learn: From urllib.parse, import urlencode (encodes query-string parameters safely); urlsplit (parses
# scheme, hostname, port, and path instead of guessing from substrings).
from urllib.parse import urlencode, urlsplit

# Learn: Import httpx: makes HTTP requests or supplies mock HTTP transports in tests.
import httpx
# Learn: Import anyio: provides bounded, shielded cancellation during cleanup.
import anyio
# Learn: From fastapi, import FastAPI (creates the ASGI application and its schema-aware routing); Request
# (exposes HTTP headers, cookies, query parameters, and request data); WebSocket (represents the browser
# streaming connection).
from fastapi import FastAPI, Request, WebSocket
# Learn: From fastapi.responses, import RedirectResponse (redirects the authorized viewer to the noVNC
# page); Response (constructs an explicit HTTP response, including empty deletion responses).
from fastapi.responses import RedirectResponse, Response
# Learn: From starlette.middleware.trustedhost, import TrustedHostMiddleware (rejects requests with
# unapproved Host headers).
from starlette.middleware.trustedhost import TrustedHostMiddleware
# Learn: Import uvicorn: serves an ASGI app such as FastAPI.
import uvicorn
# Learn: From websockets.asyncio.client, import connect (opens the upstream async WebSocket with explicit
# authentication/timeouts).
from websockets.asyncio.client import connect
# Learn: From websockets.exceptions, import InvalidStatus (identifies a failed HTTP WebSocket handshake
# without logging its raw message).
from websockets.exceptions import InvalidStatus


# Learn: Decorate the class with generated data-container methods.
@dataclass
# Learn: Define LiveViewHandle. Indented methods and attributes belong to this class.
class LiveViewHandle:
    # Learn: Declare url with type str; the destination or current page address.
    url: str
    # Learn: Set connected to field(default_factory=threading.Event, repr=False); the thread-safe event that
    # records viewer transport connection. Configure a per-instance default or representation option for
    # this dataclass field.
    connected: threading.Event = field(default_factory=threading.Event, repr=False)
    # Learn: Set errors to field(default_factory=list, repr=False); the safe connection error categories
    # retained for diagnosis. Configure a per-instance default or representation option for this dataclass
    # field.
    errors: list[str] = field(default_factory=list, repr=False)

    # Learn: Define wait_connected(timeout). The body runs when called, not when defined.
    def wait_connected(self, timeout=30):
        # Learn: Set deadline to time.monotonic() plus timeout; the absolute monotonic-clock cutoff for
        # admitting further work.
        deadline = time.monotonic() + timeout
        # Learn: Repeat this block while not (self.connected.wait(0.1)).
        while not self.connected.wait(0.1):
            # Learn: Take this branch only if self.errors.
            if self.errors:
                # Learn: Raise RuntimeError('Live viewer connection failed: ' + self.errors[-1]) to stop the
                # normal path.
                raise RuntimeError("Live viewer connection failed: " + self.errors[-1])
            # Learn: Take this branch only if time.monotonic() is at least deadline.
            if time.monotonic() >= deadline:
                # Learn: Raise TimeoutError('Live viewer did not connect within 30 seconds. Agent was not
                # started.') to stop the normal path.
                raise TimeoutError("Live viewer did not connect within 30 seconds. Agent was not started.")


# Learn: Define create_viewer_app(host, traffic_token, vnc_password, secret, local_origin, transport,
# on_connected, on_disconnected, on_error). The body runs when called, not when defined.
def create_viewer_app(host, traffic_token, vnc_password, secret, local_origin, *, transport=None,
                      # Learn: Parameters: on_connected is provided/defaulted by the caller; on_disconnected
                      # is provided/defaulted by the caller; on_error is provided/defaulted by the caller.
                      # Type hints do not enforce types by themselves.
                      on_connected=None, on_disconnected=None, on_error=None):
    # Learn: Take this branch only if not (host) OR any((character not in
    # 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-' for character in host)).
    if not host or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-" for character in host):
        # Learn: Raise ValueError('Invalid desktop stream host.') to stop the normal path.
        raise ValueError("Invalid desktop stream host.")
    # Learn: Set app to FastAPI(docs_url=None, redoc_url=None, openapi_url=None).
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    # Learn: Call app.add_middleware with the arguments shown.
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1"])
    # Learn: Set headers to a new dictionary with keys 'e2b-traffic-access-token'; the headers explicitly
    # supplied at this trust boundary.
    headers = {"e2b-traffic-access-token": traffic_token}
    # Learn: Set private_headers to a new dictionary with keys 'Cache-Control', 'Referrer-Policy';
    # no-store/no-referrer headers for credential-bearing viewer responses.
    private_headers = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}

    # Learn: Define authorized(cookies). The body runs when called, not when defined.
    def authorized(cookies):
        # Learn: Return compare_digest(cookies.get('crescendo_viewer', '').encode(), secret.encode()) to the
        # caller and stop this function.
        return compare_digest(cookies.get("crescendo_viewer", "").encode(), secret.encode())

    # Learn: Register this function as the route for the indicated HTTP method or WebSocket path;
    # dependencies enforce the configured boundary.
    @app.get("/watch/{capability}")
    # Learn: Define an async function bootstrap(capability). Awaited calls can yield control to other work.
    # The body runs when called, not when defined.
    async def bootstrap(capability: str):
        # Learn: Take this branch only if not (compare_digest(capability.encode(), secret.encode())).
        if not compare_digest(capability.encode(), secret.encode()):
            # Learn: Return Response(status_code=403, headers=private_headers) to the caller and stop this
            # function.
            return Response(status_code=403, headers=private_headers)
        # Learn: Set query to urlencode({'autoconnect': 'true', 'view_only': 'true', 'resize': 'scale',
        # 'password': vnc_password, 'path': 'websockify'}); the bounded search keywords for the current
        # page, not a navigation URL.
        query = urlencode({"autoconnect": "true", "view_only": "true", "resize": "scale",
                           # Learn: Define this named mapping field: "password": vnc_password, "path":
                           # "websockify"}). The key selects the schema/configuration value.
                           "password": vnc_password, "path": "websockify"})
        # Learn: Set response to RedirectResponse('/vnc.html?' + query, headers=private_headers); the
        # returned HTTP or model-provider response.
        response = RedirectResponse("/vnc.html?" + query, headers=private_headers)
        # Learn: Call response.set_cookie with the arguments shown.
        response.set_cookie("crescendo_viewer", secret, httponly=True, samesite="strict", max_age=180)
        # Learn: Return response to the caller and stop this function.
        return response

    # Learn: Register this function as the route for the indicated HTTP method or WebSocket path;
    # dependencies enforce the configured boundary.
    @app.websocket("/websockify")
    # Learn: Define an async function relay(browser). Awaited calls can yield control to other work. The
    # body runs when called, not when defined.
    async def relay(browser: WebSocket):
        # Learn: Take this branch only if not (authorized(browser.cookies)) OR browser.headers['origin']
        # with None as the missing-key default does not equal local_origin.
        if not authorized(browser.cookies) or browser.headers.get("origin") != local_origin:
            # Learn: Await completion without blocking the event loop: Close this owned connection, stream,
            # file, or browser resource on browser.
            await browser.close(code=1008)
            # Learn: Return None (no value) to the caller and stop this function.
            return
        # Learn: Set tasks to a new list (empty).
        tasks = []
        # Learn: Try the following operations; matching except clauses handle failures. The finally block
        # runs on every exit.
        try:
            # Learn: Set protocols to a list built from browser.scope.get('subprotocols', []) by the
            # comprehension with its filter.
            protocols = [p for p in browser.scope.get("subprotocols", []) if p == "binary"]
            # Learn: Asynchronously enter connect('wss://' + host + '/websockify',
            # additional_headers=headers, subprotocols=protocols or None, open_timeout=10, close_timeout=2,
            # max_size=4000000, compression=None) as upstream. The context manager controls setup/exit;
            # inspect it for the actual cleanup behavior.
            async with connect("wss://" + host + "/websockify", additional_headers=headers,
                               # Learn: Pass keyword subprotocols = protocols OR None (no value).
                               subprotocols=protocols or None, open_timeout=10, close_timeout=2,
                               # Learn: Pass keyword max_size = 4000000.
                               max_size=4_000_000, compression=None) as upstream:
                # Learn: Await completion without blocking the event loop: Call browser.accept with the
                # arguments shown.
                await browser.accept(subprotocol=upstream.subprotocol)
                # Learn: Take this branch only if on_connected.
                if on_connected:
                    # Learn: Call on_connected with no arguments.
                    on_connected()

                # Learn: Define an async function to_remote(). Awaited calls can yield control to other
                # work. The body runs when called, not when defined.
                async def to_remote():
                    # Learn: Repeat this block while True.
                    while True:
                        # Learn: Set message to await browser.receive().
                        message = await browser.receive()
                        # Learn: Take this branch only if message['type'] equals 'websocket.disconnect'.
                        if message["type"] == "websocket.disconnect":
                            # Learn: Return None (no value) to the caller and stop this function.
                            return
                        # Learn: Await completion without blocking the event loop: Send this protocol
                        # command or message to the selected peer on upstream; inputs: message['bytes'] with
                        # None as the missing-key default when message['bytes'] with None as the missing-key
                        # default is not None (no value), otherwise message['t....
                        await upstream.send(message.get("bytes") if message.get("bytes") is not None else message["text"])

                # Learn: Define an async function to_browser(). Awaited calls can yield control to other
                # work. The body runs when called, not when defined.
                async def to_browser():
                    # Learn: Asynchronously iterate over upstream, binding message for each item.
                    async for message in upstream:
                        # Learn: Take this branch only if message has type bytes (including subclasses).
                        if isinstance(message, bytes):
                            # Learn: Await completion without blocking the event loop: Call
                            # browser.send_bytes with the arguments shown.
                            await browser.send_bytes(message)
                        # Learn: Run this alternative only when the preceding conditional did not select its
                        # first branch.
                        else:
                            # Learn: Await completion without blocking the event loop: Call
                            # browser.send_text with the arguments shown.
                            await browser.send_text(message)

                # Learn: Set tasks to a new list containing asyncio.create_task(to_remote()),
                # asyncio.create_task(to_browser()).
                tasks = [asyncio.create_task(to_remote()), asyncio.create_task(to_browser())]
                # Learn: Await completion without blocking the event loop: Call asyncio.wait with the
                # arguments shown.
                await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        # Learn: Handle asyncio.CancelledError; unmatched errors propagate.
        except asyncio.CancelledError:
            # Learn: No operation: this body intentionally needs no executable statement.
            pass
        # Learn: Handle Exception as error; unmatched errors propagate.
        except Exception as error:
            # Report fixed categories/status numbers, never exception messages,
            # which may include connection credentials or internal details.
            # Learn: Set code to 'WEBSOCKET_TRANSPORT_ERROR'.
            code = "WEBSOCKET_TRANSPORT_ERROR"
            # Learn: Take this branch only if error has type InvalidStatus (including subclasses).
            if isinstance(error, InvalidStatus):
                # Learn: Set code to 'UPSTREAM_WEBSOCKET_HTTP_' plus str(error.response.status_code).
                code = "UPSTREAM_WEBSOCKET_HTTP_" + str(error.response.status_code)
            # Learn: Try this alternative condition only when earlier branches did not match.
            elif isinstance(error, TimeoutError):
                # Learn: Set code to 'UPSTREAM_WEBSOCKET_TIMEOUT'.
                code = "UPSTREAM_WEBSOCKET_TIMEOUT"
            # Learn: Take this branch only if on_error.
            if on_error:
                # Learn: Call on_error with the arguments shown.
                on_error(code)
        # Learn: Always run cleanup, whether the operation succeeds, returns, or raises.
        finally:
            # Learn: Take this branch only if on_disconnected.
            if on_disconnected:
                # Learn: Call on_disconnected with no arguments.
                on_disconnected()
            # Learn: Enter anyio.move_on_after(2, shield=True). The context manager controls setup/exit;
            # inspect it for the actual cleanup behavior.
            with anyio.move_on_after(2, shield=True):
                # Learn: Iterate over tasks, binding task for each item.
                for task in tasks:
                    # Learn: Call task.cancel with no arguments.
                    task.cancel()
                # Learn: Take this branch only if tasks.
                if tasks:
                    # Learn: Await completion without blocking the event loop: Call asyncio.gather with the
                    # arguments shown.
                    await asyncio.gather(*tasks, return_exceptions=True)
                # Learn: Try the following operations; matching except clauses handle failures.
                try:
                    # Learn: Await completion without blocking the event loop: Close this owned connection,
                    # stream, file, or browser resource on browser.
                    await browser.close(code=1000)
                # Learn: Handle RuntimeError; unmatched errors propagate.
                except RuntimeError:
                    # Learn: No operation: this body intentionally needs no executable statement.
                    pass

    # Learn: Register this function as the route for the indicated HTTP method or WebSocket path;
    # dependencies enforce the configured boundary.
    @app.get("/{path:path}")
    # Learn: Define an async function assets(path, request). Awaited calls can yield control to other work.
    # The body runs when called, not when defined.
    async def assets(path: str, request: Request):
        # Learn: Take this branch only if not (authorized(request.cookies)).
        if not authorized(request.cookies):
            # Learn: Return Response(status_code=403, headers=private_headers) to the caller and stop this
            # function.
            return Response(status_code=403, headers=private_headers)
        # The host is fixed from this sandbox's SDK. Browser input can select
        # only a path on that host; no browser cookies or auth headers are forwarded.
        # Learn: Try the following operations; matching except clauses handle failures.
        try:
            # Learn: Asynchronously enter httpx.AsyncClient(timeout=10, follow_redirects=False,
            # transport=transport) as client. The context manager controls setup/exit; inspect it for the
            # actual cleanup behavior.
            async with httpx.AsyncClient(timeout=10, follow_redirects=False, transport=transport) as client:
                # Learn: Set upstream to await client.get('https://' + host + '/' + path,
                # params=request.query_params, headers=headers); the fixed remote service connection or
                # response.
                upstream = await client.get("https://" + host + "/" + path,
                                            # Learn: Pass keyword params = request.query_params.
                                            params=request.query_params, headers=headers)
            # Learn: Take this branch only if upstream.status_code does not equal 200.
            if upstream.status_code != 200:
                # Learn: Take this branch only if on_error AND path equals 'vnc.html' OR
                # path.endswith('.js').
                if on_error and (path == "vnc.html" or path.endswith(".js")):
                    # Learn: Call on_error with the arguments shown.
                    on_error("UPSTREAM_ASSET_HTTP_" + str(upstream.status_code))
                # Learn: Return Response('Desktop viewer asset unavailable.', status_code=502,
                # headers=private_headers) to the caller and stop this function.
                return Response("Desktop viewer asset unavailable.", status_code=502, headers=private_headers)
            # Learn: Set response_headers to a new dictionary with keys **unpacked values, 'Content-Type'.
            response_headers = {**private_headers, "Content-Type": upstream.headers.get("content-type", "application/octet-stream")}
            # Learn: Return Response(upstream.content, headers=response_headers) to the caller and stop this
            # function.
            return Response(upstream.content, headers=response_headers)
        # Learn: Handle httpx.HTTPError; unmatched errors propagate.
        except httpx.HTTPError:
            # Learn: Take this branch only if on_error.
            if on_error:
                # Learn: Call on_error with the arguments shown.
                on_error("UPSTREAM_ASSET_CONNECTION_ERROR")
            # Learn: Return Response('Cannot reach desktop viewer.', status_code=502,
            # headers=private_headers) to the caller and stop this function.
            return Response("Cannot reach desktop viewer.", status_code=502, headers=private_headers)

    # Learn: Return app to the caller and stop this function.
    return app


# Learn: Wrap the generator as a context manager: yield enters the with-block and exit resumes cleanup.
@contextmanager
# Learn: Define open_live_view(sandbox). The body runs when called, not when defined.
def open_live_view(sandbox):
    # Learn: Document this module, class, or function with a docstring; it is not an action or a model
    # instruction.
    """Own the VNC stream and local server; sandbox cleanup belongs to caller."""
    # Learn: Set listener to socket.socket(); the loopback socket owned by the local live-view server.
    listener = socket.socket()
    # Learn: Set server to None (no value); the local viewer HTTP/WebSocket server.
    server = None
    # Learn: Set thread to None (no value); the background thread that serves the live viewer.
    thread = None
    # Learn: Set started_stream to False.
    started_stream = False
    # Learn: Try the following operations; matching except clauses handle failures. The finally block runs
    # on every exit.
    try:
        # Learn: Call listener.bind with the arguments shown.
        listener.bind(("127.0.0.1", 0))
        # Learn: Call listener.listen with the arguments shown.
        listener.listen(32)
        # Learn: Set port to listener.getsockname()[1].
        port = listener.getsockname()[1]
        # Learn: Set origin to an f-string that substitutes the expressions in {...} into the text; the
        # browser origin being checked before accepting a write or WebSocket.
        origin = f"http://127.0.0.1:{port}"
        # Learn: Call sandbox.stream.start with the arguments shown.
        sandbox.stream.start(require_auth=True)
        # Learn: Set started_stream to True.
        started_stream = True
        # Learn: Set host to urlsplit(sandbox.stream.get_url()).hostname; the parsed destination hostname
        # rather than a substring of the URL.
        host = urlsplit(sandbox.stream.get_url()).hostname
        # Learn: Set secret to token_urlsafe(32); the unpredictable local viewer capability; keep it out of
        # saved logs.
        secret = token_urlsafe(32)
        # Learn: Set handle to LiveViewHandle(origin + '/watch/' + secret).
        handle = LiveViewHandle(origin + "/watch/" + secret)
        # Learn: Define report_error(code). The body runs when called, not when defined.
        def report_error(code):
            # Learn: Append one item to the ordered collection on handle.errors; inputs: code.
            handle.errors.append(code)
            # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
            # 'Live viewer connection error:', code.
            print("Live viewer connection error:", code, flush=True)
        # Learn: Set app to create_viewer_app(host, sandbox.traffic_access_token,
        # sandbox.stream.get_auth_key(), secret, origin, on_connected=handle.connected.s....
        app = create_viewer_app(host, sandbox.traffic_access_token, sandbox.stream.get_auth_key(), secret, origin,
                               # Learn: Pass keyword on_connected = handle.connected.set.
                               on_connected=handle.connected.set, on_disconnected=handle.connected.clear,
                               # Learn: Pass keyword on_error = report_error.
                               on_error=report_error)
        # Learn: Set server to uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=port,
        # access_log=False, log_level='critical', ws='websockets-sansio', time...; the local viewer
        # HTTP/WebSocket server.
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port,
            # Learn: Pass keyword access_log = False.
            access_log=False, log_level="critical", ws="websockets-sansio", timeout_graceful_shutdown=1))
        # Learn: Set thread to threading.Thread(target=server.run, kwargs={'sockets': [listener]},
        # daemon=True); the background thread that serves the live viewer.
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        # Learn: Call thread.start with no arguments.
        thread.start()
        # Learn: Set deadline to time.monotonic() plus 5; the absolute monotonic-clock cutoff for admitting
        # further work.
        deadline = time.monotonic() + 5
        # Learn: Repeat this block while not (server.started).
        while not server.started:
            # Learn: Take this branch only if not (thread.is_alive()) OR time.monotonic() is at least
            # deadline.
            if not thread.is_alive() or time.monotonic() >= deadline:
                # Learn: Raise RuntimeError('Local desktop viewer failed to start.') to stop the normal
                # path.
                raise RuntimeError("Local desktop viewer failed to start.")
            # Learn: Pause for the requested duration; callers must bound this wait on time; inputs: 0.01.
            time.sleep(0.01)
        # Learn: Yield handle to the with-block/request; resume here for cleanup afterward.
        yield handle
    # Learn: Always run cleanup, whether the operation succeeds, returns, or raises.
    finally:
        # Learn: Take this branch only if server is not None (no value).
        if server is not None:
            # Learn: Set server.should_exit to True.
            server.should_exit = True
        # Learn: Take this branch only if thread is not None (no value).
        if thread is not None:
            # Learn: Call thread.join with the arguments shown.
            thread.join(timeout=3)
        # Learn: Close this owned connection, stream, file, or browser resource on listener.
        listener.close()
        # Learn: Take this branch only if started_stream.
        if started_stream:
            # Learn: Build a terminal RunResult retaining the transcript and denials on sandbox.stream.
            sandbox.stream.stop()


# Learn: Define wait_for_viewer(viewer, timeout, stream). The body runs when called, not when defined.
def wait_for_viewer(viewer, *, timeout=45, stream=None):
    # Learn: Document this module, class, or function with a docstring; it is not an action or a model
    # instruction.
    # Learn string line 1: Literal prompt, documentation, or fixture content: Block until the viewer
    # connects and the user presses Enter, so the agent. It remains unchanged at runtime.
    # Learn string line 2: Literal prompt, documentation, or fixture content: never starts before the person
    # can see the desktop. Shared by the demos.. It remains unchanged at runtime.
    """Block until the viewer connects and the user presses Enter, so the agent
    never starts before the person can see the desktop. Shared by the demos."""
    # Learn: Set stream to sys.stdin when stream is None (no value), otherwise stream.
    stream = sys.stdin if stream is None else stream
    # Learn: Call viewer.wait_connected with no arguments.
    viewer.wait_connected()
    # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs: 'Viewer
    # stream transport connected. Confirm that the remote desktop and page are visible.'.
    print("Viewer stream transport connected. Confirm that the remote desktop and page are visible.", flush=True)
    # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs: an
    # f-string that substitutes the expressions in {...} into the text.
    print(f"When the desktop is visible, press Enter here to start the agent ({timeout}-second limit).", flush=True)
    # Learn: Take this branch only if not (select.select([stream], [], [], timeout)[0]).
    if not select.select([stream], [], [], timeout)[0]:
        # Learn: Raise TimeoutError('Viewer wait expired; desktop will be cleaned up.') to stop the normal
        # path.
        raise TimeoutError("Viewer wait expired; desktop will be cleaned up.")
    # Learn: Take this branch only if not (stream.readline()).
    if not stream.readline():
        # Learn: Raise RuntimeError('Interactive terminal required for --watch.') to stop the normal path.
        raise RuntimeError("Interactive terminal required for --watch.")
