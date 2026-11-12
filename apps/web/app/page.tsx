// This component needs browser events and React state. API credentials stay in
// the separate server-side route; they are never read by this component.
"use client";

import { useEffect, useState, type FormEvent } from "react";

// TypeScript checks how our UI uses responses; this type does not validate JSON
// at runtime. The API's Pydantic schemas define the actual HTTP contract.
type Run = {
  id: string;
  goal: string;
  status: "draft";
  max_workers: number;
  timeout_seconds: number;
  model_budget_cents: number;
  created_at: string;
};

const examples = [
  "Plan a weekend in Boston for two, under $600, with vegetarian food and no car.",
  "Compare three beginner cameras under $500. Include tradeoffs and source links.",
  "Find ideas for a rainy Saturday with friends in NYC, under $40 per person.",
];

function errorMessage(data: { detail?: unknown }) {
  if (typeof data.detail === "string") return data.detail;
  return "Please check the task and limits, then try again.";
}

export default function Workspace() {
  // Form state and server-loaded drafts live in React memory. The database is
  // the durable source; refreshing the page reloads it rather than losing drafts.
  const [goal, setGoal] = useState("");
  const [workers, setWorkers] = useState(3);
  const [budget, setBudget] = useState(100);
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function loadRuns() {
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/runs", { cache: "no-store" });
      const data = await response.json();
      // fetch only rejects network failures automatically; 4xx/5xx responses
      // need this explicit check so an error body is not mistaken for draft data.
      if (!response.ok) throw new Error(errorMessage(data));
      setRuns(data);
    } catch (error) {
      setError(error instanceof Error ? error.message : "Unable to load drafts.");
    } finally { setLoading(false); }
  }

  // Load after the component mounts. void intentionally discards the promise;
  // loadRuns handles errors itself and updates the visible connection message.
  useEffect(() => { void loadRuns(); }, []);

  async function createRun(event: FormEvent) {
    // Handle submission in JavaScript instead of reloading the browser page.
    event.preventDefault();
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const response = await fetch("/api/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal: goal.trim(), max_workers: workers, timeout_seconds: 600, model_budget_cents: budget }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(errorMessage(data));
      // Only show a saved draft after the server confirms it. The functional
      // updater uses the latest React state, then keeps the newest 25 entries.
      setRuns(previous => [data, ...previous].slice(0, 25));
      setGoal("");
      setNotice("Draft saved. No agents have started and no model costs were incurred.");
    } catch (error) {
      setError(error instanceof Error ? error.message : "Unable to save draft.");
    } finally { setSaving(false); }
  }

  return (
    <div className="workspace">
      <aside className="sidebar">
        <a className="brand" href="/" aria-label="AgentCrescendo home"><span className="brandmark">≋</span> Agent<span>Crescendo</span></a>
        <div className="sidebar-label">WORKSPACE</div>
        <div className="nav-active"><span aria-hidden="true">◈</span> Task drafts</div>
        <div className="sidebar-note"><span className="dot" /> Local development<br /><small>First movement · Foundation</small></div>
      </aside>

      <main>
        <header className="topbar"><span>Your workspace / <strong>Task drafts</strong></span><span className="local-badge">LOCAL ONLY</span></header>
        <div className="content">
          <div className="eyebrow">MANY AGENTS. ONE OUTCOME.</div>
          <h1>What shall we work on?</h1>
          <p className="intro">Start with a goal. Give your future agent team a clear brief, a budget, and room to coordinate.</p>

          <section className="composer" aria-labelledby="brief-label">
            <form onSubmit={createRun}>
              <label id="brief-label" htmlFor="goal">Your task</label>
              <textarea id="goal" required minLength={10} maxLength={4000} value={goal} onChange={event => setGoal(event.target.value)} placeholder="Plan, compare, research, or put something together…" />
              <div className="composer-bottom">
                <div className="controls">
                  <label>Workers <select value={workers} onChange={event => setWorkers(Number(event.target.value))}><option value={1}>1 worker</option><option value={2}>2 workers</option><option value={3}>3 workers</option></select></label>
                  <label>Model budget <select value={budget} onChange={event => setBudget(Number(event.target.value))}><option value={50}>$0.50</option><option value={100}>$1.00</option><option value={200}>$2.00</option><option value={500}>$5.00</option></select></label>
                  <span className="time-limit">10 min limit</span>
                </div>
                <button className="primary" type="submit" disabled={saving || goal.trim().length < 10}>{saving ? "Saving…" : "Save task draft"}<span aria-hidden="true">↗</span></button>
              </div>
            </form>
          </section>

          <div className="examples" aria-label="Example tasks"><span>Try a brief</span>{["A weekend away", "A considered purchase", "A day with friends"].map((label, index) => <button type="button" key={label} onClick={() => setGoal(examples[index])}>{label} <span aria-hidden="true">↗</span></button>)}</div>

          <div className="development-note"><span className="note-icon" aria-hidden="true">i</span><p><strong>Draft mode</strong> Your brief is saved to the local database. Desktop agents, execution, and automatic 24-hour cleanup are coming next. No browsing or model calls happen yet.</p></div>

          {error && <div className="error" role="alert">{error} <button type="button" onClick={() => void loadRuns()}>Retry connection</button></div>}
          <div role="status" aria-live="polite">{notice && <p className="success">{notice}</p>}</div>

          <section className="drafts" aria-labelledby="drafts-heading">
            <div className="section-heading"><h2 id="drafts-heading">Recent drafts <span>{runs.length}</span></h2><button className="refresh" type="button" disabled={loading} onClick={() => void loadRuns()}>{loading ? "Loading…" : "Refresh"}</button></div>
            {loading ? <div className="empty">Loading your saved briefs…</div> : runs.length === 0 ? <div className="empty"><div className="empty-symbol" aria-hidden="true">⌁</div><h3>Your first task starts here.</h3><p>Save a brief above. It will stay here when you come back.</p></div> : <div className="run-list">{runs.map(run => <article className="run" key={run.id}><div className="run-symbol" aria-hidden="true">↗</div><div className="run-main"><h3>{run.goal}</h3><p>{run.max_workers} {run.max_workers === 1 ? "worker" : "workers"} <span>·</span> ${(run.model_budget_cents / 100).toFixed(2)} model budget <span>·</span> {run.timeout_seconds / 60} min</p></div><span className="draft-badge">Draft</span></article>)}</div>}
          </section>
          <footer>Built for thoughtful delegation. <span>Research & artifacts · Execution not connected</span></footer>
        </div>
      </main>
    </div>
  );
}
