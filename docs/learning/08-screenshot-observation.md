# Review exercise: the model sees a desktop screenshot

Scope: one observation, not an autonomous computer-use loop. Capture the E2B
desktop's PNG and send it as an actual image content block to a vision model.
No click, scroll, typing, or shell actions are offered to the model.

`E2BDesktop.capture_screen` checks the task's screenshot grant, foregrounds the
controlled tab, and calls an injected provider. `open_e2b_desktop` wires that
provider to `sandbox.screenshot(format="bytes")`. This is the full remote desktop,
not the local user's screen or a DOM text extraction. Existing cleanup owns the
sandbox lifetime. Screenshot capture is host-driven in this slice; it is not
added to the text agent's tool list or transcript format.

`Screenshot` bounds bytes and dimensions and checks the PNG signature/IHDR header.
It is not a full image decoder or validity proof. Its repr hides image bytes.
`GroqVision.describe` encodes those bytes into a PNG data URL inside an `image_url`
block alongside a short text question. It never stringifies screenshots into a
text transcript. One provider call is made, with a 30-second SDK timeout, no SDK
retries, and a 512-token completion cap. Reject incomplete or empty descriptions.
The default Qwen model uses instruct mode (`reasoning_effort="none"`). Provider
availability and account permissions can vary; errors propagate without fallback.

The live demo renders a trusted local HTML fixture on E2B with a random visual
code. The expected code is absent from the model's text prompt. It captures one
PNG and asks the model to read the code and briefly describe the screen, then
checks the code after browser/sandbox cleanup. This helps distinguish actual
visual recognition from answering a familiar fact using prior knowledge. One
matching code is not a benchmark for general desktop competence.

Run from the repository root with E2B_API_KEY and GROQ_API_KEY exported in the
same terminal:

```sh
.venv/bin/python scripts/e2b_vision_demo.py
```

This creates a metered E2B desktop and makes one real Groq call. No website is
browsed; the sandbox denies outbound traffic and keeps public service access
private. Host-side API clients hold the keys. The image goes to the model provider
as request data and is not saved locally by this script. Cleanup is attempted
on failure; successful cleanup calls do not independently prove termination.
The 180-second sandbox lifetime remains the existing fallback.

Override the model using `--model` or `GROQ_VISION_MODEL` with a compatible,
account-accessible vision model. Defaults were checked against the official docs
on November 13, 2026: [Groq image input](https://console.groq.com/docs/vision) and
[Qwen model configuration](https://console.groq.com/docs/model/qwen/qwen3.8-27b).
This is a provisional integration choice, not a measured provider comparison.

Tests inspect image-block structure and byte round-tripping, argument limits,
complete response validation, screenshot authorization, foregrounding before
capture, SDK callback wiring, and cleanup on model errors. They do not establish
real E2B display rendering or model recognition. The live result remains pending.

Local result on November 13, 2026: all 144 Python cases passed, the demo's `--help`
completed, and `git diff --check` passed. No real model or E2B resources were used
during this implementation.

Live attempt exposed a provider-type mismatch before the model request: E2B's
installed filesystem implementation returns `bytearray` for `format="bytes"`,
while Screenshot intentionally accepts immutable bytes. The adapter now converts
bytearray at its provider boundary. Regression tests cover both provider types,
immutability after source-buffer mutation, and rejection of invalid bytearray
image data. All 146 Python cases passed after this fix; live retry is pending.

User-reported live retry succeeded: model `qwen/qwen3.8-27b` read visual code
`7C4F44` from a 1024x768 screenshot. The description also referred to three other
cropped images although only one image was submitted. That claim is unsupported;
successful code recognition does not establish that every description is reliable.
Cleanup returned without an exception, without an independent termination check.

## One bounded scroll

The optional `--scroll` mode adds one host-driven scroll between two observations:

```sh
.venv/bin/python scripts/e2b_vision_demo.py --scroll
```

This uses one desktop and two paid model requests. A tall trusted fixture places
different random codes in its top and bottom panels. The adapter checks the
explicit scroll grant and exact arguments: direction `up`/`down`, integer amount
1–5 (booleans and extra arguments rejected). It foregrounds the tab, moves the
pointer to a fixed browser-content position, then invokes E2B's mouse-wheel API.
The demo scrolls down five wheel steps once and captures again. Neither code is
included in the vision prompt. It requires the first description to contain the
first code and the second to contain the second code without either description
containing the other panel's code.

All 159 Python cases passed, including argument bounds, permission checks,
foreground/pointer ordering, one provider invocation, demo action ordering, and
cleanup after a second model-call failure. No live scroll was performed during
implementation. Wheel displacement depends on browser/desktop settings, and the
fixed pointer position is appropriate only for this fixture, not general window
management. No screenshot captures or model-initiated scroll tools were added to
the text agent's loop. The host chooses this one action; autonomous vision-driven
action selection is a later slice. Existing request interception stays enabled.

Tradeoffs: screenshots lose offscreen information, may capture irrelevant desktop
windows, and incur image-input costs. Foregrounding a tab does not establish a
general multi-window focus policy. Screen instructions remain untrusted; a prompt
reminder is not a security boundary. New computer actions need external authority
checks before they are added. Existing text browsing remains available separately.
