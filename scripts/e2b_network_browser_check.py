"""Live, model-free check of browser-originated traffic (plan W1-F10). One metered desktop.

The preflight (scripts/e2b_preflight.py) tests the network from a plain program
in the guest. This script tests what the *browser* sends on its own, without a
model tool call: images, stylesheets, frames, prefetches, a meta refresh, and a
redirect to another host. Every one of those requests must pass through our
request filter (CDP Fetch, `E2BDesktop._request_paused`), and the E2B firewall
sits underneath it as the second layer.

Expected results:

  allowed stylesheet (en.wikipedia.org)     loads
  stylesheet/image/frame on example.com     blocked by the request filter
  image on en.wikipedia.org                 blocked (only documents and stylesheets allowed)
  plain-http, private-IP, metadata-IP image never loads
  prefetch to example.com                   never loads
  meta refresh to example.com               blocked; the page does not change
  /wiki/wikt:Boston (redirects to Wiktionary)  redirect hop blocked, if the server redirects

Not testable from here: Chrome's preconnect / DNS prefetch open connections or
send lookups without a request the filter can see. Only the E2B firewall (and
its DNS exception) governs those; see docs/e2b-preflight.md.
"""
import json
import os
from urllib.parse import urlsplit
from uuid import uuid4

ALLOWED_CSS = "https://en.wikipedia.org/w/load.php?modules=site.styles&only=styles"
# Each must never load. The second value says which layer we expect to stop it:
# "filter" means our request filter must record it; "any" accepts Chrome or the
# filter (Chrome may refuse private addresses itself before asking the filter).
MUST_NOT_LOAD = {
    "https://example.com/blocked.css": "filter",
    "https://example.com/blocked.png": "filter",
    "https://example.com/frame": "filter",
    "https://example.com/prefetch": "any",
    "https://en.wikipedia.org/static/images/icons/wikipedia.png": "filter",
    # Chrome may upgrade this to https before the filter sees it, so any layer counts.
    "http://en.wikipedia.org/plain-http.png": "any",
    "https://10.0.0.1/private.png": "any",
    "https://169.254.169.254/latest/meta-data/": "any",
}
SUBRESOURCE_PAGE = (
    "<html><head>"
    f'<link rel="stylesheet" href="{ALLOWED_CSS.replace("&", "&amp;")}">'
    '<link rel="stylesheet" href="https://example.com/blocked.css">'
    '<link rel="prefetch" href="https://example.com/prefetch">'
    '<link rel="preconnect" href="https://example.com">'
    '<link rel="dns-prefetch" href="//dns-prefetch.example.com">'
    "</head><body>"
    '<img src="https://example.com/blocked.png">'
    '<img src="https://en.wikipedia.org/static/images/icons/wikipedia.png">'
    '<img src="http://en.wikipedia.org/plain-http.png">'
    '<img src="https://10.0.0.1/private.png">'
    '<img src="https://169.254.169.254/latest/meta-data/">'
    '<iframe src="https://example.com/frame"></iframe>'
    "</body></html>"
)
REFRESH_TARGET = "https://example.com/refresh"
REFRESH_PAGE = f'<html><head><meta http-equiv="refresh" content="0;url={REFRESH_TARGET}"></head><body>refresh</body></html>'
REDIRECT_SOURCE = "https://en.wikipedia.org/wiki/wikt:Boston"


