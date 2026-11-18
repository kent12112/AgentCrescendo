"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { call } from "./api";
import type { Letter } from "./letters-api";
import styles from "./jobs.module.css";

type ExportState = {
  id: string; letter_id: string; letter_version: number;
  purpose: "draft" | "export";
  status: "starting" | "preparing" | "waiting_viewer" | "drafting" | "typing" | "exporting" | "cancelling" | "saved" | "failed" | "cancelled" | "interrupted";
  error: string | null; characters_typed: number; total_characters: number;
  pdf_ready: boolean; cleanup_confirmed: boolean; can_retry: boolean;
  viewer_connected: boolean; viewer_url: string | null; expires_at: string;
  diagnostics?: { total_seconds?: number; characters_per_second?: number; phase_seconds?: Record<string, number>; failure_code?: string; failure_operation?: string };
};

const ACTIVE = ["starting", "preparing", "waiting_viewer", "drafting", "typing", "exporting", "cancelling"];
const LABEL: Record<ExportState["status"], string> = {
  starting: "Opening desktop", preparing: "Preparing offline Writer", waiting_viewer: "Ready to watch",
  typing: "Typing your approved letter", exporting: "Exporting and checking the PDF", cancelling: "Stopping desktop",
  drafting: "Drafting from your resume and the role",
  saved: "PDF saved", failed: "Export needs retry", cancelled: "Export stopped", interrupted: "Live session interrupted",
};

function viewerUrl(raw: string | null) {
  if (!raw) return null;
  try {
    const url = new URL(raw);
    return url.protocol === "http:" && url.hostname === "127.0.0.1" && !url.username && !url.password && !url.search && !url.hash
      && /^\/watch\/[A-Za-z0-9_-]{32,}$/.test(url.pathname) ? url.href : null;
  } catch { return null; }
}

