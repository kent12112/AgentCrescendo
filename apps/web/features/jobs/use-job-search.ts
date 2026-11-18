"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import * as api from "./api";
import { MAX_PICKS, type Filters, type JobDetail, type JobRow, type Pick, type ResumeInfo, type SearchPage } from "./types";

// Starting filters when the URL has none. Early-career, US, at most 3 years asked: the settings
// the user chose for their own search (JOB-F06/F07). Everything is editable on the page.
export const DEFAULT_FILTERS: Filters = {
  q: "ai engineer", country: "United States", cities: "", remote: false, noSenior: true, maxYears: "3", maxAgeDays: "30", hideApplied: false,
};

// The search is kept in the URL so a reload or a bookmark reopens it.
function filtersFromUrl(): Filters {
  const params = new URLSearchParams(window.location.search);
  if (!params.has("q")) return DEFAULT_FILTERS;
  return {
    q: params.get("q") ?? "",
    country: params.get("country") ?? "",
    cities: params.getAll("location").join(", "),
    remote: params.get("remote") === "true",
    noSenior: params.get("no_senior") === "true",
    maxYears: params.get("max_years") ?? "",
    maxAgeDays: params.get("max_age_days") ?? "30",
    hideApplied: params.get("hide_applied") === "true",
  };
}

