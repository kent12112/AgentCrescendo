// Mark this module as a React client boundary so its components/hooks can use browser events and
// state.
"use client";

// Import { useEffect, useState, type FormEvent } from "react".
import { useEffect, useState, type FormEvent } from "react";
// Import types { Run } from "./types"; these are removed from emitted JavaScript.
import type { Run } from "./types";

// Define function errorMessage(data: { detail?: unknown }) {
function errorMessage(data: { detail?: unknown }) {
  // Check this condition: if (typeof data.detail === "string") return data.detail;
  if (typeof data.detail === "string") return data.detail;
  // Return "Please check the task and limits, then try again."; to the caller; this exits the
  // current function.
  return "Please check the task and limits, then try again.";
}

// Define export function useDrafts() {
export function useDrafts() {
  // Form state and server-loaded drafts live in React memory. The database is
  // the durable source; refreshing the page reloads it rather than losing drafts.
  // Start goal at ""; setGoal schedules an update and re-render.
  const [goal, setGoal] = useState("");
  // Start constraints at ""; setConstraints schedules an update and re-render.
  const [constraints, setConstraints] = useState("");
  // Start workers at 3; setWorkers schedules an update and re-render.
  const [workers, setWorkers] = useState(3);
  // Start budget at 100; setBudget schedules an update and re-render.
  const [budget, setBudget] = useState(100);
  // Start runs at []; setRuns schedules an update and re-render.
  const [runs, setRuns] = useState<Run[]>([]);
  // Start loading at true; setLoading schedules an update and re-render.
  const [loading, setLoading] = useState(true);
  // Start saving at false; setSaving schedules an update and re-render.
  const [saving, setSaving] = useState(false);
  // Start deleting at null; setDeleting schedules an update and re-render.
  const [deleting, setDeleting] = useState<string | null>(null);
  // Start error at ""; setError schedules an update and re-render.
  const [error, setError] = useState("");
  // Start notice at ""; setNotice schedules an update and re-render.
  const [notice, setNotice] = useState("");

  // Define async function loadRuns() {
  async function loadRuns() {
    // Set whether the draft list is waiting for a server response.
    setLoading(true);
    // Update the user-visible error; an empty string clears the previous error.
    setError("");
    // Start an error-handled block; thrown network/JSON/application errors flow to catch.
    try {
      // Await the same-origin or fixed-backend HTTP request. fetch rejects network errors, but
      // 4xx/5xx responses must be checked explicitly.
      const response = await fetch("/api/runs", { cache: "no-store" });
      // Decode the JSON response body; HTTP error statuses still require an explicit response.ok
      // check.
      const data = await response.json();
      // fetch only rejects network failures automatically; 4xx/5xx responses
      // need this explicit check so an error body is not mistaken for draft data.
      // Check this condition: if (!response.ok) throw new Error(errorMessage(data));
      if (!response.ok) throw new Error(errorMessage(data));
      // Update saved drafts; the functional updater receives the latest state rather than a
      // captured render snapshot.
      setRuns(data);
    // Handle a thrown error from the try block and convert it to a safe user-facing response or
    // message.
    } catch (error) {
      // Update the user-visible error; an empty string clears the previous error.
      setError(error instanceof Error ? error.message : "Unable to load drafts.");
    // Always reset pending-operation state when the try/catch exits, including a failed request.
    } finally { setLoading(false); }
  }

  // Load after the component mounts. void intentionally discards the promise;
  // loadRuns handles errors itself and updates the visible connection message.
  // Run after mount; the empty dependency array requests initial loading for each mount
  // (development Strict Mode can repeat effects).
  useEffect(() => { void loadRuns(); }, []);

  // Define async function deleteRun(run: Run) {
  async function deleteRun(run: Run) {
    // Check this condition: if (!window.confirm(`Permanently delete this draft?\n\n${run.goal}`))
    // return;
    if (!window.confirm(`Permanently delete this draft?\n\n${run.goal}`)) return;
    // Set the draft ID being deleted, or null when no deletion is pending.
    setDeleting(run.id);
    // Update the user-visible error; an empty string clears the previous error.
    setError("");
    // Update the polite success/status message shown after a confirmed result.
    setNotice("");
    // Start an error-handled block; thrown network/JSON/application errors flow to catch.
    try {
      // Await the same-origin or fixed-backend HTTP request. fetch rejects network errors, but
      // 4xx/5xx responses must be checked explicitly.
      const response = await fetch(`/api/runs/${run.id}`, { method: "DELETE" });
      // A 404 also establishes that the draft is absent (for example, another
      // tab deleted it). Never parse JSON on an empty 204 response.
      // Check this condition: if (response.status !== 204 && response.status !== 404) {
      if (response.status !== 204 && response.status !== 404) {
        // Decode the JSON response body; HTTP error statuses still require an explicit response.ok
        // check.
        const data = await response.json();
        // Continue with throw new Error(errorMessage(data));
        throw new Error(errorMessage(data));
      }
      // Update saved drafts; the functional updater receives the latest state rather than a
      // captured render snapshot.
      setRuns(previous => previous.filter(item => item.id !== run.id));
      // Update the polite success/status message shown after a confirmed result.
      setNotice(response.status === 404 ? "This draft was already deleted." : "Draft deleted.");
    // Handle a thrown error from the try block and convert it to a safe user-facing response or
    // message.
    } catch (error) {
      // Update the user-visible error; an empty string clears the previous error.
      setError(error instanceof Error ? error.message : "Unable to delete draft. Refresh to check its current status.");
    // Always reset pending-operation state when the try/catch exits, including a failed request.
    } finally { setDeleting(null); }
  }

  // Define async function createRun(event: FormEvent) {
  async function createRun(event: FormEvent) {
    // Handle submission in JavaScript instead of reloading the browser page.
    // Prevent the form’s default full-page navigation so JavaScript can handle saving.
    event.preventDefault();
    // Set whether draft submission is in progress, controlling duplicate-click prevention.
    setSaving(true);
    // Update the user-visible error; an empty string clears the previous error.
    setError("");
    // Update the polite success/status message shown after a confirmed result.
    setNotice("");
    // Start an error-handled block; thrown network/JSON/application errors flow to catch.
    try {
      // Await the same-origin or fixed-backend HTTP request. fetch rejects network errors, but
      // 4xx/5xx responses must be checked explicitly.
      const response = await fetch("/api/runs", {
        // Set this named object/configuration property: method: "POST",. The receiving API
        // determines how the value is used.
        method: "POST",
        // Set this named object/configuration property: headers: { "Content-Type":
        // "application/json" },. The receiving API determines how the value is used.
        headers: { "Content-Type": "application/json" },
        // Serialize the draft payload to JSON; the API independently validates its fields.
        body: JSON.stringify({ goal: goal.trim(), max_workers: workers, timeout_seconds: 600, model_budget_cents: budget, constraints }),
      });
      // Decode the JSON response body; HTTP error statuses still require an explicit response.ok
      // check.
      const data = await response.json();
      // Check this condition: if (!response.ok) throw new Error(errorMessage(data));
      if (!response.ok) throw new Error(errorMessage(data));
      // Only show a saved draft after the server confirms it. The functional
      // updater uses the latest React state, then keeps the newest 25 entries.
      // Update saved drafts; the functional updater receives the latest state rather than a
      // captured render snapshot.
      setRuns(previous => [data, ...previous].slice(0, 25));
      // Update the controlled goal field, either from typing, an example, or a successful save.
      setGoal("");
      // Update the controlled optional constraints field.
      setConstraints("");
      // Update the polite success/status message shown after a confirmed result.
      setNotice("Draft saved. No agents have started and no model costs were incurred.");
    // Handle a thrown error from the try block and convert it to a safe user-facing response or
    // message.
    } catch (error) {
      // Update the user-visible error; an empty string clears the previous error.
      setError(error instanceof Error ? error.message : "Unable to save draft.");
    // Always reset pending-operation state when the try/catch exits, including a failed request.
    } finally { setSaving(false); }
  }

  // Update the controlled goal field, either from typing, an example, or a successful save.
  return { goal, setGoal, constraints, setConstraints, workers, setWorkers, budget, setBudget,
    // Continue with runs, loading, saving, deleting, error, notice, loadRuns, deleteRun, createRun
    // };
    runs, loading, saving, deleting, error, notice, loadRuns, deleteRun, createRun };
}
