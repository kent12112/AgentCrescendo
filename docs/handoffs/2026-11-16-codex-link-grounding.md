# Handoff: W1X-F01 — fix model-selected link clicking

- Date/time and timezone: November 16, 2026, America/New_York.
- Author / session: Codex, user-requested aiming diagnosis and fix.
- Intended recipient: user; future review session (not an assignment).
- Base commit: `f337055856f028c85aeca91decaa69ed8108ccdb`.
- Changes: uncommitted. Updated `crescendo_agent/{e2b_desktop,vision,vision_loop}.py`,
  added `crescendo_agent/link_grounding.py`, extended `test_click.py` and
  `test_vision_tokens.py`, updated `scripts/e2b_click_{demo,check}.py` and
  clicking/plan/status docs; added decision 0002 and learning record 13.
  Several of those files already contained Claude's uncommitted F01 work;
  original pointer, gateway, adapter, and network behavior was preserved.
- State: complete for DOM-assisted link selection; ready for review.
- Ownership: released by Codex. User explicitly authorized taking over the
  earlier Claude claim. No agents were spawned and Claude was not launched.

## Goal and acceptance criteria

Make the model choose and follow the Massachusetts link on Wikipedia's Boston
page with the actual desktop pointer, then verify browser navigation and answer.
Preserve the original click restrictions. The model-facing interface adjustment
is explicit in [W1X-F01](../implementation-plan.md) and
[decision 0002](../decisions/0002-visible-link-grounding.md).

## Changes and decisions

- Added opt-in `click_link(target_id)`, with screenshot plus at most 120 visible
  link labels/IDs. No target URLs or selectors are sent to the model. The browser
  keeps element references and measured points privately.
- IDs expire at the next observation and are never reused within a desktop.
  Re-resolution rejects detached elements, changed labels/destinations, fully
  transparent elements, and points now hitting a different element.
- The selection resolves to the existing real-screen `click(x, y)` path. The
  gateway still requires the click grant/page area, the adapter still checks the
  target, and the request filter/firewall still check navigation. Screenshot
  downscaling does not rescale an already measured screen point.
- The click demo defaults to link IDs. `--click-mode coordinates --grid` retains
  the original experiment. Other vision demos keep their original tool sets.
- Full audit traces preserve every inventory; only the latest list goes to the
  model. The click demo opts into a one-retry provider wait of at most 60 seconds,
  within the unchanged 120-second deadline. Other demos keep 15 seconds.

This fixes the task by adding DOM assistance; it does not repair the model's raw
pixel-grounding ability. Inventory/capture/check/press is not an atomic operation.
The inventory currently covers visible HTML text links, not all GUI controls.

## Evidence

Local final checks:

```sh
.venv/bin/python -m pytest -q
git diff --check
```

334 tests passed; one existing Starlette/httpx deprecation warning. Diff check
passed. Tests cover ID opt-in, expiration, malformed selection, no double scaling,
ungranted clicks, page boundaries, adapter refusals, context pruning, and bounded
retry/deadline behavior. Local Chromium is not installed, so actual DOM/geometry
checks were performed on E2B rather than claimed from mocks.

Approved live checks (metered E2B/Groq, `qwen/qwen3.8-27b`):

```sh
.venv/bin/python scripts/e2b_click_demo.py --save-screenshots --max-steps 3
.venv/bin/python scripts/e2b_click_demo.py --save-screenshots --max-steps 3 --image-width 1024
.venv/bin/python scripts/e2b_click_check.py
```

- 768 px: complete PASS, 23.6 s including a 17 s provider retry. ID 39 resolved
  to `(317, 602)`, actual Boston → Massachusetts navigation, final answer
  “Massachusetts”. Artifact: `.demo-artifacts/click-d58d76be4de54f21a4378c5686dab9bb/`.
- 1024 px: complete PASS, 24.0 s including an 18 s retry. Same selected link and
  point, recorded navigation and final answer.
  Artifact: `.demo-artifacts/click-67b0c448c6c74c12b3ee111d618a7f9f/`.
- The saved post-click model-input PNG was visually inspected and shows the
  Massachusetts article. Artifacts are ignored and were not committed.
- Final model-free E2B fixture: all 23 checks passed, including all original
  restrictions plus visibility, stale targets, ID expiration, and grounded
  navigation. Ran twice during development; final run includes transparency.

Observed failures retained:

- Initial sandboxed Groq replay could not resolve its network destination.
  Automatic approval review then rejected uploading full desktop screenshots
  without explicit payload/destination approval. User explicitly approved saved
  Boston screenshot uploads and bounded E2B/Groq tests; subsequent runs succeeded.
- Saved 768×576-image replay: explicit pixels produced `(215, 301)`; normalized
  0–1000 produced `(327, 570)` → image `(251, 328)`. Target near `(238, 451)`;
  both missed. Removed the unsuccessful normalized prototype. These are model
  inference replays, not fresh desktop runs.
- An intermediate prototype broke five malformed-response tests by requiring
  image dimensions even in non-click mode. Removed with the prototype; final
  suite passes without changing those existing tests.
- First grounded run hit `(317, 602)` and opened the correct article, but its
  final answer was throttled. Full-demo FAIL, not a pass.
  Artifact: `.demo-artifacts/click-31af50656a494c638f2f54098952743d/`.

## Open issues and next action

No required work remains for this fix. Raw screenshot-only pixel aiming remains
unreliable. Two complete runs on one task are not a reliability benchmark.
Network work W1-3 still gates broad browsing, and the existing calibrated page
geometry, new-tab, and request-filter limitations remain documented in
[clicking](../e2b-clicking.md). No commit or push was made.
