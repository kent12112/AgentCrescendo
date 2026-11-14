# Annotated reading copies: the F07 vision run

Line-by-line commented copies of the code on the model-selected scroll path
(plan W1-F07), written November 13, 2026 against `9130a21` plus the working tree.
They are for reading only: nothing imports or runs them, and they will drift when
the real code changes. The real source is the authority.

Read them in the order a run executes:

1. [Demo script](1_e2b_vision_agent_demo.py) — builds the test page and grant, runs the loop, grades the answer.
2. [Vision loop](2_vision_loop.py) — screenshot, model proposal, permission check, scroll or finish.
3. [Vision model adapter](3_vision.py) — sends one screenshot plus history to Groq and parses one tool call.
4. [Permission check](4_policy.py) — `authorize()`: tool allowlist and argument rules.
5. [E2B desktop](5_e2b_desktop.py) — cloud desktop setup, firewall, Chrome relay, screenshot, scroll, cleanup.
   Only the vision-path parts are copied; source line numbers are shown in `[brackets]`.

File 5 shows the pointer fix: `page.mouse.move` did not move the real desktop
pointer that E2B's scroll uses (live-checked), so `scroll()` now moves it with
E2B's `move_mouse` first.

Out of date since W1-6 (November 13, 2026): `vision.py` gained `downscale()`,
`RateLimited`, and a split `decide()`; `vision_loop.py` gained image downscaling
and bounded rate-limit retry; `e2b_desktop.py` gained stylesheet filtering,
`wait_until="load"`, and `lifetime_seconds`; `vision.py` also gained `Proposal`
and reasons; `wait_for_viewer` moved to `live_view.py`. Refresh the copies after review.
