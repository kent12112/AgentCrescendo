import { backend } from "../../backend";

export async function DELETE(request: Request, context: { params: Promise<{ runId: string }> }) {
  // Apply the same browser-origin boundary as draft creation before forwarding
  // the server-only credential. Never accept arbitrary upstream paths.
  const origin = request.headers.get("origin");
  const host = request.headers.get("host");
  if (!origin || !host || origin !== `${new URL(request.url).protocol}//${host}`) {
    return Response.json({ detail: "Cross-origin writes are not permitted." }, { status: 403 });
  }
  const { runId } = await context.params;
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(runId)) {
    return Response.json({ detail: "Invalid draft ID." }, { status: 422 });
  }
  return backend(`/runs/${runId}`, { method: "DELETE" });
}
