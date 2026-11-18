# Handoff: E2B exit direction and job-agent proposal

- Date: November 17, 2026, America/New_York.
- Author/session: Codex primary session; no delegation or provider calls.
- Recipient: user / next implementer; proposal for discussion, not an assignment.
- Base: `d9813ed`; documentation changes uncommitted; existing work preserved.
- Ownership: no active claim; review and documentation complete.

## User direction and work done

User wants to skip E2B because complexity has poor ROI and explore multi-agent
work to speed up job finding. Reviewed current status/design, live-drafting handoff,
crawler/search implementation and daily-crawl evidence. Recorded the direction and
a concrete proposed first slice in [decision 0015](../decisions/0015-tool-first-job-agents.md),
with pointers in status, architecture and plan.

The app is unchanged: its current web draft path still requires E2B. Decoupling it
is the first proposed implementation task. No desktop code, data, migrations or
saved artifacts were deleted, and no agent roles were implemented in this review.

## Findings and proposal

- Board fetching is already parallel: `fetch_boards`, default eight workers, cap16.
- Web search uses cached postings and memoized analysis with deterministic ranking.
  No search profile was collected here; avoid claims about the active bottleneck.
- Last live-draft fixture spent 40.870 seconds preparing Writer and 14.862 seconds
  typing; fake model, so this does not establish model latency or production ROI.
- Target screening time with up to three parallel instances of a job-fit analyst
  over a bounded shortlist. Emit evidence/unknowns progressively. Use public company
  research and the existing writer for selected jobs. Code owns orchestration and
  aggregate budgets; add roles only after comparison against a serial baseline.
- Preserve reviewed redacted inputs, source provenance, saved results and approvals.
  Host research fetches need their own destination enforcement; sandbox networking
  evidence does not transfer automatically. Temporal remains the intended durable
  runtime; no new framework/workflow engine selected by this proposal.

## Validation and next action

Read-only code review plus documentation; `git diff --check` passed. No tests run
because application code did not change. No live services or schedules changed.
Next implementation should make search/drafting usable without E2B, preserve saved
artifacts, then benchmark cached ranking vs serial/parallel job analysis using the
same input set and user usefulness judgments. Agent roles/worker counts are proposed,
not a claimed speedup or final approved implementation plan.
