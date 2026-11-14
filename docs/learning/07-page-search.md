# Review exercise: retrieve bounded evidence from the current page

Problem: a fixed beginning-of-page preview can omit the fact needed for a task.
Increasing every observation makes model input larger even when only one passage
is useful. Extraction cleanup and task-directed retrieval solve different problems.

The new `search_page({"query": "population 2020"})` tool searches the current
page's full extracted text, before preview truncation. It does not navigate or
make a separate model call for ranking. The task must explicitly grant it. Queries
must contain a word/number, be nonblank, be at most 200 characters, and contain no
extra fields. Both the gateway and Groq adapter validate them.

Implementation decision: scan 450-character windows at 300-character intervals.
Rank by distinct matching query terms, then matching term frequency, then document
position. Match whole Unicode word tokens case-insensitively. Return at most two
nonoverlapping windows and cap the result text at 1,200 characters. Include offsets
into the extracted text and keep the source URL in the observation. These offsets
refer to current extracted text, not HTML, immutable artifacts, or stable citations.
The excerpts are untrusted data and may start/end mid-word or omit important context.

The loop stores the search result as its pending observation, delivering it on the
next turn instead of observing the full page again. A search consumes an existing
agent step. No-match results invite different keywords without asserting that a
fact is absent. Blocked navigation returns its existing failure observation rather
than reading the error page. Successful search never expands navigation authority.

On November 13, 2026, all 129 Python tests passed. Tests exercise a fact beyond the
preview, matching-term ranking, case-insensitivity, no matches, invalid arguments,
grant enforcement, source preservation, the real adapter's untruncated extraction,
agent delivery without rereading a preview, step limits, and blocked-page behavior.

The real Edge fixture in `scripts/smoke_page_search.py` also passed. Its initial
preview was 4,022 characters including the truncation marker; the search observation
was 301 characters including its source URL. Only search exposed the fixture's
2020 population value with year and surrounding text. The model was scripted;
this is not a measured model-quality result or total token/cost reduction.

Limitations: lexical search misses synonyms and can favor repeated keywords.
Character caps are not token budgets. The full extracted page is still processed
locally, and prior observations are still resent in the transcript. Search adds a
model decision and may increase total cost. No exact tokenizer, embeddings, automatic
summary, page cache, persistent index, transcript compaction, or section-navigation
tool was added. Missing source content cannot be recovered by searching it.

Try the no-cost browser demonstration from the repository root:

```sh
.venv/bin/python scripts/smoke_page_search.py
```

Optional live run, using keys exported in your terminal (paid E2B/model calls):

```sh
.venv/bin/python scripts/groq_e2b_demo.py --trace --question "find Boston's population at the 2020 census; use search_page to locate the supporting passage before answering"
```

Five steps allow navigation, search, refinement, and finish, but a real model may
still fail or hit a limit. Inspect the trace rather than assuming it used search.
The live result remains pending. Review the pure search helper first, then the
adapter's `search_page`, and finally the pending observation in the agent loop.
