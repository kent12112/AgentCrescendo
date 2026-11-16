# Current development status

Updated: November 16, 2026, by Claude.
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
| W1-3 | Finish controlled live network checks for private/backend destinations, redirects/subrequests, IPv6, and DNS behavior; document provider exceptions and limits | Unassigned | Open; preliminary live probes and local interception checks exist. IPv6 checked November 16: one live run, no guest IPv6 route. Redirects, DNS rebinding, subrequests remain |
| W1-4 | Compare two model candidates on the same fixed research task; record configuration, correctness/citation support, cost, and latency | Unassigned | Open |
| W1-5 | Record a cited research trace, provider termination evidence, and remaining limitations; reconcile README with implemented CLI demos and draft-only dashboard | Unassigned | Open; termination evidence done (F11, [termination](e2b-termination.md)); trace and README remain |
| W1-6 | Connect permitted public-page research to screenshot observation and model-selected scrolling; produce a cited answer while the user watches the same desktop (plan W1-F09) | Unassigned | Done (F09): user watched a live Wikipedia pass with a cited, on-screen-verified answer; see [W1-6 handoff](handoffs/2026-11-13-claude-w1-6-visual-research.md) |

Suggested next task: W1-3 (network checks), the gate for broad public browsing (W1X-F02); then W1X-F01 clicking. Do not start Week 2 orchestration
on the assumption that Week 1's networking and live-view boundaries are resolved.

## Active ownership

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
