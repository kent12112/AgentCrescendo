# Decision: "Why [company]?" answers from researched, verified company facts

Date: November 18, 2026. User request: many Ashby applications ask "Why [company]?"
instead of wanting a cover letter, so drop PDF output, make the answer easy to copy,
add a company-research agent, and use arXiv 2512.04695 for the writer.
Amends decisions 0011/0014/0016 (drafting) and implements the company-research part
of 0015. No saved letter, PDF, or Writer table is deleted.

## What changed

- **Output.** One to two short paragraphs, 100–200 words, first person, no greeting
  or signature, with a Copy button. The page no longer offers the live Writer, PDF,
  print, or text download. Their backend routes and tables remain for old data
  and are no longer linked; removing them is a separate decision.
- **Company researcher.** Before consent, the user can run research. It sends only
  company name, role title, posting URL and the first 3,000 posting characters to
  `openai/gpt-oss-120b` with Groq's server-side `browser_search` tool (`RESEARCH_MODEL`).
  No resume, name or notes. The backend fetches every cited URL itself and keeps a
  fact only if its quote appears on the page. The fetch allows only public https on
  port 443 with each redirect hop rechecked, at most 3 redirects, 1.5 MB, 10 s.
  Research changes the preview digest, so earlier consent cannot be reused.
- **Writer: TRINITY-style roles.** Thinker plans (company hooks, resume evidence,
  connection, outline), Worker writes the cited answer, Verifier accepts or returns
  numbered issues. Fixed schedule T → W → V → W → V: at most five requests, stopping
  early on acceptance, and no new turn after 200 s. Acceptance requires the Verifier
  **and** host checks (quote found, numbers verbatim, no placeholders, 60–230 words).
  Each finished turn is saved to `cover_letters.turns` (migration `0010`) and shown live.

## Why this reading of the paper

arXiv 2512.04695 is "TRINITY: An Evolved LLM Coordinator", not a writing paper. A
~0.6B model plus a ~10K-parameter head, trained with sep-CMA-ES, picks a model and
one of three roles each turn. It stops when a Verifier accepts or after a turn budget
(five in the paper). The paper's prompts are not published. The user confirmed
adapting the roles. We kept the role contracts, the shared transcript, verifier-accept
termination and the five-turn budget. We did **not** reproduce the trained coordinator
or the multi-model pool. The paper's own ablation shows a prompted LLM coordinator does
worse than the trained one (64.14 vs 70.44), so a fixed schedule in code is the honest
substitute, consistent with 0015's "no LLM manager that merely delegates fixed steps".
Gains reported in the paper therefore do not transfer to this implementation by assumption.

## Alternatives considered

- Groq Compound (`groq/compound`) for research: decommissioned September 21, 2026.
- User-pasted URLs only: safer and simpler, but the user asked for a researcher agent.
- Trusting the researcher's quotes: rejected. Browser-search answers cannot use
  structured outputs and pages are untrusted, so the host verifies.

## Costs and risks

- Up to five drafting requests per answer instead of one (Thinker, Verifier and
  revision each resend the sources). Rate limits are more likely; a provider failure
  on the Thinker stops the run, and one on a later turn keeps the last checked draft.
- One research request per company, up to three in parallel, plus page fetches.
- DNS rebinding between the host's address check and httpx's connect is not prevented.
- Quote checks prove text exists, not that the argument is sound or the facts current.
- No live model evaluation yet: all evidence is offline fakes (see the handoff).
