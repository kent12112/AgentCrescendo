# 18. "Why [company]?" — a researcher and a three-role writer

Written November 18, 2026 with [decision 0017](../decisions/0017-why-company-answers.md).

## The locked room, again

Earlier the locked room held one worker (the model) behind a guard. This feature
adds two more rooms and a fixed meeting order:

- **Researcher room** (`company_research.py`). The researcher can look outside
  through Groq's `browser_search`, but is only handed the public job card:
  company, title, posting link and excerpt. It never sees the resume.
  It slides back notes saying "fact, exact quote, page URL".
- **The guard checks the notes** (`verify_facts`). The guard does not trust the
  researcher's quotes. It walks to each page itself (public https only, and checks again
  after every redirect) and keeps a note only if the quote is really on that page.
- **Writing room** (`letters.generate_draft`). Three people take turns at one table,
  reading the same transcript:
  1. **Thinker** picks the argument: one or two company hooks, one or two resume
     facts, and the reasoning that links them.
  2. **Worker** writes the answer, citing a source quote for every sentence.
  3. **Verifier** says "ship it" or lists numbered problems with fixes.
  If rejected, the Worker revises once more and the Verifier checks again. That is
  five turns at most.
- **The guard has a veto here too** (`host_problems`). Even if the Verifier says
  "ship it", a quote that is not in its source or a number that is not in the resume
  blocks acceptance.

## Mapping to the paper (TRINITY, arXiv 2512.04695)

| Paper | Here |
| --- | --- |
| Coordinator (0.6B model + head, trained with sep-CMA-ES) chooses model and role each turn | Fixed order in code: `SCHEDULE = (thinker, worker, verifier, worker, verifier)` |
| Thinker / Worker / Verifier role contracts | `THINKER`, `WORKER`, `VERIFIER` prompts in `letters.py` |
| Each turn sees the query plus the full transcript | Each turn gets all sources, plus the plan and the previous draft and feedback |
| Stop when the Verifier accepts, or after a turn budget (5) | Same, plus host checks and a 200 s time budget |
| Pool of different LLMs | One model (`LETTER_MODEL`) for every role, for now |

The learned part of the paper (which model, which role, when) is the part we did not
build. Treat this as "the paper's protocol", not "the paper's results".

## Where to read the code

1. [company_research.py](../../services/api/crescendo_api/company_research.py):
   `public_request` (what leaves), `parse_findings` (untrusted JSON),
   `check_public_url` and `fetch_page_text` (the guard's walk), `verify_facts`.
2. [routes/letters.py](../../services/api/crescendo_api/routes/letters.py) `research`:
   runs up to three companies at once, then rewrites the preview and its digest.
3. [letters.py](../../services/api/crescendo_api/letters.py) `generate_draft`:
   the turn loop. `_ask` is one role request; `check_draft` and `host_problems` are
   the guard's checks; `on_turn` saves each turn so the page can show progress.
4. [letter-workspace.tsx](../../apps/web/features/jobs/letter-workspace.tsx):
   `ResearchSummary`, `TurnTrace`, and `copyText` (Clipboard API with a select-and-copy fallback).

## Failures observed while building

- Groq Compound, the first research choice, was decommissioned September 21, 2026.
  Checking the provider docs before coding avoided building on a dead model ID.
- `browser_search` cannot be combined with structured outputs, so the researcher's
  JSON is parsed leniently (last object with a `facts` list). Bad facts are dropped
  one by one, not the whole answer.
