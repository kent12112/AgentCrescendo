# Current development status

Updated: November 16, 2026, by Codex.
Implementation baseline: `584e662`.
Current milestone: Week 1 — one useful, constrained desktop agent.

This is an evidence summary, not a declaration that Week 1 is complete.

## Implemented and observed

- Local Next.js/FastAPI/PostgreSQL task drafts, migrations, and draft deletion.
- Gateway authorization, task identities, destination restrictions, step/deadline
  checks, E2B cleanup paths, text research, page search, and vision/scroll loops.
- Authenticated loopback live-view proxy, tested with a simulated upstream.
- Live model-selected scroll (W1-F07): `qwen/qwen3.8-27b` chose `scroll(down, 5)`,
  then finished with the correct target code; saved model-input PNGs inspected. One run.
- Scroll now moves the real desktop pointer (E2B `move_mouse`) before the wheel;
  Playwright's `page.mouse` did not move it (live probe). F07 re-passed with the fix;
  see the [pointer handoff](handoffs/2026-11-13-claude-scroll-pointer.md).
- Live viewer (W1-F08): user saw the real E2B desktop in the local noVNC viewer and
  watched the model's scroll; the same run passed F07. One user-reported run.
- Visual research (W1-F09): Wikipedia Boston article, model-selected scrolling,
  cited answer verified visible on screen; user watched it live. Stylesheets from
  permitted hosts now load; screenshots downscaled to 768 px; one bounded retry on
  provider rate limits; model reasons recorded.
- A user-reported live text research run answered Boston and reported the same
  Wikipedia URL as its source and visited page. This is one run, not a benchmark.
- Link-following (W1X-F01): two complete live Boston → Massachusetts passes at
  768/1024 image widths. The model selects a visible link ID; the browser measures
  the point and the existing guarded real pointer clicks it. 23 live fixture
  checks passed; 334 Python tests passed. This is DOM-assisted selection, not
  screenshot-only pixel grounding. See [clicking](e2b-clicking.md) and the
  [aiming handoff](handoffs/2026-11-16-codex-link-grounding.md).
- Visible-link metadata now requires explicit `read_visible_links` permission
  rather than screenshot permission; click permission remains required. The demo
  grants it only in link mode. 402 local tests passed; no live rerun for this
  change. See [permission handoff](handoffs/2026-11-16-codex-visible-link-permission.md).
- Vision request recovery: one retry shared across timeouts, rate limits, and
  transient server errors; clean failure statuses and saved diagnostics. Click
  demo request timeout is configurable (45-second default, at most 60 seconds).
  362 Python tests passed. After one live Groq over-capacity response, a final
  Boston → Massachusetts run passed in 54.5 seconds. See
  [timeout handoff](handoffs/2026-11-16-codex-vision-timeout.md).
- Source startup recovery: click demo validates HTTP success plus article
  presence, retries temporary responses once, and saves startup failure evidence
  before any model calls. 379 local tests passed; a final live Boston →
  Massachusetts run passed in 24.3 seconds. The user's original Wikimedia error
  could not be reproduced or classified from its title alone. See
  [source startup handoff](handoffs/2026-11-16-codex-source-startup.md).
- Viewer asset recovery: session-scoped HTTP pool, one transport retry, optional
  icon failures no longer abort readiness, and saved click-demo viewer failure
  diagnostics. 393 Python tests and the local Edge smoke passed. A real
  Edge/E2B check rendered the desktop despite controlled essential/optional file
  failures; no model calls. See
  [viewer recovery handoff](handoffs/2026-11-16-codex-viewer-connection.md).
