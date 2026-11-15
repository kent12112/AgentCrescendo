// Learn: Import these module exports for use below: import { backend } from "../backend";. Named imports use braces; a default import has no braces.
import { backend } from "../backend";

// Learn: Define an async function returning a Promise: export async function GET() {. Its body executes when called/rendered.
export async function GET() {
  // Browser calls /api/runs on Next.js; Next.js calls /runs on FastAPI with the
  // server credential. This avoids exposing that credential to client JavaScript.
  // Learn: Forward this permitted API path through the server-only proxy, which attaches the local credential.
  return backend("/runs");
// Learn: Close the surrounding object, function, call, or type expression; delimiters determine which construct ends here.
}

// Learn: Define an async function returning a Promise: export async function POST(request: Request) {. Its body executes when called/rendered.
export async function POST(request: Request) {
  // This is a local single-user proxy, not multi-user authentication. A browser
  // on another origin must not be able to borrow the proxy's backend credential.
  // The local server supplies the backend credential. Require same-origin writes.
  // Learn: Read the browser Origin header for the same-origin write boundary.
  const origin = request.headers.get("origin");
  // Next.js may normalize request.url to localhost even when the browser used
  // 127.0.0.1. Host retains the browser-facing authority in this local setup.
  // Learn: Read the browser-facing host, since Next.js may normalize the internal request URL.
  const host = request.headers.get("host");
  // Learn: Use URL parsing/resolution rather than concatenating arbitrary untrusted destinations.
  const expectedOrigin = `${new URL(request.url).protocol}//${host}`;
  // Learn: Evaluate this guard before continuing: if (!origin || !host || origin !== expectedOrigin) {. || short-circuits on the first truthy value; && stops at the first falsy value.
  if (!origin || !host || origin !== expectedOrigin) {
    // Learn: Return JSON with an explicit HTTP status; keep internal provider/configuration details out of browser responses.
    return Response.json({ detail: "Cross-origin writes are not permitted." }, { status: 403 });
  // Learn: Close the surrounding object, function, call, or type expression; delimiters determine which construct ends here.
  }
  // Learn: Evaluate this guard before continuing: if (!request.headers.get("content-type")?.startsWith("application/json")) {. || short-circuits on the first truthy value; && stops at the first falsy value.
  if (!request.headers.get("content-type")?.startsWith("application/json")) {
    // Learn: Return JSON with an explicit HTTP status; keep internal provider/configuration details out of browser responses.
    return Response.json({ detail: "Expected JSON." }, { status: 415 });
  // Learn: Close the surrounding object, function, call, or type expression; delimiters determine which construct ends here.
  }
  // Bound the buffered text we forward. This character-count check is not a
  // streaming byte limit; enforce transport-level body limits before public hosting.
  // Learn: Read the request body as text before applying the character-count limit.
  const body = await request.text();
  // Learn: Evaluate this guard before continuing: if (body.length > 20_000) {. || short-circuits on the first truthy value; && stops at the first falsy value.
  if (body.length > 20_000) {
    // Learn: Return JSON with an explicit HTTP status; keep internal provider/configuration details out of browser responses.
    return Response.json({ detail: "Request is too large." }, { status: 413 });
  // Learn: Close the surrounding object, function, call, or type expression; delimiters determine which construct ends here.
  }
  // Check JSON syntax here; FastAPI remains responsible for field-level validation.
  // Learn: Check JSON syntax before forwarding; field-level validation remains in FastAPI.
  try { JSON.parse(body); } catch {
    // Learn: Return JSON with an explicit HTTP status; keep internal provider/configuration details out of browser responses.
    return Response.json({ detail: "Invalid JSON." }, { status: 400 });
  // Learn: Close the surrounding object, function, call, or type expression; delimiters determine which construct ends here.
  }
  // Learn: Forward this permitted API path through the server-only proxy, which attaches the local credential.
  return backend("/runs", { method: "POST", body });
// Learn: Close the surrounding object, function, call, or type expression; delimiters determine which construct ends here.
}
