"""Gateway policy: decides whether a tool call the model proposed may run.

The model proposes; the gateway decides. A TaskGrant is created by the control
plane before the agent starts and is frozen afterwards. Nothing the model says,
nothing a web page says, and nothing another agent sends can widen it.

This is an application-level check. It cannot stop a browser that leaks data
through a page's own requests; network egress controls must enforce the same
destinations outside the desktop (a week-one feasibility check with E2B).
"""
# Import from collections.abc: Mapping (describes key/value access without requiring a concrete
# dict).
from collections.abc import Mapping
# Import from dataclasses: dataclass (generates data-container initialization and comparison
# methods); field (configures a dataclass field, including per-instance factories and repr hiding).
from dataclasses import dataclass, field
# Import from typing: Any (marks a deliberately unconstrained type, often at an SDK boundary).
from typing import Any
# Import from urllib.parse: urlsplit (parses scheme, hostname, port, and path instead of guessing
# from substrings).
from urllib.parse import urlsplit

# Import re: matches bounded text patterns such as query words or answer formats.
import re


# IPv4 ranges a desktop must never reach in public-web mode (W1X-F02). E2B's firewall
# denies them at the network layer, because a page or DNS name can lead anywhere.
# private (RFC 1918), carrier-grade NAT, "this network", loopback, link-local and
# cloud metadata, IETF protocol assignments, benchmarking, multicast, reserved.
# IPv6 has no guest route today (W1-F10); re-check before relying on that.
# 0.0.0.0/8 is left out: E2B rejects it ("invalid denied CIDR", live, November 16,
# 2026), and Linux treats a connection to 0.x as this machine, not the network.
PRIVATE_NETWORKS = (
    "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8", "169.254.0.0/16",
    "172.16.0.0/12", "192.0.0.0/24", "192.168.0.0/16", "198.18.0.0/15",
    "224.0.0.0/4", "240.0.0.0/4",
)


# Decorate the class with generated data-container methods; frozen=True prevents attribute
# reassignment.
@dataclass(frozen=True)
# Define TaskGrant.
class TaskGrant:
    """Authority given to one task. frozen=True: attributes cannot be reassigned."""

    # Declare task_id with type str.
    task_id: str
    # Declare allowed_tools with type frozenset[str].
    allowed_tools: frozenset[str]
    # Exact lowercase hostnames, e.g. "en.wikipedia.org". An allowlist fails closed:
    # anything not listed (localhost, 169.254.169.254, internal names) is denied.
    # Declare allowed_hosts with type frozenset[str].
    allowed_hosts: frozenset[str]
    # Public-web mode (W1X-F02, opened further by W1X-F03): any public site instead
    # of allowed_hosts, for page loads and for the model's own navigate. Defaults off
    # so every existing grant keeps its exact allowlist.
    public_web: bool = False


# Decorate the class with generated data-container methods; frozen=True prevents attribute
# reassignment.
@dataclass(frozen=True)
# Define ToolCall.
class ToolCall:
    """A tool request proposed by the model. Treat every field as untrusted input."""

    # Declare name with type str.
    name: str
    # Set args to field(default_factory=dict).
    args: Mapping[str, Any] = field(default_factory=dict)


# Decorate the class with generated data-container methods; frozen=True prevents attribute
# reassignment.
@dataclass(frozen=True)
# Define Decision.
class Decision:
    # Declare allowed with type bool.
    allowed: bool
    # Declare reason with type str.
    reason: str


@dataclass(frozen=True)
class ScreenArea:
    """A rectangle in real desktop pixels. left/top are inside; right/bottom are not."""
    left: int
    top: int
    right: int
    bottom: int

    def contains(self, x: int, y: int) -> bool:
        return self.left <= x < self.right and self.top <= y < self.bottom


# Largest coordinate accepted at all, matching the largest screenshot we accept.
MAX_COORDINATE = 8192
# Longest text type_text may enter: enough for a search query or a short field.
MAX_TYPED_CHARS = 200


