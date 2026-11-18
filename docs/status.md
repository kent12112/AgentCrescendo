# Current development status

Updated: November 18, 2026, by Codex.
Implementation baseline: `584e662`.
Current milestone: Week 1 — one useful, constrained desktop agent.

This is an evidence summary, not a declaration that Week 1 is complete.

Local startup November 18: Codex opened Docker Desktop, started the existing
PostgreSQL service, ran migrations, and launched the API/frontend at the user's
request. `/health` on port 8000 and `/jobs` on port 3000 returned HTTP 200.
Servers remain running; no application changes or provider calls. Startup
documentation ownership released. See [handoff](handoffs/2026-11-18-codex-local-startup.md).

## Current direction — November 17, 2026

User requested dropping E2B for this project because its complexity has low ROI,
and exploring multi-agent work to speed up job finding. The existing desktop code
and evidence below are preserved; the running app has **not yet been decoupled**
from E2B. Treat desktop milestone completion as historical evidence, not the next
product priority. Proposed next slice: cached shortlist → bounded parallel job-fit
analysts → progressive evidence-backed cards, followed by company research and
letters for selected jobs. Agent roles and budgets are proposals, not implemented
features. See [decision 0015](decisions/0015-tool-first-job-agents.md) and
[design handoff](handoffs/2026-11-17-codex-job-agent-pivot.md).

## Implemented and observed

- Company-specific letter writing (November 18, Codex): revised fit-argument
  prompt, primary plus additional sentence quotes, source-review display and more
  useful company-context guidance. **944 passed, 4 skipped**, TypeScript,
  isolated production build and fake-provider browser smoke passed. Fictional
  Groq samples demonstrated the evidence shape, with writing/validation limits;
  no broad quality claim or automatic company research. Existing drafts preserved.
  See [handoff](handoffs/2026-11-18-codex-company-fit-letters.md) and
  [decision 0016](decisions/0016-company-specific-letters.md).
- Live watching now starts with drafting (November 17, Codex): real Writer opens
  before the model request; Start drafting → generate redacted draft → visible
  typing → review/approval → optional final PDF. Migration `0009` separates draft
  previews from approved exports. Completed model text survives desktop failure or
  Stop; unchanged-preview retry reuses it. Preview PDFs are checked then discarded
  and cannot be downloaded. **937 passed, 4 skipped**, production build, mock browser
  flow, PostgreSQL schema check, and real E2B draft-first browser flow passed. The
  fictional 1,062-character draft typed in 14.862 s, exact ODT text; final approved
  1,094-character PDF also passed, both desktops cleaned up. Groq was fake in the
  real-desktop browser check. See [handoff](handoffs/2026-11-17-codex-live-drafting.md)
  and [decision 0014](decisions/0014-draft-before-approval.md).
- Writer typing reliability and workspace (November 17, Codex): reproduced the
  desktop's ASCII command locale rejecting Unicode punctuation; explicit UTF-8
  keyboard commands fix it. Full Unicode fictional browser pass: 1,094 characters
  typed in **15.334 s**, complete export **79.512 s**, one-page verified PDF, exact
  Writer document text, reload/review-pane recovery, cleanup confirmed. PDF check
  permits only the observed nonbreaking-hyphen layout representation, besides
  whitespace. Wide integrated desktop pane, fullscreen, serialized/backed-off
  polling, safe operation errors/timings, migration `0008`. **930 passed, 4 skipped**;
  production build, mock UI check, real E2B stress check, PostgreSQL schema check
  passed. Cold preparation remains about 38 s in this pass; this is one fixture,
  not a reliability benchmark. See [handoff](handoffs/2026-11-17-codex-writer-reliability-ux.md).
- Live approved-letter Writer connected (November 17, Codex): approve → open private
  offline E2B/LibreOffice desktop → watch in the page → explicitly start real typing
  → visible PDF export → word comparison → PDF saved in Postgres/downloadable after
  cleanup. Stop, page reconnect, expected-version/edit checks, duplicate prevention,
  and bounded abandoned leases included. PostgreSQL `0007`; schema check passed.
  **921 tests passed, 4 skipped**, production build and fake-provider browser check
  passed. A real E2B browser pass (fictional 152-character letter, fake Groq) showed
  typing, recovered the viewer after reload, produced a matching one-page PDF, and
  recorded cleanup. Screenshots inspected. API-process restart recovery remains
  lease-bounded rather than durable Temporal scheduling. See
  [handoff](handoffs/2026-11-17-codex-live-writer.md).
