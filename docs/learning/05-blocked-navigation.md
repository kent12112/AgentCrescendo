# Review exercise: recover after blocked browser navigation

Date: November 13, 2026

Problem: the initial URL could pass policy while its server redirected to a
forbidden destination. Interception blocked the new request, but `page.goto`
raised a browser error that stopped the run before the model could choose another source.

Decision: keep recovery inside the desktop adapter. Recover only when Playwright
reports `net::ERR_BLOCKED_BY_CLIENT` and an intercepted document request for the
current main frame was blocked during this navigation. Clear the frame tracking
before each navigation so old blocks cannot explain later errors. Other failures
continue to propagate.

The adapter stores a fixed `Observation(None, ...)` describing the block. Subsequent
observations return that message without reading the failed page. No forbidden
URL or browser exception details are copied into it. The existing agent loop
presents it to the model, which can propose another source or finish. A successful
navigation clears the failure and restores normal page observations. Failed
navigation is not added to successful visits. Existing step/deadline bounds still
apply; there is no automatic retry loop.

Tests cover blocked redirect recovery, the model receiving the observation,
skipping failed-page reads, successful subsequent observations, and propagating
unrelated errors despite image, iframe, or previous-navigation blocks. The local
Edge smoke test uses controlled CDP responses but real Chromium redirect events.
Its first assertion was too restrictive because Chrome also requested a favicon;
the corrected check requires the forbidden destination to be blocked while
allowing additional legitimate resource blocks.

Result: all 99 Python tests and the local browser smoke test passed. The existing
Starlette/httpx deprecation warning remains. No paid model or E2B resources were
used. The changed recovery path has not yet been tested on a live E2B desktop.

Review `E2BDesktop.navigate`, `_request_paused`, and `observe` together. Check that
recovery changes what the agent learns without weakening which requests may run.
The scripted model demonstrates that recovery is possible; a real model may still
repeat the failed action until an existing limit stops it.
