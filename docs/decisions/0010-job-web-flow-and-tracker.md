# Decision: job search in the web app, live letter desktops, and an application tracker

Date: November 17, 2026. Decided by the user. Adds tasks JOB-F08 to JOB-F10. Builds on
[0008](0008-job-storage-daily-crawl.md) (postings in Postgres) and keeps every rule of
[0009](0009-cover-letter-redacted-resume.md) (identity removed before Groq, placeholders
filled on the host, claims checked, full letter typed only on the offline writer desktop).

## Decision

1. **Search in the web app** (JOB-F08).
   - The local Next.js app lists the ranked postings from Postgres. The filters (search
     words, country, cities, remote, early-career, max years) are pre-filled and
     editable before searching.
   - Each job card shows score (with its title/skill parts), title, company, location
     and country, workplace, pay, years asked, posting age, matched skills, gaps, and a
     link to the real posting. Details expand to the description with matched skills
     highlighted, all locations, and first-seen/closed history.
   - The page shows when the data was crawled and how many jobs each filter hid.
   - The user selects up to 3 jobs (0009 point 2). The server enforces the limit, not
     only the browser. No further session or daily limit (user: "don't worry about
     this").
2. **"Write cover letter" opens the desktops** (JOB-F08).
   - Clicking it starts the 0009 flow for the selected jobs and shows each job's E2B
     desktop live through the existing authenticated viewer (W1-F08), with a step
     indicator: research → draft → approve → typing → saved.
   - What is watched is real work: browsing during research, then typing the approved
     letter on the offline writer desktop. Drafting happens on the host (Groq).
3. **Letters are saved on the website** (JOB-F08). Final text, its claim checks and
   citations, and the PDF are stored in local Postgres and listed on a Letters page with
   view, download, and edit.
4. **Application tracker** (JOB-F09).
   - Statuses: ready (letter saved) → applied → interviewing → offer / rejected /
     withdrawn, plus a date, notes, and a follow-up date.
   - The user marks "applied" by hand; agents never submit (0007 point 2).
   - Each tracked application keeps its own copy of the posting, because the daily crawl
     deletes postings after 30 days.
   - Search results show an "Applied <date>" badge and can hide applied jobs. Whether
     the posting is still listed comes from `job_postings.closed_at`.
5. **Resume upload, stored locally** (JOB-F10). The user uploads the PDF once in the
   local app. Its extracted text, the fact source under 0009, is stored in local
   Postgres; the PDF file is not kept. Redaction (0009 point 3) still happens before
   any Groq request.

## Correction to JOB-F04

Postings in Postgres are Ashby-only (0008), and Ashby posting pages need JavaScript,
which desktops do not run (0005), so they render blank. The researcher therefore starts
at the company's own site, found from the posting or company name, not at the posting
page. The posting text comes from Postgres.

## Consequences

- Full letters with the user's identity exist only on the host and the offline writer
  desktop (0009 point 4). The user accepted that the E2B provider hosts that sandbox
  while it runs.
- The web app now holds personal data (resume text, letters, applications) in local
  Postgres. That is acceptable on a single-user machine; it needs access control before
  any shared deployment.
- JOB-F08 depends on run commands (W4-F02) and durable runs (Week 2) for the
  multi-desktop session. A first version can start one run per click with the existing
  run-start path (W2-F01).
