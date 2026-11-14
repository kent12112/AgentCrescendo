"""Gateway policy: decides whether a tool call the model proposed may run.

The model proposes; the gateway decides. A TaskGrant is created by the control
plane before the agent starts and is frozen afterwards. Nothing the model says,
nothing a web page says, and nothing another agent sends can widen it.

This is an application-level check. It cannot stop a browser that leaks data
through a page's own requests; network egress controls must enforce the same
destinations outside the desktop (a week-one feasibility check with E2B).
"""
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

import re


@dataclass(frozen=True)
class TaskGrant:
    """Authority given to one task. frozen=True: attributes cannot be reassigned."""

    task_id: str
    allowed_tools: frozenset[str]
    # Exact lowercase hostnames, e.g. "en.wikipedia.org". An allowlist fails closed:
    # anything not listed (localhost, 169.254.169.254, internal names) is denied.
    allowed_hosts: frozenset[str]


@dataclass(frozen=True)
class ToolCall:
    """A tool request proposed by the model. Treat every field as untrusted input."""

    name: str
    args: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str


def authorize(grant: TaskGrant, call: ToolCall) -> Decision:
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
    if call.name not in grant.allowed_tools:
        return Decision(False, f"Tool '{call.name}' is not permitted for this task.")

    if call.name == "search_page":
        query = call.args.get("query")
        if (set(call.args) != {"query"} or not isinstance(query, str)
                or not query.strip() or len(query) > 200 or not re.search(r"\w", query)):
            return Decision(False, "search_page requires a nonblank query of at most 200 characters containing words or numbers.")

    if call.name == "scroll":
        if (set(call.args) != {"direction", "amount"}
                or call.args.get("direction") not in ("up", "down")
                or type(call.args.get("amount")) is not int
                or not 1 <= call.args["amount"] <= 5):
            return Decision(False, "scroll requires direction up/down and an integer amount from 1 to 5.")

    if call.name == "navigate":
        # 2a. Model output is untrusted: never assume the argument exists or is a str.
        url = call.args.get("url")
        if not isinstance(url, str):
            return Decision(False, "navigate requires a url string.")
        # 2b. urlsplit parses like a browser would; string matching does not.
        try:
            parts = urlsplit(url)
        except ValueError:
            # Malformed model output is a denied proposal, not a reason to
            # crash the run. Keep the parser's raw error out of the transcript.
            return Decision(False, "The URL is malformed.")
        if parts.scheme != "https":
            return Decision(False, "Only https URLs are permitted.")
        # 2c. .hostname is the real destination: lowercased, with any "user@" removed.
        # "https://en.wikipedia.org@evil.com" has hostname "evil.com".
        if parts.hostname not in grant.allowed_hosts:
            return Decision(False, f"Host '{parts.hostname}' is not permitted for this task.")
        # 2d. A non-default port can reach a different service on the same host.
        try:
            port = parts.port
        except ValueError:
            return Decision(False, "The URL has an invalid port.")
        if port is not None:
            return Decision(False, "Explicit ports are not permitted.")

    return Decision(True, "Permitted by task grant.")
