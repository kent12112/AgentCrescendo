# Week 1 annotated traces

Three live runs of the visual agent, chosen to show one success and two
different kinds of failure. All three used `qwen/qwen3.8-27b` on Groq inside one
E2B desktop, with the gateway, request filter, and firewall described in
[network preflight](e2b-preflight.md).

How to read them:

- **Trace** lines are copied from each run's saved `result.json`. "Reason" is the
  model's own account of its choice. It is untrusted and can be wrong.
- **Annotation** lines are ours, checked against the saved screenshots the
  model actually received.
- Pass or fail comes from the scripts' graders, which read the browser's state.
  They never take the model's word for it.

Screenshots and full `result.json` files are in the ignored `.demo-artifacts/`
folder on the machine that ran them. They are not committed.

| Run | Task | Result | Kind |
| --- | --- | --- | --- |
| [A](#a-cited-research-success) | GNIS feature ID from the Boston article | Pass, 88.5 s | Success |
| [B](#b-pixel-clicks-miss) | Click to the Massachusetts article, pixel mode | Fail | Model error: aiming |
| [C](#c-right-click-throttled-answer) | Same, link-ID mode | Fail | Provider error: throttling |

## A. Cited research success

`.demo-artifacts/research-e1b74f4c251c4e15b75a03e22fe80364/`, November 13, 2026,
23:05 ET. Script: `scripts/e2b_visual_research_demo.py --save-screenshots`.

Configuration: tools `navigate`, `screenshot`, `scroll`, `finish`; host
`en.wikipedia.org`; 8 steps allowed; screenshots downscaled to 768×576.

Goal given to the model: "What is Boston's GNIS feature ID, as listed in this
article's infobox? Scroll as needed and read the value from the screen. Finish
with only the value."

| Step | Trace | Annotation |
| --- | --- | --- |
| 1 | `scroll(down, 5)`. Reason: scroll to locate the GNIS feature ID field | The article opens at the top. The ID is near the bottom of a long infobox, so it is off screen. |
| 2 | `scroll(down, 5)`. Reason: it is below the Map section | The model correctly reads that it is still inside the infobox. |
| 3 | `scroll(down, 5)` | Steady progress, no backtracking. |
| 4 | `scroll(down, 5)` | The screenshot after this scroll shows the last rows of the infobox. |
| 5 | `finish("617565")`. Reason: "GNIS feature ID 617565" | Verified: the step-5 image shows the "GNIS feature ID 617565" row at the infobox's bottom right. The answer came from the screen. |

Grader: answer contains `617565`; the page contains it; the value was inside the
visible viewport at finish. **PASS.**

What it shows:

- The whole Week 1 loop works on a real public page: screenshot in, bounded
  scroll out, fresh screenshot, answer backed by what was visible.
- **Citation support is checked, not claimed.** The grader looks for the value
  in the browser's viewport at the moment of finish. A guessed or remembered
  answer would fail.
- **Throttling dominated the time.** Groq rate limits added waits of 8, 9 and 9
  seconds: 26 of the 88.5 seconds. Model reasoning was not the bottleneck.
- 93 page requests were blocked by the filter (images, scripts and other
  types it doesn't allow), and the answer still worked. Text and layout come from documents and stylesheets.

## B. Pixel clicks miss

`.demo-artifacts/click-d1cc33e0a9a14bcea61055b94a2ce279/`, November 16, 2026,
18:03 ET. Script: `scripts/e2b_click_demo.py` in coordinate mode, full-size
1024×768 screenshots. This was an earlier version of the goal, which did not
name the link text.

Goal: "Boston is the capital of a U.S. state. Click the link to that state's
Wikipedia article. After it opens, finish with only that article's title."

| Step | Trace | Annotation |
| --- | --- | --- |
| 1 | `click(309, 448)`. Reason: "Massachusetts" | Right idea, wrong place. In the step-1 image the "Massachusetts" link sits at about (317, 602). The model was 8 px off horizontally but 154 px too high, in blank margin beside the yellow notice box. |
| — | "Authorized click completed. The click did not start a page load." | The safety layers worked as designed. The click was inside the page area, so the gateway allowed it, the real pointer clicked, and nothing happened. |
| 2 | `click(309, 448)` again | The model repeated the exact miss even though the screen had not changed. It did not use the "no page load" feedback. |
| 3 | `click(329, 439)` | A small adjustment in the wrong direction. Still well above the link. |
| 4 | (no decision) | Groq rate limit. The run stopped as `rate_limited` after 52.1 s. |

Grader: the tab never left the Boston article. **FAIL.**

What it shows:

- The model knew *which* link was needed but could not turn that into screen
  pixels. Four live runs missed the same way, including with grids and with
  the link text named. This led to
  [decision 0002](decisions/0002-visible-link-grounding.md): the browser measures
  visible links and the model chooses an ID instead of guessing pixels.
- A safe miss is still a miss. Permissions limit what a click may touch; they
  do nothing for accuracy.
- The model did not notice that its action had no effect. Better feedback alone
  would not have fixed this run.

## C. Right click, throttled answer

`.demo-artifacts/click-31af50656a494c638f2f54098952743d/`, November 16, 2026,
18:28 ET. Script: `scripts/e2b_click_demo.py` in link-ID mode (the new default),
768×576 screenshots.

Goal: the current one, which names the link: "In the article's first paragraph,
click the blue link whose text is exactly 'Massachusetts'…"

| Step | Trace | Annotation |
| --- | --- | --- |
| 1 | Screenshot plus `visible_links`, a list of IDs and labels measured by the browser | The model sees no URLs, only labels. The runtime keeps each link's real position and destination privately. |
| 1 | `click_link(39)`, resolved to `click(317, 602)`. Reason: "Massachusetts" | Correct. ID 39 resolved to the same spot run B should have clicked, and the real pointer clicked there. |
| — | "Authorized click completed. The click opened https://en.wikipedia.org/wiki/Massachusetts." | Confirmed by the browser, not the model. |
| 2 | (no decision) | Groq rate limit on the request that would have finished. The run stopped as `rate_limited` after 6.1 s. |

Grader: the browser ended on the right article, but there was no answer.
**FAIL.**

What it shows:

- The model's part of the task succeeded and the run still failed. Provider
  capacity is a failure mode of its own, separate from model quality, and has to
  be recorded separately.
- At the time, the click demo gave up on its first rate limit. Afterwards it got
  one wait of up to 60 seconds, bounded by the deadline, plus a shared retry
  for timeouts and server errors
  ([timeout handoff](handoffs/2026-11-16-codex-vision-timeout.md)). All seven
  link-mode runs saved after this one passed, in 23.6 to 54.5 seconds.

## Across the three

| | A | B | C |
| --- | --- | --- | --- |
| Model chose the right action | Yes | Intent yes, pixels no | Yes |
| Safety layers behaved correctly | Yes | Yes | Yes |
| Provider interfered | Slowed it (26 s of waits) | Ended it | Ended it |
| Graded from | Viewport text at finish | Browser URL | Browser URL and answer |

These are three runs, not a benchmark. They show what kinds of failure exist,
not how often each occurs. Reliability numbers need repeated runs, and so does
the deferred model comparison (W1-4).
