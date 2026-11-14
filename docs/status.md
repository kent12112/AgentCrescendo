# Current development status

Updated: November 13, 2026, by Codex.
Implementation baseline: `584e662`.
Current milestone: Week 1 — one useful, constrained desktop agent.

This is an evidence summary, not a declaration that Week 1 is complete.

## Implemented and observed

- Local Next.js/FastAPI/PostgreSQL task drafts, migrations, and draft deletion.
- Gateway authorization, task identities, destination restrictions, step/deadline
  checks, E2B cleanup paths, text research, page search, and vision/scroll loops.
- Authenticated loopback live-view proxy, tested with a simulated upstream.
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
| W1-1 | Diagnose the real noVNC connection; visually confirm the remote page renders and model actions are visible | Unassigned | Open; live connection failure reported |
| W1-2 | Inspect the screenshots delivered to the vision model and demonstrate correct observation, scrolling, and final answer | Unassigned | Open; incorrect live answer reported |
| W1-3 | Finish controlled live network checks for private/backend destinations, redirects/subrequests, IPv6, and DNS behavior; document provider exceptions and limits | Unassigned | Open; preliminary live probes and local interception checks exist |
| W1-4 | Compare two model candidates on the same fixed research task; record configuration, correctness/citation support, cost, and latency | Unassigned | Open |
| W1-5 | Record a cited research trace, provider termination evidence, and remaining limitations; reconcile README with implemented CLI demos and draft-only dashboard | Unassigned | Open |
| W1-6 | Connect permitted public-page research to screenshot observation and model-selected scrolling; produce a cited answer while the user watches the same desktop (plan W1-F09) | Unassigned | Open; text research and visual fixture loops currently separate |

Suggested next task: W1-1, followed by W1-2. Do not start Week 2 orchestration
on the assumption that Week 1's networking and live-view boundaries are resolved.

## Active ownership

No active implementation claims. Visual desktop plan and weekly checklist update
complete; see the [plan handoff](handoffs/2026-11-13-codex-visual-plan.md).

For a claim, record task ID, agent/session, intended files, and start date here.
Release it explicitly at handoff; do not infer release from elapsed time.
