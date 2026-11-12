import { backend } from "../backend";

export async function GET() {
  // Browser calls /api/runs on Next.js; Next.js calls /runs on FastAPI with the
  // server credential. This avoids exposing that credential to client JavaScript.
  return backend("/runs");
}

export async function POST(request: Request) {
  // This is a local single-user proxy, not multi-user authentication. A browser
  // on another origin must not be able to borrow the proxy's backend credential.
  // The local server supplies the backend credential. Require same-origin writes.
  const origin = request.headers.get("origin");
  // Next.js may normalize request.url to localhost even when the browser used
  // 127.0.0.1. Host retains the browser-facing authority in this local setup.
  const host = request.headers.get("host");
  const expectedOrigin = `${new URL(request.url).protocol}//${host}`;
  if (!origin || !host || origin !== expectedOrigin) {
    return Response.json({ detail: "Cross-origin writes are not permitted." }, { status: 403 });
  }
  if (!request.headers.get("content-type")?.startsWith("application/json")) {
    return Response.json({ detail: "Expected JSON." }, { status: 415 });
  }
  // Bound the buffered text we forward. This character-count check is not a
  // streaming byte limit; enforce transport-level body limits before public hosting.
  const body = await request.text();
  if (body.length > 20_000) {
    return Response.json({ detail: "Request is too large." }, { status: 413 });
  }
  // Check JSON syntax here; FastAPI remains responsible for field-level validation.
  try { JSON.parse(body); } catch {
    return Response.json({ detail: "Invalid JSON." }, { status: 400 });
  }
  return backend("/runs", { method: "POST", body });
}
