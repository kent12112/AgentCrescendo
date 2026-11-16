// Import { backend } from "../backend".
import { backend } from "../backend";

// Define export async function GET() {
export async function GET() {
  // Browser calls /api/runs on Next.js; Next.js calls /runs on FastAPI with the
  // server credential. This avoids exposing that credential to client JavaScript.
  // Forward this permitted API path through the server-only proxy, which attaches the local
  // credential.
  return backend("/runs");
}

// Define export async function POST(request: Request) {
export async function POST(request: Request) {
  // This is a local single-user proxy, not multi-user authentication. A browser
  // on another origin must not be able to borrow the proxy's backend credential.
  // The local server supplies the backend credential. Require same-origin writes.
  // Read the browser Origin header for the same-origin write boundary.
  const origin = request.headers.get("origin");
  // Next.js may normalize request.url to localhost even when the browser used
  // 127.0.0.1. Host retains the browser-facing authority in this local setup.
  // Read the browser-facing host, since Next.js may normalize the internal request URL.
  const host = request.headers.get("host");
  // Use URL parsing/resolution rather than concatenating arbitrary untrusted destinations.
  const expectedOrigin = `${new URL(request.url).protocol}//${host}`;
  // Check this condition: if (!origin || !host || origin !== expectedOrigin) {
  if (!origin || !host || origin !== expectedOrigin) {
    // Return JSON with an explicit HTTP status; keep internal provider/configuration details out of
    // browser responses.
    return Response.json({ detail: "Cross-origin writes are not permitted." }, { status: 403 });
  }
  // Check this condition: if (!request.headers.get("content-type")?.startsWith("application/json"))
  // {
  if (!request.headers.get("content-type")?.startsWith("application/json")) {
    // Return JSON with an explicit HTTP status; keep internal provider/configuration details out of
    // browser responses.
    return Response.json({ detail: "Expected JSON." }, { status: 415 });
  }
  // Bound the buffered text we forward. This character-count check is not a
  // streaming byte limit; enforce transport-level body limits before public hosting.
  // Read the request body as text before applying the character-count limit.
  const body = await request.text();
  // Check this condition: if (body.length > 20_000) {
  if (body.length > 20_000) {
    // Return JSON with an explicit HTTP status; keep internal provider/configuration details out of
    // browser responses.
    return Response.json({ detail: "Request is too large." }, { status: 413 });
  }
  // Check JSON syntax here; FastAPI remains responsible for field-level validation.
  // Check JSON syntax before forwarding; field-level validation remains in FastAPI.
  try { JSON.parse(body); } catch {
    // Return JSON with an explicit HTTP status; keep internal provider/configuration details out of
    // browser responses.
    return Response.json({ detail: "Invalid JSON." }, { status: 400 });
  }
  // Forward this permitted API path through the server-only proxy, which attaches the local
  // credential.
  return backend("/runs", { method: "POST", body });
}
