# Review exercise: spend the observation budget on useful content

Problem: the user's real model trace showed navigation and language menus using
most of the bounded Wikipedia observation. The answer was correct, but the trace
provided weak evidence of grounding in the article text.

Decision: before truncation, choose the first nonempty region in this order:
`main`, `[role="main"]`, `article`, then `body`. Examine only the first matching
element for each selector. Extract links from the same region. Keep text/link
budgets and independent authorization unchanged. Do not catch unrelated DOM errors.

Prediction: a page with a long menu before its main article will retain the answer
sentence and relevant link rather than menu text and menu links. Pages without a
usable region still return body content. A selected region is untrusted content,
not a security boundary.

Evidence: on November 13, 2026, all 107 Python tests passed. Real Edge fixtures
verified semantic main, ARIA main, article, empty-main fallback, and body fallback.
In the long-menu cases the old 4,000-character body slice excluded the answer
sentence, while the new observation included it and the article link. The local
redirect recovery smoke test also passed. Initial browser validation caught an
incorrect Locator API call that unrestricted mocks had accepted; it was corrected
to `content.locator("a[href]").evaluate_all(...)` before these results.

Tradeoff: this small heuristic can omit useful content outside the chosen region,
and can still include menus or infoboxes inside it. Empty first matches are skipped
in favor of the next selector, not later matches of the same selector. This is not
a universal readability extractor. Live Wikipedia comparison remains pending.

## Revision after live comparison

The user's second trace confirmed partial improvement: more infobox content reached
the model, but the language menu remained inside `main` and all 20 observed links
were language variants. The initial fixtures placed menus outside `main`, missing
this structure. The feature was held for revision rather than declaring success
from the correct final answer.

For exactly `en.wikipedia.org`, the revised extractor first tries
`#mw-content-text .mw-parser-output`. Fixed automation code clones this container,
removes navigation, infobox, sidebar, metadata, script, and style elements from
the copy, then extracts text nodes and links from that same copy. The real page
is unchanged. Missing or empty article content falls back to the generic selectors.
The copy's text is joined with spaces, so table and paragraph formatting can be
lost. Removing infoboxes also omits potentially useful facts; the aim here is to
expose article prose within the existing budget, not preserve all page information.

Added browser fixtures put a long navigation menu inside `main`, followed by a
long infobox inside the Wikipedia article container. They verify that the earlier
main-based 4,000-character slice misses the answer, while revised extraction keeps
the answer and article link, excludes menu/infobox links, and leaves the live
infobox unchanged. Another fixture verifies empty Wikipedia-container fallback.
The Wikipedia-specific path shares existing truncation and link-budget handling.
Live E2B/Wikipedia verification of this revision remains pending.

Revision validation: all 108 Python cases passed, as did all seven local Edge
fixtures, including unchanged-DOM and empty Wikipedia-container checks.

Review `E2BDesktop.observe`, `test_page_links.py`, and
`scripts/smoke_content_observation.py`. Check that text and links share a region,
fallback still works, and the observation bounds remain in force.
