// TypeScript checks how our UI uses responses; this type does not validate JSON
// at runtime. The API's Pydantic schemas define the actual HTTP contract.
// Define a compile-time shape for Run. TypeScript types do not validate incoming JSON at runtime.
export type Run = {
  // Declare this property’s compile-time type: id: string;. A ? marks an optional property; | null
  // permits explicit absence.
  id: string;
  // Declare this property’s compile-time type: goal: string;. A ? marks an optional property; |
  // null permits explicit absence.
  goal: string;
  // Lifecycle state; mirrors the API's RunRead.status values.
  status: "draft" | "starting" | "started";
  // Declare this property’s compile-time type: max_workers: number;. A ? marks an optional
  // property; | null permits explicit absence.
  max_workers: number;
  // Declare this property’s compile-time type: timeout_seconds: number;. A ? marks an optional
  // property; | null permits explicit absence.
  timeout_seconds: number;
  // Declare this property’s compile-time type: model_budget_cents: number;. A ? marks an optional
  // property; | null permits explicit absence.
  model_budget_cents: number;
  // Declare this property’s compile-time type: constraints: string | null;. A ? marks an optional
  // property; | null permits explicit absence.
  constraints: string | null;
  // Declare this property’s compile-time type: created_at: string;. A ? marks an optional property;
  // | null permits explicit absence.
  created_at: string;
  // Stable Temporal workflow ID; null while the run is a draft.
  workflow_id: string | null;
  // When the start was first requested; null while the run is a draft.
  start_requested_at: string | null;
};

