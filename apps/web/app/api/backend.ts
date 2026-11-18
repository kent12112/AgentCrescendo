// Next.js rejects importing this module into a browser component. The credential
// belongs to the server and must never use a NEXT_PUBLIC_ environment variable.
// Prevent this credential-bearing module from being imported into a client component.
import "server-only";

// Allowed API paths. /jobs/... serves the job search page (JOB-F08).
type ApiPath = "/runs" | "/capabilities" | `/runs/${string}` | `/jobs/${string}`;

// options.timeoutMs: the first job search after a crawl builds an in-memory index and needs longer
// than the 5-second default. options.headers: extra headers such as a PDF upload's Content-Type.
export async function backend(path: ApiPath, init?: RequestInit,
  options: { timeoutMs?: number; headers?: Record<string, string>; textDownload?: boolean; pdfDownload?: boolean } = {}) {
  // Restrict destinations to explicit API paths, rather than proxying arbitrary URLs.
  // Read the local API credential in server code; a NEXT_PUBLIC_ variable would expose it to the
  // client.
  const token = process.env.DEV_API_TOKEN;
  // Check this condition: if (!token || token.startsWith("replace-with-") || token.length < 32) {
  if (!token || token.startsWith("replace-with-") || token.length < 32) {
    // Return JSON with an explicit HTTP status; keep internal provider/configuration details out of
    // browser responses.
    return Response.json({ detail: "Configure the server's local API token. See README.md." }, { status: 503 });
  }
  // Start an error-handled block; thrown network/JSON/application errors flow to catch.
  try {
    // Await the same-origin or fixed-backend HTTP request. fetch rejects network errors, but
    // 4xx/5xx responses must be checked explicitly.
    const response = await fetch(new URL(path, process.env.API_BASE_URL ?? "http://127.0.0.1:8000"), {
      // Spread the supplied object properties into this object; later explicit properties override
      // matching keys.
      ...init,
      // Drafts change over time; fetch current data instead of reusing a cache.
      // Set this named object/configuration property: cache: "no-store",. The receiving API
      // determines how the value is used.
      cache: "no-store",
      // Bound upstream waiting. A timeout does not prove a write failed: the API
      // might have committed before its response was lost. Idempotency is future work.
      // Cancel the upstream wait after 5 seconds; this cannot establish whether a write already
      // committed.
      signal: AbortSignal.timeout(options.timeoutMs ?? 5000),
      // Set this named object/configuration property: headers: { "Content-Type":
      // "application/json", Authorization: `Bearer ${token}` },. The receiving API determines how
      // the value is used.
      // Caller headers may replace Content-Type (resume upload) but never the credential.
      headers: { "Content-Type": "application/json", ...options.headers, Authorization: `Bearer ${token}` },
    });
    // A successful deletion has no JSON body to parse.
    // Check this condition: if (response.status === 204) {
    if (response.status === 204) {
      // Return an explicitly empty 204 response; a successful deletion has no JSON body.
      return new Response(null, { status: 204, headers: { "Cache-Control": "no-store" } });
    }
    // Decode the JSON response body; HTTP error statuses still require an explicit response.ok
    // check.
    if (options.textDownload && response.ok) {
      return new Response(await response.text(), { headers: {
        "Content-Type": "text/plain; charset=utf-8",
        "Content-Disposition": response.headers.get("Content-Disposition") ?? "attachment; filename=cover-letter.txt",
        "Cache-Control": "no-store",
      } });
    }
    if (options.pdfDownload && response.ok) {
      return new Response(await response.arrayBuffer(), { headers: {
        "Content-Type": "application/pdf", "X-Content-Type-Options": "nosniff",
        "Content-Disposition": response.headers.get("Content-Disposition") ?? "attachment; filename=cover-letter.pdf",
        "Cache-Control": "no-store",
      } });
    }
    const data = await response.json();
    // Do not relay backend exception bodies or configuration details to the browser.
    // Check this condition: if (response.status >= 500) {
    if (response.status >= 500) {
      // Return JSON with an explicit HTTP status; keep internal provider/configuration details out
      // of browser responses.
      return Response.json({ detail: "The API could not complete the request. Check the API and database." }, { status: 502 });
    }
    // Preserve validation/authentication errors so the caller knows the outcome.
    // Return JSON with an explicit HTTP status; keep internal provider/configuration details out of
    // browser responses.
    return Response.json(data, { status: response.status, headers: { "Cache-Control": "no-store" } });
  // Handle a thrown error from the try block and convert it to a safe user-facing response or
  // message.
  } catch {
    // Return JSON with an explicit HTTP status; keep internal provider/configuration details out of
    // browser responses.
    return Response.json({ detail: "Cannot reach the API. Start the backend and PostgreSQL, then retry." }, { status: 503 });
  }
}
