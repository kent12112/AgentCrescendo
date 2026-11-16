// Import { backend } from "../../backend".
import { backend } from "../../backend";

// Define export async function DELETE(request: Request, context: { params: Promise<{ runId: string
// }> }) {
export async function DELETE(request: Request, context: { params: Promise<{ runId: string }> }) {
  // Apply the same browser-origin boundary as draft creation before forwarding
  // the server-only credential. Never accept arbitrary upstream paths.
  // Read the browser Origin header for the same-origin write boundary.
  const origin = request.headers.get("origin");
  // Read the browser-facing host, since Next.js may normalize the internal request URL.
  const host = request.headers.get("host");
  // Check this condition: if (!origin || !host || origin !== `${new
  // URL(request.url).protocol}//${host}`) {
  if (!origin || !host || origin !== `${new URL(request.url).protocol}//${host}`) {
    // Return JSON with an explicit HTTP status; keep internal provider/configuration details out of
    // browser responses.
    return Response.json({ detail: "Cross-origin writes are not permitted." }, { status: 403 });
  }
  // Await Next.js dynamic route parameters before using the run ID.
  const { runId } = await context.params;
  // Check this condition: if
  // (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(runId)) {
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(runId)) {
    // Return JSON with an explicit HTTP status; keep internal provider/configuration details out of
    // browser responses.
    return Response.json({ detail: "Invalid draft ID." }, { status: 422 });
  }
  // Forward this permitted API path through the server-only proxy, which attaches the local
  // credential.
  return backend(`/runs/${runId}`, { method: "DELETE" });
}
