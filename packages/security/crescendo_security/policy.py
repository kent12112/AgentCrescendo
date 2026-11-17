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


# Define authorize with parameters grant, call.
def authorize(grant: TaskGrant, call: ToolCall, *, click_area: ScreenArea | None = None) -> Decision:
    """Return Decision(True, ...) only when the call is permitted.

    Rules, checked in this order (packages/security/tests encodes them):

    1. call.name must be in grant.allowed_tools. Otherwise deny.
    2. For "navigate":
       a. args["url"] must exist and be a str.
       b. Parse it with urllib.parse.urlsplit; deny parsing errors. The scheme
          must be exactly "https".
       c. Use .hostname (already lowercased, userinfo removed). It must be in
          grant.allowed_hosts. Do NOT use string tricks such as startswith or "in":
          "en.wikipedia.org.evil.com" and "https://en.wikipedia.org@evil.com"
          must both be denied.
       d. Deny any explicit port (.port is not None). Reading .port can raise
          ValueError for malformed ports; treat that as a denial too.
    3. For "search_page": require exactly one query string, nonblank, containing
       a word/number, and no longer than 200 characters. It searches the current
       page; it cannot supply a URL or widen navigation authority.
    4. For "click": args are exactly integer "x" and "y" in real screen pixels.
       The caller must pass `click_area`, the browser page rectangle; the point must
       be inside it. No area means the page position is unknown, so deny. This keeps
       clicks off the address bar, tabs, taskbar, and dock. What the click *hits*
       inside the page is checked separately by the desktop adapter.
    5. For "read_visible_links": no arguments. This permits reading visible link
       labels and geometry; it does not capture an image or permit a click.
    6. Anything that passes is allowed.

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
    # Check whether call.name equals 'navigate'.
    if call.name == "navigate":
        # 2a. Model output is untrusted: never assume the argument exists or is a str.
        # Set url to call.args['url'], or None if absent.
        url = call.args.get("url")
        # Check whether not (whether url is an instance of str).
        if not isinstance(url, str):
            # Return Decision(False, 'navigate requires a url string.').
            return Decision(False, "navigate requires a url string.")
        # 2b. urlsplit parses like a browser would; string matching does not.
        # Try the following operations; matching except clauses handle failures.
        try:
            # Set parts to urlsplit(url).
            parts = urlsplit(url)
        # Handle ValueError; unmatched errors propagate.
        except ValueError:
            # Malformed model output is a denied proposal, not a reason to
            # crash the run. Keep the parser's raw error out of the transcript.
            # Return Decision(False, 'The URL is malformed.').
            return Decision(False, "The URL is malformed.")
        # Check whether parts.scheme does not equal 'https'.
        if parts.scheme != "https":
            # Return Decision(False, 'Only https URLs are permitted.').
            return Decision(False, "Only https URLs are permitted.")
        # 2c. .hostname is the real destination: lowercased, with any "user@" removed.
        # "https://en.wikipedia.org@evil.com" has hostname "evil.com".
        # Check whether parts.hostname is not in grant.allowed_hosts.
        if parts.hostname not in grant.allowed_hosts:
            # Return Decision(False, f"Host '{parts.hostname}' is not permitted for this task.").
            return Decision(False, f"Host '{parts.hostname}' is not permitted for this task.")
        # 2d. A non-default port can reach a different service on the same host.
        # Try the following operations; matching except clauses handle failures.
        try:
            # Set port to parts.port.
            port = parts.port
        # Handle ValueError; unmatched errors propagate.
        except ValueError:
            # Return Decision(False, 'The URL has an invalid port.').
            return Decision(False, "The URL has an invalid port.")
        # Check whether port is not None.
        if port is not None:
            # Return Decision(False, 'Explicit ports are not permitted.').
            return Decision(False, "Explicit ports are not permitted.")

    # Return Decision(True, 'Permitted by task grant.').
    return Decision(True, "Permitted by task grant.")