# Define authorize with parameters grant, call.
def authorize(grant: TaskGrant, call: ToolCall, *, click_area: ScreenArea | None = None) -> Decision:
    """Return Decision(True, ...) only when the call is permitted.

    Rules, checked in this order (packages/security/tests encodes them):

    1. call.name must be in grant.allowed_tools. Otherwise deny.
    2. For "navigate":
       a. args["url"] must exist and be a str.
       b. authorize_destination() decides: https only, no user name or
          password, no explicit port, and .hostname (lowercased, userinfo
          removed) must be in grant.allowed_hosts, or, in public-web mode, be
          a public site name. Do NOT use string tricks such as startswith or
          "in": "en.wikipedia.org.evil.com" and
          "https://en.wikipedia.org@evil.com" must both be denied.
    3. For "search_page": require exactly one query string, nonblank, containing
       a word/number, and no longer than 200 characters. It searches the current
       page; it cannot supply a URL or widen navigation authority.
    4. For "click": args are exactly integer "x" and "y" in real screen pixels.
       The caller must pass `click_area`, the browser page rectangle; the point must
       be inside it. No area means the page position is unknown, so deny. This keeps
       clicks off the address bar, tabs, taskbar, and dock. What the click *hits*
       inside the page is checked separately by the desktop adapter.
    5. For "read_visible_links": no arguments. This permits reading visible link
       and field labels and geometry; it does not capture an image or permit a click.
    6. For "type_text": args are exactly integer "x"/"y" (the field, in real
       screen pixels, inside `click_area` as for click), "text" (one nonblank
       line of printable characters, at most MAX_TYPED_CHARS), and boolean
       "submit" (press Enter afterwards). Which field is under the point, and
       that it really has keyboard focus, is checked by the desktop adapter.
    7. Anything that passes is allowed.

    Every denial needs a short human-readable reason. The agent sees it in its
    transcript, so it must not reveal secrets, but should explain enough to replan.
    """
    # 1. Tool allowlist. Unknown or ungranted tools fail closed.
    # Check whether call.name is not in grant.allowed_tools.
    if call.name not in grant.allowed_tools:
        # Return Decision(False, f"Tool '{call.name}' is not permitted for this task.").
        return Decision(False, f"Tool '{call.name}' is not permitted for this task.")

    if call.name == "read_visible_links" and call.args:
        return Decision(False, "read_visible_links takes no arguments.")

    # Check whether call.name equals 'search_page'.
    if call.name == "search_page":
        # Set query to call.args['query'], or None if absent.
        query = call.args.get("query")
        # Check whether set(call.args) does not equal a set of 'query' (unique members) OR not
        # (query has type str (including subclasses)) OR not (query.strip()) OR the number of
        # items/characters in query is greater than 200 OR not (re.search('\\w', query)).
        if (set(call.args) != {"query"} or not isinstance(query, str)
                # Call query.strip with no arguments.
                or not query.strip() or len(query) > 200 or not re.search(r"\w", query)):
            # Return Decision(False, 'search_page requires a nonblank query of at most 200
            # characters containing words or numbers.').
            return Decision(False, "search_page requires a nonblank query of at most 200 characters containing words or numbers.")

    # Check whether call.name equals 'scroll'.
    if call.name == "scroll":
        if (set(call.args) != {"direction", "amount"}
                # Read a key/row, using the supplied default when applicable on call.args; inputs:
                # 'direction'.
                or call.args.get("direction") not in ("up", "down")
                # Call type with the arguments shown.
                or type(call.args.get("amount")) is not int
                # Alternatively accept not 1 <= call.args["amount"] <= 5):. Python short-circuits
                # boolean expressions from left to right.
                or not 1 <= call.args["amount"] <= 5):
            # Return Decision(False, 'scroll requires direction up/down and an integer amount from 1
            # to 5.').
            return Decision(False, "scroll requires direction up/down and an integer amount from 1 to 5.")

    if call.name == "click":
        x, y = call.args.get("x"), call.args.get("y")
        # type(...) is int rejects True/False, which Python otherwise treats as 1/0.
        if (set(call.args) != {"x", "y"} or type(x) is not int or type(y) is not int
                or not 0 <= x <= MAX_COORDINATE or not 0 <= y <= MAX_COORDINATE):
            return Decision(False, "click requires integer x and y screen coordinates.")
        if click_area is None:
            return Decision(False, "The browser page position is unknown, so clicks are not permitted.")
        if not click_area.contains(x, y):
            return Decision(False, f"Click at ({x}, {y}) is outside the browser page area.")

    if call.name == "type_text":
        x, y = call.args.get("x"), call.args.get("y")
        text, submit = call.args.get("text"), call.args.get("submit")
        if (set(call.args) != {"x", "y", "text", "submit"} or type(x) is not int or type(y) is not int
                or not 0 <= x <= MAX_COORDINATE or not 0 <= y <= MAX_COORDINATE):
            return Decision(False, "type_text requires integer x and y screen coordinates of a page field.")
        # isprintable() is False for newlines, tabs, and other control characters: a
        # newline would submit and a tab would move focus, outside what was checked.
        if (not isinstance(text, str) or not text.strip() or len(text) > MAX_TYPED_CHARS
                or not text.isprintable()):
            return Decision(False, f"type_text requires one line of 1 to {MAX_TYPED_CHARS} printable characters.")
        if type(submit) is not bool:
            return Decision(False, "type_text requires submit to be true or false.")
        if click_area is None:
            return Decision(False, "The browser page position is unknown, so typing is not permitted.")
        if not click_area.contains(x, y):
            return Decision(False, f"Field at ({x}, {y}) is outside the browser page area.")
    # Check whether call.name equals 'navigate'.
    if call.name == "navigate":
        # 2a. Model output is untrusted: never assume the argument exists or is a str.
        url = call.args.get("url")
        if not isinstance(url, str):
            return Decision(False, "navigate requires a url string.")
        # 2b. The destination rules are shared with the browser request filter. In
        # public-web mode any public site is allowed, including one the model names
        # itself (decision 0005 accepts that model-written URLs can carry data).
        destination = authorize_destination(grant, url)
        if not destination.allowed:
            return destination

    # Return Decision(True, 'Permitted by task grant.').
    return Decision(True, "Permitted by task grant.")



