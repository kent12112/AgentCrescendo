# Handoff: JOB-P01 writer desktop probe

- Date/time and timezone: November 17, 2026, 17:58 EST
- Author / session: Claude (VS Code session)
- Intended recipient: the user, for a live run; review requested, not an assignment
- Base commit: `e8843ca`
- Change commit(s), or uncommitted paths: uncommitted `scripts/e2b_writer_probe.py`,
  `packages/agent_runtime/tests/test_writer_probe.py`, this handoff, status
- State: complete. Run 4 passed, and the follow-up (AutoCorrect off, visible
  export, 50 ms typing) passed in run 5; both runs by the user
- Ownership: released

## Goal and acceptance criteria

Find out, before designing the cover-letter writer, whether an E2B desktop with
**no internet** can type a letter visibly into LibreOffice Writer and hand the host
a PDF. Design idea: the letter is drafted and checked on the host; a separate,
offline desktop only types it (the visible part), so resume-derived text can leave
only as the PDF the host downloads (consistent with
[decision 0007](../decisions/0007-job-search-scenario.md) point 5).

Pass = all eight steps ok in `result.json`: network blocked, LibreOffice present,
Writer window, typing, GUI save, PDF conversion, download is a PDF, PDF text keeps
the typed words (AutoCorrect typography allowed and reported).

## Changes and decisions

- `scripts/e2b_writer_probe.py`: creates a desktop with `deny_out: 0.0.0.0/0` and no
  allowlist, then runs the steps; kills the desktop in `finally` (E2B kill timer
  300 s as backstop). No model calls; fixed fictional letter. Evidence goes to
  `.demo-artifacts/writer-probe-<id>/` (screenshots, `letter.pdf`, `pdf-text.txt`,
  `result.json`).
- Typing uses the SDK's `write` (xdotool, chunks of 25, 20 ms per character by
  default instead of the SDK's 75 ms). Tunable with `--delay-ms` / `--chunk-size`.
- Save is visible (Ctrl+S, path typed into the dialog); PDF export uses
  `soffice --headless --convert-to pdf` with a separate profile, because the open
  Writer window locks the default profile. A visible File → Export as PDF is not
  tried yet.
- `--install` exists only in case LibreOffice is missing: it adds Ubuntu's package
  servers to the allowlist by name. The real feature should use a custom template
  with Writer preinstalled so the writer desktop needs no network at all.

## Evidence

Local only:

- `.venv/bin/python -m pytest -q` → 781 passed, 4 skipped. The 11 new tests cover
  network settings, the text comparison (PDF line breaks, AutoCorrect vs. lost
  keys) and the PDF byte check.
- The first test run caught two script bugs, both fixed: `network_config` returned
  a shallow copy that shared the constant's `deny_out` list, and the AutoCorrect
  undo mapped an en dash to `-` instead of `--`.
- `--help` parses.

Live run 1 (user, `--watch`, sandbox `ietiys9vg3myy3x3kjou2`, evidence
`.demo-artifacts/writer-probe-b824bdf49687/`): **stopped at `network`** after
20.0 s with the SDK's `TimeoutException`. The guest's `urlopen(..., timeout=5)`
never returned; most likely the DNS lookup, which socket timeouts don't cover,
kept retrying against a blocked resolver. This is not evidence of reachability,
but the check measured nothing. Desktop killed; nothing later ran.

Fix (local only, 790 passed):
- The network step now runs four checks inside the guest in parallel threads
  (DNS lookup of example.com; TCP to `8.8.8.8:443`, `8.8.8.8:53`, `1.1.1.1:443`)
  with one shared 6 s deadline, under guest `timeout 15`, and a 30 s host limit.
- Pass only if every check is blocked or still timing out. Missing or unknown
  results fail as "not measured".
- `8.8.8.8` was added because the [preflight](../e2b-preflight.md) found it open on
  all ports in allowlist mode. The SDK docstring says DNS servers are opened only
  when `allow_out` names a domain, so this mode should block it; run 2 will show.
- `--install` now also passes `dns_servers: []` and writes the mirror names into
  `/etc/hosts` (`192.0.2.1`; E2B routes allowed names by name, as measured in
  W1-F10).

Live run 2 (user, `--watch`, sandbox `ifj3nwmphrrjrczelh187`, evidence
`.demo-artifacts/writer-probe-46f253a8b8c5/`): **stopped at `network`** in 6.2 s,
with DNS lookup `timeout` and TCP connect "reachable" to `8.8.8.8:443`,
`8.8.8.8:53` and `1.1.1.1:443`. **Judged a false alarm, not a leak**: this repeats
the preflight's recorded mistake. E2B's proxy accepts every TCP connection and
judges it afterwards, so a TCP connect proves nothing. My error: the preflight
notes say so explicitly.

Fix (local, 793 passed):
- Judged checks are now server-proven answers only, as in the preflight: system DNS
  lookup of example.com; a UDP DNS question to `8.8.8.8` and to `1.1.1.1` (reply must
  carry our random ID); a TLS handshake verified for `dns.google` on `8.8.8.8` and
  for `one.one.one.one` on `1.1.1.1`.
- A certificate for the wrong name (`other_answer`) fails. TCP connects are kept
  under `info` only.
