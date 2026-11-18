"use client";

import { useEffect, useState, type FormEvent } from "react";
import * as api from "./api";
import { JobShell } from "./job-shell";
import { APPLICATION_STATUS, type Application, type ApplicationStatus } from "./types";
import styles from "./jobs.module.css";

const message = (error: unknown) => error instanceof Error ? error.message : "The request could not be completed.";
const key = (row: Application) => `${row.source}:${row.posting_id}`;
const dateLabel = (day: string | null) => day ? new Date(`${day}T12:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : "Not recorded";

function ApplicationCard({ row, onSave, onRemove }: {
  row: Application; onSave: (row: Application) => void; onRemove: (row: Application) => void;
}) {
  const [status, setStatus] = useState(row.status);
  const [appliedOn, setAppliedOn] = useState(row.applied_on ?? "");
  const [followUp, setFollowUp] = useState(row.follow_up_on ?? "");
  const [notes, setNotes] = useState(row.notes);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const dirty = status !== row.status || appliedOn !== (row.applied_on ?? "") || followUp !== (row.follow_up_on ?? "") || notes !== row.notes;
  const due = row.follow_up_on && row.follow_up_on <= api.today() && !["offer", "rejected", "withdrawn"].includes(row.status);

  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  async function save(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true); setError("");
    try {
      onSave(await api.saveApplication(row, { status, applied_on: appliedOn || null,
        follow_up_on: followUp || null, notes, version: row.version }));
    } catch (caught) { setError(message(caught)); }
    finally { setBusy(false); }
  }

  async function remove() {
    if (busy || !window.confirm(`Remove ${row.posting.company} from your tracker? This removes its saved notes and dates.`)) return;
    setBusy(true); setError("");
    try { await api.deleteApplication(row); onRemove(row); }
    catch (caught) { setError(message(caught)); }
    finally { setBusy(false); }
  }

  return <article className={styles.applicationCard} aria-label={`${row.posting.title} at ${row.posting.company}`}>
    <div className={styles.headingRow}>
      <div><p className={styles.company}>{row.posting.company}</p><h2>{row.posting.title}</h2></div>
      <span className={styles.applicationBadge}>{APPLICATION_STATUS[row.status]}</span>
    </div>
    <p className={styles.facts}>Applied {dateLabel(row.applied_on)} · {row.posting.locations.join(" · ") || "Location not stated"}</p>
    {row.follow_up_on && <p className={due ? styles.followUpDue : styles.facts}>{due ? "Follow-up due" : "Follow up"} · {dateLabel(row.follow_up_on)}</p>}
    {row.notes && <p className={styles.applicationNotes}>{row.notes}</p>}
    <div className={styles.row}>
      <a href={row.posting.url} target="_blank" rel="noopener noreferrer" className={styles.linkButton}>View original posting</a>
      {row.posting_state !== "open" && <span className={styles.small}>{row.posting_state === "closed" ? "Posting closed" : "Posting no longer in search"} · snapshot saved</span>}
    </div>
    <details className={styles.applicationEdit}>
      <summary>Update application</summary>
      <form className={styles.panel} onSubmit={event => void save(event)}>
        <div className={styles.applicationFields}>
          <label>Status<select aria-label="Application status" value={status} onChange={event => setStatus(event.target.value as ApplicationStatus)} disabled={busy}>
            {Object.entries(APPLICATION_STATUS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select></label>
          <label>Applied date<input type="date" required={status !== "ready"} value={appliedOn} onChange={event => setAppliedOn(event.target.value)} disabled={busy} /></label>
          <label>Follow-up date<input type="date" value={followUp} onChange={event => setFollowUp(event.target.value)} disabled={busy} /></label>
        </div>
        <label>Notes<textarea value={notes} maxLength={8000} disabled={busy} onChange={event => setNotes(event.target.value)} placeholder="Contact, next steps, interview notes…" /></label>
        <div className={styles.row}>
          <button type="submit" className="primary" disabled={busy || !dirty}>{busy ? "Saving…" : "Save changes"}</button>
          <button type="button" className={styles.linkButton} disabled={busy} onClick={() => void remove()}>Remove from tracker</button>
        </div>
        {error && <p className="error" role="alert">{error}</p>}
      </form>
    </details>
    <details className={styles.snapshot}><summary>Saved job description</summary><p>{row.posting.description || "No description was provided."}</p></details>
  </article>;
}

export default function ApplicationTracker() {
  const [rows, setRows] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [status, setStatus] = useState("all");
  const [query, setQuery] = useState("");

  useEffect(() => {
    let cancelled = false;
    void api.getApplications().then(data => { if (!cancelled) setRows(data.applications); })
      .catch(caught => { if (!cancelled) setError(message(caught)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const visible = rows.filter(row => (status === "all" || row.status === status)
    && `${row.posting.title} ${row.posting.company} ${row.notes}`.toLowerCase().includes(query.trim().toLowerCase()));
  const due = rows.filter(row => row.follow_up_on && row.follow_up_on <= api.today()
    && !["offer", "rejected", "withdrawn"].includes(row.status)).length;

  return <JobShell active="applications"><div className={styles.trackerPage}>
    <div className={styles.headingRow}><div><p className="eyebrow">YOUR JOB SEARCH, IN ONE PLACE</p>
      <h1>Your applications.</h1><p className={styles.lede}>Keep the dates, conversations, and next steps together.</p></div>
      <a className={styles.secondary} href="/jobs">Find jobs</a>
    </div>
    <div className={styles.trackerStats} aria-label="Application summary">
      <span><strong>{rows.length}</strong> tracked</span>
      <span><strong>{rows.filter(row => row.status === "interviewing").length}</strong> interviewing</span>
      <span><strong>{rows.filter(row => row.status === "offer").length}</strong> offers</span>
      <span><strong>{due}</strong> follow-ups due</span>
    </div>
    <div className={`${styles.panel} ${styles.trackerFilters}`}>
      <label>Find an application<input type="search" value={query} onChange={event => setQuery(event.target.value)} placeholder="Company, role, or notes" /></label>
      <label>Status<select aria-label="Filter by status" value={status} onChange={event => setStatus(event.target.value)}><option value="all">All statuses</option>
        {Object.entries(APPLICATION_STATUS).map(([value, label]) => <option key={value} value={value}>{label} ({rows.filter(row => row.status === value).length})</option>)}
      </select></label>
    </div>
    {notice && <p className={styles.notice} role="status">{notice}</p>}
    {error && <p className="error" role="alert">{error} <button type="button" onClick={() => window.location.reload()}>Retry loading</button></p>}
    {loading && <p className={styles.empty} role="status">Loading applications…</p>}
    {!loading && !error && !rows.length && <div className={styles.empty}><h2>A little less to keep in your head.</h2>
      <p>After applying to a role, select “Mark applied” in job search. Your application and a copy of the posting will be saved here.</p>
      <a className={styles.secondary} href="/jobs">Browse Ashby jobs</a></div>}
    {!loading && rows.length > 0 && !visible.length && <p className={styles.empty}>No applications match these filters.</p>}
    <div className={styles.applicationList}>{visible.map(row => <ApplicationCard key={`${key(row)}:${row.version}`} row={row}
      onSave={saved => { setRows(current => [saved, ...current.filter(item => key(item) !== key(saved))]); setNotice(`Saved ${saved.posting.company}.`); }}
      onRemove={removed => { setRows(current => current.filter(item => key(item) !== key(removed))); setNotice(`Removed ${removed.posting.company} from the tracker.`); }} />)}</div>
    {rows.length > 0 && <p className={styles.small}>Changes are saved on this machine. Follow-up dates appear here; no reminders are sent.</p>}
  </div></JobShell>;
}
