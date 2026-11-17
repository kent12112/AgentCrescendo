# An unavailable source is different from a failed model action

The user saw “Wikimedia Error” before any model request. The source page itself
was unavailable. The guard correctly stopped the model from treating the error
page as the Boston article, but it saved no screenshot or HTTP status, because
diagnostic capture began only after that guard passed.

An error title does not tell us whether the HTTP response was a temporary 5xx,
a rate limit, an access refusal, or another problem. A fresh E2B request returned
HTTP 200 with the Boston article; this does not identify the earlier cause.

We preserve the source guard and improve the evidence around it. The adapter
retains the final response status and `Retry-After`, clearing them before every
new navigation so an earlier success cannot validate a later failure. The demo
requires both HTTP 2xx and the article element before making a model call.

Only temporary responses (429/5xx) and navigation timeouts get one retry of the
same authorized GET. The wait defaults to five seconds and cannot exceed 15
seconds. Refusals, certificate/browser errors, missing articles, unknown status,
and unacceptable server delays stop cleanly. The retry uses Playwright's wait,
which keeps the request-filter callbacks running. It grants no new destination
or action and does not change network restrictions.

Failed startup images now have `source-*` names; model-input images retain
`step-*` names. A `source_unavailable` result explicitly records zero model
calls. Tests deliberately return 503 then 200, repeated 503, 403, a successful
HTTP response with no article, a 404 containing article-like markup, and browser
timeouts. A CLI test verifies that evidence is saved and the desktop closes
while the model remains uncalled.

See [handoff](../handoffs/2026-11-16-codex-source-startup.md) and
[clicking](../e2b-clicking.md#startup-source-failures).
