# Handoff: W1X-F02 — broad public browsing (public-web mode)

- Date/time and timezone: November 16, 2026, America/New_York.
- Author / session: Claude, VS Code session; no delegation.
- Intended recipient: Codex or user; review requested, not an assignment.
- Base commit: `811701a`.
- Uncommitted paths (this task): `packages/security/crescendo_security/policy.py`,
  `packages/security/tests/test_public_web.py` (new),
  `packages/agent_runtime/crescendo_agent/e2b_desktop.py`,
  `packages/agent_runtime/crescendo_agent/e2b_preflight.py`,
  `packages/agent_runtime/tests/test_e2b_preflight.py`,
  `packages/agent_runtime/tests/test_public_web_desktop.py` (new),
  `packages/agent_runtime/tests/test_public_browse_demo.py` (new),
  `packages/agent_runtime/tests/test_network_browser_check.py`,
  `scripts/e2b_preflight.py`, `scripts/e2b_network_browser_check.py`,
  `scripts/e2b_public_browse_demo.py` (new), `docs/decisions/0004-public-web-mode.md` (new),
  `docs/e2b-preflight.md`, `docs/implementation-plan.md`, `README.md`, `docs/status.md`,
  this handoff. W1-F10 and W1-F13 changes are also uncommitted in the same tree.
- State: complete, with open follow-ups below.
- Ownership: released.

## Goal and acceptance criteria

Allow public destinations while blocking private, link-local, metadata, and
backend addresses. The model moves only by clicking existing links, never by
composing URLs. Agents hold no credentials.

## Changes and decisions

See [decision 0004](../decisions/0004-public-web-mode.md). In short:
`TaskGrant.public_web` (default off); `PRIVATE_NETWORKS`;
`authorize_destination()` (tool-independent, used by the request filter);
`public_host_problem()`; model `navigate` refused in public mode;
`E2BDesktop.open_start_page()` for host start pages; `network_config(grant)`.
Allowlist mode is unchanged except that `user:password@` URLs are now refused,
and the filter no longer depends on the `navigate` tool.

## Evidence

Local: `.venv/bin/python -m pytest -q`: 524 passed (existing Starlette/httpx
warning). `scripts/smoke_browser_subrequests.py` and
`scripts/smoke_redirect_recovery.py` passed (allowlist-mode regression, local Edge).

Live (Claude-run):
- `scripts/e2b_preflight.py --public`: two passing runs with the TLS/DNS canary.
  Before those: one run with E2B rejecting `0.0.0.0/8` (no desktop created), one
  run whose plain-TCP canary falsely "connected", and a two-desktop scratch
  diagnostic proving the deny list is enforced in both deny-only and
  deny-all-plus-public-CIDR configurations.
- `scripts/e2b_network_browser_check.py --public`: two passing runs. The first
  attempt timed out waiting for page load, because dropped requests hang; fixed
  by recording them as `pending`.
- `scripts/e2b_public_browse_demo.py --save-screenshots`: two passes (20.0 s,
  17.9 s), one `click_link` plus finish. Before those: one deadline error (I
  passed 240 s; the loop caps at 120 s), one Groq `model_unavailable`, and one
  deadline after four throttled scrolls. The start page then moved to
  `#External_links`. Saved under `.demo-artifacts/public-*` (ignored).

## Open issues and next action

1. Readability: fonts, scripts, and images are blocked, so boston.gov rendered
   with invisible text. Deciding whether to allow fonts (and images) is the user's
   call; fonts would add no new destinations.
2. Search results: there is no typing tool, so "search results" in the plan
   item is not covered.
3. Metadata MMDS exception and IPv6 (no route) are unchanged; recheck after
   provider changes.
4. A hostile page can offer links that encode page content into URLs. The agent
   holds no credentials or secrets, so only page content and the goal could leak.
