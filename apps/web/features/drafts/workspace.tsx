// Mark this module as a React client boundary so its components/hooks can use browser events and
// state.
"use client";

// Import { DraftList } from "./draft-list".
import { DraftList } from "./draft-list";
// Import { useDrafts } from "./use-drafts".
import { useDrafts } from "./use-drafts";

// Define const examples = [
const examples = [
  // Supply this literal text value; literal task examples are only copied into the goal field when
  // selected.
  "Plan a weekend in Boston for two, under $600, with vegetarian food and no car.",
  // Supply this literal text value; literal task examples are only copied into the goal field when
  // selected.
  "Compare three beginner cameras under $500. Include tradeoffs and source links.",
  // Supply this literal text value; literal task examples are only copied into the goal field when
  // selected.
  "Find ideas for a rainy Saturday with friends in NYC, under $40 per person.",
];

// Define export default function Workspace() {
export default function Workspace() {
  // Update the controlled goal field, either from typing, an example, or a successful save.
  const { goal, setGoal, constraints, setConstraints, workers, setWorkers, budget, setBudget,
    // Continue with runs, loading, saving, deleting, error, notice, loadRuns, deleteRun, createRun
    // } = useDrafts();
    runs, loading, saving, deleting, error, notice, loadRuns, deleteRun, createRun } = useDrafts();

  // Return the JSX tree below; React turns these element descriptions into the rendered interface.
  return (
    // JSX line 1: Render a layout/grouping container. className selects styles from globals.css.
    // JSX line 2: Render the workspace navigation sidebar. className selects styles from
    // globals.css.
    // JSX line 3: Supply an accessible name for assistive technology: <a className="brand" href="/"
    // aria-label="AgentCrescendo home"><span className="brandmark">≋</span>
    // Agent<span>Crescendo</span></a>.
    // JSX line 4: Render a layout/grouping container. className selects styles from globals.css.
    // JSX line 5: Hide the purely decorative symbol from assistive technology while leaving it
    // visible. <div className="nav-active"><span aria-hidden="true">◈</span> Task drafts</div>
    // JSX line 6: Render a layout/grouping container. className selects styles from globals.css.
    // JSX line 7: Close the aside element so subsequent content returns to its parent.
    // JSX line 9: Render the primary page content.
    // JSX line 10: Render the page header. className selects styles from globals.css.
    // JSX line 11: Render a layout/grouping container. className selects styles from globals.css.
    // JSX line 12: Render a layout/grouping container. className selects styles from globals.css.
    // JSX line 13: Render the page heading.
    // JSX line 14: Render a paragraph. className selects styles from globals.css.
    // JSX line 16: Render a labeled content section. className selects styles from globals.css.
    // JSX line 17: Connect form submission to createRun; that handler prevents page navigation and
    // waits for confirmed persistence.
    // JSX line 18: Render an input label.
    // JSX line 20: Existing JSX comment: it documents the UI without rendering visible text.
    // JSX line 21: Render an input label.
    // JSX line 23: Render a layout/grouping container. className selects styles from globals.css.
    // JSX line 24: Render a layout/grouping container. className selects styles from globals.css.
    // JSX line 27: Render inline text or a decorative/status marker. className selects styles from
    // globals.css.
    // JSX line 28: Close the div element so subsequent content returns to its parent.
    // JSX line 29: Disable this control while the indicated operation/input condition requires it,
    // preventing duplicate UI actions. <button className="primary" type="submit" disabled={saving
    // || goal.trim().length < 10}>{saving ? "Saving…" : "Save task draft"}<span
    // aria-hidden="true">↗</span></button>
    // JSX line 30: Close the div element so subsequent content returns to its parent.
    // JSX line 31: Close the form element so subsequent content returns to its parent.
    // JSX line 32: Close the section element so subsequent content returns to its parent.
    // JSX line 34: Map this array into UI elements; keys identify the elements across renders.
    // JSX line 36: Hide the purely decorative symbol from assistive technology while leaving it
    // visible. <div className="development-note"><span className="note-icon"
    // aria-hidden="true">i</span><p><strong>Draft mode</strong> Your brief is saved to the local
    // database. Desktop agents, execution, and automatic 24-hour cleanup
    // JSX line 38: Register a click callback; it executes on user interaction, not while rendering.
    // void discards the Promise after the handler handles errors. {error && <div className="error"
    // role="alert">{error} <button type="button" onClick={() => void loadRuns()}>Retry
    // connection</button></div>}
    // JSX line 39: Announce operation notices politely through the live status region.
    // JSX line 41: Render the saved-drafts component with state and callbacks supplied as props.
    // Expressions in braces read current props/state.
    // JSX line 42: Render the page footer.
    // JSX line 43: Close the div element so subsequent content returns to its parent.
    // JSX line 44: Close the main element so subsequent content returns to its parent.
    // JSX line 45: Close the div element so subsequent content returns to its parent.
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
              {/* Optional. A blank value is sent as "" and the API stores it as null. */}
              <label htmlFor="constraints">Constraints <small>(optional)</small></label>
              <textarea id="constraints" maxLength={1000} value={constraints} onChange={event => setConstraints(event.target.value)} placeholder="Budget, dates, must-haves, things to avoid…" />
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

          <DraftList runs={runs} loading={loading} deleting={deleting} onRefresh={loadRuns} onDelete={deleteRun} />
          <footer>Built for thoughtful delegation. <span>Research & artifacts · Execution not connected</span></footer>
        </div>
      </main>
    </div>
  );
}
