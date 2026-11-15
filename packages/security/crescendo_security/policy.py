# Learn: Document this module, class, or function with a docstring; it is not an action or a model
# instruction.
# Learn string line 1: Literal prompt, documentation, or fixture content: Gateway policy: decides whether a
# tool call the model proposed may run.. It remains unchanged at runtime.
# Learn string line 3: Literal prompt, documentation, or fixture content: The model proposes; the gateway
# decides. A TaskGrant is created by the control. It remains unchanged at runtime.
# Learn string line 4: Literal prompt, documentation, or fixture content: plane before the agent starts and
# is frozen afterwards. Nothing the model says,. It remains unchanged at runtime.
# Learn string line 5: Literal prompt, documentation, or fixture content: nothing a web page says, and
# nothing another agent sends can widen it.. It remains unchanged at runtime.
# Learn string line 7: Literal prompt, documentation, or fixture content: This is an application-level
# check. It cannot stop a browser that leaks data. It remains unchanged at runtime.
# Learn string line 8: Literal prompt, documentation, or fixture content: through a page's own requests;
# network egress controls must enforce the same. It remains unchanged at runtime.
# Learn string line 9: Literal prompt, documentation, or fixture content: destinations outside the desktop
# (a week-one feasibility check with E2B).. It remains unchanged at runtime.
"""Gateway policy: decides whether a tool call the model proposed may run.

The model proposes; the gateway decides. A TaskGrant is created by the control
plane before the agent starts and is frozen afterwards. Nothing the model says,
nothing a web page says, and nothing another agent sends can widen it.

This is an application-level check. It cannot stop a browser that leaks data
through a page's own requests; network egress controls must enforce the same
destinations outside the desktop (a week-one feasibility check with E2B).
"""
# Learn: From collections.abc, import Mapping (describes key/value access without requiring a concrete
# dict).
from collections.abc import Mapping
# Learn: From dataclasses, import dataclass (generates data-container initialization and comparison
# methods); field (configures a dataclass field, including per-instance factories and repr hiding).
from dataclasses import dataclass, field
# Learn: From typing, import Any (marks a deliberately unconstrained type, often at an SDK boundary).
from typing import Any
# Learn: From urllib.parse, import urlsplit (parses scheme, hostname, port, and path instead of guessing
# from substrings).
from urllib.parse import urlsplit

# Learn: Import re: matches bounded text patterns such as query words or answer formats.
import re


# Learn: Decorate the class with generated data-container methods; frozen=True prevents attribute
# reassignment.
@dataclass(frozen=True)
# Learn: Define TaskGrant. Indented methods and attributes belong to this class.
class TaskGrant:
    # Learn: Document this module, class, or function with a docstring; it is not an action or a model
    # instruction.
    """Authority given to one task. frozen=True: attributes cannot be reassigned."""

    # Learn: Declare task_id with type str.
    task_id: str
    # Learn: Declare allowed_tools with type frozenset[str]; the exact set of tools this task can request.
    allowed_tools: frozenset[str]
    # Exact lowercase hostnames, e.g. "en.wikipedia.org". An allowlist fails closed:
    # anything not listed (localhost, 169.254.169.254, internal names) is denied.
    # Learn: Declare allowed_hosts with type frozenset[str]; the exact permitted destination hostnames.
    allowed_hosts: frozenset[str]


# Learn: Decorate the class with generated data-container methods; frozen=True prevents attribute
# reassignment.
@dataclass(frozen=True)
# Learn: Define ToolCall. Indented methods and attributes belong to this class.
class ToolCall:
    # Learn: Document this module, class, or function with a docstring; it is not an action or a model
    # instruction.
    """A tool request proposed by the model. Treat every field as untrusted input."""

    # Learn: Declare name with type str.
    name: str
    # Learn: Set args to field(default_factory=dict); the arguments for the current operation. Configure a
    # per-instance default or representation option for this dataclass field.
    args: Mapping[str, Any] = field(default_factory=dict)


# Learn: Decorate the class with generated data-container methods; frozen=True prevents attribute
# reassignment.
@dataclass(frozen=True)
# Learn: Define Decision. Indented methods and attributes belong to this class.
class Decision:
    # Learn: Declare allowed with type bool.
    allowed: bool
    # Learn: Declare reason with type str; the explanatory text; a model reason is display data, not
    # authority.
    reason: str


