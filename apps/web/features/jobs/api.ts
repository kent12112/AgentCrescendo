// Browser-side calls to this app's own /api/jobs routes (same origin). Those server routes add
// the API credential; nothing here sees it.
import type { Application, ApplicationStatus, Filters, JobDetail, Pick, ResumeInfo, SearchPage } from "./types";

export class ApiError extends Error {
  constructor(message: string, readonly status: number) { super(message); }
}

export async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, { cache: "no-store", ...init });
  } catch {
    throw new ApiError("Cannot reach the app server.", 0);
  }
  if (response.status === 204) return undefined as T;
  let data: unknown = null;
  try { data = await response.json(); } catch { /* non-JSON error body */ }
  if (!response.ok) {
    // FastAPI validation errors carry a list in detail; show a plain sentence instead.
    const detail = (data as { detail?: unknown } | null)?.detail;
    throw new ApiError(typeof detail === "string" ? detail : "Please check the search settings.", response.status);
  }
  return data as T;
}

export function searchParams(filters: Filters, offset = 0): URLSearchParams {
  const params = new URLSearchParams({ q: filters.q.trim(), source: "ashby", offset: String(offset), limit: "50" });
  if (filters.hideApplied) params.set("hide_applied", "true");
  if (filters.country.trim()) params.set("country", filters.country.trim());
  for (const city of filters.cities.split(",").map(c => c.trim()).filter(Boolean).slice(0, 5)) {
    params.append("location", city);
  }
  if (filters.remote) params.set("remote", "true");
  if (filters.noSenior) params.set("no_senior", "true");
  if (filters.maxYears !== "") params.set("max_years", filters.maxYears);
  params.set("max_age_days", filters.maxAgeDays);
  return params;
}

export const getSearch = (filters: Filters, offset = 0) =>
  call<SearchPage>(`/api/jobs/search?${searchParams(filters, offset)}`);

export const getDetail = (source: string, postingId: string) =>
  call<JobDetail>(`/api/jobs/postings/${encodeURIComponent(source)}/${encodeURIComponent(postingId)}`);

export const getPicks = () => call<{ picks: Pick[]; max: number }>("/api/jobs/picks");

export const putPicks = (picks: { source: string; posting_id: string }[]) =>
  call<{ picks: Pick[]; max: number }>("/api/jobs/picks", {
    method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ picks }),
  });

export const getResume = () => call<{ resume: ResumeInfo | null }>("/api/jobs/resume");

export function uploadResume(file: File) {
  const extension = file.name.split(".").pop()?.toLowerCase();
  const type = ({ pdf: "application/pdf", md: "text/markdown", txt: "text/plain" } as Record<string, string>)[extension ?? ""];
  if (!type) throw new ApiError("Upload a PDF, .txt, or .md resume.", 415);
  if (file.size > 10 * 1024 * 1024) throw new ApiError("The resume file is larger than 10 MB.", 413);
  return call<{ resume: ResumeInfo }>("/api/jobs/resume", {
    method: "PUT", body: file, headers: { "Content-Type": type, "X-Filename": encodeURIComponent(file.name) },
  });
}

export const deleteResume = () => call<void>("/api/jobs/resume", { method: "DELETE" });

const applicationPath = (ref: { source: string; posting_id: string }) =>
  `/api/jobs/applications/${encodeURIComponent(ref.source)}/${encodeURIComponent(ref.posting_id)}`;
export const getApplications = () => call<{ applications: Application[] }>("/api/jobs/applications");
export const saveApplication = (ref: { source: string; posting_id: string }, data: {
  status: ApplicationStatus; applied_on?: string | null; follow_up_on?: string | null; notes?: string; version?: number;
}) => call<Application>(applicationPath(ref), {
  method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data),
});
export const deleteApplication = (row: Application) => call<void>(`${applicationPath(row)}?version=${row.version}`, { method: "DELETE" });

// Calendar dates follow the user's browser timezone, including near midnight.
export function today() {
  const date = new Date();
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}
