# Learn: Document this module, class, or function with a docstring; it is not an action or a model
# instruction.
# Learn string line 1: Literal prompt, documentation, or fixture content: Fixed Python programs executed
# inside E2B to start Chrome and its CDP relay.. It remains unchanged at runtime.
# Learn string line 3: Literal prompt, documentation, or fixture content: These are remote program strings,
# not host-side browser operations.. It remains unchanged at runtime.
"""Fixed Python programs executed inside E2B to start Chrome and its CDP relay.

These are remote program strings, not host-side browser operations.
"""

# Learn: Set START_BROWSER to '\nimport os, shutil, subprocess, time, urllib.request\nfrom pathlib import
# Path\nbinary = n....
# Learn string line 2: Import os: reads process environment/configuration and OS facilities; Import shutil:
# locates the installed Chrome/Chromium executable; Import subprocess: starts or inspects child processes;
# Import time: measures monotonic elapsed time and provides bounded pauses; Import urllib.request:
# constructs explicit HTTP requests and ha...
# Learn string line 3: From pathlib, import Path (represents filesystem paths and explicit file operations).
# Learn string line 4: Set binary to next((path for name in ('google-chrome', 'google-chrome-stable',
# 'chromium', 'chromium-browser') if (path := shutil.which(name))), N....
# Learn string line 5: Continue the remote Python expression: "google-chrome", "google-chrome-stable",
# "chromium", "chromium-browser".
# Learn string line 6: Close this embedded-language block or expression.
# Learn string line 7: Take this branch only if binary is None (no value).
# Learn string line 8: Raise RuntimeError('No Chrome/Chromium executable found in the E2B template') to stop
# the normal path.
# Learn string line 9: Set args to a new list containing binary, '--no-sandbox', '--disable-dev-shm-usage',
# '--no-first-run', '--no-default-browser-check', '--disable-background-networking'...; the arguments for
# the current operation.
# Learn string line 10: Continue the remote Python expression: "--no-default-browser-check",
# "--disable-background-networking",.
# Learn string line 11: Continue the remote Python expression: "--remote-debugging-port=9222",
# "--user-data-dir=/tmp/crescendo-chrome",.
# Learn string line 12: Continue the remote Python expression: "about:blank"].
# Learn string line 13: Enter open('/tmp/crescendo-chrome.log', 'wb') as log. The context manager controls
# setup/exit; inspect it for the actual cleanup behavior.
# Learn string line 14: Set child to subprocess.Popen(args, stdout=log, stderr=log, env={**os.environ,
# 'DISPLAY': ':0'}, start_new_session=True).
# Learn string line 15: Continue the remote Python expression: env={**os.environ, "DISPLAY": ":0"},
# start_new_session=True).
# Learn string line 16: Set deadline to time.monotonic() plus 45; the absolute monotonic-clock cutoff for
# admitting further work.
# Learn string line 17: Set opener to urllib.request.build_opener(urllib.request.ProxyHandler({})).
# Learn string line 18: Repeat this block while True.
# Learn string line 19: Set code to child.poll().
# Learn string line 20: Take this branch only if code is not None (no value).
# Learn string line 21: Raise RuntimeError('Chrome exited during startup (code ' + str(code) + '): ' +
# Path('/tmp/crescendo-chrome.log').read_text(errors='replace... to stop the normal path.
# Learn string line 22: Continue the remote Python expression:
# Path("/tmp/crescendo-chrome.log").read_text(errors="replace")[-4000:]).
# Learn string line 23: Try the following operations; matching except clauses handle failures.
# Learn string line 24: Enter opener.open('http://127.0.0.1:9222/json/version', timeout=1). The context
# manager controls setup/exit; inspect it for the actual cleanup behavior.
# Learn string line 25: Exit the nearest loop immediately; continue with the code after it.
# Learn string line 26: Continue the remote Python expression: except OSError as exc:.
# Learn string line 27: Take this branch only if time.monotonic() is at least deadline.
# Learn string line 28: Raise RuntimeError('Chrome debugger port 9222 did not become ready within 45
# seconds. ' + 'Last error: ' + repr(exc) + '\\n' + Path('/tmp/... to stop the normal path; preserve the
# explicit exception cause.
# Learn string line 29: Continue the remote Python expression: "Last error: " + repr(exc) + "\\n" +.
# Learn string line 30: Continue the remote Python expression:
# Path("/tmp/crescendo-chrome.log").read_text(errors="replace")[-4000:]) from exc.
# Learn string line 31: Pause for the requested duration; callers must bound this wait on time; inputs: 0.2.
START_BROWSER = '''
import os, shutil, subprocess, time, urllib.request
from pathlib import Path
binary = next((path for name in (
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser"
) if (path := shutil.which(name))), None)
if binary is None:
    raise RuntimeError("No Chrome/Chromium executable found in the E2B template")
args = [binary, "--no-sandbox", "--disable-dev-shm-usage", "--no-first-run",
        "--no-default-browser-check", "--disable-background-networking",
        "--remote-debugging-port=9222", "--user-data-dir=/tmp/crescendo-chrome",
        "about:blank"]
with open("/tmp/crescendo-chrome.log", "wb") as log:
    child = subprocess.Popen(args, stdout=log, stderr=log,
                             env={**os.environ, "DISPLAY": ":0"}, start_new_session=True)
deadline = time.monotonic() + 45
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
while True:
    code = child.poll()
    if code is not None:
        raise RuntimeError("Chrome exited during startup (code " + str(code) + "): " +
                           Path("/tmp/crescendo-chrome.log").read_text(errors="replace")[-4000:])
    try:
        with opener.open("http://127.0.0.1:9222/json/version", timeout=1):
            break
    except OSError as exc:
        if time.monotonic() >= deadline:
            raise RuntimeError("Chrome debugger port 9222 did not become ready within 45 seconds. " +
                               "Last error: " + repr(exc) + "\\n" +
                               Path("/tmp/crescendo-chrome.log").read_text(errors="replace")[-4000:]) from exc
        time.sleep(0.2)
'''