- Letter failure recovery (November 17, Codex): reproduced a valid JSON draft marked
  `finish_reason=length` being discarded by the old adapter. Strict schema/low reasoning
  and a 3,072-token completion cap now reduce saturation; complete drafts at the limit
  remain reviewable with a completeness flag, while truncated JSON fails. Safe messages
  distinguish provider failures. 903 tests passed (4 skipped). The reported Notion
  frontend-intern letter was retried through the running API using the existing
  consented snapshot and saved as a 225-word draft in 2.9 seconds. Historical cause of
  the original generic error cannot be proven from its saved metadata. See
  [handoff](handoffs/2026-11-17-codex-letter-failure-recovery.md).
- Local Next.js/FastAPI/PostgreSQL task drafts, migrations, and draft deletion.
- Connected local job-search/letter slice (November 17, Codex): Claude's resume,
  ranking, details, and saved picks UI/API preserved and finished. Home opens `/jobs`;
  `/drafts` retains the old dashboard. Selected jobs lead to immutable redacted-input
  preview/consent, Groq drafting from resume + posting/company + optional user notes,
  source evidence/review flags, editable saved drafts, approval, text download, and
  browser print-to-PDF. Local Postgres upgraded `0005 -> 0006`; schema check passed.
  884 tests passed (4 skipped), TypeScript/production build and isolated real
  frontend/API browser smoke passed. Two fictional-source live model successes;
  one intervening safe drafting failure was not classified. No user resume sent
  during that verification. Independent company research remains open; Writer is
  now connected as recorded above.
  See [handoff](handoffs/2026-11-17-codex-job-letter-workspace.md).
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
- Public-web mode (W1X-F02): with no host list, E2B's deny list of private ranges
  is enforced (denied public canary gave no TLS/DNS answer; twin answered), rebinding
  names resolving to `10.0.0.1`/`192.168.0.1` could not connect from the guest or
  from Chrome, and the model reached boston.gov from Wikipedia by `click_link` with
  no navigate tool. Two live runs each. Public pages render without fonts/images.
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

Suggested next task: decide W1-4's second model candidate (user), the last Week 1 gate.
Job track: [decision 0009](decisions/0009-cover-letter-redacted-resume.md) (November 17,
user) drops the profile step; Groq drafts letters from a resume with identity removed, up
to 3 per session. CLI picks and the first connected web drafting slice are implemented.
Next, unclaimed: independent company research (JOB-F04) and durable desktop
scheduling/recovery. The live offline Writer/PDF portion is connected. See
[decision 0011](decisions/0011-connected-letter-drafting.md) for the current scope.
Open public-web follow-up: whether to allow fonts (and images) so public pages are
readable ([decision 0004](decisions/0004-public-web-mode.md)). Networking and live-view
boundaries are measured for allowlist and public-web modes; rerun both checks after
E2B, Chrome, or SDK upgrades.

## Active ownership

SEARCH-TRACKER **claimed by Codex** primary session November 18, 2026. Simplify
Ashby search and add persistent manual application tracking. Expected edits:
job search/card/shell/side-panels/types/API/CSS, new applications page/proxies,
`routes/jobs.py`, `job_search.py`, new application model/migration/tests, docs.
Claude's WHY-COMPANY files remain reserved; coordination question pending with
the user. No agents spawned or Claude launched.

WHY-COMPANY **implemented and released by Claude** (VS Code session) November 18,
2026. "Why [company]?" answers with Copy (no PDF/Writer in the page), a company
researcher (Groq browser_search; public inputs only; host re-fetches each cited page
and keeps only quotes found there), and a TRINITY-style Thinker/Worker/Verifier loop
(max 5 turns, Verifier + host checks must accept). Migration `0010`, decision 0017.
**965 passed, 4 skipped**; typecheck; isolated browser smoke with fake providers.
No live Groq run yet. `smoke_job_search.py` still targets the removed Writer UI.
See [handoff](handoffs/2026-11-18-claude-why-company.md).

LETTER-FIT **implemented and released by Codex** primary session November 18,
2026. Prompt, multi-source sentence evidence, notes guidance, tests/browser smoke
and documentation complete; ready for user evaluation on a new draft. No active
ownership or delegation. **944 passed, 4 skipped**, TypeScript, isolated production
build, browser smoke and fictional Groq results in the
[handoff](handoffs/2026-11-18-codex-company-fit-letters.md). Existing drafts and
consented snapshots preserved; independent company research remains open.

LIVE-DRAFT **implemented and released by Codex** November 17, 2026. Real desktop
watching moved into letter drafting before review/approval; redacted sources and
final approval gates preserved. Writer lifecycle/model/routes, drafting UI/consent,
migration 0009, tests/smoke and docs complete. No active ownership or delegation;
existing uncommitted work preserved. **937 passed, 4 skipped**, build, mock and real
E2B browser flow passed; see [handoff](handoffs/2026-11-17-codex-live-drafting.md).

