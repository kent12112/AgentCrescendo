# Direction: skip E2B and focus agents on finding useful jobs

Date: November 17, 2026.
Status: user-directed departure from the E2B product path; the worker design and
implementation sequence below are proposals for discussion. No application change
is implemented by this note. Supersedes E2B as the core product requirement in
decisions 0001/0012/0014; preserves their code and historical evidence.

## Evidence and objective

The user considers E2B's complexity poor ROI and wants multi-agent work that speeds
up job finding. The last fictional live draft spent 40.870 seconds preparing the
desktop and 14.862 seconds typing, within a 91.365-second flow. Its model was fake;
do not interpret that fixture as a model-latency benchmark.

`job_sources.fetch_boards` already uses bounded parallel HTTP requests (8 by default,
maximum 16). Daily crawling writes to PostgreSQL; `job_search.current_index` caches
open postings and memoizes posting analysis. Current ranking uses title/skill scores
and explicit filters. We have not profiled the current cold/warm search paths in
this review. Adding agents cannot be assumed to make that deterministic search
faster. Target the user's time spent screening and researching useful matches.

## Proposed first slice

1. Decouple web generation from Writer. Restore direct model drafting, keep source
   preview/consent/review/approval and browser print/PDF. Replace the desktop area
   with real task progress, source evidence and completed results. Preserve existing
   saved letters/PDFs and historical desktop modules; no destructive schema cleanup.
2. Show a cached, deterministic shortlist immediately. Keep freshness, deduplication,
   explicit location/experience filters and source identities in ordinary code.
3. Run up to three job-analyst instances over a bounded top candidate set, initially
   10–20 postings. Each receives a redacted resume and posting, extracts explicit
   requirements, links fit claims to source excerpts, and distinguishes unsupported
   or unknown eligibility from confirmed requirements. No keyword-only rejection
   of transferable experience, and no guessed eligibility. Return completed cards
   progressively instead of waiting for the whole batch. These outputs assist user
   review; a model verdict is not proof of eligibility.
4. Research selected companies in parallel from public source tools, returning
   quotes/URLs and unresolved questions. Research workers do not need resume or
   identity. Reuse the existing letter generator after each selected job has its
   reviewed inputs. Independent companies/jobs can progress concurrently; within
   one job, writing depends on the evidence it uses.

Start with multiple instances of one job-analyst role, then add the distinct public
company-research role where it saves user effort. Query expansion/source discovery
is a later experiment if coverage remains poor; ATS fetching itself already runs
in parallel and does not require an LLM agent per source.

## Execution and boundaries

Use explicit dependencies and bounded tool-using workers. A coordinator written in
code owns scheduling, deduplication, budgets, retries, cancellation and persisted
status. Do not add an LLM manager that merely delegates fixed steps or a new agent
framework for this slice. The repository's intended durable execution owner remains
Temporal; this note does not authorize a competing durable workflow engine or
declare its integration complete.

Cache by the inputs that affect each result: posting content, redacted resume and
preferences, model/prompt version; company research also needs freshness/source
identity. Bound aggregate provider concurrency and rate limits across workers.
Do not multiply a per-worker budget into an unbounded run budget. Persist successes
independently so one failed company does not discard the shortlist.

Public research tools must enforce destination/redirect restrictions and bounded
responses on the host. Existing sandbox firewall evidence does not establish the
safety of new host HTTP fetches. Keep credentials outside agent context, treat pages
as untrusted data, and preserve consent for external model inputs. No application
submission or external messaging is part of the proposal.

## Evaluation before expansion

Compare current ranking, serial job analysis and bounded parallel analysis on the
same fixed postings and resume/preferences. Record cold/warm latency separately:
time to the first useful matches and complete shortlist, user-kept matches in the
top ten, source-supported explanations, missed hard constraints/unknowns, total
requests/tokens/cost, and retry/failure behavior. Measure model-only latency and
end-to-end latency separately. More workers may increase rate limiting and cost;
there is no speedup claim until measured.

Acceptance for the first implementation: search and drafting work without an E2B
key or desktop package; existing artifacts remain accessible; independent analyses
run concurrently within a shared cap; completed cards appear progressively; duplicate
starts, one-worker failure, cancellation and reload preserve correct saved results.
