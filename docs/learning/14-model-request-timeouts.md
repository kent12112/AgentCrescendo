# Retrying inference without replaying actions

The user reported `groq.APITimeoutError: Request timed out.` The configured
Groq client used a 30-second timeout and disabled SDK retries. The loop caught
HTTP rate limits, but did not catch the SDK timeout exception, so the exception
escaped before the demo could save its result. This symptom does not identify
whether the provider or network was slow.

We translate the SDK exception into a sanitized `ModelTimedOut` signal. The
vision loop owns the retry budget: two inference requests total per step,
including any mixture of a timeout, rate limit, or transient server error. This avoids stacking SDK
retries underneath application retries.

A model request proposes an action. It does not press the mouse. Retrying that
request before receiving a proposal cannot replay a desktop action. The retry
uses the same screenshot, link inventory, and transcript; transient-error trace
entries are appended afterward. Once a proposal arrives, the usual authorization
and stale-target checks still apply. A timeout on the step after a completed
click does not cause that earlier click to run again.

The click demo uses a 45-second SDK timeout, configurable up to 60 seconds. A
second timeout returns a `model_timeout` result, saves diagnostics when requested,
and leaves context managers to close the viewer and desktop. The deadline is
checked before every attempt and after a request returns. It does not forcibly
interrupt a request already in flight.

The first live check returned a new failure: HTTP 503, with Groq reporting the
model over capacity. That is consistent with temporary provider pressure, but
does not prove why the earlier user request timed out. We added sanitized HTTP
5xx handling under the same retry budget, with `Retry-After` or a two-second
backoff and a clean `model_unavailable` result if retry does not recover.
The public status page reported operational during this request; a status page
does not supersede the outcome of a specific API call.

Tests use the actual Groq SDK with an in-memory HTTP transport that raises a
read timeout. No provider traffic is needed to exercise the SDK exception path.
Other tests inject repeated/mixed failures, advance a fake clock through the
deadline, and verify that the click count stays zero or one as appropriate.
A mocked CLI run verifies diagnostic output and desktop cleanup on failure.

See the [timeout handoff](../handoffs/2026-11-16-codex-vision-timeout.md).
SDK reference: [official Groq Python documentation](https://github.com/groq/groq-python#timeouts).
Status reference: [Groq status](https://groqstatus.com/).
