# Handoff: W1-3 / W1-F10 — network checks completed

- Date/time and timezone: November 16, 2026, America/New_York.
- Author / session: Claude, VS Code session; no delegation.
- Intended recipient: Codex or user; review requested, not an assignment.
- Base commit: `811701a`.
- Uncommitted paths: `packages/agent_runtime/crescendo_agent/e2b_preflight.py`,
  `packages/agent_runtime/tests/test_e2b_preflight.py`,
  `packages/agent_runtime/tests/test_network_browser_check.py` (new),
  `scripts/e2b_network_browser_check.py` (new), `scripts/smoke_browser_subrequests.py` (new),
  `docs/e2b-preflight.md`, `docs/status.md`, `docs/implementation-plan.md`, this handoff.
- State: complete, with an explicit narrowing of supported behavior.
- Ownership: released.

## Goal and acceptance criteria

Finish W1-F10: redirects, browser subrequests, DNS/rebinding, shared IPs, and
private/backend restrictions, measured live; resolve gaps or narrow supported
behavior before adding workers. IPv6 was done earlier
([IPv6 handoff](2026-11-16-claude-w1-f10-ipv6-probe.md)).

## Changes and decisions

- Preflight `PROBE` gains DNS probes (unlisted lookup, UDP to `8.8.8.8` and
  `1.1.1.1`, TCP 443 to `8.8.8.8`), name-bound probes (allowed TLS/HTTP name sent
  to example.com's IP and to `10.0.0.1`), a shared-IP probe (`en.wiktionary.org`),
  domain fronting, and an off-host redirect followed by hand.
- `evaluate_preflight()` adds a `NAME_BOUND` outcome rule (`other_server` and
  ambiguous outcomes fail) and a redirect rule; DNS and fronting are notes.
- Preflight sandbox: lifetime 240 s, `on_timeout: kill`, probe timeout 170 s.
- New live `scripts/e2b_network_browser_check.py`: `collect()` drives the
  real browser and records raw facts; pure `judge()` passes or fails them.
  `scripts/smoke_browser_subrequests.py` runs the same checks in local Edge with the
  real filter and locally supplied responses.
- Decision: rebinding is tested as "allowed name, other IP" rather than with a
  hostile DNS server. The firewall matches names (SDK docstring), so this is
  the same connection a lying DNS reply would cause.
- Decision: the `8.8.8.8` and domain-fronting paths are accepted and narrowed,
  not fixed: only a program composing its own traffic can use them, and the
  model has no such tool. Recorded in [preflight](../e2b-preflight.md#narrowed-supported-behavior).

## Evidence

Local:
- `.venv/bin/python -m pytest -q`: 446 passed, existing Starlette/httpx warning.
- Probe helpers run against loopback servers in tests; `other_server` checked
  once with a throwaway self-signed certificate in the scratchpad.
- `.venv/bin/python scripts/smoke_browser_subrequests.py`: passed (local Edge, no internet).
  The first version failed a correct block (Chrome's error page read as a host); fixed.

Live (Claude-run, no model calls, E2B key from `.env`):
- `.venv/bin/python scripts/e2b_preflight.py`: two runs passed with identical results.
  The first labeled TLS closes `ENOEXEC` (OpenSSL code read as an OS errno);
  fixed, second run shows `SSLEOFError`.
- `.venv/bin/python scripts/e2b_network_browser_check.py`: two runs passed.

Key results: allowed names are routed by name to the real Wikipedia regardless
of the guest's chosen IP; private IPs time out even with an allowed name;
Wiktionary (shared IPs) and the Wiktionary redirect target are closed at TLS;
only the default resolver answers DNS. Exceptions: `8.8.8.8` open on all
ports; domain fronting served Wiktionary; prefetch/preconnect/dns-prefetch bypass
the filter (prefetch was not issued on E2B).

Not proven: behavior after E2B/Chrome upgrades; WebSocket/fetch (JavaScript is off);
whether `dns_servers: []` with `/etc/hosts` keeps browsing working.

## Open issues and next action

1. Before any code-execution tool or secrets in the guest: close `8.8.8.8`
   (try `dns_servers: []` + `/etc/hosts`) and rerun both checks.
2. W1X-F02 (broad public browsing) can't use a name allowlist. It needs a
   different design: allow public, deny private ranges. Rerun the name-bound
   and private probes under that configuration.
3. Optional: `--dns-prefetch-disable` for Chrome, verified by a live run.
4. Review question: is the residual DNS-leak risk acceptable for Week 1 exit?
