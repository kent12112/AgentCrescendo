// Next.js rejects importing this module into a browser component. The credential
// belongs to the server and must never use a NEXT_PUBLIC_ environment variable.
import "server-only";

export async function backend(path: "/runs" | "/capabilities" | `/runs/${string}`, init?: RequestInit) {
  // Restrict destinations to explicit API paths, rather than proxying arbitrary URLs.
  const token = process.env.DEV_API_TOKEN;
  if (!token || token.startsWith("replace-with-") || token.length < 32) {
    return Response.json({ detail: "Configure the server's local API token. See README.md." }, { status: 503 });
  }
  try {
    const response = await fetch(new URL(path, process.env.API_BASE_URL ?? "http://127.0.0.1:8000"), {
      ...init,
      // Drafts change over time; fetch current data instead of reusing a cache.
      cache: "no-store",
      // Bound upstream waiting. A timeout does not prove a write failed: the API
      // might have committed before its response was lost. Idempotency is future work.
      signal: AbortSignal.timeout(5000),
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    });
    // A successful deletion has no JSON body to parse.
    if (response.status === 204) {
      return new Response(null, { status: 204, headers: { "Cache-Control": "no-store" } });
    }
    const data = await response.json();
    // Do not relay backend exception bodies or configuration details to the browser.
    if (response.status >= 500) {
      return Response.json({ detail: "The API could not complete the request. Check the API and database." }, { status: 502 });
    }
    // Preserve validation/authentication errors so the caller knows the outcome.
    return Response.json(data, { status: response.status, headers: { "Cache-Control": "no-store" } });
  } catch {
    return Response.json({ detail: "Cannot reach the API. Start the backend and PostgreSQL, then retry." }, { status: 503 });
  }
}
