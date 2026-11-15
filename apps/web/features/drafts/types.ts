// TypeScript checks how our UI uses responses; this type does not validate JSON
// at runtime. The API's Pydantic schemas define the actual HTTP contract.
// Learn: Define a compile-time shape for Run. TypeScript types do not validate incoming JSON at runtime.
export type Run = {
  // Learn: Declare this property’s compile-time type: id: string;. A ? marks an optional property; | null permits explicit absence.
  id: string;
  // Learn: Declare this property’s compile-time type: goal: string;. A ? marks an optional property; | null permits explicit absence.
  goal: string;
  // Learn: Set this named object/configuration property: status: "draft";. The receiving API determines how the value is used.
  status: "draft";
  // Learn: Declare this property’s compile-time type: max_workers: number;. A ? marks an optional property; | null permits explicit absence.
  max_workers: number;
  // Learn: Declare this property’s compile-time type: timeout_seconds: number;. A ? marks an optional property; | null permits explicit absence.
  timeout_seconds: number;
  // Learn: Declare this property’s compile-time type: model_budget_cents: number;. A ? marks an optional property; | null permits explicit absence.
  model_budget_cents: number;
  // Learn: Declare this property’s compile-time type: constraints: string | null;. A ? marks an optional property; | null permits explicit absence.
  constraints: string | null;
  // Learn: Declare this property’s compile-time type: created_at: string;. A ? marks an optional property; | null permits explicit absence.
  created_at: string;
// Learn: Close the surrounding object, function, call, or type expression; delimiters determine which construct ends here.
};

