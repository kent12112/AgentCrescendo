# ANNOTATED READING COPY — not executed, not imported, may drift from the source.
# Source: packages/security/crescendo_security/policy.py (9130a21, Nov 13 2026).
# The permission check ("gateway"). Called by file 2 (loop) and again by file 5 (desktop).
# The original long docstring of authorize() is shortened here; its rules are commented inline.

"""Gateway policy: decides whether a tool call the model proposed may run.

The model proposes; the gateway decides. A TaskGrant is created by the control
plane before the agent starts and is frozen afterwards. Nothing the model says,
nothing a web page says, and nothing another agent sends can widen it.

This is an application-level check. It cannot stop a browser that leaks data
through a page's own requests; network egress controls must enforce the same
destinations outside the desktop (a week-one feasibility check with E2B).
"""
# ^ Key idea: the model only SUGGESTS. This file decides. And because a browser can
#   make its own requests, a network firewall (E2B allow/deny lists, file 5) is also needed.

from collections.abc import Mapping  # Type for "dict-like"; used for ToolCall.args.
from dataclasses import dataclass, field  # Shorthand for simple data classes.
from typing import Any  # "Any type" for argument values.
from urllib.parse import urlsplit  # Splits a URL into scheme/host/port like a browser does.

import re  # Regular expressions; used to require a word/number in search queries.


@dataclass(frozen=True)  # frozen: once created, fields can't be reassigned (the model can't widen it).
class TaskGrant:  # The permission slip for one task.
    """Authority given to one task. frozen=True: attributes cannot be reassigned."""

    task_id: str  # Name of the task, e.g. "vision-agent-demo".
    allowed_tools: frozenset[str]  # Which tool names may run, e.g. {"screenshot", "scroll", "finish"}. frozenset = immutable set.
    # Exact lowercase hostnames, e.g. "en.wikipedia.org". An allowlist fails closed:
    # anything not listed (localhost, 169.254.169.254, internal names) is denied.
    allowed_hosts: frozenset[str]  # Which websites may be visited. Empty in the F07 demo = no websites.


@dataclass(frozen=True)  # Immutable.
class ToolCall:  # One action the model proposed.
    """A tool request proposed by the model. Treat every field as untrusted input."""

    name: str  # Tool name, e.g. "scroll".
    args: Mapping[str, Any] = field(default_factory=dict)  # Its arguments, e.g. {"direction": "down", "amount": 5}. Defaults to {}.


@dataclass(frozen=True)  # Immutable.
class Decision:  # The answer from authorize().
    allowed: bool  # True = go ahead; False = refuse.
    reason: str  # Human-readable why. On refusal, the model sees this text, so it must not contain secrets.


def authorize(grant: TaskGrant, call: ToolCall) -> Decision:  # "May this proposed call run under this grant?"
    """Return Decision(True, ...) only when the call is permitted. (Full rule list in the source docstring.)"""
    # 1. Tool allowlist. Unknown or ungranted tools fail closed.
    if call.name not in grant.allowed_tools:  # Tool not on the permission slip (including made-up tool names)?
        return Decision(False, f"Tool '{call.name}' is not permitted for this task.")  # Refuse.

    if call.name == "search_page":  # Rules for searching text on the current page (text agent, not F07):
        query = call.args.get("query")  # Get the query; .get avoids a crash if it's missing.
        if (set(call.args) != {"query"} or not isinstance(query, str)  # Exactly one key "query", holding a string...
                or not query.strip() or len(query) > 200 or not re.search(r"\w", query)):  # ...not blank, ≤200 chars, has a letter/digit.
            return Decision(False, "search_page requires a nonblank query of at most 200 characters containing words or numbers.")  # Otherwise refuse.

    if call.name == "scroll":  # Rules for scrolling (the F07 action):
        if (set(call.args) != {"direction", "amount"}  # Exactly these two keys, nothing extra...
                or call.args.get("direction") not in ("up", "down")  # ...direction is "up" or "down"...
                or type(call.args.get("amount")) is not int  # ...amount is a real int (`type(...) is int` rejects True and 2.0)...
                or not 1 <= call.args["amount"] <= 5):  # ...and between 1 and 5.
            return Decision(False, "scroll requires direction up/down and an integer amount from 1 to 5.")  # Otherwise refuse.

    if call.name == "navigate":  # Rules for visiting a URL (text agent / W1-6, not F07):
        # 2a. Model output is untrusted: never assume the argument exists or is a str.
        url = call.args.get("url")  # Get the URL (may be missing).
        if not isinstance(url, str):  # Missing or not text?
            return Decision(False, "navigate requires a url string.")  # Refuse.
        # 2b. urlsplit parses like a browser would; string matching does not.
        try:  # Parsing can fail on malformed input...
            parts = urlsplit(url)  # Split into scheme, host, port, path, ...
        except ValueError:  # ...if it does:
            # Malformed model output is a denied proposal, not a reason to
            # crash the run. Keep the parser's raw error out of the transcript.
            return Decision(False, "The URL is malformed.")  # Refuse politely.
        if parts.scheme != "https":  # Only encrypted https (no http, file:, javascript:, ...).
            return Decision(False, "Only https URLs are permitted.")  # Refuse.
        # 2c. .hostname is the real destination: lowercased, with any "user@" removed.
        # "https://en.wikipedia.org@evil.com" has hostname "evil.com".
        if parts.hostname not in grant.allowed_hosts:  # Exact match against the allowlist (no "starts with" tricks).
            return Decision(False, f"Host '{parts.hostname}' is not permitted for this task.")  # Refuse.
        # 2d. A non-default port can reach a different service on the same host.
        try:  # Reading .port can itself fail on garbage like ":abc"...
            port = parts.port  # The explicit port, or None if none was written.
        except ValueError:  # ...if so:
            return Decision(False, "The URL has an invalid port.")  # Refuse.
        if port is not None:  # Any explicit port (even :443) is refused.
            return Decision(False, "Explicit ports are not permitted.")  # Refuse.

    return Decision(True, "Permitted by task grant.")  # Passed every applicable rule: allow.