- Network boundary (W1-F10): two live preflight and two live browser-check runs
  passed. Allowed names are routed by name (guest's chosen IP ignored), private IPs
  blocked, shared-IP names and off-host redirects closed, page subrequests and meta
  refresh blocked by the filter. Exceptions: `8.8.8.8` open on all ports; domain
  fronting works for self-composed traffic. Narrowed: no model code execution, no
  guest secrets. See [preflight](e2b-preflight.md) and
  [handoff](handoffs/2026-11-16-claude-w1-f10-network-completion.md).
- Before baseline commit: 194 Python tests passed; web TypeScript checking and
  production build passed. These checks do not establish live E2B behavior.

Evidence and limitations: [browser integration](e2b-browser.md),
[network preflight](e2b-preflight.md),
[vision loop](learning/09-vision-action-loop.md), and
[live viewer diagnosis](learning/10-live-desktop-view.md).

## Remaining Week 1 work

All tasks below are unassigned. Claim only the task you are actually starting.

| ID | Task and acceptance evidence | Owner | State |
| --- | --- | --- | --- |
| W1-1 | Diagnose the real noVNC connection; visually confirm the remote page renders and model actions are visible | Unassigned | Done for the fixture (F08): user saw the real desktop and the live scroll; see [viewer handoff](handoffs/2026-11-13-claude-w1-1-live-viewer.md) |
| W1-2 | Inspect the screenshots delivered to the vision model and demonstrate correct observation, scrolling, and final answer | Unassigned | Fixture done (F07): one live pass with inspected PNGs, see [handoff](handoffs/2026-11-13-claude-w1-f07-model-scroll.md). Earlier wrong answer was `visual=51,174` (format check added); public-page case is W1-6 |
| W1-3 | Finish controlled live network checks for private/backend destinations, redirects/subrequests, IPv6, and DNS behavior; document provider exceptions and limits | Unassigned | Done November 16 (two live runs each): firewall routes allowed names by name, private IPs blocked, redirects/subrequests blocked. Exceptions `8.8.8.8` and domain fronting accepted with narrowing; see [preflight](e2b-preflight.md#completion-results-november-16-2026) |
| W1-4 | Compare two model candidates on the same fixed research task; record configuration, correctness/citation support, cost, and latency | Unassigned | Open; deferred by the user November 16. Groq lists one vision model (`qwen/qwen3.8-27b`); `gpt-oss-*` are text-only; only a Groq key is configured. Second candidate (text loop or another vision provider) is the user's decision |
| W1-5 | Record a cited research trace, provider termination evidence, and remaining limitations; reconcile README with implemented CLI demos and draft-only dashboard | Unassigned | Done November 16: [traces](week1-traces.md), [decision 0003](decisions/0003-week1-outcome.md), README updated; termination evidence from F11 |
| W1-6 | Connect permitted public-page research to screenshot observation and model-selected scrolling; produce a cited answer while the user watches the same desktop (plan W1-F09) | Unassigned | Done (F09): user watched a live Wikipedia pass with a cited, on-screen-verified answer; see [W1-6 handoff](handoffs/2026-11-13-claude-w1-6-visual-research.md) |

Suggested next task: decide W1-4's second model candidate (user), the last Week 1 gate. W1X-F02 needs a new
network design (public allowed, private denied) and its own rerun of the W1-F10 checks. Do not start Week 2 orchestration
on the assumption that Week 1's networking and live-view boundaries are resolved.

## Active ownership

W1-5 / W1-F13 completed and released by Claude on November 16, 2026. Added
[annotated traces](week1-traces.md) from three saved live runs (screenshots
checked), [decision 0003](decisions/0003-week1-outcome.md) on the Week 1 outcome, and a
README section listing the CLI scripts separately from the draft-only dashboard.
Docs only; no code or live runs. See
[handoff](handoffs/2026-11-16-claude-w1-f13-traces-readme.md). Uncommitted.

W1-3 / W1-F10 completed and released by Claude on November 16, 2026. Added DNS,
name-bound (rebinding), shared-IP, fronting, and redirect probes to the preflight;
new live browser subrequest check plus a local Edge version. 446 tests passed; two
live preflight and two live browser runs passed. Accepted exceptions: `8.8.8.8`
open on all ports, domain fronting; narrowed by having no code-execution tool. See
[handoff](handoffs/2026-11-16-claude-w1-f10-network-completion.md). Uncommitted.

READ-VISIBLE-LINKS completed and released by Codex on November 16, 2026. Replaced
the screenshot-permission check inside `visible_links()` with explicit
`read_visible_links` authorization. Updated policy, demo/check grants, tests, and
clicking/learning docs. 115 focused and 402 full local tests passed; one existing
Starlette/httpx deprecation warning. No live provider calls. Existing uncommitted
work preserved. See [handoff](handoffs/2026-11-16-codex-visible-link-permission.md).
Uncommitted.

VIEWER-CONNECTION completed and released by Codex on November 16, 2026 after a
user-reported `_CONNECTION_ERROR` at the viewer gate. Reproduced false fatal
readiness from an optional favicon failure; the exact original network failure
was not reproduced. Added pooled viewer asset requests, one transport retry,
essential-file-only gate errors, safe error categories, and click-demo saved
viewer failure results with zero model calls. 393 tests and the local browser
smoke passed. A real Edge/E2B probe rendered the fixture despite one controlled
essential JS failure and two optional icon failures; image inspected. Existing
uncommitted work preserved. See
[viewer recovery handoff](handoffs/2026-11-16-codex-viewer-connection.md). Uncommitted.

SOURCE-STARTUP completed and released by Codex on November 16, 2026 after a
user-reported Wikimedia error page. Added status/Retry-After metadata, a bounded
startup retry for temporary responses, HTTP-plus-article validation, and saved
startup screenshots/results with zero model calls on failure. 379 local tests
passed. A model-free E2B probe loaded Boston with HTTP 200; a final complete
click demo passed in 24.3 seconds. The reported original failure had no saved
startup screenshot/status, so its exact cause remains unknown. Existing changes
were preserved. See the
[source startup handoff](handoffs/2026-11-16-codex-source-startup.md). Uncommitted.

VISION-TIMEOUT completed and released by Codex on November 16, 2026 after the
user reported `groq.APITimeoutError`. Added bounded model-request retries and
sanitized `model_timeout`/`model_unavailable` results, configurable click-demo
request timeout, and SDK/loop/CLI failure-injection checks. 362 local tests
passed. One live request returned Groq 503 over capacity; a final run passed
Boston → Massachusetts with the normal click guards in 54.5 seconds. This
does not prove the cause of the user's earlier timeout. Existing uncommitted
work was preserved. See the
[timeout handoff](handoffs/2026-11-16-codex-vision-timeout.md). Uncommitted.

W1X-F01 aiming fix completed and released by Codex, November 16, 2026. The user
explicitly requested takeover of Claude's earlier in-progress task. Original
click/security work was preserved. Visible-link grounding fixes model-selected
link interaction; two complete live demos passed, along with 23 browser fixture
checks and 334 local Python tests. Raw pixel aiming and a normalized-coordinate
replay still miss, so no screenshot-only grounding claim is made. One earlier
grounded run opened the correct article but failed the demo due to final-answer
throttling; the click demo now allows one deadline-bounded wait up to 60 seconds.
See [aiming handoff](handoffs/2026-11-16-codex-link-grounding.md),
[decision](decisions/0002-visible-link-grounding.md), and the preserved
[original handoff](handoffs/2026-11-16-claude-w1x-f01-click.md). Uncommitted.

W1-F11 (provider termination) completed and released by Claude on November 16,
2026. The adapter now sets `on_timeout: kill` explicitly. A new live check confirms
destruction through E2B's API for normal exit, deliberate failure, and an abandoned
process (lifetime timer). Two passing live runs per scenario; 261 Python tests
passed. See [termination](e2b-termination.md) and the
[F11 handoff](handoffs/2026-11-16-claude-w1-f11-termination.md). Uncommitted.

W1-3 / W1-F10 IPv6 probe completed locally and released by Claude on November 16,
2026. Adds IPv6 probes and the unit-tested `evaluate_preflight()`; 252 Python tests
passed. One user-run live pass: every IPv6 probe `ENETUNREACH` (no guest IPv6
route; not a firewall rule). See the
[IPv6 handoff](handoffs/2026-11-16-claude-w1-f10-ipv6-probe.md).

COMMENT-CLARITY-ALL completed and released by Codex on November 15, 2026:
updated annotations across maintained source, tests, scripts, frontend, and supported
configuration; updated the reading guide. Code/configuration comparisons unchanged;
239 Python tests, frontend typecheck, and production build passed. See
[handoff](handoffs/2026-11-15-codex-all-comment-clarity.md).

COMMENT-CLARITY completed and released by Codex on November 15, 2026:
rewrote `scripts/e2b_visual_research_demo.py` comments as direct plain-English
translations without Learn labels. Python AST unchanged; 13 existing demo tests
passed. See [handoff](handoffs/2026-11-15-codex-comment-clarity.md).

Previous status: No active implementation claims. Codex completed and released ANNOTATE on
November 14, 2026: learning comments directly in source/tests/scripts and supported
configuration, plus a [reading guide](learning/12-commented-source.md) covering
strict JSON. Local checks: 239 Python tests, TypeScript/build, unchanged syntax
and configuration comparisons; see the
[annotation handoff](handoffs/2026-11-14-codex-source-comments.md). Changes remain
uncommitted. Week 1 live-provider gates are unchanged.

Previous claim: Codex completed and released REFACTOR on
November 14, 2026: API auth/routes, web draft feature, remote browser bootstrap,
and codebase guide. Local evidence: 239 Python tests, TypeScript, production build,
unchanged OpenAPI and remote program strings. Changes remain uncommitted; see the
[refactor handoff](handoffs/2026-11-14-codex-codebase-refactor.md) and
[codebase guide](codebase.md).

Claude released W1-6 / W1-F09 on November 13,
2026; see the [W1-6 handoff](handoffs/2026-11-13-claude-w1-6-visual-research.md).

Claude released W1-1 / W1-F08 and W1-2 / W1-F07
on November 13, 2026; see the
[viewer handoff](handoffs/2026-11-13-claude-w1-1-live-viewer.md) and the
[F07 handoff](handoffs/2026-11-13-claude-w1-f07-model-scroll.md).

Visual desktop plan and weekly checklist update complete; see the
[plan handoff](handoffs/2026-11-13-codex-visual-plan.md).

For a claim, record task ID, agent/session, intended files, and start date here.
Release it explicitly at handoff; do not infer release from elapsed time.