# Learn: Define authorize(grant, call). The body runs when called, not when defined.
def authorize(grant: TaskGrant, call: ToolCall) -> Decision:
    # Learn: Document this module, class, or function with a docstring; it is not an action or a model
    # instruction.
    # Learn string line 1: Literal prompt, documentation, or fixture content: Return Decision(True, ...)
    # only when the call is permitted.. It remains unchanged at runtime.
    # Learn string line 3: Literal prompt, documentation, or fixture content: Rules, checked in this order
    # (packages/security/tests encodes them):. It remains unchanged at runtime.
    # Learn string line 5: Literal prompt, documentation, or fixture content: 1. call.name must be in
    # grant.allowed_tools. Otherwise deny.. It remains unchanged at runtime.
    # Learn string line 6: Literal prompt, documentation, or fixture content: 2. For "navigate":. It remains
    # unchanged at runtime.
    # Learn string line 7: Literal prompt, documentation, or fixture content: a. args["url"] must exist and
    # be a str.. It remains unchanged at runtime.
    # Learn string line 8: Literal prompt, documentation, or fixture content: b. Parse it with
    # urllib.parse.urlsplit; deny parsing errors. The scheme. It remains unchanged at runtime.
    # Learn string line 9: Literal prompt, documentation, or fixture content: must be exactly "https".. It
    # remains unchanged at runtime.
    # Learn string line 10: Literal prompt, documentation, or fixture content: c. Use .hostname (already
    # lowercased, userinfo removed). It must be in. It remains unchanged at runtime.
    # Learn string line 11: Literal prompt, documentation, or fixture content: grant.allowed_hosts. Do NOT
    # use string tricks such as startswith or "in":. It remains unchanged at runtime.
    # Learn string line 12: Literal prompt, documentation, or fixture content: "en.wikipedia.org.evil.com"
    # and "https://en.wikipedia.org@evil.com". It remains unchanged at runtime.
    # Learn string line 13: Literal prompt, documentation, or fixture content: must both be denied.. It
    # remains unchanged at runtime.
    # Learn string line 14: Literal prompt, documentation, or fixture content: d. Deny any explicit port
    # (.port is not None). Reading .port can raise. It remains unchanged at runtime.
    # Learn string line 15: Literal prompt, documentation, or fixture content: ValueError for malformed
    # ports; treat that as a denial too.. It remains unchanged at runtime.
    # Learn string line 16: Literal prompt, documentation, or fixture content: 3. For "search_page": require
    # exactly one query string, nonblank, containing. It remains unchanged at runtime.
    # Learn string line 17: Literal prompt, documentation, or fixture content: a word/number, and no longer
    # than 200 characters. It searches the current. It remains unchanged at runtime.
    # Learn string line 18: Literal prompt, documentation, or fixture content: page; it cannot supply a URL
    # or widen navigation authority.. It remains unchanged at runtime.
    # Learn string line 19: Literal prompt, documentation, or fixture content: 4. Anything that passes is
    # allowed.. It remains unchanged at runtime.
    # Learn string line 21: Literal prompt, documentation, or fixture content: Every denial needs a short
    # human-readable reason. The agent sees it in its. It remains unchanged at runtime.
    # Learn string line 22: Literal prompt, documentation, or fixture content: transcript, so it must not
    # reveal secrets, but should explain enough to replan.. It remains unchanged at runtime.
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
    4. Anything that passes is allowed.

    Every denial needs a short human-readable reason. The agent sees it in its
    transcript, so it must not reveal secrets, but should explain enough to replan.
    """
    # 1. Tool allowlist. Unknown or ungranted tools fail closed.
    # Learn: Take this branch only if call.name is not in grant.allowed_tools.
    if call.name not in grant.allowed_tools:
        # Learn: Return Decision(False, f"Tool '{call.name}' is not permitted for this task.") to the caller
        # and stop this function.
        return Decision(False, f"Tool '{call.name}' is not permitted for this task.")

    # Learn: Take this branch only if call.name equals 'search_page'.
    if call.name == "search_page":
        # Learn: Set query to call.args['query'] with None as the missing-key default; the bounded search
        # keywords for the current page, not a navigation URL. Read a key/row, using the supplied default
        # when applicable.
        query = call.args.get("query")
        # Learn: Take this branch only if set(call.args) does not equal a set of 'query' (unique members) OR
        # not (query has type str (including subclasses)) OR not (query.strip()) OR the number of
        # items/characters in query is greater than 200 OR not (re.search('\\w', query)).
        if (set(call.args) != {"query"} or not isinstance(query, str)
                # Learn: Call query.strip with no arguments.
                or not query.strip() or len(query) > 200 or not re.search(r"\w", query)):
            # Learn: Return Decision(False, 'search_page requires a nonblank query of at most 200 characters
            # containing words or numbers.') to the caller and stop this function.
            return Decision(False, "search_page requires a nonblank query of at most 200 characters containing words or numbers.")

    # Learn: Take this branch only if call.name equals 'scroll'.
    if call.name == "scroll":
        # Learn: Take this branch only if set(call.args) does not equal a set of 'direction', 'amount'
        # (unique members) OR call.args['direction'] with None as the missing-key default is not in the
        # tuple ('up', 'down') (positional values) OR the exact Python type of call.args['amount'] with None
        # as ....
        if (set(call.args) != {"direction", "amount"}
                # Learn: Read a key/row, using the supplied default when applicable on call.args; inputs:
                # 'direction'.
                or call.args.get("direction") not in ("up", "down")
                # Learn: Call type with the arguments shown.
                or type(call.args.get("amount")) is not int
                # Learn: Alternatively accept not 1 <= call.args["amount"] <= 5):. Python short-circuits
                # boolean expressions from left to right.
                or not 1 <= call.args["amount"] <= 5):
            # Learn: Return Decision(False, 'scroll requires direction up/down and an integer amount from 1
            # to 5.') to the caller and stop this function.
            return Decision(False, "scroll requires direction up/down and an integer amount from 1 to 5.")

    # Learn: Take this branch only if call.name equals 'navigate'.
    if call.name == "navigate":
        # 2a. Model output is untrusted: never assume the argument exists or is a str.
        # Learn: Set url to call.args['url'] with None as the missing-key default; the destination or
        # current page address. Read a key/row, using the supplied default when applicable.
        url = call.args.get("url")
        # Learn: Take this branch only if not (url has type str (including subclasses)).
        if not isinstance(url, str):
            # Learn: Return Decision(False, 'navigate requires a url string.') to the caller and stop this
            # function.
            return Decision(False, "navigate requires a url string.")
        # 2b. urlsplit parses like a browser would; string matching does not.
        # Learn: Try the following operations; matching except clauses handle failures.
        try:
            # Learn: Set parts to urlsplit(url); the structured URL fields; use hostname and port for
            # destination checks.
            parts = urlsplit(url)
        # Learn: Handle ValueError; unmatched errors propagate.
        except ValueError:
            # Malformed model output is a denied proposal, not a reason to
            # crash the run. Keep the parser's raw error out of the transcript.
            # Learn: Return Decision(False, 'The URL is malformed.') to the caller and stop this function.
            return Decision(False, "The URL is malformed.")
        # Learn: Take this branch only if parts.scheme does not equal 'https'.
        if parts.scheme != "https":
            # Learn: Return Decision(False, 'Only https URLs are permitted.') to the caller and stop this
            # function.
            return Decision(False, "Only https URLs are permitted.")
        # 2c. .hostname is the real destination: lowercased, with any "user@" removed.
        # "https://en.wikipedia.org@evil.com" has hostname "evil.com".
        # Learn: Take this branch only if parts.hostname is not in grant.allowed_hosts.
        if parts.hostname not in grant.allowed_hosts:
            # Learn: Return Decision(False, f"Host '{parts.hostname}' is not permitted for this task.") to
            # the caller and stop this function.
            return Decision(False, f"Host '{parts.hostname}' is not permitted for this task.")
        # 2d. A non-default port can reach a different service on the same host.
        # Learn: Try the following operations; matching except clauses handle failures.
        try:
            # Learn: Set port to parts.port.
            port = parts.port
        # Learn: Handle ValueError; unmatched errors propagate.
        except ValueError:
            # Learn: Return Decision(False, 'The URL has an invalid port.') to the caller and stop this
            # function.
            return Decision(False, "The URL has an invalid port.")
        # Learn: Take this branch only if port is not None (no value).
        if port is not None:
            # Learn: Return Decision(False, 'Explicit ports are not permitted.') to the caller and stop this
            # function.
            return Decision(False, "Explicit ports are not permitted.")

    # Learn: Return Decision(True, 'Permitted by task grant.') to the caller and stop this function.
    return Decision(True, "Permitted by task grant.")