# Chrome's debugger listens on loopback. Relay it to a private E2B service port.
# The relay carries browser control only; it is not an outbound browsing proxy.
# Learn: Set RELAY to '\nimport select, socket, socketserver\n\ndef chrome_request(data):\n head, body =
# data.spli....
# Learn string line 2: Import select: waits for file/socket readiness without polling continuously; Import
# socket: creates or probes network sockets; Import socketserver: serves the fixed TCP relay using a handler
# per connection.
# Learn string line 4: Define chrome_request(data). The body runs when called, not when defined.
# Learn string line 5: Set (head, body) to data.split(b'\r\n\r\n', 1).
# Learn string line 6: Set lines to head.split(b'\r\n').
# Learn string line 7: E2B has authenticated the external request already. Chrome's debugger
# Learn string line 8: accepts only IP/localhost Host headers (including WebSocket upgrades).
# Learn string line 9: Set headers to a list built from lines[1:] by the comprehension with its filter; the
# headers explicitly supplied at this trust boundary.
# Learn string line 10: Continue the remote Python expression: if line.partition(b":")[0].strip().lower().
# Learn string line 11: Continue the remote Python expression: not in (b"host",
# b"e2b-traffic-access-token")].
# Learn string line 12: Return b'\r\n'.join([lines[0], b'Host: 127.0.0.1:9222', *headers]) plus b'\r\n\r\n'
# plus body to the caller and stop this function.
# Learn string line 14: Define Handler inheriting socketserver.BaseRequestHandler. Indented methods and
# attributes belong to this class.
# Learn string line 15: Define handle(). The body runs when called, not when defined.
# Learn string line 16: Call self.request.settimeout with the arguments shown.
# Learn string line 17: Set data to b''; the decoded response or bytes being processed.
# Learn string line 18: Repeat this block while b'\r\n\r\n' is not in data.
# Learn string line 19: Set chunk to self.request.recv(4096).
# Learn string line 20: Take this branch only if not (chunk).
# Learn string line 21: Return None (no value) to the caller and stop this function.
# Learn string line 22: Update data using its previous value plus chunk.
# Learn string line 23: Take this branch only if the number of items/characters in data is greater than
# 65536.
# Learn string line 24: Return None (no value) to the caller and stop this function.
# Learn string line 25: Enter socket.create_connection(('127.0.0.1', 9222), timeout=10) as upstream. The
# context manager controls setup/exit; inspect it for the actual cleanup behavior.
# Learn string line 26: Call upstream.sendall with the arguments shown.
# Learn string line 27: Set peers to a new list containing self.request, upstream.
# Learn string line 28: Repeat this block while True.
# Learn string line 29: Set (ready, _, _) to select.select(peers, [], [], 60).
# Learn string line 30: Take this branch only if not (ready).
# Learn string line 31: Return None (no value) to the caller and stop this function.
# Learn string line 32: Iterate over ready, binding source for each item.
# Learn string line 33: Set data to source.recv(65536); the decoded response or bytes being processed.
# Learn string line 34: Take this branch only if not (data).
# Learn string line 35: Return None (no value) to the caller and stop this function.
# Learn string line 36: Set target to upstream when source is self.request, otherwise self.request.
# Learn string line 37: Call target.sendall with the arguments shown.
# Learn string line 38: Define Server inheriting socketserver.ThreadingTCPServer. Indented methods and
# attributes belong to this class.
# Learn string line 39: Set allow_reuse_address to True.
# Learn string line 40: Set daemon_threads to True.
# Learn string line 41: Take this branch only if __name__ equals '__main__'. The __main__ guard keeps
# imports from launching the CLI.
# Learn string line 42: Call Server(('0.0.0.0', 9223), Handler).serve_forever with no arguments.
RELAY = r'''
import select, socket, socketserver

def chrome_request(data):
    head, body = data.split(b"\r\n\r\n", 1)
    lines = head.split(b"\r\n")
    # E2B has authenticated the external request already. Chrome's debugger
    # accepts only IP/localhost Host headers (including WebSocket upgrades).
    headers = [line for line in lines[1:]
               if line.partition(b":")[0].strip().lower()
               not in (b"host", b"e2b-traffic-access-token")]
    return b"\r\n".join([lines[0], b"Host: 127.0.0.1:9222", *headers]) + b"\r\n\r\n" + body

class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(10)
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = self.request.recv(4096)
            if not chunk:
                return
            data += chunk
            if len(data) > 65536:
                return
        with socket.create_connection(("127.0.0.1", 9222), timeout=10) as upstream:
            upstream.sendall(chrome_request(data))
            peers = [self.request, upstream]
            while True:
                ready, _, _ = select.select(peers, [], [], 60)
                if not ready:
                    return
                for source in ready:
                    data = source.recv(65536)
                    if not data:
                        return
                    target = upstream if source is self.request else self.request
                    target.sendall(data)
class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
if __name__ == "__main__":
    Server(("0.0.0.0", 9223), Handler).serve_forever()
'''

