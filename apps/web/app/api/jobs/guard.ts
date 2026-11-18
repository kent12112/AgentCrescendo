// Shared checks for the job search proxy routes (JOB-F08). Server-only, like backend.ts.
import "server-only";

// Writes must come from this app's own page: a page on another origin must not be able to use
// the server's API credential through this proxy (same rule as /api/runs).
export function crossOriginWrite(request: Request): Response | null {
  const origin = request.headers.get("origin");
  const host = request.headers.get("host");
  if (!origin || !host || origin !== `${new URL(request.url).protocol}//${host}`) {
    return Response.json({ detail: "Cross-origin writes are not permitted." }, { status: 403 });
  }
  return null;
}

// Same shapes the API accepts; checked here too so nothing unexpected is put into an API path.
export const SOURCE = /^(ashby|greenhouse|lever)$/;
export const POSTING_ID = /^[A-Za-z0-9-]{1,64}$/;