export function LiveWriter({ letter, onReview, onActiveChange, onStatusChange }: {
  letter: Letter; onReview: () => void; onActiveChange: (active: boolean) => void; onStatusChange: (status: string) => void;
}) {
  const [state, setState] = useState<ExportState | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [frame, setFrame] = useState(0);
  const operation = useRef(false);
  const reading = useRef(false);
  const revision = useRef(0);
  const mounted = useRef(false);
  const surface = useRef<HTMLDivElement>(null);
  const [fullscreen, setFullscreen] = useState(false);
  const active = !!state && (ACTIVE.includes(state.status) || (state.status === "interrupted" && !state.can_retry));
  const current = state?.letter_version === letter.version;
  const draftMode = state && current ? state.purpose === "draft" : letter.status !== "approved";
  const draftReady = draftMode && letter.status === "draft" && !active;

  const refresh = useCallback(async () => {
    if (reading.current || operation.current) return;
    reading.current = true;
    const ticket = revision.current;
    try {
      const data = await call<{ export: ExportState | null }>(`/api/jobs/letters/${letter.id}/writer`);
      if (mounted.current && ticket === revision.current) setState(previous => JSON.stringify(previous) === JSON.stringify(data.export) ? previous : data.export);
    } catch (caught) {
      if (mounted.current) setError(caught instanceof Error ? caught.message : "Could not load the Writer status.");
    } finally { reading.current = false; if (mounted.current) setLoading(false); }
  }, [letter.id]);

  useEffect(() => {
    mounted.current = true;
    void refresh();
    return () => { mounted.current = false; onActiveChange(false); onStatusChange(""); };
  }, [refresh, onActiveChange, onStatusChange]);

  useEffect(() => { onActiveChange(active || busy); }, [active, busy, onActiveChange]);
  useEffect(() => { onStatusChange(current ? state?.status ?? "" : ""); }, [state?.status, current, onStatusChange]);
  useEffect(() => { void refresh(); }, [letter.status, letter.version, refresh]);
  useEffect(() => {
    if (busy || !(active || letter.status === "generating" || ((state?.status === "failed" || state?.status === "cancelled") && !state.can_retry))) return;
    let cancelled = false;
    let timer: number;
    const poll = async () => {
      await refresh();
      if (!cancelled) timer = window.setTimeout(poll, document.hidden ? 5000 : 1000);
    };
    timer = window.setTimeout(poll, 1000);
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [state?.id, state?.status, state?.can_retry, letter.status, active, busy, refresh]);

  useEffect(() => {
    const update = () => setFullscreen(document.fullscreenElement === surface.current);
    document.addEventListener("fullscreenchange", update);
    return () => document.removeEventListener("fullscreenchange", update);
  }, []);

  async function toggleFullscreen() {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await surface.current?.requestFullscreen();
    } catch { setError("The browser could not expand the desktop. You can keep watching here."); }
  }

  async function act(kind: "start" | "begin" | "cancel") {
    if (operation.current) return;
    operation.current = true; setBusy(true); setError("");
    revision.current++;
    try {
      const path = kind === "start" ? `/api/jobs/letters/${letter.id}/${letter.status === "approved" ? "writer" : "draft-writer"}` : `/api/jobs/writer-exports/${state!.id}/${kind}`;
      const result = await call<ExportState>(path, { method: "POST", ...(kind === "start" ? {
        headers: { "Content-Type": "application/json" }, body: JSON.stringify({ version: letter.version }),
      } : {}) });
      if (mounted.current) setState(result);
    } catch (caught) {
      if (mounted.current) setError(caught instanceof Error ? caught.message : "The Writer request failed. Refresh status before retrying.");
    } finally { operation.current = false; if (mounted.current) setBusy(false); }
  }

  const source = viewerUrl(state?.viewer_url ?? null);
  const canOpen = !loading && (!state || (!active && !current) || (current && state.can_retry))
    && (letter.status !== "draft" || (current && state?.purpose === "draft" && state.can_retry));
  const stage = state?.status === "saved" ? 4 : state?.status === "exporting" || (draftMode && state?.status === "typing") ? 3 : state?.status === "typing" || state?.status === "drafting" ? 2 : state?.status === "waiting_viewer" ? 1 : 0;
  const typingSeconds = state?.diagnostics?.phase_seconds?.typing;
  return <section className={styles.liveWriter} aria-labelledby="live-writer-title">
    <div className={styles.headingRow}><h3 id="live-writer-title">{draftMode ? "Draft your letter live" : "Final PDF export"}</h3>
      {state && <span className={styles.status} role="status">{draftReady ? "Draft ready for review" : draftMode && state.status === "typing" ? "Writing your draft" : draftMode && state.status === "exporting" ? "Checking your draft" : LABEL[state.status]}</span>}</div>
    <p className={styles.small}>{draftMode ? "Watch the draft take shape in Writer, then review its text and sources before approving." : "Export your approved version on the private, offline desktop."}</p>
    {error && <p className="error" role="alert">{error} <button className={styles.linkButton} disabled={busy} onClick={() => { setError(""); void refresh(); }}>Refresh status</button></p>}
    {state?.error && <p className={styles.warn} role="alert">{state.error}</p>}
    {state && !current && <p className={styles.small}>This desktop used an earlier version. Your current letter is saved separately.</p>}
    <div className={styles.desktopSurface} ref={surface}>
      <div className={styles.desktopToolbar}>
        <div><span className={`${styles.connectionDot} ${state?.viewer_connected ? styles.connectedDot : ""}`} />
          <strong>Writer desktop</strong><span className={styles.desktopConnection} role="status">{source ? state?.viewer_connected ? "Live desktop connected" : "Reconnecting…" : draftReady ? "Draft complete" : state?.pdf_ready ? "Export complete" : "Private · offline"}</span></div>
        {source && <div className={styles.row}>
          <button type="button" onClick={() => setFrame(n => n + 1)}>Reconnect live view</button>
          <button type="button" onClick={() => void toggleFullscreen()}>{fullscreen ? "Exit full screen" : "Expand desktop"}</button>
        </div>}
      </div>
      <ol className={styles.desktopStages} aria-label="PDF export progress">
        {(draftMode ? ["Prepare", "Ready", "Draft", "Write", "Review"] : ["Prepare", "Ready", "Typing", "Export", "Saved"]).map((label, i) => <li key={label} aria-current={stage === i ? "step" : undefined}
          className={i < stage ? styles.desktopStageDone : i === stage ? styles.desktopStageCurrent : ""}><span>{i < stage ? "✓" : i + 1}</span>{label}</li>)}
      </ol>
      {source ? <iframe key={`${state!.id}:${frame}`} src={source} title="Live E2B Writer desktop" className={styles.writerFrame}
        referrerPolicy="no-referrer" sandbox="allow-scripts allow-same-origin" /> : <div className={styles.desktopEmpty}>
        <div className={styles.documentIcon} aria-hidden="true"><span /><span /><span /><span /></div>
        <h4>{draftReady ? "Your draft is ready to review." : state?.pdf_ready ? "Your PDF is ready." : active ? "Preparing your desktop…" : loading ? "Loading your workspace…" : draftMode ? "Write it together, live." : "Bring your letter to life."}</h4>
        <p>{draftReady ? "Read the draft and its source flags. Your identity placeholders stay in place until you approve." : state?.pdf_ready ? "The exported words match your approved letter. Your PDF is saved in this workspace." : active ? "Opening LibreOffice and checking the offline connection." : draftMode ? "Open Writer before drafting. The model creates the text, then the desktop types it for you to watch." : "Watch your approved text become a document, then take the verified PDF with you."}</p>
        {draftReady && <button className="primary" onClick={onReview}>Review draft & sources →</button>}
        {canOpen && <button className="primary" disabled={busy} onClick={() => void act("start")}>{busy ? "Opening…" : state && current ? "Retry live Writer" : draftMode ? "Draft with live Writer →" : "Open live Writer →"}</button>}
      </div>}
      <div className={styles.desktopControls}>
        <div className={styles.desktopProgressCopy}>
          {current && state && ["typing", "exporting"].includes(state.status) ? <>
            <progress aria-label={draftMode ? "Draft characters typed" : "Approved letter characters typed"} value={state.characters_typed} max={state.total_characters} />
            <span>{state.characters_typed.toLocaleString()} / {state.total_characters.toLocaleString()} characters typed</span>
          </> : <span>{state?.status === "waiting_viewer" ? draftMode ? "When the blank document is visible, start drafting." : "When the blank document is visible, start typing." : state?.status === "drafting" ? "Generating from the reviewed resume and job description…" : draftReady ? "Draft saved · review before approval" : state?.pdf_ready ? state.cleanup_confirmed ? "Text verified · desktop closed" : "Text verified · desktop cleanup pending" : draftMode ? "Only the generated draft goes to this desktop." : "Only your approved text goes to this desktop."}</span>}
          {(state?.pdf_ready || draftReady) && typingSeconds !== undefined && <small>Typed in {Math.round(typingSeconds)}s</small>}
        </div>
        <div className={styles.row}>
          {current && state?.status === "waiting_viewer" && <button className="primary" disabled={busy || !state.viewer_connected} onClick={() => void act("begin")}>{draftMode ? "Start drafting" : "Start typing"}</button>}
          {state && ACTIVE.includes(state.status) && <button className={styles.secondary} disabled={busy || state.status === "cancelling"} onClick={() => void act("cancel")}>Stop live Writer</button>}
          {state?.pdf_ready && <a className={`primary ${styles.actionLink}`} href={`/api/jobs/writer-exports/${state.id}/pdf`} download>Download Writer PDF ↓</a>}
        </div>
      </div>
    </div>
    {state && !active && !state.can_retry && ["failed", "cancelled", "interrupted"].includes(state.status) &&
      <p className={styles.small}>The previous desktop lease expires at {new Date(state.expires_at).toLocaleTimeString()}. Retry becomes available after that if cleanup wasn&apos;t confirmed.</p>}
    {active && <p className={styles.small}>{draftMode ? "You can reload this page while drafting continues. Review opens when writing finishes." : "You can switch to Letter & sources or reload this page while the export continues."}</p>}
  </section>;
}
