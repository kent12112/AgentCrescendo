"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { getPicks, getResume } from "./api";
import { JobShell, ProcessSteps } from "./job-shell";
import * as api from "./letters-api";
import { STATUS, type CompanyResearch, type Letter, type LetterSession, type Turn } from "./letters-api";
import type { Pick, ResumeInfo } from "./types";
import styles from "./jobs.module.css";

const message = (error: unknown) => error instanceof Error ? error.message : "The request could not be completed.";
const ROLE: Record<Turn["role"], string> = { thinker: "Thinker · plan", worker: "Worker · draft", verifier: "Verifier · check" };
const host = (url: string) => { try { return new URL(url).hostname; } catch { return url; } };

async function copyText(text: string, fallback: HTMLTextAreaElement | null) {
  try { await navigator.clipboard.writeText(text); return true; } catch {
    // Clipboard API needs a secure context and permission; select the text as a fallback.
    if (!fallback) return false;
    fallback.focus(); fallback.select();
    return document.execCommand("copy");
  }
}

function ResearchSummary({ research }: { research?: CompanyResearch }) {
  if (!research) return <p className={styles.small}>Not researched. Only the posting and your notes describe this company.</p>;
  if (research.status === "failed") return <p className={styles.warn}>{research.error} You can research again or continue without it.</p>;
  return <>
    <p className={styles.small}>{research.facts.length} verified {research.facts.length === 1 ? "fact" : "facts"}. Each quote was found on the linked page by the backend, not just claimed by the model.</p>
    {research.facts.map((fact, i) => <div key={i} className={styles.checkItem}>
      <p><strong>{fact.topic}</strong> · {fact.claim}</p>
      <blockquote>{fact.quote}</blockquote>
      <a className={styles.linkButton} href={fact.url} target="_blank" rel="noopener noreferrer">{host(fact.url)} ↗</a>
    </div>)}
    {!!research.excluded.length && <details><summary className={styles.small}>{research.excluded.length} excluded (not used for drafting)</summary>
      {research.excluded.map((fact, i) => <p key={i} className={styles.small}>{fact.claim} — {host(fact.url)}: {fact.reason}</p>)}
    </details>}
    {!!research.open_questions.length && <p className={styles.small}>Could not confirm: {research.open_questions.join(" · ")}</p>}
  </>;
}

function TurnTrace({ turns, live }: { turns: Turn[]; live: boolean }) {
  if (!turns.length) return live ? <p className={styles.small} role="status">Thinker is planning the argument…</p> : null;
  return <ol className={styles.small} aria-label="Agent turns">
    {turns.map(turn => <li key={turn.turn}>
      <strong>{ROLE[turn.role]}</strong> · {turn.status === "failed" ? "failed" : `${turn.seconds}s`} — {turn.summary}
      {turn.role === "verifier" && turn.detail.accepted === false && !!turn.detail.issues?.length && <ul>
        {turn.detail.issues.map((issue, i) => <li key={i}>{issue.sentence ? `Sentence ${issue.sentence}: ` : ""}{issue.problem} → {issue.fix}</li>)}
      </ul>}
    </li>)}
    {live && <li role="status">Working on the next turn…</li>}
  </ol>;
}

