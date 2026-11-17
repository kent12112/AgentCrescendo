# Handoff: W1X-F03 — open browsing (model navigate + type_text)

- Date/time and timezone: November 17, 2026, America/New_York.
- Author / session: Claude, VS Code session; no delegation.
- Intended recipient: the user (review requested, as senior reviewer); not an assignment.
- Base commit: `e8843ca`. W1X-F02, W1-F10, and W1-F13 work is still uncommitted
  in the same tree, so `git diff` on shared files shows both.
- Uncommitted paths (this task):
  - Changed: `packages/security/crescendo_security/policy.py`,
    `packages/agent_runtime/crescendo_agent/e2b_desktop.py`,
    `link_grounding.py`, `vision.py`, `vision_loop.py`,
    `packages/security/tests/test_public_web.py`,
    `packages/agent_runtime/tests/test_public_web_desktop.py`,
    `docs/decisions/0004-public-web-mode.md` (pointer only),
    `docs/implementation-plan.md`, `docs/status.md`.
  - New: `packages/security/tests/test_type_text.py`,
    `packages/agent_runtime/tests/test_type_text_desktop.py`,
    `packages/agent_runtime/tests/test_open_browsing_loop.py`,
    `packages/agent_runtime/tests/test_open_browse_demo.py`,
    `scripts/e2b_open_browse_demo.py`, `scripts/smoke_type_text_fields.py`,
    `docs/decisions/0005-open-browsing.md`, this handoff.
- State: ready for review; live demo not yet run.
- Ownership: released.

## Goal and acceptance criteria

In public-web mode, the model can open any public site by URL and type into page
text fields (search boxes), never into browser controls. Acceptance: local tests,
then a live run of `scripts/e2b_open_browse_demo.py`. In that run the model
searches Wikipedia by typing, reaches the Boston Common article, opens
boston.gov by `navigate`, and names it. The browser's own records decide the
grade.

## Changes and decisions

See [decision 0005](../decisions/0005-open-browsing.md).

- **Policy.** Public-web `navigate` now goes through `authorize_destination()`.
  New `type_text` rule: exact args, one printable line of at most
  `MAX_TYPED_CHARS = 200` characters, boolean `submit`, point inside the page area.
- **Field listing.** `TEXT_FIELD` defines what counts as a field, shared by
  every check. Fields are listed in `READ_LINK_TARGETS` only when `fieldLimit`
  is above 0 (that is, when `type_text` is granted), and are resolved with
  `RESOLVE_FIELD_TARGET`. Link records keep their `{id, label}` shape. Field
  and link IDs can't be swapped.
- **Desktop adapter.** `type_text()` runs: field check (`FIELD_TARGET`,
  `field_target_problem`), focus emulation off, real click, focus check
  (`FOCUSED_FIELD`), Ctrl+A, write, re-check, Enter. The page-load wait was
  pulled out of `click()` into `_before_action()`/`_after_action()`; click's
  messages are unchanged. `navigate_and_report()` turns load failures into an
  outcome that reports only `net::ERR_*`. Plain `navigate()` keeps raising
  (the existing tests require this). E2B `write`/`press` are wired in
  `open_e2b_desktop`.
- **Model and loop.** `GroqVision(allow_typing=, allow_navigate=)` adds two
  tools. Typing requires link mode, because it relies on field IDs. The loop
  turns a field ID into a screen point, as `click_link` does, and runs
  `type_text`/`navigate`. Adapter refusals come back to the model as denials.

## Evidence

Local:

- `.venv/bin/python -m pytest -q packages`: 567 passed (the existing
  Starlette/httpx warning).
- `.venv/bin/python scripts/smoke_type_text_fields.py` (local Edge, scripts
  disabled): all 16 checks passed.
  - The listing excludes password, disabled, read-only, checkbox, hidden,
    transparent, and covered fields.
  - A framed field and a `target=_blank` form are refused.
  - With Playwright's focus emulation on, `document.hasFocus()` is true even
    for an unfocused window; with it off, it is false. This is why the adapter
    turns emulation off.
- `scripts/smoke_browser_subrequests.py` and `scripts/smoke_redirect_recovery.py`
  passed (regression after the `click()` refactor).

Live: none.

## Open issues and next action

1. **Live run.** Run `.venv/bin/python scripts/e2b_open_browse_demo.py
   --save-screenshots` (metered E2B + Groq). It is the first real test of:
   - the focus check after a real xdotool click. If `hasFocus()` stays false,
     typing is refused, which fails closed but is unusable;
   - E2B `write`/`press` key names (`["ctrl","a"]`, `"enter"`);
   - Wikipedia's search form without scripts.
2. **Address-bar case not tested live.** No test yet focuses the omnibox on E2B
   and confirms that `FOCUSED_FIELD` is false.
3. **Accepted risk.** Model-written text can reach any public site. Revisit
   before tasks carry user data or sign in (0005).
4. **Annotated copies.** `docs/learning/annotated/4_policy.py` and
   `5_e2b_desktop.py` predate this change.
