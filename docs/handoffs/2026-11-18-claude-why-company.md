# Handoff: WHY-COMPANY researched "Why [company]?" answers

- Date/time and timezone: November 18, 2026, America/New_York.
- Author / session: Claude (VS Code session); no agents launched.
- Intended recipient: user (reviewer); Codex for the shared-file notes below. Review requested, not an assignment.
- Base commit: `d9813ed`. Uncommitted; earlier uncommitted work by others preserved.
- Change paths: `services/api/crescendo_api/{company_research.py (new), letters.py, config.py, models.py}`,
  `routes/letters.py`, `migrations/versions/0010_answer_turns.py` (new),
  `services/api/tests/{test_company_research.py (new), test_letter_provider.py, test_letters_api.py}`,
  `apps/web/features/jobs/{letter-workspace.tsx, letters-api.ts}`,
  `apps/web/app/api/jobs/{letters,letter-sessions}/[...segments]/route.ts`,
  `scripts/smoke_why_company.py` (new), `.env.example`, decision 0017, learning 18, status, this handoff.
- State: implemented; ready for user review. No live Groq run yet.
- Ownership: released.

## Goal and acceptance criteria

User: answer Ashby-style "Why [company]?" questions instead of cover letters; no PDF;
easy copy; a company-specific researcher agent; use arXiv 2512.04695 for the writer.
User confirmed (question in session) that 2512.04695 is TRINITY and to adapt its
Thinker/Worker/Verifier roles, and chose a dedicated researcher agent over pasted URLs.

## Changes and decisions

See [decision 0017](../decisions/0017-why-company-answers.md) and
[learning 18](../learning/18-why-company-agents.md). In short:

- `company_research.py`: Groq `browser_search` on public posting facts. Its answer is
  untrusted. The host fetches each cited URL (public https only; redirects rechecked;
  size/time bounds) and keeps facts whose quote is on the page.
- `POST /jobs/letter-sessions/{id}/research`: only before consent; up to 3 companies
  in parallel; failures are recorded per company; rewrites inputs, letter posting
  snapshots and the digest.
- `letters.generate_draft`: T → W → V → W → V, accept = Verifier ∧ host checks. Each
  turn is persisted via `on_turn` into `cover_letters.turns`. Returns `(text, checks)`
  as before, so the Writer service still works. A provider failure on the Thinker
  stops the run (`ProviderDown`); on a later turn, the last checked draft is kept.
- Output has no greeting or signature. The page has Copy (Clipboard API, falling back
  to select-and-copy), a live turn trace, research facts with links and exclusions,
  and "Mark ready". Live Writer, PDF, print and .txt links are removed from the page.
  Backend routes and components remain.
- Proxy timeouts: generate 300 s (was 90 s), research 180 s.

## Evidence (all local, fake providers)

- `.venv/bin/python -m pytest -q`: **965 passed, 4 skipped** (baseline focused
  letter/Writer/migration suite was 52 passed before changes).
  New: 16 researcher tests (URL/IP guard, redirect to private host never requested,
  size/type/status bounds, quote verification incl. typographic dashes, researcher
  never sees resume/notes, safe 429). 25 provider tests (3-turn accept, 5-turn revise
  with feedback, host veto over Verifier, bad plan skipped, failed revision keeps
  draft, time budget, safe provider categories with exactly one call).
  2 API tests (research before consent, digest/consent invalidation, failure recorded).
- `npm run typecheck` (apps/web): passed. Production build not run this session.
- `.venv/bin/python scripts/smoke_why_company.py`: passed. Real Next/FastAPI/SQLite,
  Edge, fake researcher/generator. It checks research display and consent reset, live
  turn trace, no greeting/PDF/desktop, clipboard equal to the answer, and Mark ready
  surviving reload. Screenshots inspected: `.demo-artifacts/why-company-smoke/{research,turns-live,answer}.png` (ignored).
- Not proven: real `browser_search` quality, quote-match rate on real pages, latency,
  Groq rate-limit behavior across five turns, or answer quality.

## Open issues and next action

1. **Live evaluation** (needs the user's go-ahead; it spends Groq quota): one fictional
   or consented posting, run research and drafting, and record facts kept/excluded,
   turns, seconds, and the answer.
2. **Codex / shared files**: `ProcessSteps` labels in `job-shell.tsx` still say
   "Draft letters" / "Review & approve"; the sidebar looked unstyled in the smoke run
   during SEARCH-TRACKER's in-progress edits. I did not edit `job-shell.tsx`, `types.ts`
   or CSS. `scripts/smoke_job_search.py` still drives the removed live-Writer UI and will
   fail at the letters step; I left it for whoever owns the search smoke now.
3. Review questions: is 100–200 words right for your forms? Should Thinker/Verifier
   use a different model than the Worker (closer to the paper's model pool)? Should the
   unused Writer/PDF backend be removed?
