# Handoff: LETTER-FIT company-specific cover letters

- Date/time and timezone: November 18, 2026, America/New_York.
- Author/session: Codex primary; no delegation.
- Intended recipient: user / next reviewer; review requested, not assigned.
- Base commit: `d9813ed`. No commits or pushes; earlier uncommitted work preserved.
- Changed paths: `services/api/crescendo_api/letters.py`,
  `services/api/tests/test_letter_provider.py`, `services/api/tests/test_letters_api.py`,
  `apps/web/features/jobs/letters-api.ts`, `letter-workspace.tsx`,
  `scripts/smoke_job_search.py`, README, plan, decisions 0011/0016, status, this handoff.
- State: implementation complete, ready for user evaluation. Ownership released.
  User's local API/frontend remain running; isolated smoke/build processes stopped.

## Goal and resulting behavior

User reported simplistic letters and requested stronger connections between company
product/culture and resume experience. The prompt now asks for a central argument
based on one or two concrete shared problems, decisions or working practices, with
a specific opening and a grounded proposed contribution. Past projects must stay
in their original setting; product use, motives and culture must not be invented.

The old prompt required candidate/company claims in separate sentences. Added
`supporting_quotes` to sentence records so natural connections can cite both sides.
Each quote is checked and displayed, with explicit argument/paraphrase review flags.
Existing primary fields remain; older responses and saved checks are supported.
Strict provider schema requires all properties even when host fields have defaults.
Candidate number checks also run when resume evidence is an additional citation.

Company-context guidance asks for product/users, a concrete working practice, and
the candidate's connection. Sources remain consented snapshot data; automatic
company research is not implemented. No migration, model/budget change, saved-letter
rewrite or consent changes. See [decision 0016](../decisions/0016-company-specific-letters.md).

## Verification

- `.venv/bin/python -m pytest -q`: **944 passed, 4 skipped**, existing
  Starlette/httpx deprecation warning. Focused final letter/Writer suite: **51 passed**.
  Added cases cover both primary-source orders, invented metrics, missing additional
  quotes, user-note attribution, weak citation recovery, adapter/schema boundary,
  and save/reload/approval retaining additional evidence.
- `npm run typecheck` in `apps/web`: passed.
- `npm run build` in a temporary source copy with the installed dependencies:
  passed. Source copied with `.next`, `.env*`, `node_modules`, and incremental cache
  excluded; dependencies symlinked. Local development server was left running.
  Build log: `.demo-artifacts/letter-fit-eval/build.log` (ignored).
- `.venv/bin/python scripts/smoke_job_search.py`: passed, real browser and isolated
  frontend/API/SQLite, fake model/desktop. Includes displaying both resume and posting
  quotes with the connection review flag, followed by existing consent, controlled
  failure/retry, review/edit/approval, export, reload, mobile and request-guard checks.
  Inspected `.demo-artifacts/job-search-smoke/connected-evidence.png`.
- `git diff --check`: passed.

## Fictional live experiment and observed failures

Eight bounded Groq requests total; no user resume, saved letter or E2B desktop used.
Fictional RelayField repair scheduling plus a volunteer dispatch project with offline
queues, assignment conflict handling, user interviews and written decisions. Exact
inputs, prompts, outputs, metrics and runnable local script under ignored
`.demo-artifacts/letter-fit-eval/`. `run.py` compares prompts using the same current
schema; `--after-only` tests the current prompt. This isolates prompt effects rather
than reproducing the historical adapter. The fixture was reused during prompt tuning;
it is not a held-out evaluation or evidence of general persuasive quality.

- Initial revised response failed host structure validation; its raw response was
  not captured, so the precise cause is unknown. A diagnostic request was rejected
  by the provider; a later diagnostic response was valid. Initial failure metadata
  remains in `initial-after.json` / `initial-metrics.json`.
- Hardened weak additional citations: empty/short quotes are review flags rather
  than fatal validation, consistent with primary quotes. This is tested but is not
  claimed as the proven cause of the initial failure.
- Intermediate prose blurred candidate volunteer work with company technician work.
  Tightened the prompt to keep past work in its actual setting and make transfer
  explicit. Samples can still make questionable inferences; review remains required.
- Final default fixture: **112 words**, **1.93 s**, **5 matched quotes**, **2 sentences
  with both candidate/company sources**. The baseline comparison: **156 words**,
  **1.94 s**, **6 citations, 1 unmatched quote**, **0 dual-source sentences**.
  Word counts include host greeting/signature. Neither request obeyed the suggested
  length; no minimum word-count padding was added. These are individual samples.
- Medium reasoning / 6,144-token experiment: **168 words**, **7.65 s**, all 9 quotes
  matched, but no clear prose improvement; not adopted. Production remains low
  reasoning / 3,072 tokens with no SDK retries. Experiment files retained as
  `medium-reasoning-after.*`; production-config sample is `after.*`.
- Actual token usage/cost not measured. Quote matches do not verify complete factual
  support, culture fit or the proposed contribution. Subjective quality still needs
  user evaluation on real consented inputs and a broader fixed set.

## Next action and limits

Refresh the local app, select jobs, and prepare a **new** letter session. Add concrete
product details and working-practice excerpts in Company context, review the redacted
snapshot, then draft. Completed old letters are reused unchanged and cannot demonstrate
the new prompt. Automatic research and the E2B decoupling proposal remain open.