WRITER-RELIABILITY-UX **implemented and released by Codex** on November 17, 2026.
UTF-8 keyboard fix, bounded faster typing, narrow PDF hyphen comparison, safe
diagnostics/migration 0008, integrated wide live/review workspace, fullscreen, and
serialized/background polling complete. Existing work and approved snapshots
preserved; all live reproduction uses fictional data. No active ownership. Full
suite: 930 passed, 4 skipped; real Unicode E2B browser pass and remaining limits in
the [handoff](handoffs/2026-11-17-codex-writer-reliability-ux.md).

WRITER-LIVE **implemented and released by Codex** on November 17, 2026, at the user's
explicit request. Shared Writer adapter/helpers, private viewer cookie/reconnect
fixes, API export service/routes/model and migration 0007, frontend live controls,
and verified PDF persistence/download connected. Existing work preserved. Full
suite: 921 passed, 4 skipped; production build, fake-provider browser regression,
PostgreSQL schema check, and real E2B fictional-letter browser pass recorded in the
[handoff](handoffs/2026-11-17-codex-live-writer.md). No active ownership. No user
letter was sent to E2B during validation; actual exports require approval and an
explicit Open live Writer / Start typing action.

LETTER-FAILURE **implemented and released by Codex** on November 17, 2026. Changed
only the letter provider adapter, provider failure tests, and supporting docs. 903
tests passed (4 skipped). Fictional-source reproduction and revised live request
passed; after diagnosis, the reported frontend-intern draft was recovered through
the running API using its already-consented saved inputs. Successful other drafts
were left untouched; approval remains the user's action. See
[handoff](handoffs/2026-11-17-codex-letter-failure-recovery.md). No active ownership.

JOB-F08 frontend + JOB-F05 first connected letter slice **implemented and released by
Codex** on November 17, 2026, at the user's explicit request to take over the frontend
and build the missing letter generation. Ready for user/reviewer evaluation. Claude's
existing uncommitted work preserved. No active Codex ownership. 884 Python tests
passed (4 skipped), production build/typecheck, isolated browser smoke, PostgreSQL
migration/schema check, and fictional-source live model checks recorded in the
[handoff](handoffs/2026-11-17-codex-job-letter-workspace.md). Full JOB-F04/F05/F08
desktop acceptance remains open; do not infer live research or Writer work from this UI.

JOB-F03 (job picker) implemented and released by Claude on November 17, 2026; ready
for review. `scripts/pick_jobs.py` shows the newest ranked list and saves up to 3 picks
(checked board + posting ID) to `.demo-artifacts/jobs-picked-<id>.json`. 45 offline tests;
full suite 859 passed (4 skipped); 779 real ranked rows, 0 wrongly refused. See
[handoff](handoffs/2026-11-17-claude-job-f03-job-picker.md). Uncommitted.

JOB-P01 (writer desktop probe: no-internet E2B desktop types a fictional letter in
LibreOffice Writer, exports a PDF, host downloads it) written and released by Claude
on November 17, 2026. Runs 1–2 stopped at a flawed network check (now fixed:
server-proven answers only). Run 3: network blocked (all five proofs), LibreOffice
7.3 preinstalled, typed at 65 characters/s, GUI save and PDF download worked;
compare correctly failed because `xdotool type` newlines were ignored by Writer. Fixed by
pressing Return between lines. **Run 4 passed** all 8 steps (105 s; PDF inspected: one page,
layout intact, only AutoCorrect typography differs). Complete as a probe. Follow-up
(AutoCorrect off with an exact-match check, visible "Export Directly as PDF" click, 50 ms
typing) **passed live in run 5** (exact word match, visible export, 30 characters/s). 27 offline tests; full suite 813 passed (4 skipped). See
[handoff](handoffs/2026-11-17-claude-job-p01-writer-probe.md). Uncommitted.

JOB-F07 (daily Ashby crawl into Postgres, 30-day window, launchd schedule) implemented
and released by Claude on November 17, 2026; ready for review. Migration 0004 (job
companies, postings with first/last seen and closed dates, crawl runs; local database
migrated 0002 -> 0004). `scripts/crawl_jobs_daily.py` syncs ~3,100 Ashby boards (only
boards that answered close postings) and is run at 08:00 by a launchd agent
(`scripts/install_jobs_schedule.py`; installed). `find_jobs.py` reads Postgres (119 US
matches in 3 s). Live: run 1 inserted 19,643 postings; launchd run 2 exited 0 with +16
new, 19,638 updated, 5 closed. 814 tests passed (4 skipped). See
[decision 0008](decisions/0008-job-storage-daily-crawl.md) and
[handoff](handoffs/2026-11-17-claude-job-f07-daily-crawl.md). Uncommitted.