# Learn: Set WAIT_READY to '\nimport time, urllib.request\nfrom pathlib import Path\ndeadline =
# time.monotonic() + 20\n....
# Learn string line 2: Import time: measures monotonic elapsed time and provides bounded pauses; Import
# urllib.request: constructs explicit HTTP requests and handles URL/network errors.
# Learn string line 3: From pathlib, import Path (represents filesystem paths and explicit file operations).
# Learn string line 4: Set deadline to time.monotonic() plus 20; the absolute monotonic-clock cutoff for
# admitting further work.
# Learn string line 5: Set opener to urllib.request.build_opener(urllib.request.ProxyHandler({})).
# Learn string line 6: Repeat this block while True.
# Learn string line 7: Try the following operations; matching except clauses handle failures.
# Learn string line 8: Enter opener.open('http://127.0.0.1:9223/json/version', timeout=1). The context
# manager controls setup/exit; inspect it for the actual cleanup behavior.
# Learn string line 9: Exit the nearest loop immediately; continue with the code after it.
# Learn string line 10: Continue the remote Python expression: except OSError as exc:.
# Learn string line 11: Take this branch only if time.monotonic() is at least deadline.
# Learn string line 12: Set logs to a new list (empty).
# Learn string line 13: Iterate over the tuple ('chrome', 'relay') (positional values), binding name for
# each item.
# Learn string line 14: Set path to Path('/tmp/crescendo-' + name + '.log').
# Learn string line 15: Append one item to the ordered collection on logs; inputs: name plus ': ' plus
# path.read_text(errors='replace')[-4000:] when path.exists(), otherwise 'no log file'.
# Learn string line 16: Continue the remote Python expression: if path.exists() else "no log file")).
# Learn string line 17: Raise RuntimeError('Chrome debugger did not become ready. Last error: ' + repr(exc)
# + '\\n' + '\\n'.join(logs)) to stop the normal path; preserve the explicit exception cause.
# Learn string line 18: Continue the remote Python expression: repr(exc) + "\\n" + "\\n".join(logs)) from
# exc.
# Learn string line 19: Pause for the requested duration; callers must bound this wait on time; inputs: 0.2.
WAIT_READY = '''
import time, urllib.request
from pathlib import Path
deadline = time.monotonic() + 20
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
while True:
    try:
        with opener.open("http://127.0.0.1:9223/json/version", timeout=1):
            break
    except OSError as exc:
        if time.monotonic() >= deadline:
            logs = []
            for name in ("chrome", "relay"):
                path = Path("/tmp/crescendo-" + name + ".log")
                logs.append(name + ": " + (path.read_text(errors="replace")[-4000:]
                            if path.exists() else "no log file"))
            raise RuntimeError("Chrome debugger did not become ready. Last error: " +
                               repr(exc) + "\\n" + "\\n".join(logs)) from exc
        time.sleep(0.2)
'''
