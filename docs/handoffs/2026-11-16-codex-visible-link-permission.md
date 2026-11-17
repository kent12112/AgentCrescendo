# Handoff: READ-VISIBLE-LINKS — explicit metadata permission

- Date/time and timezone: November 16, 2026, America/New_York.
- Author / session: Codex, user-requested permission clarity change.
- Intended recipient: user; future review session (not an assignment).
- Base commit: `f337055856f028c85aeca91decaa69ed8108ccdb`.
- Changes: uncommitted; desktop adapter, security policy, click demo/check grants,
  policy/click/source-loading tests, clicking guide, learning record 13, status,
  and this handoff. Existing uncommitted clicking and recovery work preserved.
- State: complete for the requested permission change.
- Ownership: released.

## Goal and acceptance criteria

The user found `ToolCall("screenshot")` confusing inside `visible_links()`, which
reads DOM metadata without taking an image. Use an explicit `read_visible_links`
permission and keep existing demo modes working. Track as READ-VISIBLE-LINKS in
[status](../status.md); Week 1 scope and live evidence gates remain unchanged.

## Changes and decisions

- `visible_links()` authorizes `ToolCall("read_visible_links")`; it still requires
  click permission and clears previous snapshot IDs before any refusal.
- Policy requires the explicit grant and rejects arguments to this metadata read.
  Screenshot permission no longer grants access to link metadata. Screenshot
  capture continues to check its own permission.
- The click demo grants metadata reading only in link mode. The model-free live
  check also grants it because it exercises link inventory and resolution.
- No model-facing tool or JavaScript geometry changes. Existing point, target,
  and network checks continue to protect clicks. Custom callers of
  `visible_links()` must now explicitly include `read_visible_links` in their
  task grant; screenshot capture remains separately authorized.
- Updated [clicking guide](../e2b-clicking.md) and
  [learning record](../learning/13-link-grounding.md) to distinguish authorizing
  an operation from executing it. No observed implementation failures this turn.

## Evidence

Local, with fake browser/provider objects:

```sh
.venv/bin/python -m pytest -q packages/security/tests/test_policy.py packages/agent_runtime/tests/test_click.py packages/agent_runtime/tests/test_click_source_loading.py
.venv/bin/python -m pytest -q
git diff --check
```

Focused: 115 passed. Full: 402 passed with one existing Starlette/httpx
deprecation warning. Whitespace check passed. Checks cover missing metadata or
click permission before browser inspection, stale-ID invalidation on refusal,
metadata reads without screenshot permission or capture, unexpected arguments,
and demo grants in both link and coordinate modes.

No E2B/Groq calls or new live browser evidence. Local tests establish the
permission contract, not live geometry or model reliability.

## Open issues and next action

No required work remains for this request. Handoff ready for review; no review
assignment or acknowledgment assumed. No commit or push made.