JOB-F06 (Ashby companies from Common Crawl, local caches, country filter) implemented
and released by Claude on November 17, 2026; ready for review. Company discovery reads
Common Crawl's public URL index (idea from whatrunsindia's open-source repo; own code,
their site not used, see [decision 0007](decisions/0007-job-search-scenario.md)) in a
background job, `scripts/refresh_job_companies.py`. `find_jobs.py` reads saved lists and
24 h board caches (`.cache/jobs/`, JSON, ignored) and adds `--country`; posting age
defaults to 30 days. Live: 3,137 Ashby companies from 2 crawls (4 crawls hit HTTP 504);
133 US AI-engineer matches for the user's resume in 16 s from cache, compared with 12
from HN alone. 52 offline tests; full suite 783 passed (4 skipped). Refresh script not run
live yet. See [handoff](handoffs/2026-11-17-claude-job-f06-common-crawl.md). Uncommitted.

JOB-F02 (find and rank jobs for a resume) implemented and released by Claude on
November 17, 2026; ready for review, not complete. `scripts/find_jobs.py --resume
<file> --search "applied ai engineer"`: HN "Who is hiring?" boards -> ATS postings ->
local keyword ranking with link, score, matched skills, gaps, years asked, location,
pay, age. The resume never leaves the machine. 37 offline tests; full suite 720
passed (4 skipped). Live with a fictional sample resume, then the user's resume (filters and vocabulary added; company coverage is the main limit). New dependency: `pypdf`
(`jobs` extra). See [handoff](handoffs/2026-11-17-claude-job-f02-find-jobs.md). Uncommitted.

JOB-F00 (ATS posting sources) completed and released by Claude on November 17, 2026;
ready for user review. Host-side fetch and normalization of Greenhouse, Lever, and Ashby
public job-board APIs (`crescendo_agent/job_sources.py`, `scripts/fetch_jobs.py`).
31 offline tests; full suite 683 passed (4 skipped). Live: 659 + 301 + 839 postings
from three real boards, a missing board reported as 404. Search engines were probed
and rejected (see the update in [decision 0007](decisions/0007-job-search-scenario.md)).
See [handoff](handoffs/2026-11-17-claude-job-f00-ats-sources.md). Uncommitted.

JOB-F01 (offer finder) implemented and released by Claude on November 17, 2026;
ready for review, not complete. Job search is now the primary scenario
([decision 0007](decisions/0007-job-search-scenario.md)). The model finishes with
link IDs only, and the host accepts an ID when the browser shows a posting link on the same
Greenhouse/Lever board (button labels like Lever's APPLY are refused). 49 offline
tests, full suite 652 passed (4 skipped), local Edge smoke on two real boards
passed. **No live run yet**: `scripts/e2b_offer_finder_demo.py` is the
acceptance check. See [handoff](handoffs/2026-11-17-claude-job-f01-offer-finder.md).
Uncommitted.

W2-F01 completed and released by Claude on November 17, 2026; user-reviewed
(Temporal Compose service deferred to W2-F02). `POST /runs/{id}/start` persists a start command (`draft -> starting`,
workflow ID `run-<run id>`), starts `RunWorkflow` with `USE_EXISTING` +
`REJECT_DUPLICATE`, then marks `started`. Real Temporal dev server: concurrent
and post-completion duplicates gave one execution; random-ID control gave two.
Live: 10 concurrent POSTs -> 1 execution; Temporal down -> 503 and retry onto the
same workflow. Migration 0003 checked on SQLite and PostgreSQL 17. 603 tests
passed (+9 opt-in Temporal). See [decision 0006](decisions/0006-stable-run-start.md)
and [handoff](handoffs/2026-11-17-claude-w2-f01-stable-start.md). Uncommitted.

W1X-F03 files.

W1X-F03 (open browsing) implemented and released by Claude on November 17, 2026;
ready for review, not complete. Public-web `navigate` now allowed to any public site;
new `type_text` into page text fields (checked field, real click, real keyboard-focus
check with Playwright focus emulation off, Ctrl+A/text/Enter only). Typed text leaves
only by GET form submission through the same destination check. 567 local tests and
a local Edge field check passed. **No live run yet**: `scripts/e2b_open_browse_demo.py`
is the acceptance check. See [decision 0005](decisions/0005-open-browsing.md) and
[handoff](handoffs/2026-11-17-claude-w1x-f03-open-browsing.md). Uncommitted.

W1X-F02 completed and released by Claude on November 16, 2026. Public-web grant
mode: E2B denies private ranges (deny list proven with a public canary), rebinding
names blocked live, filter allows public names only, model `navigate` refused,
host-only `open_start_page`. Two live passes each: public preflight, public browser
check, boston.gov click demo. 524 tests passed. See
[decision 0004](decisions/0004-public-web-mode.md) and
[handoff](handoffs/2026-11-16-claude-w1x-f02-public-web.md). Uncommitted.

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
