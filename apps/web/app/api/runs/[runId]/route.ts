// Learn: Import these module exports for use below: import { backend } from "../../backend";. Named imports use braces; a default import has no braces.
import { backend } from "../../backend";

// Learn: Define an async function returning a Promise: export async function DELETE(request: Request, context: { params: Promise<{ runId: string }> }) {. Its body executes when called/rendered.
export async function DELETE(request: Request, context: { params: Promise<{ runId: string }> }) {
  // Apply the same browser-origin boundary as draft creation before forwarding
  // the server-only credential. Never accept arbitrary upstream paths.
  // Learn: Read the browser Origin header for the same-origin write boundary.
  const origin = request.headers.get("origin");
  // Learn: Read the browser-facing host, since Next.js may normalize the internal request URL.
  const host = request.headers.get("host");
  // Learn: Evaluate this guard before continuing: if (!origin || !host || origin !== `${new URL(request.url).protocol}//${host}`) {. || short-circuits on the first truthy value; && stops at the first falsy value.
  if (!origin || !host || origin !== `${new URL(request.url).protocol}//${host}`) {
    // Learn: Return JSON with an explicit HTTP status; keep internal provider/configuration details out of browser responses.
    return Response.json({ detail: "Cross-origin writes are not permitted." }, { status: 403 });
  // Learn: Close the surrounding object, function, call, or type expression; delimiters determine which construct ends here.
  }
  // Learn: Await Next.js dynamic route parameters before using the run ID.
  const { runId } = await context.params;
  // Learn: Evaluate this guard before continuing: if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(runId)) {. || short-circuits on the first truthy value; && stops at the first falsy value.
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(runId)) {
    // Learn: Return JSON with an explicit HTTP status; keep internal provider/configuration details out of browser responses.
    return Response.json({ detail: "Invalid draft ID." }, { status: 422 });
  // Learn: Close the surrounding object, function, call, or type expression; delimiters determine which construct ends here.
  }
  // Learn: Forward this permitted API path through the server-only proxy, which attaches the local credential.
  return backend(`/runs/${runId}`, { method: "DELETE" });
// Learn: Close the surrounding object, function, call, or type expression; delimiters determine which construct ends here.
}
