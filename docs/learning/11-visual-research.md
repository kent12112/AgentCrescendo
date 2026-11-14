# Visual research on a real public page (W1-6 / plan W1-F09)

This slice joins the separate pieces: host-authorized navigation to a permitted
public page, screenshot observation, model-selected scrolling, and a cited answer.

```sh
.venv/bin/python scripts/e2b_visual_research_demo.py --watch --save-screenshots
```

## What runs

- Grant: `navigate`, `screenshot`, `scroll`, `finish` (+ `view_desktop` with
  `--watch`); hosts: `en.wikipedia.org` only. The E2B firewall uses the same list.
- Host code navigates to `https://en.wikipedia.org/wiki/Boston`. The model is
  offered only `scroll` and `finish`; the loop denies anything else, so the model
  cannot navigate even though the grant contains `navigate` for the host.
- Question: Boston's GNIS feature ID from the infobox (`617565`). Chosen because a
  model is unlikely to know it without reading the screen, and it sits about five
  screens down in a table.
- Citation: the URL of the page the screenshots came from, confirmed to be on the
  permitted host. The model does not compose the citation.

## Honest grading

Pass requires all three, checked after the model finished and never shown to it:

1. the answer contains `617565`;
2. the article text still contains `617565` (otherwise "fixture changed", not a
   model failure);
3. `617565` is drawn inside the viewport at finish, from the browser layout. A
   correct value that is not on screen could be memorized or guessed, so it fails.

The model's only evidence channel is screenshots; the page-text read is for
grading. `result.json` records the tools the model proposed.

## Findings while building

- **Blank first screenshot.** `navigate()` waited for `domcontentloaded`; Chrome
  had not painted. It now waits for `load`.
- **Unstyled pages bury content.** The browser filter allowed only `Document`
  requests, so Wikipedia's CSS was blocked and about four screens of menus, a
  contents list, and 182 language links preceded the article. The filter now also
  continues `GET` `Stylesheet` requests from permitted hosts. Scripts, images,
  fonts, XHR, other hosts, and non-GET requests remain blocked; requests a
  stylesheet triggers are paused and checked like any other. Images show as alt
  text (they come from `upload.wikimedia.org`, which is not permitted).
- **Rate limits.** The first live run stopped with Groq 429 on step 3: about 2.8k
  input tokens per 1024x768 screenshot against a 7k tokens/minute limit. Fixes:
  screenshots are downscaled to 768 px wide before being saved and sent (the
  saved PNG is still exactly the model input), and the loop absorbs one
  provider-requested wait per step (at most 15 s, only if it fits the deadline),
  otherwise it stops with status `rate_limited`. Provider error text, which
  includes the account's organization identifier, is not kept.
- **Desktop lifetime.** A full run took about 2 min 19 s end to end, close to the
  180 s sandbox lifetime before adding a viewer wait. `open_e2b_desktop` now takes
  `lifetime_seconds` (default 180, allowed 60-600); this demo uses 300. The agent
  deadline stays 120 s.

- **Model reasons.** Every tool now asks for a one-sentence `reason`. The parser
  removes it from the arguments before the gateway sees them (so `scroll` still has
  exactly `direction` and `amount`), cleans it to one line of at most 200
  characters, and never fails a step if it is missing. The loop records it in the
  action entry; the demo prints one line per decision. Reasons are the model's own
  account: useful for debugging and a future activity panel, not evidence.
- **The source can rate-limit us too.** One run received Wikipedia's "Too many
  requests" error page (E2B desktops share outbound addresses, plus repeated runs).
  The agent then ran on an error page and grading crashed. The demo now checks the
  article element exists before the agent starts and stops with "SOURCE
  UNAVAILABLE" without any model call.

## Live results

November 13, 2026, without the viewer, 768 px screenshots: PASS. The model chose
`scroll(down,5)`, `scroll(down,1)`, then three `scroll(down,5)`, and
`finish("617565")`; 0 denials; 93 blocked browser requests; value visible at
finish. The final 768x576 model input shows "GNIS feature ID 617565" legibly.
Artifacts: `.demo-artifacts/research-48e2096b5eb94b9cb43b7d96747a49a7/`. One run;
rate-limit waits were not yet logged in that run.

A run the user started (`research-dbe8…`, presumed watched, to be confirmed):
PASS, 82.4 s agent time, three rate-limit waits (6, 7, 8 s).

With reasons (`research-e1b74f4c…`): PASS, 88.5 s, three waits totalling 26 s.
Reasons such as "GNIS feature ID is further down the infobox; need to keep
scrolling" show the model expected the field's position from prior knowledge of
Wikipedia layouts before it was visible; the value itself was visible at finish.

## Limits

One page, one question, one model. No clicking, typing, or model-chosen
navigation. Downscaling may hurt reading of small text on other pages. The
citation is the displayed page, not a paragraph-level anchor.