# Names that point inside a network by convention, never to a public site.
# Not complete (a public name can still resolve to a private address), which is
# why E2B's firewall denies PRIVATE_NETWORKS; this check only refuses the obvious.
INTERNAL_SUFFIXES = (".localhost", ".local", ".internal", ".home.arpa", ".lan",
                     ".intranet", ".corp", ".private")


def public_host_problem(host: str) -> str | None:
    """Why `host` is not an acceptable public site name, or None if it is.

    Refuses every IP address, including forms browsers read as IPv4 such as
    "2130706433" or "0x7f.1" (the URL standard treats a numeric last label as
    an address), single-label names, and conventional internal names.
    """
    import ipaddress

    name = host.rstrip(".")
    try:
        ipaddress.ip_address(name)
        return "IP addresses are not permitted; use a site name."
    except ValueError:
        pass
    last = name.rsplit(".", 1)[-1]
    if last.isdigit() or re.fullmatch(r"0x[0-9a-f]*", last):
        return "IP addresses are not permitted; use a site name."
    if "." not in name or not re.fullmatch(r"[a-z0-9.-]+", name):
        return f"Host '{host}' is not a public site name."
    if name == "localhost" or name.endswith(INTERNAL_SUFFIXES):
        return f"Host '{host}' is an internal name."
    return None


def authorize_destination(grant: TaskGrant, url: str) -> Decision:
    """May the browser fetch `url` for this task? Used for every request.

    Independent of tools: the model's navigate tool, the host's start page, and
    every request a page makes all pass through here. Rules, in order:
    https only; no user:password@; no explicit port; then the host must be on
    the grant's allowlist, or, in public-web mode, be a public site name.
    """
    if not isinstance(url, str):
        return Decision(False, "The URL must be a string.")
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return Decision(False, "The URL is malformed.")
    if parts.scheme != "https":
        return Decision(False, "Only https URLs are permitted.")
    if parts.username is not None or parts.password is not None:
        return Decision(False, "URLs with a user name or password are not permitted.")
    if port is not None:
        return Decision(False, "Explicit ports are not permitted.")
    host = parts.hostname
    if not host:
        return Decision(False, "The URL has no host.")
    if grant.public_web:
        problem = public_host_problem(host)
        if problem is not None:
            return Decision(False, problem)
        return Decision(True, "Public site permitted by task grant.")
    if host not in grant.allowed_hosts:
        return Decision(False, f"Host '{host}' is not permitted for this task.")
    return Decision(True, "Permitted by task grant.")