- Positive control, local: the same guest program run on the developer Mac (open
  network) reported `answered` for all five checks and `connected` for both TCP
  infos. So the proofs detect real answers; a `blocked` on E2B means no answer.
- Not proven: the E2B guest's Python and CA bundle behave like the Mac's. A
  missing CA bundle would give `other_answer`, which fails safe.

Live run 3 (user, `--watch`, sandbox `ithbzdqw1gtqoncok496i`, evidence
`.demo-artifacts/writer-probe-8684483f6c5c/`): **7 of 8 steps ok; stopped at
`compare`**.

| Step | Result |
| --- | --- |
| network (11.2 s) | All five server proofs blocked: TLS `SSLEOFError`, UDP DNS `TimeoutError`, lookup timeout. TCP connects to both IPs "connected" (info only), confirming the proxy behavior |
| office | LibreOffice 7.3.7.2 **preinstalled** in E2B's desktop image; no `--install` needed |
| launch (27.3 s) | Writer window at 1024x768 |
| type | 657 characters in 10.1 s (64.9/s) at 20 ms, chunks of 25 |
| save (4.3 s) | Ctrl+S, typed path, Enter: `letter.odt` written |
| pdf / download | 15,871-byte PDF, one page |
| compare | **Failed, correctly**: every line break was lost |

On the compare failure, `2-typed.png` and pypdf's layout extraction both show
one wrapped paragraph: all words present, but "Riveraalex.rivera@…", "2026Hiring".
The SDK's `write()` passes `\n` through to `xdotool type` (its shell quoting keeps
it), and Writer ignored it. Assumed cause, not verified: xdotool sends a Linefeed
keysym rather than Return. AutoCorrect was visible as expected (curly quotes,
`--` → en dash) and was correctly separated by the undo map.

Fix (local, 796 passed): `typing_plan` splits the letter into lines; each line is
typed with `write()`, and the real Return key is pressed between lines with
`press("enter")`. Tests check that the plan never sends `\n` as text and that it
rebuilds the original exactly.

Live run 4 (user, `--watch`, sandbox `ihtdc1fe90reotci0c9rj`, evidence
`.demo-artifacts/writer-probe-876026b613ed/`): **PASSED**, all 8 steps, 104.9 s in
total.
- Network: same five blocked proofs as run 3.
- Typing: 657 characters in 12.1 s (54.4/s, slightly slower with the per-line
  Enter calls). Launch took 31 s.
- Compare: only AutoCorrect typography differed (`I'm` → `I’m`, curly quotes,
  `--` → en dash).
- The PDF, inspected visually, is one page with every line and blank line intact.
  AutoCorrect also turned the email address into a hyperlink.

Conclusion: an E2B desktop with no reachable server can type a letter visibly in
Writer and return a PDF only through E2B's file API, with no image changes. One
probe pass, not a reliability measure.

Not covered: visible File → Export as PDF (headless converter used); disabling
AutoCorrect (needed if exact text matters); letters longer than one page;
formatting such as bold or headings; the 31 s launch (startup cost, not optimized).

## Follow-up (user request): AutoCorrect off, visible export, slower typing

Local only; **no live run yet**.
- **AutoCorrect off (default now):** Writer starts with a fresh settings folder
  (`-env:UserInstallation=file:///home/user/writer-profile`). It is seeded with a
  `registrymodifications.xcu` that sets these to false: the Common AutoCorrect
  options (quotes, dashes, URL links, capitalization, replacement table, …), Writer
  word completion, and the Tip of the Day.
  - The setting names are from memory. The `office` step checks each one against
    the guest's `main.xcd` and reports any that are missing.
  - The compare step now requires an exact word match; only `--autocorrect` keeps
    the old tolerant mode.
- **Visible PDF export:** clicks "Export Directly as PDF" at (160, 96), measured
  from run 3's screenshot. The screen is pinned to 1024x768 for that reason. Then
  it types the path and presses Enter.
  - If no PDF appears within 20 s, the hidden converter runs and the run is
    reported as NOT PASSED, with screenshots `5-export-dialog.png` and
    `6-export-failed.png`.
  - The coordinate is fragile: any toolbar or resolution change breaks it.
- **Typing:** default delay 50 ms per character (was 20).
- Tests: 27 for the probe. Full suite: one unidentified failure in one run
  (813 total), then three clean runs of 813 passed. The test count grew during the
  session (other JOB-F06 work), so the failure may not involve this probe;
  unconfirmed.

Live run 5 (user, `--watch`, evidence `.demo-artifacts/writer-probe-fd3760cc77ce/`):
**PASSED**.
- All settings names were found in the guest schema.
- Typing: 657 characters in 22.0 s (29.9/s) at 50 ms.
- `pdf_export: visible`: the toolbar click and typed path wrote the PDF.
- The PDF text matched the typed letter word for word, so AutoCorrect really was
  off.

One pass; the toolbar coordinate remains the fragile part.

## Open issues and next action

Next: `python scripts/e2b_writer_probe.py --watch` (add `--install` if the office
step reports LibreOffice missing). Questions the run answers: is Writer
preinstalled; real characters per second, including per-call overhead; whether a
first-run dialog steals focus; whether AutoCorrect changes the text; whether
`allow_out` by name works for apt over HTTP (only with `--install`).
