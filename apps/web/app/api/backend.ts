// Next.js rejects importing this module into a browser component. The credential
// belongs to the server and must never use a NEXT_PUBLIC_ environment variable.
// Learn: Prevent this credential-bearing module from being imported into a client component.
import "server-only";

// Learn: Define an async function returning a Promise: export async function backend(path: "/runs" | "/capabilities" | `/runs/${string}`, init?: RequestInit) {. Its body executes when called/rendered.
export async function backend(path: "/runs" | "/capabilities" | `/runs/${string}`, init?: RequestInit) {
  // Restrict destinations to explicit API paths, rather than proxying arbitrary URLs.
  // Learn: Read the local API credential in server code; a NEXT_PUBLIC_ variable would expose it to the client.
  const token = process.env.DEV_API_TOKEN;
  // Learn: Evaluate this guard before continuing: if (!token || token.startsWith("replace-with-") || token.length < 32) {. || short-circuits on the first truthy value; && stops at the first falsy value.
  if (!token || token.startsWith("replace-with-") || token.length < 32) {
    // Learn: Return JSON with an explicit HTTP status; keep internal provider/configuration details out of browser responses.
    return Response.json({ detail: "Configure the server's local API token. See README.md." }, { status: 503 });
  // Learn: Close the surrounding object, function, call, or type expression; delimiters determine which construct ends here.
  }
  // Learn: Start an error-handled block; thrown network/JSON/application errors flow to catch.
  try {
    // Learn: Await the same-origin or fixed-backend HTTP request. fetch rejects network errors, but 4xx/5xx responses must be checked explicitly.
    const response = await fetch(new URL(path, process.env.API_BASE_URL ?? "http://127.0.0.1:8000"), {
      // Learn: Spread the supplied object properties into this object; later explicit properties override matching keys.
      ...init,
      // Drafts change over time; fetch current data instead of reusing a cache.
      // Learn: Set this named object/configuration property: cache: "no-store",. The receiving API determines how the value is used.
      cache: "no-store",
      // Bound upstream waiting. A timeout does not prove a write failed: the API
      // might have committed before its response was lost. Idempotency is future work.
      // Learn: Cancel the upstream wait after 5 seconds; this cannot establish whether a write already committed.
      signal: AbortSignal.timeout(5000),
      // Learn: Set this named object/configuration property: headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },. The receiving API determines how the value is used.
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    // Learn: Close the surrounding object, function, call, or type expression; delimiters determine which construct ends here.
    });
    // A successful deletion has no JSON body to parse.
    // Learn: Evaluate this guard before continuing: if (response.status === 204) {. || short-circuits on the first truthy value; && stops at the first falsy value.
    if (response.status === 204) {
      // Learn: Return an explicitly empty 204 response; a successful deletion has no JSON body.
      return new Response(null, { status: 204, headers: { "Cache-Control": "no-store" } });
    // Learn: Close the surrounding object, function, call, or type expression; delimiters determine which construct ends here.
    }
    // Learn: Decode the JSON response body; HTTP error statuses still require an explicit response.ok check.
    const data = await response.json();
    // Do not relay backend exception bodies or configuration details to the browser.
    // Learn: Evaluate this guard before continuing: if (response.status >= 500) {. || short-circuits on the first truthy value; && stops at the first falsy value.
    if (response.status >= 500) {
      // Learn: Return JSON with an explicit HTTP status; keep internal provider/configuration details out of browser responses.
      return Response.json({ detail: "The API could not complete the request. Check the API and database." }, { status: 502 });
    // Learn: Close the surrounding object, function, call, or type expression; delimiters determine which construct ends here.
    }
    // Preserve validation/authentication errors so the caller knows the outcome.
    // Learn: Return JSON with an explicit HTTP status; keep internal provider/configuration details out of browser responses.
    return Response.json(data, { status: response.status, headers: { "Cache-Control": "no-store" } });
  // Learn: Handle a thrown error from the try block and convert it to a safe user-facing response or message.
  } catch {
    // Learn: Return JSON with an explicit HTTP status; keep internal provider/configuration details out of browser responses.
    return Response.json({ detail: "Cannot reach the API. Start the backend and PostgreSQL, then retry." }, { status: 503 });
  // Learn: Close the surrounding object, function, call, or type expression; delimiters determine which construct ends here.
  }
// Learn: Close the surrounding object, function, call, or type expression; delimiters determine which construct ends here.
}
