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
  // Set this named object/configuration property: status: "draft";. The receiving API determines
  // how the value is used.
  status: "draft";
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
};