export function useJobSearch() {
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [resume, setResume] = useState<ResumeInfo | null | undefined>(undefined); // undefined = loading
  const [page, setPage] = useState<SearchPage | null>(null);
  const [results, setResults] = useState<JobRow[]>([]);
  const [searching, setSearching] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [removingResume, setRemovingResume] = useState(false);
  const [activeFilters, setActiveFilters] = useState<Filters | null>(null);
  const [picks, setPicks] = useState<Pick[]>([]);
  const [savingPicks, setSavingPicks] = useState(false);
  const [details, setDetails] = useState<Record<string, JobDetail | "loading" | "error">>({});
  const [error, setError] = useState("");
  const [tracking, setTracking] = useState<string[]>([]);
  const [notice, setNotice] = useState("");
  const trackingRequests = useRef(new Set<string>());
  const latest = useRef(0); // ignore responses from searches that were superseded
  const applied = useRef<Filters | null>(null);
  const paging = useRef(false);
  const picking = useRef(false);
  const chosen = useRef<Pick[]>([]);
  const detailRequests = useRef<Record<string, number>>({});

  function withPicks(rows: JobRow[]) {
    const keys = new Set(chosen.current.map(p => `${p.source}:${p.posting_id}`));
    return rows.map(row => ({ ...row, picked: keys.has(`${row.source}:${row.posting_id}`) }));
  }

  const runSearch = useCallback(async (next: Filters) => {
    if (!next.q.trim()) { setError("Type what you are looking for, e.g. \"ai engineer\"."); return; }
    const ticket = ++latest.current;
    setSearching(true);
    setLoadingMore(false);
    paging.current = false;
    setPage(null);
    setResults([]);
    setDetails({});
    detailRequests.current = {};
    setError("");
    window.history.replaceState(null, "", `?${api.searchParams(next)}`);
    try {
      const data = await api.getSearch(next);
      if (ticket !== latest.current) return;
      setPage(data);
      applied.current = { ...next };
      setActiveFilters({ ...next });
      setResults(withPicks(data.results));
    } catch (caught) {
      if (ticket !== latest.current) return;
      setPage(null);
      setResults([]);
      setError(caught instanceof Error ? caught.message : "Search failed.");
    } finally {
      if (ticket === latest.current) setSearching(false);
    }
  }, []);

  // On first load: read the URL, then the stored resume and picks, then search if possible.
  useEffect(() => {
    let cancelled = false;
    const initial = filtersFromUrl();
    setFilters(initial);
    void (async () => {
      try {
        const [{ resume: stored }, { picks: saved }] = await Promise.all([api.getResume(), api.getPicks()]);
        if (cancelled) return;
        setResume(stored);
        setPicks(saved);
        chosen.current = saved;
        if (stored) await runSearch(initial);
      } catch (caught) {
        if (cancelled) return;
        setError(caught instanceof Error ? caught.message : "Cannot load the job search.");
      }
    })();
    return () => { cancelled = true; latest.current++; };
  }, [runSearch]);

  async function loadMore() {
    if (!page || !applied.current || results.length >= page.total || paging.current || searching) return;
    const ticket = latest.current;
    const snapshot = applied.current;
    paging.current = true;
    setLoadingMore(true);
    try {
      const data = await api.getSearch(snapshot, results.length);
      if (ticket !== latest.current) return;
      setResults(current => [...current, ...withPicks(data.results)]);
    } catch (caught) {
      if (ticket === latest.current) setError(caught instanceof Error ? caught.message : "Could not load more jobs.");
    } finally { if (ticket === latest.current) { setLoadingMore(false); paging.current = false; } }
  }

  async function upload(file: File) {
    if (uploading || removingResume) return;
    latest.current++;
    setSearching(false);
    setPage(null); setResults([]); setDetails({}); detailRequests.current = {};
    setUploading(true);
    setError("");
    try {
      const { resume: stored } = await api.uploadResume(file);
      setResume(stored);
      await runSearch(filters);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Upload failed.");
    } finally { setUploading(false); }
  }

  async function removeResume() {
    if (uploading || removingResume) return;
    latest.current++;
    setSearching(false); setLoadingMore(false); paging.current = false;
    setRemovingResume(true);
    setError("");
    try {
      await api.deleteResume();
      setResume(null);
      setPage(null);
      setResults([]);
      setDetails({}); detailRequests.current = {};
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not remove the resume.");
    } finally { setRemovingResume(false); }
  }

  // The server replaces the whole selection and enforces the limit; the page mirrors its answer.
  async function savePicks(next: { source: string; posting_id: string }[]) {
    if (picking.current) return;
    picking.current = true;
    const previous = chosen.current;
    const candidates = [...results.map(row => ({ ...row, closed: false })), ...previous];
    chosen.current = next.map(ref => candidates.find(p => p.source === ref.source && p.posting_id === ref.posting_id)!)
      .filter(Boolean).map(p => ({ source: p.source, posting_id: p.posting_id, title: p.title, company: p.company, url: p.url, closed: p.closed }));
    setPicks(chosen.current);
    setResults(current => withPicks(current));
    setSavingPicks(true);
    setError("");
    try {
      const { picks: saved } = await api.putPicks(next);
      setPicks(saved);
      chosen.current = saved;
      setResults(current => withPicks(current));
    } catch (caught) {
      // A lost response may still have committed. Re-read before falling back to the old selection.
      try { chosen.current = (await api.getPicks()).picks; } catch { chosen.current = previous; }
      setPicks(chosen.current);
      setResults(current => withPicks(current));
      setError(caught instanceof Error ? caught.message : "Could not save your picks.");
    } finally { setSavingPicks(false); picking.current = false; }
  }

  function togglePick(row: JobRow) {
    const key = (p: { source: string; posting_id: string }) => `${p.source}:${p.posting_id}`;
    const current = chosen.current.map(p => ({ source: p.source, posting_id: p.posting_id }));
    const isPicked = current.some(p => key(p) === key(row));
    if (!isPicked && current.length >= MAX_PICKS) return; // the checkbox is disabled; the server would refuse too
    void savePicks(isPicked ? current.filter(p => key(p) !== key(row))
                            : [...current, { source: row.source, posting_id: row.posting_id }]);
  }

  function removePick(pick: Pick) {
    void savePicks(chosen.current.filter(p => `${p.source}:${p.posting_id}` !== `${pick.source}:${pick.posting_id}`)
      .map(p => ({ source: p.source, posting_id: p.posting_id })));
  }

  async function toggleDetail(row: JobRow) {
    const key = `${row.source}:${row.posting_id}`;
    if (details[key] && details[key] !== "error") {
      delete detailRequests.current[key];
      setDetails(({ [key]: _, ...rest }) => rest); // collapse
      return;
    }
    setDetails(current => ({ ...current, [key]: "loading" }));
    const ticket = Date.now() + Math.random();
    detailRequests.current[key] = ticket;
    try {
      const detail = await api.getDetail(row.source, row.posting_id);
      if (detailRequests.current[key] !== ticket) return;
      setDetails(current => ({ ...current, [key]: detail }));
    } catch {
      if (detailRequests.current[key] !== ticket) return;
      setDetails(current => ({ ...current, [key]: "error" }));
    }
  }

  async function markApplied(row: JobRow) {
    const key = `${row.source}:${row.posting_id}`;
    if (trackingRequests.current.has(key) || row.application) return;
    trackingRequests.current.add(key);
    setTracking([...trackingRequests.current]); setError(""); setNotice("");
    try {
      const saved = await api.saveApplication(row, { status: "applied", applied_on: api.today() });
      setResults(current => current.map(item => item.source === row.source && item.posting_id === row.posting_id
        ? { ...item, application: { status: saved.status, applied_on: saved.applied_on } } : item));
      setNotice(`${row.company} saved to your application tracker.`);
      // Requery so hide-applied totals and pagination stay consistent with the server.
      if (applied.current?.hideApplied) await runSearch(applied.current);
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Could not track this application."); }
    finally { trackingRequests.current.delete(key); setTracking([...trackingRequests.current]); }
  }

  return {
    filters, setFilters, resume, page, results, searching, loadingMore, uploading, picks, savingPicks,
    details, error, runSearch, loadMore, upload, removeResume, togglePick, removePick, toggleDetail,
    removingResume, activeFilters, tracking, markApplied, notice, clearPicks: () => void savePicks([]),
  };
}
