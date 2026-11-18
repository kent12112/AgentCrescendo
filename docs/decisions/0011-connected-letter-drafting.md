# Decision: deliver the first connected letter flow from stored sources

Date: November 17, 2026. User requested completion of the frontend, then clarified
that the letter pipeline did not exist and asked to build it from job description,
company, and resume. This is an incremental slice of JOB-F05/F08, not completion of
the live researcher/Writer-desktop design in decisions 0009/0010.

Update November 17: the approved-letter Writer desktop and verified PDF storage
are now connected under [decision 0012](0012-live-writer-exports.md). The description
below records the earlier drafting slice; independent company research remains open.
The current web drafting path opens the real desktop before the model request and
types the unapproved draft before review: [decision 0014](0014-draft-before-approval.md).

Update November 18: [decision 0016](0016-company-specific-letters.md) replaces the
single-source-per-sentence instruction with primary and additional source quotes.
The writer now develops a company-specific fit argument from the same consented
inputs. Independent company research remains open; quote matches remain review aids.

## Implemented boundary

- Sources: stored posting description and company name, the uploaded resume, and
  optional company notes entered by the user. No independent company web research.
- Prepare locally, remove known name spellings and contact patterns, re-scan, and
  display the exact source snapshot for explicit consent. First resume line is
  treated as a name line. Pattern removal is conservative and imperfect; the
  preview remains a required human check. Identity stays outside model inputs.
- Snapshot inputs and selected postings before consent, with a SHA-256 digest.
  Later resume/posting changes cannot silently change an approved request. At
  most three jobs in a session, enforced by the API. No daily/session-count limit.
- Use one bounded Groq request per job, from the host. The default GPT-OSS model
  uses strict JSON Schema, low reasoning effort, and a 3,072-token completion cap;
  other configured models retain JSON mode unless explicitly supported. Host
  validation enforces content bounds in every case. See
  [Groq's structured output contract](https://console.groq.com/docs/structured-outputs).
  No model tools, sandbox access, or automatic SDK retries.
- After a user-reported Notion drafting failure, a fictional-resume reproduction
  returned `finish_reason=length` with a complete, schema-valid JSON draft. Validate
  such a response instead of discarding it solely for its finish reason, and attach
  a required-review warning about completeness. Truncated JSON remains a failure.
  Rate limits, timeouts, request rejection, and invalid structure have separate safe
  messages; provider exception bodies are never relayed or logged by this adapter.
- Construct letter text only from returned sentence records. Match each source
  quote against the snapshot, check candidate numbers verbatim, and flag missing
  quotes, paraphrases, unsourced wording, and attribution problems. Quote existence
  is not semantic entailment. A real fictional-input run embellished achievements;
  this motivated mandatory review flags for non-exact paraphrases and a stricter
  prompt. We do not claim automatic factual verification.
- Persist partial results. A conditional database update prevents concurrent
  active requests from duplicating generation; completed requests return the saved
  draft. Stale generating rows can be retried after 120 seconds. A crash after the
  provider response but before persistence can still incur a repeat paid request.
- Explicit approval and review acknowledgment restore the supplied name locally.
  Edits require the expected version, invalidate approval, and preserve a warning
  that source checks refer to the generated wording. Download only approved text.
- Print-ready approved letters support browser Save as PDF. This is not the
  offline Writer desktop export, and PDFs are not stored by the server.

## Execution tradeoff and deferred work

Each HTTP request drafts one letter; the browser sequences up to three and polls
persisted state. It is not a second workflow engine and is not durable scheduling:
closing the tab stops starting later jobs. Reopen the session and continue.
Temporal remains the intended runtime for live desktop orchestration. JOB-F04,
offline Writer PDF storage/live viewing, application tracking, semantic claim
verification, and retention/deletion of session snapshots remain open.

The local API/proxy token and same-origin write boundary are preserved. This
remains a single-user loopback application with personal data in local Postgres;
the user uploads their resume and explicitly authorizes each model-input snapshot.
