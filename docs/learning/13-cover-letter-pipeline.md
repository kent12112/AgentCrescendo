# From a search result to a reviewed letter

The interesting boundary is the input snapshot: the thing the user approves must
be the thing the model receives. Previewing a mutable resume and fetching it again
at generation could send something different. `LetterSession.inputs` freezes the
redacted resume, posting, company notes, and model; consent checks its digest.

One selected job becomes one `CoverLetter`, independent of the live posting. The
daily crawl can delete its posting without deleting the draft or source evidence.
The database claims generation atomically and exposes real state to browser polls.
That is concurrency control, not exactly-once delivery or durable orchestration.

Observed failures and lessons from November 17:

- SQLite returns naive timestamps. SQLAlchemy's in-memory bulk-update evaluator
  compared them with an aware UTC deadline and crashed on the duplicate-generation
  path. Run that condition in SQL (`synchronize_session=False`), then reload.
- Pagination originally used editable form values rather than the submitted query.
  Keep a search snapshot and generation counter; ignore responses after a newer
  search or resume mutation. The browser smoke edits the form before paginating
  and deliberately delivers an old response after resume removal.
- Server-only selection updates made controlled checkboxes briefly revert. Update
  the selection immediately, then reconcile to the server, including after errors.
- An implicit label enclosing a controlled textarea made exact label lookup
  unreliable once a draft existed. Use explicit `htmlFor`/`id` association.
- A real Groq run with fictional inputs added unsupported adjectives/outcomes
  alongside genuine quotes. Quote containment cannot prove a sentence is true.
  Strengthen the prompt and flag paraphrases for human review instead of labeling
  them verified. The signature is filled only after the user approves the text.
- The restricted execution sandbox blocks loopback binds/connections. Browser and
  socket tests need that environment permission; failures at `bind` do not establish
  an application bug. The isolated smoke uses a temporary database and fake provider.
- A reported Notion failure exposed another boundary: a provider finish reason is
  metadata, not a structural validator. With a fictional resume of similar length
  and the public posting, the old 6,000-token request took 14.2 seconds and returned
  `length` despite valid JSON with three paragraphs. The adapter rejected it before
  parsing. The revised request uses strict schema/low reasoning and a 3,072-token
  cap; the same reproduction passed in 2.2 seconds without a length-limit warning.
  A complete JSON response at the limit is now reviewable with a completeness flag;
  truncated or invalid structures still fail. Safe, separate provider messages make
  future rate-limit/auth/timeout failures diagnosable without exposing the prompt.

Useful reading order: `routes/letters.py` (HTTP and persistence), `letters.py`
(redaction/model/source boundary), `letter-workspace.tsx` (consent/review), and
`test_letters_api.py` / `scripts/smoke_job_search.py` (failure evidence).
