# Decision: show the real Writer desktop during drafting

Date: November 17, 2026. User corrected the interaction: live watching belongs
when drafting the letter, before approval. This supersedes the ordering in 0012,
while retaining its final-export and desktop lifecycle boundaries.

- The web drafting action opens a private offline Writer first. The user sees the
  blank document and chooses **Start drafting**. Only then does the host call Groq
  with the confirmed redacted sources. The actual generated draft is typed on that
  same visible desktop, checked against the Writer PDF, then presented for review.
  The structured model result is validated before typing; this is not token-level
  streaming or a visual model choosing individual keystrokes. No animation stands
  in for the E2B screen.
- Consent explains both Groq drafting and the generated draft's E2B preview. The
  resume, source documents, model credentials and supplied identity stay off the
  desktop. Draft signatures retain `[NAME]`. Approval still fills the name locally;
  final text/PDF downloads require approval. Previously confirmed sessions start a
  live run only through an explicit drafting action with the E2B explanation shown.
- Reuse the bounded Writer manager with a persisted `purpose` (`draft` or `export`)
  and `drafting` phase (migration 0009). The model call runs after preparation,
  connected viewer and explicit begin. Generation and desktop ownership share the
  letter row lock and expected version. The legacy synchronous generation endpoint
  refuses an active live draft. All versions of a letter share its cleanup gate.
- Save text/checks immediately after a complete model result. The letter stays
  `generating` until the desktop finishes, fails or stops, preventing mid-typing
  edits/approval. A desktop failure or Stop after model completion retains the draft
  for review; retrying its unchanged preview never makes another model call. Stop
  before generation makes no model call. Stop during a bounded model request waits
  for its return, keeps completed text and does not start typing afterward.
- Draft PDFs are used for verification, then discarded. They cannot be downloaded
  from final-export endpoints. An approved export snapshots the current reviewed
  version independently. Manual draft edits cannot be sent through the generated-
  preview retry path; approve them before final export.
- The UI opens the desktop when drafting, returns to review on completion, and
  shows **Draft live → Review & approve → Final PDF** in that order. Active desktops
  recover on reload and remain mounted when reviewing sources. The browser starts
  up to three letters sequentially; leaving stops starting later letters, while the
  active API-owned worker continues. Reopen and continue the remaining jobs.

This remains a single-process bridge with bounded leases, not durable Temporal
scheduling. Restart loses the viewer; replacement waits for lease expiry. A crash
after a model response but before persistence can still cause a repeat request.
No independent company browsing, application submission or retention policy added.
