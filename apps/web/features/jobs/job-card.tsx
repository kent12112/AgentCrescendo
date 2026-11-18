"use client";

import styles from "./jobs.module.css";
import { APPLICATION_STATUS, type JobDetail, type JobRow } from "./types";

const WORKPLACE: Record<string, string> = { remote: "Remote", hybrid: "Hybrid", onsite: "Onsite" };

function posted(days: number | null) {
  if (days === null) return "date not stated";
  return days === 0 ? "posted today" : `posted ${days}d ago`;
}

function day(iso: string | null) {
  return iso ? new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" }) : "—";
}

type Props = {
  row: JobRow;
  detail: JobDetail | "loading" | "error" | undefined;
  canPick: boolean;
  busy: boolean;
  onTogglePick: () => void;
  onToggleDetail: () => void;
  onMarkApplied: () => void;
  tracking: boolean;
};

export function JobCard({ row, detail, canPick, busy, onTogglePick, onToggleDetail, onMarkApplied, tracking }: Props) {
  const places = row.locations.slice(0, 3).join(" · ") + (row.locations.length > 3 ? ` +${row.locations.length - 3}` : "");
  const facts = [
    places || "Location not stated",
    row.workplace ? WORKPLACE[row.workplace] ?? row.workplace : null,
    row.compensation,
    row.years_asked !== null ? `asks ${row.years_asked}+ yrs` : null,
    posted(row.age_days),
  ].filter(Boolean);
  const scoreHelp = `Title match ${Math.round(row.title_match * 100)}% · skills on your resume `
    + `${row.matched_skills.length} of ${row.matched_skills.length + row.missing_skills.length}`;
  const open = detail !== undefined;

  return (
    <article className={`${styles.card} ${row.picked ? styles.cardPicked : ""}`}>
      <div className={styles.cardTop}>
        <label className={styles.pick} title={canPick || row.picked ? "Pick for a Why-company answer" : "Remove a pick to add another (3 at most)"}>
          <input type="checkbox" checked={row.picked} disabled={busy || (!row.picked && !canPick)} onChange={onTogglePick}
                 aria-label={`Pick ${row.title} at ${row.company}`} />
        </label>
        <div className={styles.score} title={scoreHelp} aria-label={`Score ${row.score}. ${scoreHelp}`}>{row.score}</div>
        <div className={styles.cardMain}>
          <h3>{row.title} <span className={styles.company}>· {row.company}</span></h3>
          <p className={styles.facts}>{facts.join(" · ")}
            {row.countries.length > 0 && <span> · {row.countries.join(", ")}</span>}
            {!row.country_known && <span className={styles.warn}> · country not stated</span>}
            {row.other_postings > 0 && <span> · also posted {row.other_postings}× elsewhere</span>}
          </p>
          {row.application && <a className={styles.applicationBadge} href="/jobs/applications">{APPLICATION_STATUS[row.application.status]}{row.application.applied_on ? ` · ${row.application.applied_on}` : ""}</a>}
          <p className={styles.skills}>
            {row.matched_skills.map(skill => <span key={skill} className={styles.have}>✓ {skill}</span>)}
            {row.missing_skills.map(skill => <span key={skill} className={styles.gap}>✗ {skill}</span>)}
            {!row.matched_skills.length && !row.missing_skills.length && <span className={styles.muted}>No known skills named</span>}
          </p>
        </div>
        <div className={styles.cardActions}>
          <a href={row.url} target="_blank" rel="noopener noreferrer">View on {row.source === "ashby" ? "Ashby" : row.source}</a>
          {!row.application && <button type="button" className={styles.trackButton} onClick={onMarkApplied} disabled={tracking}>
            {tracking ? "Saving…" : "Mark applied"}
          </button>}
          <button type="button" className={styles.linkButton} onClick={onToggleDetail} aria-expanded={open}>
            {open ? "Hide details ▴" : "Details ▾"}
          </button>
        </div>
      </div>

      {detail === "loading" && <p className={styles.detailNote}>Loading details…</p>}
      {detail === "error" && <p className={styles.detailNote}>Could not load details. <button type="button" className={styles.linkButton} onClick={onToggleDetail}>Retry</button></p>}
      {detail && typeof detail === "object" && (
        <div className={styles.detail}>
          <dl className={styles.meta}>
            <div><dt>All locations</dt><dd>{detail.locations.join(" · ") || "—"}</dd></div>
            <div><dt>Countries</dt><dd>{detail.countries.join(", ") || "not stated"}</dd></div>
            {detail.employment_type && <div><dt>Type</dt><dd>{detail.employment_type.replace(/([a-z])([A-Z])/g, "$1 $2").replace(/^(\w)(.*)$/, (_, a, b) => a + b.toLowerCase())}</dd></div>}
            <div><dt>Seen</dt><dd>first {day(detail.first_seen)} · last crawl {day(detail.last_seen)}{detail.closed_at ? ` · closed ${day(detail.closed_at)}` : " · still open"}</dd></div>
          </dl>
          <p className={styles.legend}><mark className={styles.markHave}>on your resume</mark> <mark className={styles.markGap}>not on your resume</mark></p>
          {/* Posting text is untrusted; it is rendered as text nodes, never as HTML. */}
          <div className={styles.description}>
            {detail.segments.map((segment, index) => segment.kind
              ? <mark key={index} className={segment.kind === "have" ? styles.markHave : styles.markGap} title={segment.skill}>{segment.text}</mark>
              : <span key={index}>{segment.text}</span>)}
          </div>
        </div>
      )}
    </article>
  );
}
