# Decision: UTF-8 keyboard commands, measured exports, and a desktop workspace

Date: November 17, 2026. User reported failure after typing started and requested a
more integrated, faster application experience.

## Observed failure

The saved export stopped after the 17-character greeting of a 1,113-character
approved letter. A non-ASCII character occurs in its first body chunk. The old
generic error did not preserve the SDK reason. No personal text was printed or
resent during diagnosis.

A full-length fictional reproduction hit `CommandExitException` (exit 1) on
typographic punctuation. A controlled live test measured `locale charmap` as
`ANSI_X3.4-1968`; the keyboard command reported `Invalid multi-byte sequence
encountered`. The same fixed phrase succeeded with `LC_ALL=C.UTF-8`.

## Implementation decisions

- Explicit UTF-8 locale on every xdotool text command, with one shell-quoted data
  argument and a bounded command timeout. Preserve the approved Unicode text;
  do not strip curly quotes, accented letters, or dashes to bypass the failure.
- Type in 100-character commands at 20 ms per character, replacing the old nested
  50/25-character chunks at 50 ms. This reduces text-command RPC count by up to
  four times for long lines. Cancellation is still checked between bounded chunks.
  Never replay a failed typing command on the same document: its partial effect
  cannot be inferred from an exception.
- Persist only safe failure categories, operation names, phase times, and typing
  throughput in `writer_exports.diagnostics` (migration 0008). Exception messages,
  command bodies, source text, and viewer capabilities do not enter diagnostics.
  Preserve the existing PDF word check; any new comparison behavior must be backed
  by inspected fictional artifacts and remain strict about the actual words.
- The full Unicode test typed all 1,094 characters, then exposed a second issue:
  the extracted PDF contains `front-end` for approved `front‑end` (U+2011). Every
  other word, smart quote, accent, and dash matched. PDF comparison now ignores
  only that hyphen's no-break property, in addition to existing whitespace/page
  wrapping differences. It does not undo AutoCorrect or normalize other dashes,
  quotes, accents, letters, or numbers. Regressions reject each of those changes.
  The captured fictional ODT's text matches the approved Unicode exactly, including
  U+2011: the difference is in PDF export, not lost keyboard input.
- Approved letters default to a wide Live desktop pane. Letter & sources stays
  available without unmounting an active viewer. Controls, real progress, connection
  status, fullscreen, and saved output belong in the same stage. Completed model
  inputs collapse; pending/failed drafting keeps its retry controls available.
- Serial polling avoids overlapping reads, discards reads superseded by an action,
  skips identical-state rerenders, and backs off for a background document. These
  changes do not fabricate desktop progress or replace explicit Start typing.

Keep the lifecycle/privacy limits in decision 0012: approved snapshot only, offline
network gate, private viewer, bounded provider lifetime, verified PDF persistence,
and single-process recovery limitations. A short ASCII pass is no longer sufficient
acceptance evidence for the writing path; use a full-length Unicode letter.

Final live fixture: 1,094 characters, typing 15.334 s (71.3 characters/s), total
79.512 s including opening 7.468 s, preparing 38.166 s, viewer/reload wait 8.502 s,
export 8.372 s, cleanup 1.670 s. One-page 16,072-byte PDF saved and cleanup confirmed.
The older ASCII test alone did not establish this behavior. Cold preparation is
still the largest measured phase; no claim of removing that latency.
