# Decision: cover letters are drafted by Groq from a resume with identity removed

Date: November 17, 2026. Decided by the user. Affects JOB-F03 to JOB-F05.
Amends [decision 0007](0007-job-search-scenario.md) point 5: there is no separate
reviewed profile; the resume text is the source of facts.

## Context

The end-to-end flow is: find and rank jobs → the user picks a few → research each
company on a desktop → draft a letter → the user approves → an offline desktop types
it and exports a PDF (proven by [JOB-P01](../handoffs/2026-11-17-claude-job-p01-writer-probe.md)).
The user does not apply automatically (0007 point 2).

Drafting a good letter needs a language model to read the resume. Until now the
resume never left the machine (JOB-F02 ranks locally). The user considered three
options: send the full resume to Groq; send it with identity removed; or use a local
model. The user chose the second.

## Decision

1. **No profile step.** The resume text is the fact source. Search filters (location,
   seniority, remote) stay as `find_jobs.py` options.
2. **Up to 3 letters per session**, one per job the user picks from the ranked list.
   Never one letter per ranked job.
3. **Identity is removed on the host before anything is sent to Groq**:
   - Removed and replaced by placeholders: the name (from a user-supplied `--name`,
     plus the resume's first line), email addresses, phone numbers, street
     addresses, and personal links (LinkedIn, GitHub, personal sites). Placeholders
     are `[NAME]`, `[EMAIL]`, `[PHONE]`, `[ADDRESS]`, `[LINK]`.
   - After redaction the host scans again for anything that still looks like an
     email, phone number, link, or the given name. If it finds one, nothing is sent.
   - Before the first send in a session, the user sees exactly what will be sent and
     confirms.
   - Sent: work history, employers, schools, dates, skills, achievements, plus the
     posting text and the checked research facts.
4. **Placeholders are filled on the host** after the user approves the draft, then the
   finished letter is typed on the offline writer desktop (no reachable server; see
   JOB-P01). Only the host and that offline desktop ever hold the full letter.
5. **Claims are checked before the user sees the draft.** Every statement about the
   candidate must trace to the resume (numbers must appear in it verbatim). Every
   statement about the company must trace to a researcher quote the host verified
   on the page. Unsupported lines are flagged for the user, not silently kept.

## Alternatives considered

- **Full resume to Groq.** Simplest, and slightly better letters (the model knows the
  name). Rejected: identity is not needed to write the letter.
- **Local model.** Most private, but weaker letters and more setup. Kept as a later
  option if the redacted flow is not private enough.
- **Reviewed profile first.** Dropped by the user: the resume already holds the facts,
  and the claim check gives the same protection against invented experience.

## Consequences and residual risk

- Redaction is pattern-based and can miss things (a name written differently, a
  personal project domain). The re-scan and the preview are the safeguards; the user
  is the final check.
- Employers, schools, and dates together can still identify a person. That is
  accepted: they are what the letter is about.
- What Groq keeps and for how long is governed by Groq's terms and account settings;
  the user should check them. This project does not rely on deletion.
- The Groq API key stays on the host, never in a guest.
