# Handoff: letter generation failure recovery

- Date/time and timezone: November 17, 2026, America/New_York.
- Author/session: Codex, primary local session; no delegation.
- Intended recipient: user / next reviewer; review requested, not assigned.
- Base commit: `d9813ed`.
- Change commits: none; existing checkout changes preserved, all work uncommitted.
- Paths: `services/api/crescendo_api/letters.py`, new
  `services/api/tests/test_letter_provider.py`, decision 0011, learning note 13,
  status, and this handoff. No frontend or migration changes in this follow-up.
- State: fix implemented, tests passed, reported draft recovered.
- Ownership: released; no processes started or stopped in this follow-up.

## Goal and acceptance criteria

User reported the Notion frontend-intern letter in Needs retry with a generic error.
Reproduce a failure safely, improve response handling and diagnosability, and recover
the requested letter using its existing consented input snapshot.

## Findings and decisions

- Read only saved status/timing/input-size metadata during diagnosis. Two letters
  had failed almost immediately, while another in the session succeeded. Existing
  generic errors saved no finish reason/status, so the historical cause is unknown.
- Live reproduction used a fictional resume of similar size and the public posting,
  with no personal resume or private notes. Old request returned `length` after
  14.2 seconds, but its JSON was complete and passed the three-paragraph draft schema.
  The adapter rejected it solely because the finish reason was not `stop`.
- Supported models now use strict structural JSON Schema (all required fields,
  closed objects, constrained source values), low reasoning effort, and a 3,072-token
  completion cap. Other configured models retain JSON mode with no unsupported
  reasoning option. Host checks continue enforcing all string/array/content bounds.
- Complete schema-valid responses marked `length` become drafts with an explicit
  source-check warning to review completeness. This does not claim that a structurally
  valid response is semantically complete. Truncated JSON/invalid structure still fail.
- Preserve specific host validation messages. Separately classify quota/rate limit,
  auth/access, model/request rejection, provider outages, timeout, connection, invalid
  output, and missing SDK setup. Inspect only error type/status/numeric Retry-After;
  never relay/log provider bodies or prompts. No hidden SDK retries added.
- Once fictional-input verification passed, retry only the reported frontend-intern
  letter via the running authenticated API and its already-confirmed snapshot.
  Do not modify its inputs, approve the result, or retry other selected letters.

## Evidence

- `.venv/bin/python -m pytest services/api/tests/test_letter_provider.py services/api/tests/test_letters_api.py -q`:
  **28 passed**, existing Starlette/httpx deprecation warning.
- `.venv/bin/python -m pytest -q`, with loopback permission: **903 passed, 4 skipped**,
  same warning. Adapter tests cover actual SDK-call arguments, strict schema/fallback,
  complete and truncated length-limited responses, invalid structure, host bounds,
  safe failure categories, no prompt leakage, and one request per attempt.
- Old-request live reproduction: **14.2 seconds**, `finish_reason=length`, complete
  valid JSON, three paragraphs. Revised production adapter, same fictional resume and
  public posting: **2.2 seconds**, 142 words, seven checks, five quotes found, no
  length-limit warning. This is a reliability check, not a letter-quality benchmark.
- Recovery of the user's reported letter: authenticated `POST /jobs/letters/{id}/generate`
  against the existing loopback API, using the existing saved and consented inputs:
  HTTP **200**, status **draft**, error **null**, **2.9 seconds**, **225 words**, nine
  checks. Only safe metadata printed; no personal source/generated text or credentials
  logged. Other successful draft untouched. No approval or external application sent.
- `git diff --check`: passed. No frontend changes, so no new frontend build/browser
  run required; prior frontend evidence remains in the workspace handoff.

## Remaining limits and next action

Refresh the existing letter page to review the recovered draft. Original failed
attempts cannot be classified retrospectively because only the generic message was
stored; the reproduction demonstrates a real adapter bug, not proof that every
original failure had the same cause. Source evidence and paraphrase flags still
require human review. The separate iOS-intern letter was not retried in this follow-up.
