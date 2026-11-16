# Handoff: W1-3 / W1-F10 — IPv6 egress probe

- Date/time and timezone: November 16, 2026, America/New_York.
- Author / session: Claude, VS Code session; no delegation.
- Intended recipient: user (live run needed); review requested, not an assignment.
- Base commit: `fc3d128`.
- Uncommitted paths: `packages/agent_runtime/crescendo_agent/e2b_preflight.py`,
  `packages/agent_runtime/tests/test_e2b_preflight.py`, `scripts/e2b_preflight.py`,
  `docs/e2b-preflight.md`, `docs/status.md`, this handoff. Earlier uncommitted work
  in the tree (refactor and comment passes) is preserved and not part of this change.
- State: ready for live run; W1-F10 remains open.
- Ownership: released.

## Goal and acceptance criteria

The W1-F10 slice covering IPv6 behavior. `deny_out` is `0.0.0.0/0` (IPv4 only), so
IPv6 egress was unmeasured. Acceptance requires a live run showing the public and
private IPv6 probes unreachable, with the error names recorded.

## Changes and decisions

- `PROBE` gains `public_ipv6_tcp` (`2606:4700:4700::1111`:443), `private_ipv6_tcp`
  (`fd00::1`:80), and informational `wikipedia_ipv6_tcp` (AAAA lookup, then TCP 443).
  All TCP probes now record an `error` name (e.g. `ENETUNREACH`, `TimeoutError`).
- New `evaluate_preflight(results) -> Verdict` holds the pass/fail rules previously
  inline in the script. It fails closed on missing or malformed entries.
- Remote command timeout is now 75 s instead of 45 s (worst case about 50 s; desktop
  lifetime still 120 s).
- Sandbox network configuration is unchanged by design: measure first.
- Probe-string comments moved inside the remote code. The old "string line N"
  block would no longer match the literal.

## Evidence

Local only; no E2B or model calls:
- `.venv/bin/python -m pytest -q packages/agent_runtime/tests/test_e2b_preflight.py`: 18 passed.
- `.venv/bin/python -m pytest -q`: 252 passed, existing Starlette/httpx warning.
- Probe helper extracted from `PROBE` and run against closed loopback ports
  `127.0.0.1:9` and `[::1]:9`: both `{"reachable": false, "error": "ECONNREFUSED"}`.
- `git diff --check` on changed code: clean.

Local checks do not prove anything about E2B's IPv6 behavior.

Live, user-run (`.venv/bin/python scripts/e2b_preflight.py`, one run, November 16):
passed. Wikipedia 200; example.com unreachable; metadata TCP reachable (MMDS note);
private IPv4 `TimeoutError`; all three IPv6 probes `ENETUNREACH`. Interpretation:
the guest had no IPv6 route. This shows no IPv6 egress path in this run. It does not
show an IPv6 firewall rule.

## Open issues and next action

1. IPv6 is closed by absence of a route, not by policy. Rerun after SDK/provider
   changes. Optional hardening: confirm whether `deny_out` accepts `"::/0"`, and
   share one network-config builder between `run_preflight` and `open_e2b_desktop`
   (currently duplicated).
2. Remaining W1-F10: redirects (suggested next), DNS rebinding, browser
   subrequests, controlled reachable destination.
