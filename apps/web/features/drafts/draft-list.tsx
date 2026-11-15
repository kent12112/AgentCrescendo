// Learn: Import compile-time types only; this import is erased from emitted JavaScript: import type { Run } from "./types";.
import type { Run } from "./types";

// Learn: Define a compile-time shape for DraftListProps. TypeScript types do not validate incoming JSON at runtime.
type DraftListProps = {
  // Learn: Require an array of Run response objects for the draft-list props.
  runs: Run[];
  // Learn: Declare this property’s compile-time type: loading: boolean;. A ? marks an optional property; | null permits explicit absence.
  loading: boolean;
  // Learn: Declare this property’s compile-time type: deleting: string | null;. A ? marks an optional property; | null permits explicit absence.
  deleting: string | null;
  // Learn: Declare this callback type; => separates its parameters from its return type. It does not execute a callback here.
  onRefresh: () => Promise<void>;
  // Learn: Declare this callback type; => separates its parameters from its return type. It does not execute a callback here.
  onDelete: (run: Run) => Promise<void>;
// Learn: Close the surrounding object, function, call, or type expression; delimiters determine which construct ends here.
};

// Learn: Define a function/component: export function DraftList({ runs, loading, deleting, onRefresh, onDelete }: DraftListProps) {. Its body executes when called/rendered.
export function DraftList({ runs, loading, deleting, onRefresh, onDelete }: DraftListProps) {
  // Learn: Return the JSX tree below; React turns these element descriptions into the rendered interface.
  return (
    // Learn JSX line 1: Render a labeled content section. className selects styles from globals.css.
    // Learn JSX line 2: Render a layout/grouping container. className selects styles from globals.css.
    // Learn JSX line 3: Render a section heading. Expressions in braces read current props/state.
    // Learn JSX line 4: Register a click callback; it executes on user interaction, not while rendering. void discards the Promise after the handler handles errors. <button className="refresh" type="button" disabled={loading || deleting !== null} onClick={() => void onRefresh()}>
    // Learn JSX line 5: Show Loading… on the refresh button while a request is pending; otherwise show Refresh.
    // Learn JSX line 6: Close the button element so subsequent content returns to its parent.
    // Learn JSX line 7: Close the div element so subsequent content returns to its parent.
    // Learn JSX line 8: Render the loading state first; otherwise choose the empty state or saved-draft list.
    // Learn JSX line 9: Render a layout/grouping container. className selects styles from globals.css.
    // Learn JSX line 10: Close the current JSX expression/conditional branch; rendering continues in the enclosing element.
    // Learn JSX line 11: Render a layout/grouping container. className selects styles from globals.css.
    // Learn JSX line 12: Hide the purely decorative symbol from assistive technology while leaving it visible. <div className="empty-symbol" aria-hidden="true">⌁</div>
    // Learn JSX line 13: Render a draft title or empty-state heading.
    // Learn JSX line 14: Render a paragraph.
    // Learn JSX line 15: Close the div element so subsequent content returns to its parent.
    // Learn JSX line 16: Close the current JSX expression/conditional branch; rendering continues in the enclosing element.
    // Learn JSX line 17: Render a layout/grouping container. className selects styles from globals.css.
    // Learn JSX line 18: Map each saved draft to a keyed article; a stable run.id lets React track item identity across updates.
    // Learn JSX line 19: Render one saved draft. className selects styles from globals.css. Expressions in braces read current props/state.
    // Learn JSX line 20: Hide the purely decorative symbol from assistive technology while leaving it visible. <div className="run-symbol" aria-hidden="true">↗</div>
    // Learn JSX line 21: Render a layout/grouping container. className selects styles from globals.css.
    // Learn JSX line 22: Render a draft title or empty-state heading. Expressions in braces read current props/state.
    // Learn JSX line 23: Render the constraints paragraph only when the draft has nonempty constraints.
    // Learn JSX line 24: Render a paragraph.
    // Learn JSX line 25: Render inline text or a decorative/status marker. Expressions in braces read current props/state.
    // Learn JSX line 26: Convert integer cents to dollars for display, formatting exactly two decimal places; stored money remains integer cents.
    // Learn JSX line 27: Convert saved seconds to minutes for display.
    // Learn JSX line 28: Close the p element so subsequent content returns to its parent.
    // Learn JSX line 29: Close the div element so subsequent content returns to its parent.
    // Learn JSX line 30: Render inline text or a decorative/status marker. className selects styles from globals.css.
    // Learn JSX line 31: Render an explicit user action.
    // Learn JSX line 32: Set this JSX prop: className="delete-draft". Quoted values are strings; braces evaluate JavaScript expressions.
    // Learn JSX line 33: Set this JSX prop: type="button". Quoted values are strings; braces evaluate JavaScript expressions.
    // Learn JSX line 34: Disable this control while the indicated operation/input condition requires it, preventing duplicate UI actions. disabled={deleting !== null}
    // Learn JSX line 35: Supply an accessible name for assistive technology: aria-label={`Delete draft: ${run.goal}`}.
    // Learn JSX line 36: Register a click callback; it executes on user interaction, not while rendering. void discards the Promise after the handler handles errors. onClick={() => void onDelete(run)}
    // Learn JSX line 37: Finish the multi-line opening tag; the following lines become this element’s children.
    // Learn JSX line 38: Evaluate this JSX expression as content: {deleting === run.id ? "Deleting…" : "Delete"}. React escapes string content rather than treating it as executable HTML.
    // Learn JSX line 39: Close the button element so subsequent content returns to its parent.
    // Learn JSX line 40: Close the article element so subsequent content returns to its parent.
    // Learn JSX line 41: Close the current JSX expression/conditional branch; rendering continues in the enclosing element.
    // Learn JSX line 42: Close the div element so subsequent content returns to its parent.
    // Learn JSX line 43: Close the current JSX expression/conditional branch; rendering continues in the enclosing element.
    // Learn JSX line 44: Close the section element so subsequent content returns to its parent.
    <section className="drafts" aria-labelledby="drafts-heading">
      <div className="section-heading">
        <h2 id="drafts-heading">Recent drafts <span>{runs.length}</span></h2>
        <button className="refresh" type="button" disabled={loading || deleting !== null} onClick={() => void onRefresh()}>
          {loading ? "Loading…" : "Refresh"}
        </button>
      </div>
      {loading ? (
        <div className="empty">Loading your saved briefs…</div>
      ) : runs.length === 0 ? (
        <div className="empty">
          <div className="empty-symbol" aria-hidden="true">⌁</div>
          <h3>Your first task starts here.</h3>
          <p>Save a brief above. It will stay here when you come back.</p>
        </div>
      ) : (
        <div className="run-list">
          {runs.map(run => (
            <article className="run" key={run.id}>
              <div className="run-symbol" aria-hidden="true">↗</div>
              <div className="run-main">
                <h3>{run.goal}</h3>
                {run.constraints && <p>Constraints: {run.constraints}</p>}
                <p>
                  {run.max_workers} {run.max_workers === 1 ? "worker" : "workers"} <span>·</span>{" "}
                  ${(run.model_budget_cents / 100).toFixed(2)} model budget <span>·</span>{" "}
                  {run.timeout_seconds / 60} min
                </p>
              </div>
              <span className="draft-badge">Draft</span>
              <button
                className="delete-draft"
                type="button"
                disabled={deleting !== null}
                aria-label={`Delete draft: ${run.goal}`}
                onClick={() => void onDelete(run)}
              >
                {deleting === run.id ? "Deleting…" : "Delete"}
              </button>
            </article>
          ))}
        </div>
      )}
    </section>
  // Learn: Close the surrounding object, function, call, or type expression; delimiters determine which construct ends here.
  );
// Learn: Close the surrounding object, function, call, or type expression; delimiters determine which construct ends here.
}
