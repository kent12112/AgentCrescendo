# Owning a visible desktop export

An approved letter is data; typing it is a side effect. Keep an immutable approved
snapshot and a separate export record rather than changing the letter's drafting
status. One version can be retried without regenerating its text, and the saved PDF
must match the same snapshot the user approved.

The export worker owns the sandbox and viewer together. Cancellation is a request,
not proof that cleanup finished. The UI reports stopping until the worker closes its
resources; an uncertain cleanup keeps consuming a lease until its provider timer
expires. The database can preserve an export and PDF after a process dies, but it
cannot restore a live in-memory viewer. That limitation is shown as interruption,
with a wait before replacement, rather than calling the local thread durable work.

Observed issues during the November 17 implementation:

- Cookies ignore TCP ports. The original fixed viewer-cookie name meant that a
  second localhost viewer could invalidate the first. A name per viewer port and
  a lifetime bounded to the desktop avoid the collision.
- A reload can open a new WebSocket before the old one finishes closing. A shared
  Boolean event set on connect and cleared on every close can then report false
  while a live connection exists. Count successful connections; failed handshakes
  must not decrement that count. The first real E2B browser attempt exposed this
  readiness race after reload; the corrected run passed.
- The UI's background polling originally cleared an action error on its next
  successful GET. The Start request could return 409 and the explanation disappeared.
  Polling now updates state without erasing action failures. The fake browser smoke
  injects this exact sequence and checks that the error stays visible.
- A terminal database write precedes thread teardown. Starting a replacement in
  that gap could let the old attempt remove the new registry entry. Do not replace
  an attempt while its registry entry exists; remove an entry only if it still
  belongs to that exact runtime object.
- FastAPI's installed version has no `app.add_event_handler`. The test harness
  wraps the application's lifespan instead. A new WebSocket test also initially
  hit the trusted-host check because a relative test URL used `testserver` rather
  than the intended loopback host; use the explicit WebSocket origin to test the
  upstream-failure branch.
- Running a second Next dev server in the same checkout shares its dev lock and
  generated files. The smoke copies frontend source to a temporary directory,
  excludes local environment files, and reuses installed dependencies via a link.

The live acceptance check used a fictional 152-character approved letter. The page
showed real LibreOffice, reconnected after reload, typed the text, visibly exported,
downloaded and checked the PDF, and recorded cleanup. The PDF has one page and all
approved words. This is one pass on the current image, not a reliability benchmark.
Longer/unusual-character letters and toolbar/image upgrades can still fail safely
at the PDF comparison; repeat live checks after upgrades.

## Follow-up: the long Unicode letter (November 17, 2026)

The first short ASCII pass did not exercise the user's real failure. The saved
failed attempt stopped at the greeting, with non-ASCII text in the next chunk;
the old generic message lost its reason. A full-length fictional reproduction
failed with a command exit. A controlled command measured an ASCII guest locale
(`ANSI_X3.4-1968`) and produced `Invalid multi-byte sequence encountered` on smart
punctuation. The same fixed phrase passed with `LC_ALL=C.UTF-8`. Explicit UTF-8
typing preserves the approved text; stripping punctuation would hide the cause.

With that fixed, all 1,094 characters typed in about 16 seconds, but verification
found `front‑end` became `front-end` in the extracted PDF. No other words differed.
The PDF comparator now ignores only U+2011's no-break property, like the line
wrapping already ignored. It still rejects changed numbers, accents, smart quotes,
other dashes, missing spaces, and words. Keep a strict comparison helper for probe
diagnosis so those original differences remain visible.

Performance comes from fewer bounded remote commands (100-character chunks,
20-ms key delay), serialized status polls, background-tab backoff, and skipping
unchanged-state renders. Persist safe phase durations and failure categories so
future work can target measured time, not assumptions. The integrated desktop
pane remains mounted while reviewing sources and can expand to fullscreen. Cold
desktop startup is separate from typing time; this change does not remove that
provider latency or add durable orchestration. See [decision 0013](../decisions/0013-writer-unicode-and-workspace.md).

## Follow-up: watching belongs to drafting

The user pointed out a product error: a well-integrated export screen still appears
too late if the intended experience is watching the letter being drafted. Fix the
sequence in the API lifecycle, not just the location of the iframe. Opening a screen
after the model finished would not establish that drafting happened while watched.

The draft worker now opens/prepares Writer, waits for the connected viewer and
Start drafting, then requests the structured model draft, saves it, types it and
returns it for review. A test holds the worker before Start and proves no model
call occurred. Another holds the model request, stops the worker and proves its
completed text is saved without typing. Preview PDFs are checked then discarded;
approval and final artifacts remain separate. Retrying a failed unchanged preview
reuses its text, while manual edits require approval before export. See
[decision 0014](../decisions/0014-draft-before-approval.md).

Observed UI failure: reopening an approved active export initially selected the
review pane, hiding Start typing despite a connected viewer. A transition to active
Writer now selects the desktop; subsequent deliberate review-pane switches keep
the connection mounted. The isolated browser test covers reload and pane changes.
