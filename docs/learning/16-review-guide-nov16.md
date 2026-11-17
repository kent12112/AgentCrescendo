# Review guide: W1-F10, W1-F13, W1X-F02 (November 16, 2026)

Three features, all uncommitted on `claude/w1-f07-vision-scroll` (base
`811701a`). Nothing is committed until you approve. Read in this order: each
file only uses things from files above it.

In the locked-room picture: `authorize_destination()` is a **new rule in the
guard's book** ("may this address be visited?"), the request filter is the
**guard at the inner door** reading full addresses, and E2B's firewall is the
**outer door**, which reads only the name on the envelope (W1-F10) or the street
number (W1X-F02).

Tests: `.venv/bin/python -m pytest -q` (524 pass). Free local checks:
`scripts/smoke_browser_subrequests.py`, `scripts/smoke_redirect_recovery.py`.

## 1. Policy: the security core (W1X-F02)

[policy.py](../../packages/security/crescendo_security/policy.py)

| Where | What to check |
| --- | --- |
| [L34 `PRIVATE_NETWORKS`](../../packages/security/crescendo_security/policy.py#L34) | Is any range missing? `0.0.0.0/8` is left out on purpose (E2B rejects it). No IPv6 ranges, because the guest has no IPv6 route. |
| [L59 `public_web`](../../packages/security/crescendo_security/policy.py#L59) | Defaults to `False`, so every existing grant is unchanged. |
| [L189 navigate rule](../../packages/security/crescendo_security/policy.py#L189) | In public mode the model's `navigate` is refused **before** any URL check. |
| [L209 `public_host_problem`](../../packages/security/crescendo_security/policy.py#L209) | Browser IPv4 spellings (`2130706433`, `0x7f.1`): is the "numeric last label" rule enough? The internal-suffix list is a convention, not complete; the firewall is the real control. |
| [L234 `authorize_destination`](../../packages/security/crescendo_security/policy.py#L234) | Order: https, no `user:pw@`, no port, then host. Allowlist mode now also refuses `user:pw@` (stricter than before). |

Tests: [test_public_web.py](../../packages/security/tests/test_public_web.py).

**Question to ask yourself:** does anything other than the request filter and
`open_start_page` call `authorize_destination`? (It shouldn't.)

## 2. Desktop adapter: wiring (W1X-F02)

[e2b_desktop.py](../../packages/agent_runtime/crescendo_agent/e2b_desktop.py)

| Where | What to check |
| --- | --- |
| [L475 request filter](../../packages/agent_runtime/crescendo_agent/e2b_desktop.py#L475) | Now judges destinations, not the `navigate` tool. A behavior change in allowlist mode too: the filter no longer needs `navigate` granted. |
| [L616 `open_start_page`](../../packages/agent_runtime/crescendo_agent/e2b_desktop.py#L616) / [L627 `_load`](../../packages/agent_runtime/crescendo_agent/e2b_desktop.py#L627) | `navigate()` (model, needs the tool) and `open_start_page()` (host, destination only) share `_load`. Could the model ever reach `open_start_page`? Check the vision loop: it can't. |
| [L679 `public_network_config`](../../packages/agent_runtime/crescendo_agent/e2b_desktop.py#L679) / [L688 `network_config`](../../packages/agent_runtime/crescendo_agent/e2b_desktop.py#L688) | Public mode: no `allow_out`, deny the private list. Allowlist mode: same values as before, moved into a function. |

Tests: [test_public_web_desktop.py](../../packages/agent_runtime/tests/test_public_web_desktop.py).

## 3. Network preflight (W1-F10 and W1X-F02)

[e2b_preflight.py](../../packages/agent_runtime/crescendo_agent/e2b_preflight.py). The
long `PROBE` string runs **inside** the sandbox; everything after it runs on
your Mac and only judges results.

W1-F10 (allowlist mode):

| Where | What to check |
| --- | --- |
| [L32 `error_name`](../../packages/agent_runtime/crescendo_agent/e2b_preflight.py#L32) | The `ENOEXEC` bug fix: TLS errors are named by type, not errno. |
| [L42 `tls_as_allowed_name`](../../packages/agent_runtime/crescendo_agent/e2b_preflight.py#L42) | The rebinding test. Certificate verification is **on**: a valid Wikipedia certificate means the firewall picked the IP by name. |
| [L165–L240 probe sections](../../packages/agent_runtime/crescendo_agent/e2b_preflight.py#L165) | DNS, name-bound, shared IP, fronting, redirect. |
| [L254 `NAME_BOUND`](../../packages/agent_runtime/crescendo_agent/e2b_preflight.py#L254), [L341–L396 judges](../../packages/agent_runtime/crescendo_agent/e2b_preflight.py#L341) | Which results fail and which are notes. Are `8.8.8.8` and domain fronting right as notes rather than failures? |

W1X-F02 (public mode):

| Where | What to check |
| --- | --- |
| [L462 canary](../../packages/agent_runtime/crescendo_agent/e2b_preflight.py#L462), [L488 `cloudflare_answers`](../../packages/agent_runtime/crescendo_agent/e2b_preflight.py#L488) | **The most important idea of the day.** A plain TCP connect is not evidence on E2B. Only a server-proven answer (verified TLS or a DNS reply) counts. |
| [L546 `evaluate_public_preflight`](../../packages/agent_runtime/crescendo_agent/e2b_preflight.py#L546) | A reachable canary must fail the run. |

Tests: [test_e2b_preflight.py](../../packages/agent_runtime/tests/test_e2b_preflight.py)
(the bottom half runs the probe's helpers against loopback servers).
Script: [scripts/e2b_preflight.py](../../scripts/e2b_preflight.py) (`--public` flag).

## 4. Browser checks (W1-F10 and W1X-F02)

[e2b_network_browser_check.py](../../scripts/e2b_network_browser_check.py). Pattern:
`collect()` records raw facts and `judge()` turns them into PASS/FAIL, so `judge`
can be tested without E2B.

| Where | What to check |
| --- | --- |
| [L33 `MUST_NOT_LOAD`](../../scripts/e2b_network_browser_check.py#L33) | `"filter"` means our filter must catch it; `"any"` accepts any layer. Is each choice justified? |
| [L104 `left_allowed_host`](../../scripts/e2b_network_browser_check.py#L104) | The fix for Chrome's error page being read as a foreign site. |
| [L171 `PUBLIC_MUST_NOT_LOAD`](../../scripts/e2b_network_browser_check.py#L171), [L194 `collect_public`](../../scripts/e2b_network_browser_check.py#L194) | Rebinding names are `"any"`, because the filter can't catch them. Requests still `pending` after 25 s count as not loaded. Is 25 s enough? |

Local version: [smoke_browser_subrequests.py](../../scripts/smoke_browser_subrequests.py)
(real Edge, fake responses, no internet). Tests:
[test_network_browser_check.py](../../packages/agent_runtime/tests/test_network_browser_check.py).

## 5. Public browsing demo (W1X-F02)

[e2b_public_browse_demo.py](../../scripts/e2b_public_browse_demo.py)

| Where | What to check |
| --- | --- |
| [L31 `on_target`](../../scripts/e2b_public_browse_demo.py#L31) | `boston.gov` or a subdomain only; look-alikes rejected. |
| [L37 `grade`](../../scripts/e2b_public_browse_demo.py#L37) | Graded from the browser's record, not the model's claim. |
| `START_URL` comment | The start page was moved to `#External_links` because of Groq throttling. Is that a fair simplification? |

Tests: [test_public_browse_demo.py](../../packages/agent_runtime/tests/test_public_browse_demo.py).

## 6. Documents (all three)

- [decision 0004](../decisions/0004-public-web-mode.md): public-web design and consequences.
- [decision 0003](../decisions/0003-week1-outcome.md): Week 1 outcome (W1-4 deferred).
- [week1-traces.md](../week1-traces.md): three annotated runs.
- [e2b-preflight.md](../e2b-preflight.md): W1-F10 results, narrowing, and the public-mode section at the end.
- [README.md](../../README.md): dashboard versus CLI split, script table.
- Status, plan, and three handoffs in `docs/handoffs/2026-11-16-claude-*`.

## Decisions waiting for you

1. Allow fonts (and images?) in the filter so public pages are readable.
2. W1-4's second model candidate.
3. Commit plan: one new branch with three commits (W1-F10, W1-F13, W1X-F02)?
