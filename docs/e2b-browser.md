# Groq + real E2B browser

The browser adapter implements the same `observe()` and `navigate()` interface
as `FakeDesktop`. Chrome runs inside a temporary E2B desktop. Playwright runs on
your machine and connects over a private Chrome DevTools Protocol (CDP) endpoint.
Groq receives page text and proposes tools; the existing gateway authorizes them.

## Run

Install the dependencies from the project root. `-e` links to your local project;
`[e2b,groq]` selects both optional SDKs. This changes the virtual environment:

```sh
.venv/bin/python -m pip install -e '.[e2b,groq]'
```

Keep `GROQ_API_KEY` and `E2B_API_KEY` set in the same terminal. If needed, use
`read -s` followed by `export` as described in the preflight guide. No keys are
loaded automatically from `.env`, and no Groq key is sent to the sandbox.

Run the demo. This creates a metered E2B resource, sends real model requests,
and visits the live Wikipedia Boston page:

```sh
.venv/bin/python scripts/groq_e2b_demo.py
```

Expected output: finished status, an answer identifying Boston, Wikipedia as a
source, and the page in `Visited`. Blocked browser requests may be nonzero because
the text-only browser blocks images, stylesheets, and other non-document traffic.
The sandbox is killed on normal completion or exceptions; its 180-second lifetime
is a fallback if the controlling process disappears. The agent has five steps
and a 120-second deadline checked between steps. Each model decision permits
one corrective retry for provider-rejected tool generation (at most ten API
requests across five steps); other API errors are not retried.

## Workflow

1. Create the desktop with deny-by-default egress and the grant's allowed hosts.
2. Launch a fresh Chrome profile on the virtual display.
3. Relay its loopback debugger to port 9223. E2B requires a per-sandbox traffic
   token for this endpoint; the adapter supplies it without logging it.
4. Create a browser context with JavaScript, service workers, and downloads disabled.
5. Enable CDP Fetch interception before the first navigation. Every paused request
   is checked against `authorize()` and must be a GET document request. Redirect
   destinations are separate intercepted requests. Rejected requests are aborted.
6. Run the existing loop; observations contain the actual URL, body text capped
   at 4,000 characters, and an untrusted list of link labels and destination URLs.
   We inspect the first 400 anchors and retain at most 20 unique HTTPS destinations,
   with a combined label/URL budget of 2,000 characters (JSON formatting is extra).
   Labels are capped at 80 characters; URLs over 512 characters are skipped rather
   than truncated. Fragment duplicates and links to the same page are omitted.
   Browser-resolved destinations honor relative URLs and the page's base URL.
7. Close the browser and destroy the desktop in cleanup blocks.

## Scope and validation

Links are data, not permissions: the gateway still authorizes each proposed
navigation. Link selection is sampled in document order, so navigation menus may
use up the budget before useful article links. The model is prompted to prefer
observed links, but can still propose other URLs. Link observations are inside
the run's transcript; the demo's final summary does not print the full transcript.

This is an initial text-browsing integration, not a screenshot/click agent or an
authenticated live-view UI. JavaScript-dependent sites will not work. Browser
navigation failures propagate and still trigger cleanup. Model-reported sources
are not independently validated against visits.

Unit tests exercise request decisions, simulated redirect events, observations,
private control connection setup, and cleanup after setup/model errors. No live
cloud run was performed during implementation; Chrome startup, the relay, and
actual browser redirect interception still require a live smoke test. There is
no verified claim of complete network isolation. E2B's sandbox-local metadata
exception remains as documented in the preflight investigation. DNS behavior,
shared IPs, and traffic outside this instrumented page still rely on E2B controls.

If startup fails, share the error without keys or control tokens. Do not make the
debugging port public to work around authentication failures.

References: [Playwright CDP connection](https://playwright.dev/python/docs/api/class-browsertype#browser-type-connect-over-cdp),
[CDP Fetch](https://chromedevtools.github.io/devtools-protocol/tot/Fetch/),
[E2B private service access](https://docs.e2b.dev/network/restrict-public-access).

Decision record: use a text-only browser with an explicit request gate as the
smallest live research slice. Prediction: Wikipedia loads, while disallowed
document destinations are aborted before sending. Local unit tests pass; actual
cloud behavior remains to be measured and recorded after the smoke test.
