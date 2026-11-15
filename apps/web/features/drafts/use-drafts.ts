// Learn: Mark this module as a React client boundary so its components/hooks can use browser events and state.
"use client";

// Learn: Import these module exports for use below: import { useEffect, useState, type FormEvent } from "react";. Named imports use braces; a default import has no braces.
import { useEffect, useState, type FormEvent } from "react";
// Learn: Import compile-time types only; this import is erased from emitted JavaScript: import type { Run } from "./types";.
import type { Run } from "./types";

// Learn: Define a function/component: function errorMessage(data: { detail?: unknown }) {. Its body executes when called/rendered.
function errorMessage(data: { detail?: unknown }) {
  // Learn: Evaluate this guard before continuing: if (typeof data.detail === "string") return data.detail;. || short-circuits on the first truthy value; && stops at the first falsy value.
  if (typeof data.detail === "string") return data.detail;
  // Learn: Return "Please check the task and limits, then try again."; to the caller; this exits the current function.
  return "Please check the task and limits, then try again.";
// Learn: Close the surrounding object, function, call, or type expression; delimiters determine which construct ends here.
}

// Learn: Define a function/component: export function useDrafts() {. Its body executes when called/rendered.
export function useDrafts() {
  // Form state and server-loaded drafts live in React memory. The database is
  // the durable source; refreshing the page reloads it rather than losing drafts.
  // Learn: Create state plus a setter; calling the setter schedules a render, rather than mutating the current render value. This line initializes goal, setGoal.
  const [goal, setGoal] = useState("");
  // Learn: Create state plus a setter; calling the setter schedules a render, rather than mutating the current render value. This line initializes constraints, setConstraints.
  const [constraints, setConstraints] = useState("");
  // Learn: Create state plus a setter; calling the setter schedules a render, rather than mutating the current render value. This line initializes workers, setWorkers.
  const [workers, setWorkers] = useState(3);
  // Learn: Create state plus a setter; calling the setter schedules a render, rather than mutating the current render value. This line initializes budget, setBudget.
  const [budget, setBudget] = useState(100);
  // Learn: Create state plus a setter; calling the setter schedules a render, rather than mutating the current render value. This line initializes runs, setRuns.
  const [runs, setRuns] = useState<Run[]>([]);
  // Learn: Create state plus a setter; calling the setter schedules a render, rather than mutating the current render value. This line initializes loading, setLoading.
  const [loading, setLoading] = useState(true);
  // Learn: Create state plus a setter; calling the setter schedules a render, rather than mutating the current render value. This line initializes saving, setSaving.
  const [saving, setSaving] = useState(false);
  // Learn: Create state plus a setter; calling the setter schedules a render, rather than mutating the current render value. This line initializes deleting, setDeleting.
  const [deleting, setDeleting] = useState<string | null>(null);
  // Learn: Create state plus a setter; calling the setter schedules a render, rather than mutating the current render value. This line initializes error, setError.
  const [error, setError] = useState("");
  // Learn: Create state plus a setter; calling the setter schedules a render, rather than mutating the current render value. This line initializes notice, setNotice.
  const [notice, setNotice] = useState("");

  // Learn: Define an async function returning a Promise: async function loadRuns() {. Its body executes when called/rendered.
  async function loadRuns() {
    // Learn: Set whether the draft list is waiting for a server response.
    setLoading(true);
    // Learn: Update the user-visible error; an empty string clears the previous error.
    setError("");
    // Learn: Start an error-handled block; thrown network/JSON/application errors flow to catch.
    try {
      // Learn: Await the same-origin or fixed-backend HTTP request. fetch rejects network errors, but 4xx/5xx responses must be checked explicitly.
      const response = await fetch("/api/runs", { cache: "no-store" });
      // Learn: Decode the JSON response body; HTTP error statuses still require an explicit response.ok check.
      const data = await response.json();
      // fetch only rejects network failures automatically; 4xx/5xx responses
      // need this explicit check so an error body is not mistaken for draft data.
      // Learn: Evaluate this guard before continuing: if (!response.ok) throw new Error(errorMessage(data));. || short-circuits on the first truthy value; && stops at the first falsy value.
      if (!response.ok) throw new Error(errorMessage(data));
      // Learn: Update saved drafts; the functional updater receives the latest state rather than a captured render snapshot.
      setRuns(data);
    // Learn: Handle a thrown error from the try block and convert it to a safe user-facing response or message.
    } catch (error) {
      // Learn: Update the user-visible error; an empty string clears the previous error.
      setError(error instanceof Error ? error.message : "Unable to load drafts.");
    // Learn: Always reset pending-operation state when the try/catch exits, including a failed request.
    } finally { setLoading(false); }
  // Learn: Close the surrounding object, function, call, or type expression; delimiters determine which construct ends here.
  }

  // Load after the component mounts. void intentionally discards the promise;
  // loadRuns handles errors itself and updates the visible connection message.
  // Learn: Run after mount; the empty dependency array requests initial loading for each mount (development Strict Mode can repeat effects).
  useEffect(() => { void loadRuns(); }, []);

  // Learn: Define an async function returning a Promise: async function deleteRun(run: Run) {. Its body executes when called/rendered.
  async function deleteRun(run: Run) {
    // Learn: Evaluate this guard before continuing: if (!window.confirm(`Permanently delete this draft?\n\n${run.goal}`)) return;. || short-circuits on the first truthy value; && stops at the first falsy value.
    if (!window.confirm(`Permanently delete this draft?\n\n${run.goal}`)) return;
    // Learn: Set the draft ID being deleted, or null when no deletion is pending.
    setDeleting(run.id);
    // Learn: Update the user-visible error; an empty string clears the previous error.
    setError("");
    // Learn: Update the polite success/status message shown after a confirmed result.
    setNotice("");
    // Learn: Start an error-handled block; thrown network/JSON/application errors flow to catch.
    try {
      // Learn: Await the same-origin or fixed-backend HTTP request. fetch rejects network errors, but 4xx/5xx responses must be checked explicitly.
      const response = await fetch(`/api/runs/${run.id}`, { method: "DELETE" });
      // A 404 also establishes that the draft is absent (for example, another
      // tab deleted it). Never parse JSON on an empty 204 response.
      // Learn: Evaluate this guard before continuing: if (response.status !== 204 && response.status !== 404) {. || short-circuits on the first truthy value; && stops at the first falsy value.
      if (response.status !== 204 && response.status !== 404) {
        // Learn: Decode the JSON response body; HTTP error statuses still require an explicit response.ok check.
        const data = await response.json();
        // Learn: Continue this expression: throw new Error(errorMessage(data));. Its braces/brackets keep it within the enclosing declaration or call.
        throw new Error(errorMessage(data));
      // Learn: Close the surrounding object, function, call, or type expression; delimiters determine which construct ends here.
      }
      // Learn: Update saved drafts; the functional updater receives the latest state rather than a captured render snapshot.
      setRuns(previous => previous.filter(item => item.id !== run.id));
      // Learn: Update the polite success/status message shown after a confirmed result.
      setNotice(response.status === 404 ? "This draft was already deleted." : "Draft deleted.");
    // Learn: Handle a thrown error from the try block and convert it to a safe user-facing response or message.
    } catch (error) {
      // Learn: Update the user-visible error; an empty string clears the previous error.
      setError(error instanceof Error ? error.message : "Unable to delete draft. Refresh to check its current status.");
    // Learn: Always reset pending-operation state when the try/catch exits, including a failed request.
    } finally { setDeleting(null); }
  // Learn: Close the surrounding object, function, call, or type expression; delimiters determine which construct ends here.
  }

  // Learn: Define an async function returning a Promise: async function createRun(event: FormEvent) {. Its body executes when called/rendered.
  async function createRun(event: FormEvent) {
    // Handle submission in JavaScript instead of reloading the browser page.
    // Learn: Prevent the form’s default full-page navigation so JavaScript can handle saving.
    event.preventDefault();
    // Learn: Set whether draft submission is in progress, controlling duplicate-click prevention.
    setSaving(true);
    // Learn: Update the user-visible error; an empty string clears the previous error.
    setError("");
    // Learn: Update the polite success/status message shown after a confirmed result.
    setNotice("");
    // Learn: Start an error-handled block; thrown network/JSON/application errors flow to catch.
    try {
      // Learn: Await the same-origin or fixed-backend HTTP request. fetch rejects network errors, but 4xx/5xx responses must be checked explicitly.
      const response = await fetch("/api/runs", {
        // Learn: Set this named object/configuration property: method: "POST",. The receiving API determines how the value is used.
        method: "POST",
        // Learn: Set this named object/configuration property: headers: { "Content-Type": "application/json" },. The receiving API determines how the value is used.
        headers: { "Content-Type": "application/json" },
        // Learn: Serialize the draft payload to JSON; the API independently validates its fields.
        body: JSON.stringify({ goal: goal.trim(), max_workers: workers, timeout_seconds: 600, model_budget_cents: budget, constraints }),
      // Learn: Close the surrounding object, function, call, or type expression; delimiters determine which construct ends here.
      });
      // Learn: Decode the JSON response body; HTTP error statuses still require an explicit response.ok check.
      const data = await response.json();
      // Learn: Evaluate this guard before continuing: if (!response.ok) throw new Error(errorMessage(data));. || short-circuits on the first truthy value; && stops at the first falsy value.
      if (!response.ok) throw new Error(errorMessage(data));
      // Only show a saved draft after the server confirms it. The functional
      // updater uses the latest React state, then keeps the newest 25 entries.
      // Learn: Update saved drafts; the functional updater receives the latest state rather than a captured render snapshot.
      setRuns(previous => [data, ...previous].slice(0, 25));
      // Learn: Update the controlled goal field, either from typing, an example, or a successful save.
      setGoal("");
      // Learn: Update the controlled optional constraints field.
      setConstraints("");
      // Learn: Update the polite success/status message shown after a confirmed result.
      setNotice("Draft saved. No agents have started and no model costs were incurred.");
    // Learn: Handle a thrown error from the try block and convert it to a safe user-facing response or message.
    } catch (error) {
      // Learn: Update the user-visible error; an empty string clears the previous error.
      setError(error instanceof Error ? error.message : "Unable to save draft.");
    // Learn: Always reset pending-operation state when the try/catch exits, including a failed request.
    } finally { setSaving(false); }
  // Learn: Close the surrounding object, function, call, or type expression; delimiters determine which construct ends here.
  }

  // Learn: Update the controlled goal field, either from typing, an example, or a successful save.
  return { goal, setGoal, constraints, setConstraints, workers, setWorkers, budget, setBudget,
    // Learn: Continue this expression: runs, loading, saving, deleting, error, notice, loadRuns, deleteRun, createRun };. Its braces/brackets keep it within the enclosing declaration or call.
    runs, loading, saving, deleting, error, notice, loadRuns, deleteRun, createRun };
// Learn: Close the surrounding object, function, call, or type expression; delimiters determine which construct ends here.
}