def collect(desktop):
    """Drive the real browser and record raw facts. Judges nothing."""
    page = desktop.page
    finished, failed = set(), {}
    page.on("requestfinished", lambda request: finished.add(request.url))
    page.on("requestfailed", lambda request: failed.setdefault(request.url, request.failure))

    # 1. Subresources the page requests by itself.
    page.set_content(SUBRESOURCE_PAGE, wait_until="load", timeout=30000)
    page.wait_for_timeout(2000)  # let late requests (prefetch, frame) settle
    blocked = set(desktop.blocked_requests)
    subresources = {}
    for url in [ALLOWED_CSS, *MUST_NOT_LOAD]:
        if url in finished:
            subresources[url] = "loaded"
        elif url in blocked:
            subresources[url] = "blocked_by_filter"
        elif url in failed:
            subresources[url] = "failed_elsewhere"
        else:
            subresources[url] = "not_requested"

    # 2. A meta refresh: a navigation started by the page, not by a tool call.
    before = len(desktop.blocked_requests)
    page.set_content(REFRESH_PAGE, wait_until="load", timeout=30000)
    page.wait_for_timeout(3000)
    refresh = {"blocked": REFRESH_TARGET in desktop.blocked_requests[before:],
               "final_url": page.url}

    # 3. A live redirect from the allowed host to another host.
    before = len(desktop.blocked_requests)
    desktop.navigate(REDIRECT_SOURCE)
    hops = desktop.blocked_requests[before:]
    redirect = {"blocked_hosts": sorted({urlsplit(url).hostname for url in hops
                                         if urlsplit(url).hostname != "en.wikipedia.org"}),
                "final_url": page.url, "status": desktop.last_navigation_status}
    return {"subresources": subresources, "meta_refresh": refresh, "redirect": redirect}


def left_allowed_host(url):
    """True when the browser ended up on a real web page outside the allowlist.

    about:blank and Chrome's own error page (chrome-error://) are not web hosts:
    landing there after a block is the expected result.
    """
    parts = urlsplit(url or "")
    return parts.scheme in ("http", "https") and parts.hostname != "en.wikipedia.org"


def judge(evidence):
    """Return (passed, lines). Every line starts PASS, FAIL, or NOTE."""
    lines, passed = [], True

    def record(ok, message):
        nonlocal passed
        passed = passed and ok
        lines.append(("PASS: " if ok else "FAIL: ") + message)

    subresources = evidence["subresources"]
    record(subresources.get(ALLOWED_CSS) == "loaded",
           f"allowed Wikipedia stylesheet loaded ({subresources.get(ALLOWED_CSS)})")
    for url, layer in MUST_NOT_LOAD.items():
        state = subresources.get(url)
        ok = state == "blocked_by_filter" if layer == "filter" else state in (
            "blocked_by_filter", "failed_elsewhere", "not_requested")
        record(ok, f"{url} did not load ({state})")

    refresh = evidence["meta_refresh"]
    record(refresh["blocked"] and not left_allowed_host(refresh["final_url"]),
           f"meta refresh to example.com blocked (page stayed at {refresh['final_url']})")

    redirect = evidence["redirect"]
    if redirect["blocked_hosts"]:
        record(not left_allowed_host(redirect["final_url"]),
               f"redirect hop to {', '.join(redirect['blocked_hosts'])} blocked; page at {redirect['final_url']}")
    else:
        record(not left_allowed_host(redirect["final_url"]),
               f"no off-host request was made; page at {redirect['final_url']}")
        lines.append("NOTE: the server did not redirect to another host, so the live redirect "
                     "case was not exercised (scripts/smoke_redirect_recovery.py covers it locally).")
    return passed, lines


def run(sandbox_type):
    from crescendo_agent.e2b_desktop import open_e2b_desktop
    from crescendo_security.policy import TaskGrant

    grant = TaskGrant(str(uuid4()), frozenset({"navigate"}), frozenset({"en.wikipedia.org"}))
    with open_e2b_desktop(grant, sandbox_type=sandbox_type, lifetime_seconds=180) as desktop:
        evidence = collect(desktop)
    print(json.dumps(evidence, indent=2))
    passed, lines = judge(evidence)
    print("\n".join(lines))
    if not passed:
        raise SystemExit("Browser network check failed; do not enable broader browsing.")
    print("All browser network checks passed. No model calls were made.")


# ---------------------------------------------------------------------------
# Public-web mode (W1X-F02): `--public`. Public hosts are now allowed, so the
# questions change: do private destinations stay blocked, and does a public
# NAME that resolves to a private address (DNS rebinding) get stopped? The
# filter cannot see where a name resolves, so only E2B's firewall can stop it.
# ---------------------------------------------------------------------------

