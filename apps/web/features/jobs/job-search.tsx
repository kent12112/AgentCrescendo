"use client";

import type { FormEvent } from "react";
import { JobCard } from "./job-card";
import styles from "./jobs.module.css";
import { PicksTray, ResumeBox } from "./side-panels";
import { MAX_PICKS, type Filters, type HiddenCounts } from "./types";
import { useJobSearch } from "./use-job-search";
import { JobShell } from "./job-shell";

// Each "hidden" count names the filter that removed those jobs and how to show them again.
const HIDDEN: { key: keyof HiddenCounts; label: string; relax: (f: Filters) => Filters }[] = [
  { key: "country", label: "outside the country", relax: f => ({ ...f, country: "" }) },
  { key: "location", label: "outside your cities", relax: f => ({ ...f, cities: "", remote: false }) },
  { key: "senior", label: "senior titles", relax: f => ({ ...f, noSenior: false }) },
  { key: "years", label: "ask for more years", relax: f => ({ ...f, maxYears: "" }) },
  { key: "age", label: "older postings", relax: f => ({ ...f, maxAgeDays: "30" }) },
];

function when(iso: string | null | undefined) {
  if (!iso) return "unknown";
  return new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

export default function JobSearch() {
  const s = useJobSearch();
  const { filters, setFilters, page } = s;
  const set = <K extends keyof Filters>(key: K, value: Filters[K]) => setFilters(current => ({ ...current, [key]: value }));
  const submit = (event: FormEvent) => { event.preventDefault(); void s.runSearch(filters); };
  const relax = (next: Filters) => { setFilters(next); void s.runSearch(next); };
  const canPick = s.picks.length < MAX_PICKS;
  const hidden = page ? HIDDEN.filter(h => page.hidden[h.key] > 0) : [];

  return (
    <JobShell active="search">
        <div className={styles.pageIntro}>
          <p className="eyebrow">AGENTCRESCENDO · ASHBY JOB SEARCH</p>
          <h1>Find your next role.</h1>
          <p>Search Ashby openings, craft a thoughtful “Why company?” answer, and keep track of your applications.</p>
        </div>
        <div className={styles.layout}>
          <div className={styles.side}>
            <ResumeBox resume={s.resume} uploading={s.uploading || s.removingResume} onUpload={file => void s.upload(file)} onRemove={() => void s.removeResume()} />

            <form className={styles.panel} onSubmit={submit} aria-labelledby="filters-title">
              <h2 id="filters-title">Search</h2>
              <label>Looking for<input value={filters.q} maxLength={100} required onChange={e => set("q", e.target.value)} placeholder="ai engineer" /></label>
              <label>Country<input value={filters.country} maxLength={60} onChange={e => set("country", e.target.value)} placeholder="Any country" /></label>
              <label className={styles.check}><input type="checkbox" checked={filters.remote} onChange={e => set("remote", e.target.checked)} /> Remote only</label>
              <label className={styles.check}><input type="checkbox" checked={filters.hideApplied} onChange={e => set("hideApplied", e.target.checked)} /> Hide applied jobs</label>
              <details className={styles.advancedFilters}>
              <summary>More filters</summary>
              <label>Cities <small>(comma-separated)</small><input value={filters.cities} maxLength={300} onChange={e => set("cities", e.target.value)} placeholder="Any city" /></label>
              <label className={styles.check}><input type="checkbox" checked={filters.noSenior} onChange={e => set("noSenior", e.target.checked)} /> Early-career titles only</label>
              <label>Max years asked
                <select value={filters.maxYears} onChange={e => set("maxYears", e.target.value)}>
                  <option value="">Any</option>
                  {[0, 1, 2, 3, 4, 5, 7, 10].map(n => <option key={n} value={String(n)}>{n}</option>)}
                </select>
              </label>
              <label>Posted within<select value={filters.maxAgeDays} onChange={e => set("maxAgeDays", e.target.value)}>
                {[1, 3, 7, 14, 30].map(n => <option key={n} value={String(n)}>{n} {n === 1 ? "day" : "days"}</option>)}
              </select></label>
              </details>
              <button className="primary" type="submit" disabled={s.searching || s.uploading || s.removingResume || !s.resume}>{s.searching ? "Searching…" : "Search jobs"}</button>
            </form>
          </div>

          <section className={styles.results} aria-labelledby="results-title" aria-busy={s.searching}>
            {s.picks.length > 0 && <div className={styles.shortlist}>
              <PicksTray picks={s.picks} busy={s.savingPicks} ready={!!s.resume && !s.uploading && !s.removingResume} onRemove={s.removePick} onClear={s.clearPicks} />
            </div>}
            <h2 id="results-title" className={styles.resultsTitle}>
              {page ? `${page.total.toLocaleString()} jobs` : s.searching ? "Finding your matches…" : "Your matches"}
            </h2>
            {page && (
              <p className={styles.summary}>
                From {page.postings_searched.toLocaleString()} open postings · data from the{" "}
                {page.crawl ? `${when(page.crawl.finished_at ?? page.crawl.started_at)} crawl${page.crawl.status === "ok" ? "" : ` (${page.crawl.status})`}` : "— no crawl recorded yet"}
              </p>
            )}
            {hidden.length > 0 && (
              <p className={styles.hidden}>Hidden by your filters:{" "}
                {hidden.map(h => (
                  <button key={h.key} type="button" className={styles.chip} onClick={() => relax(h.relax(s.activeFilters ?? filters))}>
                    {page!.hidden[h.key]} {h.label} · show
                  </button>
                ))}
              </p>
            )}
            <details className={styles.searchHelp}><summary>About these matches</summary><p className={styles.small}>Ranked locally: 30% title match and 70% named skill coverage. Scores are a sorting aid. Select up to three roles for company research and drafting. Use Mark applied after you submit an application yourself.</p></details>

            {s.error && <div className="error" role="alert">{s.error}{s.resume === undefined && <p><button type="button" onClick={() => window.location.reload()}>Retry loading</button></p>}</div>}
            {s.notice && <p className={styles.notice} role="status">{s.notice} <a href="/jobs/applications">View applications</a></p>}
            {s.searching && <p className={styles.empty} role="status">Comparing titles and skills with your resume…</p>}
            {s.resume === null && !s.error && <p className={styles.empty}>Upload your resume to see ranked jobs.</p>}
            {page && page.total === 0 && (
              <p className={styles.empty}>No jobs match.{hidden.length ? " Some were hidden by filters above." : " Try broader words, e.g. \"engineer\"."}</p>
            )}

            <div className={styles.cards}>
              {s.results.map(row => {
                const key = `${row.source}:${row.posting_id}`;
                return <JobCard key={key} row={row} detail={s.details[key]} canPick={canPick} busy={s.savingPicks}
                                onTogglePick={() => s.togglePick(row)} onToggleDetail={() => void s.toggleDetail(row)}
                                tracking={s.tracking.includes(key)} onMarkApplied={() => void s.markApplied(row)} />;
              })}
            </div>
            {page && s.results.length < page.total && (
              <button type="button" className={styles.more} disabled={s.loadingMore} onClick={() => void s.loadMore()}>
                {s.loadingMore ? "Loading…" : `Show more (${page.total - s.results.length} left)`}
              </button>
            )}
          </section>

        </div>
    </JobShell>
  );
}
