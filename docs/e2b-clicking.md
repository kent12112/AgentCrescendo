# Clicking with the real pointer (W1X-F01)

How `click(x, y)` works, the layers that limit it, and what was observed live.
Status: the security cases pass live. A DOM-assisted model-selected link-follow
passed November 16, 2026. Raw screenshot pixel aiming remains unreliable; see
[grounded link selection](#grounded-link-selection).

## Path of one click

In the locked-room picture, the worker (model) points at a spot on the camera
image. The guard checks the spot, looks at what is there, and only then lets the
robot hand press the button. The doors (request filter and firewall) still check
whatever the press makes the browser request.

1. **Model** proposes `click(x, y)` in pixels of the screenshot it saw, or
   `click_link(target_id)` from the current visible-link inventory. Clicking is
   offered only when a demo opts in (`GroqVision(allow_click=True)`). The click
   demo defaults to link IDs; other vision demos keep their existing tools.
2. **Loop** scales the point to real screen pixels. Screenshots may be downscaled,
   for example from 1024 to 768 wide. The trace records both points.
3. **Gateway** (`authorize(..., click_area=...)`) requires integer x/y inside the
   page area. With no area it denies. The `click` tool must be granted.
4. **Page area** is a fixed rectangle measured live: screen `(0,114)` to
   `(1024,700)`. It is used only if Chrome's window and viewport match the sizes it
   was measured with. Otherwise clicks are refused.
5. **Target check**: the adapter asks the page what the point would hit
   (`elementFromPoint`, run as automation code with page scripts disabled). It
   refuses new-tab links and forms (`target`, `formtarget`, `<base target>`),
   `download` links, frames, image maps, and anything it cannot classify.
6. **Real click**: E2B `move_mouse` then `left_click`, the same real pointer that
   scrolling uses.
7. **Wait**: the adapter waits with Playwright's own waits until the tab's
   main-frame page request appears and the new document loads. It reports one of
   these outcomes to the model: opened URL, blocked, no page load, or timeout.
8. **Request filter and firewall** check every request the click causes: GET only,
   permitted hosts, document and stylesheet only. The E2B firewall is the outer
   layer.
9. **Backstop**: if a new tab opens anyway, it is closed at once and recorded in
   `closed_pages`.

## Measured facts (live probes, November 16, 2026)

- **Geometry.** E2B's screen is 1024×768. Chrome's window is 1282×800 at (−4, 27),
  so it extends past the screen; the viewport is 1280×720. Fixture boxes placed at
  page (40, 40) appeared at screen (40, 154), so the page origin is (0, 114).
  Calculating the origin from JavaScript window sizes gave (−2, 107), which is
  wrong, so it is not used.
- **Dock.** Moving the pointer to the bottom screen edge reveals a desktop dock
  (terminal, file manager, browser) at about y 720–768. Clicking it could launch a
  terminal, so the page area stops at y=700. The visible page below that is not
  clickable; the model can scroll instead.
- **Waiting must use Playwright.** Playwright runs our request-filter callback only
  while the script is inside a Playwright call. With `time.sleep`, the click's page
  request stayed paused and the tab hung loading.
- **New tabs bypass the request filter.** A `target="_blank"` link or form opened
  a new tab and loaded Wikipedia with none of its requests seen by our filter
  (only the E2B firewall applied). Chrome's `--block-new-web-contents` flag was
  tried and did **not** prevent this. Hence the target check (step 5) and the
  backstop (step 9). The backstop alone is not enough: the tab's first request
  has already gone out when it is closed.
- **Downloads.** A `data:` link with a `download` attribute saved nothing to
  `~/Downloads`, because Playwright's `accept_downloads=False` makes Chrome deny
  downloads. `action=raw` on Wikipedia is displayed, not downloaded.

## Live evidence

`.venv/bin/python scripts/e2b_click_check.py`: one desktop, no model, run from
this machine. The first run (22:58Z) exposed a bug: a click's completion was
detected by a URL change, which never comes when two error pages share a URL.
`click()` now waits for the tab's navigation event instead. Second run (22:59Z),
all checks passed:

| Case | Result |
| --- | --- |
| Chrome geometry matches measured page area | Pass |
| Permitted link | Opened `.../wiki/Massachusetts` |
| Link to `example.com` | Request failed by filter; reported as blocked |
| POST form to a permitted host | Request failed by filter (non-GET) |
| `target=_blank` link, `target=_blank` form, `download` link | Refused before pressing; no new tab |
| Address bar (512, 90), dock (512, 740) | Refused by gateway: outside page area |
| Second layer: raw click on download link | No file saved |
| Second layer: raw click on new-tab link | Backstop closed the tab (it had already loaded Boston) |

`.venv/bin/python scripts/e2b_click_demo.py --save-screenshots` (Groq
`qwen/qwen3.8-27b`, Boston → Massachusetts): **failed in all four runs.**
Image coordinates below are in the image the model saw.

| Run (UTC) | Setup | Model's clicks | Link at about | Outcome |
| --- | --- | --- | --- | --- |
| 23:00 | 768 px, no grid, "state Boston is capital of" | (276, 487), (253, 297) | (238, 451) | Both hit plain text: "did not start a page load" |
| 23:01 | 1024 px, no grid | (309, 448) ×2, (329, 439) | (317, 602) | Plain text |
| 23:09 | 768 px, grid | (509, 544), (646, 423) "State capital" | (238, 451) | One outside the page area (denied), one on the infobox heading |
| 23:10 | 768 px, grid, goal names the link "Massachusetts" | (279, 570), (380, 544) | (238, 451) | Both outside the page area (denied) |

Every run ended `rate_limited` after two or three model calls (about 13 s).
Groq's per-minute token limit allows only a few screenshots, so each run had at
most three tries. Screenshots show the real pointer exactly where the model asked,
so the coordinate mapping works. The grid (below) did not improve aim in two runs.

## Grounded link selection

The fix adds a browser-measured target inventory. The model chooses a link; it
does not estimate that link's pixel position. This is **DOM-assisted interaction**,
not evidence that the model learned screenshot-only pixel grounding.

1. After capturing a screenshot, `visible_links()` retains references to at most
   120 text links inside the calibrated page area. It chooses the center of a
   visible client rectangle, including for wrapped or partially clipped links.
   Hit testing excludes covered/off-screen links; hidden and fully transparent
   links are excluded. No page content or layout is modified. This metadata read
   requires explicit `read_visible_links` and `click` permissions; it does not
   capture an image or reuse screenshot permission. The click demo grants
   `read_visible_links` only in link mode; screenshot capture stays separate.
2. The model receives only each link's ID and visible label, alongside the
   screenshot. It receives no target URLs or selectors. IDs are never reused
   within a desktop and expire with the next observation.
3. `click_link(target_id)` resolves only against that snapshot. The same element
   must still be attached, have the same label and destination, and occupy the
   saved point. Changes cause a denial and fresh observation, not a guessed click.
4. The loop converts the selection to `click(x, y)` in **screen pixels**, without
   applying screenshot downscaling again. Both the model's ID and the resolved
   point are recorded. All existing gateway, target, pointer, and network checks
   then run through the original click path.

The complete audit retains every inventory, but model requests include only the
latest inventory. Expired IDs consume tokens and can confuse the next selection.
The loop permits at most one additional inference request per step, shared by
rate limits, timeouts, and temporary server errors. For a rate limit, the click demo permits a provider-
requested wait of at most 60 seconds, only when it fits within the existing
120-second run deadline. Other demos retain their 15-second wait limit.

For a Groq request timeout, the loop retries the same screenshot and link
inventory once, without replaying any desktop action. Repeated timeouts return
`model_timeout`; provider failures are recorded separately from page evidence.
The click demo prints a retry notice and still writes `result.json` when saving
diagnostics. Its SDK request timeout defaults to 45 seconds and can be set with
`--request-timeout` (positive, at most 60). SDK automatic retries remain disabled.
The adapter default for other vision demos remains 30 seconds. Deadlines prevent
new requests/actions after expiry; they do not hard-interrupt an in-flight SDK
operation.

Groq HTTP 5xx responses also use this retry budget, respecting a numeric
`Retry-After` header or a two-second default backoff. Persistent errors return
`model_unavailable`, with a clear message and saved diagnostic result. A live
follow-up to the user's timeout report returned HTTP 503 with the model reported
over capacity; this is evidence about that request, not proof of a broad outage
or the cause of the earlier timeout. See the
[timeout handoff](handoffs/2026-11-16-codex-vision-timeout.md).

Run the default mode with:

```sh
.venv/bin/python scripts/e2b_click_demo.py --save-screenshots
```

For the original screenshot-only experiment, use `--click-mode coordinates`;
`--grid` adds the old experimental pixel grid. The grid now defaults off.

Live evidence for the fix:

- First grounded run selected ID 39 and clicked `(317, 602)`, opening
  Massachusetts. The final-answer call was throttled, so the full demo failed.
  Artifact: `.demo-artifacts/click-31af50656a494c638f2f54098952743d/`.
- The next 768-pixel run **passed**: ID 39 → screen `(317, 602)`, recorded browser
  navigation Boston → Massachusetts, then `finish("Massachusetts")`. 23.6 seconds,
  including a 17-second provider-requested retry. The saved post-click model-input
  screenshot was inspected and shows the Massachusetts article.
  Artifact: `.demo-artifacts/click-d58d76be4de54f21a4378c5686dab9bb/`.
- A full-size 1024-pixel repeat also **passed**: ID 39 → screen `(317, 602)`,
  Boston → Massachusetts, then `finish("Massachusetts")`. 24.0 seconds including
  an 18-second provider-requested retry.
  Artifact: `.demo-artifacts/click-67b0c448c6c74c12b3ee111d618a7f9f/`.
- Extended `scripts/e2b_click_check.py` passed 23 model-free live checks: the
  original 12 plus link visibility, point resolution, ID expiration, changed
  destination/text/position, detached elements, grounded new-tab/download
  refusals, and a grounded real-pointer navigation. The final rerun also checks
  transparent-link exclusion.

These are small development checks, not a pointing or task reliability benchmark.
Local regression check at the grounding handoff: `.venv/bin/python -m pytest -q` — 334 passed; one
pre-existing Starlette/httpx deprecation warning. `git diff --check` passed.
The timeout follow-up passed 362 local tests and one additional live demo in
54.5 seconds (including a 17-second rate-limit wait). Artifact:
`.demo-artifacts/click-711fb3c6229348d488458eae8462a353/`.

## Why coordinate prompting was not the fix

The click machinery and its limits were verified before this fix. The four
earlier runs showed inconsistent offsets, not a single fixed translation.
Codex replayed the saved 768×576 Boston image with the exact target named:

- An explicit pixel prompt returned `(215, 301)`; the target is near `(238, 451)`.
- A normalized 0–1000 prompt returned `(327, 570)`, mapping to image `(251, 328)`;
  this also misses. The normalized-coordinate prototype was removed.

[Qwen's vision documentation](https://docs.qwencloud.com/developer-guides/multimodal/vision)
describes normalized grounding for related model series. That motivated the
experiment; it does not establish that a coordinate convention caused these
failures. The replay used real Groq inference on saved screenshots, not a live
desktop. One comparison cannot characterize all model grounding behavior.

**Grid overlay.** `run_vision_agent(grid=True)` draws thin lines every 50 px,
labelled every 100 px, on the model's copy of each screenshot, after
downscaling. The real screen and the coordinate space are unchanged, and saved
PNGs show the grid exactly as the model saw it. The demo enables it with `--grid`
(`--no-grid` is also accepted). The goal names the link text, so the demo tests
pointing rather than knowing which state Boston is the capital of. Model
judgement is W1-F12's job.

## Limits

- Link IDs currently cover visible HTML text links only, capped at 120 per
  observation. They do not add button, form, image-only link, or canvas grounding.
  Raw pixel clicking remains available for explicit experiments.
- Target inventory and screenshot capture are separate browser operations.
  Resolution checks catch stale link selections; this does not make the entire
  screenshot/model/check/press sequence atomic.
- The page area is calibrated for this E2B template and Chrome layout. Any change
  makes clicks fail closed until it is re-measured.
- The request filter checks hosts through the `navigate` rule. A task must be
  granted `navigate` for clicks to load pages at all. W1X-F02 (moving only by
  clicking) needs a host check that does not depend on the model's tools.
- Only a left single click exists: no typing, right/middle click, or drag. Forms
  can still be submitted by a click, but non-GET requests are blocked.
- A click on a link to the page already open, or a slow page, can end in the
  20-second "did not finish" outcome.
- The target check reads the page just before the click. A page that changed
  between the check and the click is not re-checked. With page scripts disabled,
  such changes are limited to loading, not script activity.

## Startup source failures

The click demo admits the model only after an HTTP 2xx response containing
`#mw-content-text`. A site error page, even at the correct URL, is not source
evidence. The initial “Wikimedia Error” report had no HTTP status or saved image:
the original screenshot callback ran only after startup validation succeeded.
A fresh model-free E2B check loaded Boston with HTTP 200; the original failure's
cause remains unknown.

Startup now records the final response status and only the `Retry-After` header.
It retries the same authorized source GET once for HTTP 429/5xx or a navigation
timeout. Backoff defaults to five seconds; a numeric server delay is accepted only
from zero to 15 seconds. Longer, negative, non-finite, or unparseable delays stop
the attempt. HTTP refusals such as 403, unknown browser failures, unknown status,
and successful HTTP responses lacking the article do not trigger retries.

With `--save-screenshots`, failed source attempts save `source-01.png` (and
`source-02.png` if applicable), plus `source-attempts.json`. If startup still
fails, `result.json` records `status: source_unavailable` and `model_calls: 0`.
These images are source diagnostics, not model-input screenshots. The ordinary
`step-*.png` files still save exactly what the model receives after validation.
Successful runs also retain source attempt metadata in their final result.

Checks: 379 local tests passed; transient/refused/missing-source and startup
artifact paths are tested with controlled responses. See the
[source startup handoff](handoffs/2026-11-16-codex-source-startup.md).
Final live check: source HTTP 200 on the first attempt, complete Boston →
Massachusetts PASS in 24.3 seconds, including a 17-second model rate-limit wait.
Artifact: `.demo-artifacts/click-86e09d556bc3494fb5f41a914444065a/`.

## Viewer startup failures

With `--watch`, the model still waits for the authenticated live-view transport
and the person's Enter confirmation. Viewer asset GETs share one connection pool
and retry transport failure once. Optional icons do not fail the gate; missing
required HTML/JS/CSS still does. On a gate failure, `--save-screenshots` now saves
a `viewer_unavailable` result, safe error codes, zero model calls, and a best-
effort screenshot of the underlying desktop. Private viewer URLs, passwords,
and traffic tokens are excluded from saved result metadata.

To check the real viewer without relying on Wikipedia or Groq, run
`.venv/bin/python scripts/e2b_live_view_check.py`. This uses one metered E2B
desktop and local Microsoft Edge, and deliberately tests transport recovery.
See the [viewer recovery handoff](handoffs/2026-11-16-codex-viewer-connection.md).
