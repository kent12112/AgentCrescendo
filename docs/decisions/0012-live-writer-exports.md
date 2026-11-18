# Decision: connect approved letters to a bounded offline Writer desktop

Date: November 17, 2026. User explicitly requested the missing E2B live writing
integration after the connected drafting slice in decision 0011.

Superseded ordering: [decision 0014](0014-draft-before-approval.md) moves live watching
into drafting before review/approval, at the user's request. This document still
describes the approved final-export path and shared lease/network/viewer boundaries.

## Boundary and interaction

- A separate export record snapshots one approved letter version. Opening Writer
  requires the current approved version; draft generation and export are separate
  actions. Edits are blocked while the desktop lease is active. Exporting never
  makes a new model call or sends a resume to the desktop.
- Reuse JOB-P01's network/settings/typing/PDF checks in shared helpers. No guest
  outbound allowlist or installation path is enabled. All five server-answer
  network probes must pass before any letter text is typed.
- Open a fresh LibreOffice Writer with AutoCorrect/word completion disabled. The
  user watches through the authenticated loopback noVNC proxy and explicitly starts
  typing once the blank document is visible. A connected transport alone is not
  treated as proof that the user saw a rendered desktop.
- Type actual keyboard text and real Enter keys, visibly save the document, click
  Export Directly as PDF, and download through E2B's file API. No headless export
  fallback. Compare extracted PDF words with the approved snapshot; a mismatch does
  not become a saved PDF. The toolbar coordinate remains image/resolution-dependent.
- Persist verified PDFs in local Postgres (migration 0007). PDF download is independent
  of the live desktop. Status/progress survives page reload; the viewer capability
  stays only in process memory, excluded from ordinary letter/library responses.

## Lease and cleanup ownership

One local API process owns this bridge; it is not durable scheduling. Each worker
owns one sandbox and viewer, handles cancellation, and cleans up in `finally`.
An approved-version row lock, unique version export, attempt number, and process
registry prevent duplicate local starts and stale callbacks. Never replace an
attempt until it has released its registry entry. Retry only after confirmed
cleanup or expiry of the old provider lease.

At most three unexpired desktops/uncertain-cleanup leases are admitted. The E2B
provider timer kills a sandbox after 600 seconds; the persisted lease includes
60 more seconds for creation/cleanup uncertainty. Viewer confirmation is limited
to 90 seconds. Letters are limited to 6,000 characters; typing checks cancellation
between bounded chunks. Provider bodies and private URLs are not logged.

The viewer uses a distinct cookie name per local port: cookies ignore ports, so
the old fixed cookie name could break concurrent localhost viewers. Writer cookies
last for the desktop lifetime. Connected state counts live WebSockets so an older
connection's delayed shutdown cannot clear a new connection. Bootstrap capabilities
are returned only by token-protected status and embedded with no referrer.

After API restart, the in-memory viewer is unavailable and an export is interrupted
until its lease expires. Saved PDFs remain downloadable. No W2 durable Temporal
criterion is marked complete. The run-start workflow remains separate; a later
implementation should move this adapter into owned Temporal activities.

The provider lifecycle/network shape follows the
[E2B SDK](https://github.com/e2b-dev/E2B/blob/main/packages/python-sdk/e2b/sandbox_sync/main.py)
and the live JOB-P01 probe; rerun live checks after image/SDK changes.
