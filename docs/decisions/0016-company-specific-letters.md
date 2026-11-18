# Decision: build a company-specific argument with evidence from both sides

Date: November 18, 2026. User reported that letters were too simple and requested
connections between the company's product/culture and unique resume experience.
Amends the drafting prompt and evidence shape in decision 0011; no new research
worker, provider, desktop flow, or source collection is introduced.

## Problem and change

The old prompt favored concise source restatement and required splitting candidate
and company facts into separate sentences. That made it hard to express a natural
argument about why a past decision matters for a particular product or team.

The writer now selects the strongest one or two connections between concrete resume
experience and company product, users, problems, or documented working practices.
It should lead with a specific connection, explain relevance, and close with a
grounded possible contribution. Accurate paraphrasing is permitted. Past work must
stay in its original setting; transferable experience is not prior experience in
the company's industry. Product use, motivation, and culture are not to be invented.
The company-name replacement check encourages specificity. The 220–320 word range
is guidance, not a validator; sparse sources should produce shorter letters.

Each sentence keeps its existing primary `source`/`quote` and gains up to three
`supporting_quotes` with source and excerpt. Host validation accepts older responses
without the field. The provider's strict schema requires the field for new requests.
Every additional quote is matched separately and displayed in review. Short/empty
quotes become warnings rather than discarding otherwise usable text. This matches
the primary-quote behavior. Unsupported numbers still flag a mixed-source sentence
when resume evidence is supplied; the check is conservative and can flag company
numbers too. Adding a company quote cannot excuse a fabricated candidate metric.

## Context boundary and tradeoffs

Inputs remain the immutable, consented redacted resume, stored posting and optional
user notes. The form now prompts for product/users, a concrete working practice and
the candidate's connection. User notes remain labeled as unverified. Automatic
company research is still open; a writing prompt cannot supply missing facts.

No migrations or changes to saved drafts/approvals. Completed drafts remain
idempotent, so use a new session to evaluate the new prompt. The default request
still uses low reasoning, a 3,072-token completion cap and no automatic retries.
An experiment with medium reasoning and a 6,144-token cap did not clearly improve
the fictional sample, so the more expensive configuration was not adopted.

## Evidence and limitations

See the [handoff](../handoffs/2026-11-18-codex-company-fit-letters.md) for exact checks
and local fictional comparison artifacts. Tests establish schema compatibility,
quote checks, persistence and UI behavior; they do not measure persuasive quality.
The live fixture was reused while tuning the prompt and is not a held-out benchmark.
Some drafts remained terse and included questionable inferences despite matching
quotes. Human review is required; quote occurrence does not establish semantic
support, authenticity of motivation, or hiring effectiveness.
