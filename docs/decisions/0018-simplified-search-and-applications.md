# Decision: focused Ashby search and a manual application tracker

Date: November 18, 2026. User requested simplifying the webpage around faster
Ashby job search and researched “Why [company]?” answers, and tracking applications.
The user explicitly kept Claude's WHY-COMPANY implementation with that session;
Codex handles search and tracking. Amends decision 0010's tracker entry point.

## Resulting behavior

- Shared job navigation contains Find jobs, Why company?, and Applications. The
  old task dashboard remains accessible at `/drafts`. Search removes its process
  checklist, collapses advanced filters, and displays the shortlist only after
  selection. Resume scoring and the cached deterministic index remain local.
- The web search explicitly accepts Ashby as its source, matching the actual
  `open_postings` cache. It does not pretend that other ATS sources are loaded.
  Crawl freshness, highlighted descriptions, filter counts, and saved picks remain.
- After submitting a job application themselves, users click **Mark applied**.
  This stores an independent posting snapshot in `job_applications` (migration
  `0011`, following Claude's `0010`). No posting foreign key or cascade: crawl
  closure/deletion must not delete application history. A tracker needs no resume,
  generated answer, E2B key, or model call.
- `/jobs/applications` supports ready, applied, interviewing, offer, rejected, and
  withdrawn; editable applied/follow-up calendar dates and notes; company/role/notes
  search; status filtering; due follow-up counts; and explicit removal. Tracking
  starts with the manual action; answer approval does not automatically create it.
  Dates come from the user's browser calendar. Follow-ups are displayed locally.
- Search badges read current tracker state on every request. Hide-applied filtering
  happens before ranking/pagination, so totals and subsequent pages agree. Ready
  entries without an applied date stay visible; previously applied entries remain
  hidden even if their status is later changed to ready.
- Repeating a create request returns the existing record without resetting it.
  Edits/removal require the latest version; stale tabs receive a conflict instead
  of silently overwriting notes. Posting availability is read separately from the
  immutable saved description. Text is rendered as text, never HTML.

## Learning and limits

The key persistence concept is separating records with different lifetimes: crawled
postings expire, while user-maintained application history must persist. The key
concurrency concept is optimistic locking: a version check protects edits without
holding a database transaction open while a person fills a form.

This change simplifies the user's workflow; no new search-latency benchmark or
agent speedup is claimed. It preserves the single-user local authentication and
same-origin mutation checks. Research/writer quality and provider behavior belong
to Claude's separate decision 0017. No subagents, commits, pushes, or deployments
were initiated by Codex for this task.

See the [handoff](../handoffs/2026-11-18-codex-search-tracker.md) for verification,
observed failures, shared-checkout changes, and operational state.