PUBLIC_MUST_LOAD = (ALLOWED_CSS, "https://www.boston.gov/")
PUBLIC_MUST_NOT_LOAD = {
    "https://10.0.0.1.sslip.io/rebind.css": "any",       # filter allows the name; firewall must stop it
    "https://192.168.0.1.sslip.io/rebind.css": "any",
    "https://10.0.0.1/private.css": "filter",            # IP literal: refused by the filter
    "https://169.254.169.254/latest/meta-data/": "filter",
    "https://localhost/local.css": "filter",
    "https://example.com/image.png": "filter",           # images are still not an allowed type
}
PUBLIC_PAGE = (
    "<html><head>"
    f'<link rel="stylesheet" href="{ALLOWED_CSS.replace("&", "&amp;")}">'
    '<link rel="stylesheet" href="https://10.0.0.1.sslip.io/rebind.css">'
    '<link rel="stylesheet" href="https://192.168.0.1.sslip.io/rebind.css">'
    '<link rel="stylesheet" href="https://10.0.0.1/private.css">'
    '<link rel="stylesheet" href="https://localhost/local.css">'
    "</head><body>"
    '<img src="https://169.254.169.254/latest/meta-data/">'
    '<img src="https://example.com/image.png">'
    '<iframe src="https://www.boston.gov/"></iframe>'
    "</body></html>"
)


def collect_public(desktop):
    """Load the public-mode page in the real browser and record what happened to each URL."""
    page = desktop.page
    started, finished, failed = set(), set(), {}
    page.on("request", lambda request: started.add(request.url))
    page.on("requestfinished", lambda request: finished.add(request.url))
    page.on("requestfailed", lambda request: failed.setdefault(request.url, request.failure))
    # Do not wait for "load": the firewall drops packets to private addresses, so
    # those requests hang instead of failing. Wait a fixed time, then record.
    page.set_content(PUBLIC_PAGE, wait_until="commit", timeout=30000)
    page.wait_for_timeout(25000)
    blocked = set(desktop.blocked_requests)
    states = {}
    for url in [*PUBLIC_MUST_LOAD, *PUBLIC_MUST_NOT_LOAD]:
        states[url] = ("loaded" if url in finished else "blocked_by_filter" if url in blocked
                       else "failed_elsewhere" if url in failed
                       else "pending" if url in started else "not_requested")
    errors = {url: failed[url] for url in PUBLIC_MUST_NOT_LOAD if url in failed}
    return {"subresources": states, "network_errors": errors}


def judge_public(evidence):
    """Return (passed, lines) for public-web mode."""
    lines, passed = [], True
    states = evidence["subresources"]
    for url in PUBLIC_MUST_LOAD:
        ok = states.get(url) == "loaded"
        passed = passed and ok
        lines.append(("PASS: " if ok else "FAIL: ") + f"public {url} loaded ({states.get(url)})")
    for url, layer in PUBLIC_MUST_NOT_LOAD.items():
        state = states.get(url)
        ok = state == "blocked_by_filter" if layer == "filter" else state in (
            "blocked_by_filter", "failed_elsewhere", "not_requested", "pending")
        passed = passed and ok
        lines.append(("PASS: " if ok else "FAIL: ") + f"{url} did not load ({state})")
    return passed, lines


def run_public(sandbox_type):
    from crescendo_agent.e2b_desktop import open_e2b_desktop
    from crescendo_security.policy import TaskGrant

    grant = TaskGrant(str(uuid4()), frozenset(), frozenset(), public_web=True)
    with open_e2b_desktop(grant, sandbox_type=sandbox_type, lifetime_seconds=180) as desktop:
        evidence = collect_public(desktop)
    print(json.dumps(evidence, indent=2))
    passed, lines = judge_public(evidence)
    print("\n".join(lines))
    if not passed:
        raise SystemExit("Public-mode browser network check failed; do not enable public browsing.")
    print("All public-mode browser network checks passed. No model calls were made.")


def main():
    from crescendo_agent.local_env import load_local_env

    load_local_env()
    if not os.environ.get("E2B_API_KEY"):
        raise SystemExit("Set E2B_API_KEY in this terminal. This check uses E2B resources.")
    import sys
    from e2b_desktop import Sandbox

    run_public(Sandbox) if "--public" in sys.argv[1:] else run(Sandbox)


if __name__ == "__main__":
    main()
