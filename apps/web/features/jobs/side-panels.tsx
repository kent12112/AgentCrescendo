"use client";

import styles from "./jobs.module.css";
import { MAX_PICKS, type Pick, type ResumeInfo } from "./types";

export function ResumeBox({ resume, uploading, onUpload, onRemove }: {
  resume: ResumeInfo | null | undefined; uploading: boolean; onUpload: (file: File) => void; onRemove: () => void;
}) {
  const input = (label: string) => (
    <label className={styles.uploadButton}>
      {uploading ? "Reading…" : label}
      <input aria-label="Upload resume" type="file" accept=".pdf,.txt,.md,application/pdf,text/plain,text/markdown" disabled={uploading}
             onChange={event => { const file = event.target.files?.[0]; if (file) onUpload(file); event.target.value = ""; }} />
    </label>
  );
  if (resume === undefined) return <section className={styles.panel}><p className={styles.muted}>Loading…</p></section>;
  if (resume === null) {
    return (
      <section className={styles.panel} aria-labelledby="resume-title">
        <h2 id="resume-title">Your resume</h2>
        <p>Upload a PDF, text, or Markdown resume to rank jobs locally. Up to 10 MB.</p>
        {input("Upload resume")}
      </section>
    );
  }
  return (
    <section className={styles.panel} aria-labelledby="resume-title">
      <h2 id="resume-title">Your resume</h2>
      <p className={styles.resumeName}>{resume.filename}</p>
      <p className={styles.muted}>{resume.skills.length} skills found · uploaded {new Date(resume.uploaded_at).toLocaleDateString()}</p>
      <details className={styles.skillList}><summary>Skills used for scoring</summary><p>{resume.skills.join(", ") || "none found"}</p></details>
      <div className={styles.row}>{input("Replace")}<button type="button" disabled={uploading} className={styles.linkButton} onClick={onRemove}>Remove</button></div>
      <p className={styles.small}>Extracted text is saved locally; the uploaded file is not kept.</p>
    </section>
  );
}

export function PicksTray({ picks, busy, ready, onRemove, onClear }: { picks: Pick[]; busy: boolean; ready: boolean; onRemove: (pick: Pick) => void; onClear: () => void }) {
  return (
    <section className={`${styles.panel} ${styles.tray}`} aria-labelledby="picks-title">
      <h2 id="picks-title">Research shortlist <span className={styles.muted}>({picks.length}/{MAX_PICKS})</span></h2>
      <ol className={styles.slots}>
        {picks.map(pick => <li key={`${pick.source}:${pick.posting_id}`}>
              <span><strong>{pick.title}</strong><br /><small>{pick.company}{pick.closed ? " · closed" : ""}</small></span>
              <button type="button" className={styles.remove} disabled={busy} onClick={() => onRemove(pick)} aria-label={`Remove ${pick.title}`}>✕</button>
            </li>)}
      </ol>
      {picks.length > 0 && ready && !busy && !picks.some(p => p.closed)
        ? <a href="/jobs/letters?new=1" className={`primary ${styles.actionLink}`}>Craft Why-company answers</a>
        : <button type="button" className="primary" disabled>Craft Why-company answers</button>}
      {(picks.some(p => p.closed) || !ready) && <p className={styles.small}>{picks.some(p => p.closed) ? "Remove closed postings before continuing." : "Upload a resume before drafting."}</p>}
      {picks.length > 0 && <button type="button" className={styles.linkButton} disabled={busy} onClick={onClear}>Clear picks</button>}
    </section>
  );
}