export default function LetterWorkspace() {
  const [session, setSession] = useState<LetterSession | null>(null);
  const [library, setLibrary] = useState<Letter[]>([]);
  const [picks, setPicks] = useState<Pick[]>([]);
  const [resume, setResume] = useState<ResumeInfo | null>(null);
  const [creating, setCreating] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [researching, setResearching] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [name, setName] = useState("");
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [consent, setConsent] = useState(false);
  const [selectedId, setSelectedId] = useState("");
  const [text, setText] = useState("");
  const [reviewed, setReviewed] = useState(false);
  const [copied, setCopied] = useState(false);
  const operation = useRef(false);
  const mounted = useRef(false);
  const editor = useRef<HTMLTextAreaElement>(null);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    const params = new URLSearchParams(window.location.search);
    try {
      if (params.get("session")) {
        const data = await api.getSession(params.get("session")!);
        if (!mounted.current) return;
        setSession(data);
        const requested = params.get("letter");
        setSelectedId(data.letters.find(l => l.id === requested)?.id ?? data.letters[0]?.id ?? "");
      } else if (params.has("new")) {
        const [selection, stored] = await Promise.all([getPicks(), getResume()]);
        if (!mounted.current) return;
        setPicks(selection.picks); setResume(stored.resume); setCreating(true);
      } else {
        const data = await api.listLetters();
        if (mounted.current) setLibrary(data.letters);
      }
    } catch (caught) { if (mounted.current) setError(message(caught)); }
    finally { if (mounted.current) setLoading(false); }
  }, []);

  useEffect(() => {
    mounted.current = true;
    void load();
    return () => { mounted.current = false; };
  }, [load]);

  const selected = session?.letters.find(l => l.id === selectedId);
  useEffect(() => { setText(selected?.text ?? ""); setReviewed(false); setCopied(false); }, [selected?.id, selected?.version, selected?.text]);
  const dirty = !!selected && text !== selected.text;
  const inFlight = session?.letters.some(l => l.status === "generating") ?? false;

  // Poll only while a request is executing or the persisted status says drafting.
  // Each finished agent turn is saved by the API, so polling shows real progress.
  useEffect(() => {
    if (!session || (!busy && !inFlight)) return;
    let cancelled = false;
    const timer = window.setInterval(() => {
      void api.getSession(session.id).then(data => {
        if (!cancelled && mounted.current) setSession(data);
      }).catch(() => { /* The active request reports failures; a transient poll must not erase work. */ });
    }, 2000);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, [session?.id, busy, inFlight]);

  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  async function prepare(event: FormEvent) {
    event.preventDefault();
    if (operation.current) return;
    operation.current = true; setBusy(true); setError("");
    try {
      const data = await api.prepare(name, picks, notes);
      if (!mounted.current) return;
      setSession(data); setCreating(false); setSelectedId(data.letters[0]?.id ?? ""); setConsent(false);
      window.history.replaceState(null, "", `?session=${data.id}`);
    } catch (caught) { if (mounted.current) setError(message(caught)); }
    finally { operation.current = false; if (mounted.current) setBusy(false); }
  }

  async function research() {
    if (!session || session.confirmed_at || operation.current) return;
    operation.current = true; setBusy(true); setResearching(true); setError(""); setNotice("");
    try {
      const data = await api.research(session);
      if (!mounted.current) return;
      // Research changes what will be sent, so any earlier consent checkbox no longer applies.
      setSession(data); setConsent(false);
      setNotice("Company research finished. Review the verified facts below before drafting.");
    } catch (caught) { if (mounted.current) setError(message(caught)); }
    finally { operation.current = false; if (mounted.current) { setBusy(false); setResearching(false); } }
  }

  async function generate() {
    if (!session || operation.current || (!session.confirmed_at && !consent)) return;
    operation.current = true; setBusy(true); setError(""); setNotice("");
    let current = session;
    try {
      if (!current.confirmed_at) { current = await api.confirm(current); if (mounted.current) setSession(current); }
      for (const letter of current.letters) {
        if (!mounted.current) break; // Stop starting more jobs if the user leaves.
        if (letter.status === "draft" || letter.status === "approved") continue;
        setSelectedId(letter.id);
        window.history.replaceState(null, "", `?session=${current.id}&letter=${letter.id}`);
        const result = await api.generate(letter.id);
        current = { ...current, letters: current.letters.map(l => l.id === result.id ? result : l) };
        if (mounted.current) setSession(current);
      }
      if (mounted.current) setNotice("Drafting finished. Review each answer, then copy it into the application.");
    } catch (caught) {
      if (mounted.current) {
        setError(`${message(caught)} Saved answers are kept. Refresh status before retrying.`);
        try { setSession(await api.getSession(current.id)); } catch { /* keep saved state */ }
      }
    } finally { operation.current = false; if (mounted.current) setBusy(false); }
  }

  async function save(approve: boolean) {
    if (!session || !selected || operation.current) return;
    operation.current = true; setBusy(true); setError(""); setNotice("");
    try {
      const updated = await api.save(selected, text, approve, reviewed);
      if (!mounted.current) return;
      setSession(current => current ? { ...current, letters: current.letters.map(l => l.id === updated.id ? updated : l) } : current);
      setText(updated.text); setReviewed(false);
      setNotice(approve ? "Marked ready and saved." : "Answer saved.");
    } catch (caught) { if (mounted.current) setError(message(caught)); }
    finally { operation.current = false; if (mounted.current) setBusy(false); }
  }

  async function copy() {
    const ok = await copyText(text, editor.current);
    if (!mounted.current) return;
    setCopied(ok);
    if (!ok) setError("Copy was blocked by the browser. Select the text and copy it manually.");
  }

  function select(letter: Letter) {
    if (dirty && !window.confirm("Discard unsaved edits to this answer?")) return;
    setSelectedId(letter.id); setNotice("");
    window.history.replaceState(null, "", `?session=${letter.session_id}&letter=${letter.id}`);
  }

  const finished = session?.letters.every(l => l.status === "approved");
  const hasDraft = session?.letters.some(l => l.status === "draft" || l.status === "approved");
  const remaining = session?.letters.some(l => ["pending", "failed", "generating"].includes(l.status));
  const researched = session?.inputs.jobs.some(job => job.company_research);
  const words = text.split(/\s+/).filter(Boolean).length;

  return <JobShell active="letters"><div className={styles.lettersPage}>
    <div className={`${styles.headingRow} ${session ? styles.workspaceHeading : ""}`}>
      <div><p className="eyebrow">MAKE IT PERSONAL</p><h1>{session ? "Your “Why this company?” answers" : creating ? "Answer “Why this company?”" : "Your “Why this company?” answers"}</h1>
        <p className={styles.lede}>A researched, evidence-checked answer for each role: your experience, the job, and the company itself.</p></div>
      <a href="/jobs" className={styles.secondary}>← Find jobs</a>
    </div>
    <ProcessSteps current={selected?.status === "approved" || finished ? 5 : hasDraft && !inFlight ? 4 : session?.confirmed_at ? 3 : 2} />
    {error && <div className="error" role="alert">{error} <button className={styles.linkButton} disabled={busy} onClick={() => void load()}>Refresh status</button></div>}
    {notice && <p className={styles.notice} role="status">{notice}</p>}
    {loading && <p className={styles.empty} role="status">Loading your workspace…</p>}

    {!loading && creating && <form className={`${styles.panel} ${styles.setup}`} onSubmit={prepare}>
      <h2>1. Prepare your inputs</h2>
      {!resume || !picks.length ? <p>Upload a resume and choose up to three jobs in <a href="/jobs">job search</a> first.</p> : <>
        <p>Resume: <strong>{resume.filename}</strong>. We&apos;ll use the stored job descriptions, optional company research, and any notes you add below.</p>
        <label>Your full name<input value={name} onChange={e => setName(e.target.value)} minLength={3} maxLength={120} required autoComplete="name" disabled={busy} /></label>
        <p className={styles.small}>Your name and contact details are removed before drafting. The first line of your resume is treated as your name line. You&apos;ll review the result next.</p>
        {picks.map(p => <div key={`${p.source}:${p.posting_id}`} className={styles.companyInput}>
          <h3>{p.title} <span className={styles.company}>at {p.company}</span></h3>
          {p.closed && <p className={styles.warn}>This posting is closed. Update your picks before continuing.</p>}
          <label>Why you, why them <small>(optional)</small><textarea value={notes[`${p.source}:${p.posting_id}`] ?? ""}
            onChange={e => setNotes(n => ({ ...n, [`${p.source}:${p.posting_id}`]: e.target.value }))}
            maxLength={4000} disabled={busy} placeholder={"Your real reason: Have you used the product, hit the problem it solves, or followed its work?\nSomething specific: a launch, blog post, or practice you noticed (paste exact excerpts where possible)."} /></label>
          <p className={styles.small}>Only you know your personal reasons; the drafter will not invent them. Company facts can also be researched automatically in the next step.</p>
        </div>)}
        <button className="primary" disabled={busy || picks.some(p => p.closed)} type="submit">{busy ? "Preparing…" : "Preview redacted inputs →"}</button>
        <p className={styles.small}>Preparing this preview makes no model request.</p>
      </>}
    </form>}

    {!loading && session && <>
      <details className={`${styles.panel} ${styles.preview} ${styles.inputPreview}`} open={!session.confirmed_at || (!!remaining && !busy && !inFlight)}>
        <summary className={styles.inputSummary}>{session.confirmed_at ? `Approved inputs · resume + ${session.inputs.jobs.length} selected roles` : "Research and review model inputs"}</summary>
        <section aria-labelledby="preview-title">
        <h2 id="preview-title">{session.confirmed_at ? "Inputs you approved" : "2. Research the companies, then review what will be sent"}</h2>
        {!session.confirmed_at && <div className={styles.row}>
          <button className={styles.secondary} type="button" disabled={busy} onClick={() => void research()}>
            {researching ? "Researching companies…" : researched ? "Research again" : "Research companies"}
          </button>
          <span className={styles.small}>Sends only each company name, role title, posting link and posting excerpt to Groq&apos;s browser search. Your resume, name and notes are not sent. The backend then opens each cited page and keeps only quotes it finds there.</span>
        </div>}
        <p>Drafting sends the sources below to Groq using <strong>{session.inputs.model}</strong>: a Thinker plans the argument, a Worker writes it, and a Verifier checks it, up to five requests per answer. Check for any identifying details the automatic removal missed.</p>
        <details open={!session.confirmed_at}><summary>Resume with identity removed</summary><pre className={styles.sourceText}>{session.inputs.resume}</pre></details>
        {session.inputs.jobs.map(job => <details key={`${job.source}:${job.posting_id}`} open={!session.confirmed_at && !!job.company_research}><summary>{job.title} · {job.company}</summary>
          <h3>Company research</h3><ResearchSummary research={job.company_research} />
          <h3>Job description</h3><pre className={styles.sourceText}>{job.description}</pre>
          <h3>Your notes</h3><pre className={styles.sourceText}>{job.company_notes || "No notes added."}</pre>
        </details>)}
        {!session.confirmed_at && <>
          <label className={styles.check}><input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} disabled={busy} />
            I reviewed these inputs and agree to send them to Groq for drafting.</label>
          <p className={styles.small}>Need to change something? <a href="/jobs/letters?new=1">Prepare a new preview</a>. Once you start drafting, these inputs stay fixed.</p>
        </>}
        {remaining && <div className={styles.row}>
          <button className="primary" disabled={busy || (!session.confirmed_at && !consent) || dirty} onClick={() => void generate()}>
            {busy && !researching ? "Drafting…" : session.confirmed_at ? "Continue / retry drafting" : `Draft ${session.letters.length} ${session.letters.length === 1 ? "answer" : "answers"} →`}
          </button>
          {busy && !researching && <span role="status">Drafting one job at a time. Each finished turn is saved.</span>}
        </div>}
        </section>
      </details>

      <div className={styles.letterGrid}>
        <section className={`${styles.panel} ${styles.sessionPanel}`} aria-labelledby="letter-jobs"><h2 id="letter-jobs">This session</h2>
          {session.letters.map(letter => <button key={letter.id} type="button" onClick={() => select(letter)} disabled={busy}
            className={`${styles.letterTab} ${letter.id === selectedId ? styles.letterTabActive : ""}`} aria-pressed={letter.id === selectedId}>
            <strong>{letter.posting.company}</strong><span>{letter.posting.title}</span><span className={styles.status}>{STATUS[letter.status]}</span>
          </button>)}
          <a href="/jobs/letters" className={styles.linkButton}>All saved answers →</a>
        </section>

        {selected && <section className={`${styles.panel} ${styles.workbench}`} aria-labelledby="editor-title">
          <div className={styles.headingRow}><div><h2 id="editor-title">Why {selected.posting.company}?</h2><p>{selected.posting.title} · {STATUS[selected.status]}</p></div>
            <a href={selected.posting.url} target="_blank" rel="noopener noreferrer" className={styles.linkButton}>View posting ↗</a></div>
          {selected.error && <p className="error" role="alert">{selected.error} Use Continue / retry drafting above.</p>}
          {selected.status === "generating" && <TurnTrace turns={selected.turns ?? []} live />}
          {["draft", "approved"].includes(selected.status) && <div className={styles.reviewPane}>
            <div className={styles.workbenchBar}>
              <label htmlFor="letter-text">Answer</label>
              <button type="button" className="primary" disabled={!text.trim()} onClick={() => void copy()} aria-describedby="copy-status">{copied ? "Copied ✓" : "Copy answer"}</button>
            </div>
            <textarea id="letter-text" ref={editor} className={styles.editor} value={text} onChange={e => { setText(e.target.value); setReviewed(false); setNotice(""); setCopied(false); }} disabled={busy} maxLength={16000} />
            <p className={styles.small} id="copy-status" role="status">{words} words · {text.length} characters · {dirty ? "Unsaved changes" : "Saved locally"}{copied ? " · Copied to clipboard" : ""}</p>
            {!!selected.turns?.length && <details><summary className={styles.small}>How this answer was made ({selected.turns.length} agent turns)</summary><TurnTrace turns={selected.turns} live={false} /></details>}
            <div className={styles.evidence}>
              <h3>Source evidence & review flags</h3>
              <p className={styles.small}>Quote matches check whether source text exists. Review whether it supports the sentence. Edits are not automatically checked.</p>
              {selected.checks.map((check, i) => <details key={i} className={styles.checkItem}>
                <summary><span className={check.flags.length ? styles.warn : styles.muted}>{check.flags.length ? "Review" : check.source === "verifier" ? "Verified" : "Quote found"}</span> · {check.text}</summary>
                <p className={styles.small}>Source: {check.source.replaceAll("_", " ")}</p>
                {check.quote && <blockquote>{check.quote}</blockquote>}
                {check.source === "posting" && <a className={styles.linkButton} href={selected.posting.url} target="_blank" rel="noopener noreferrer">Posting source ↗</a>}
                {check.supporting_quotes?.map((evidence, i) => <div key={i}>
                  <p className={styles.small}>Additional source: {evidence.source.replaceAll("_", " ")} · {evidence.quote_found ? "Quote found" : "Quote not found"}</p>
                  <blockquote>{evidence.quote}</blockquote>
                </div>)}
                {check.flags.map(flag => <p key={flag} className={styles.warn}>{flag}</p>)}
              </details>)}
            </div>
            <label className={styles.check}><input type="checkbox" checked={reviewed} onChange={e => setReviewed(e.target.checked)} disabled={busy} />I reviewed this text and its source flags.</label>
            <div className={styles.row}>
              <button className={styles.secondary} disabled={busy || !dirty || text.trim().length < 40} onClick={() => void save(false)}>Save edits</button>
              <button className={styles.secondary} disabled={busy || !reviewed || text.trim().length < 40 || (selected.status === "approved" && !dirty)} onClick={() => void save(true)}>Mark ready</button>
            </div>
          </div>}
        </section>}
      </div>
    </>}

    {!loading && !session && !creating && !error && <section aria-label="Saved answers">
      {!library.length ? <div className={styles.empty}><h2>Your first answer starts with a job.</h2><p>Pick a role from your matches, then draft a researched “Why this company?” answer.</p><a href="/jobs" className={styles.secondary}>Find your matches →</a></div> : <>
        <p className={styles.muted}>{library.length} saved answers and pending drafts · most recent first</p>
        <div className={styles.library}>{library.map(letter => <a className={styles.libraryCard} key={letter.id} href={`?session=${letter.session_id}&letter=${letter.id}`}>
          <span className={styles.status}>{STATUS[letter.status]}</span><h2>{letter.posting.company}</h2><p>{letter.posting.title}</p>
          <small>{new Date(letter.created_at).toLocaleDateString()} · Open answer →</small>
        </a>)}</div>
      </>}
    </section>}
  </div></JobShell>;
}
