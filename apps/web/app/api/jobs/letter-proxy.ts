import { backend } from "../backend";
import { crossOriginWrite } from "./guard";

export const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function letterWrite(request: Request, path: `/jobs/${string}`, timeoutMs = 5000) {
  const refused = crossOriginWrite(request);
  if (refused) return refused;
  const body = await request.text();
  if (body.length > 30_000) return Response.json({ detail: "Request is too large." }, { status: 413 });
  if (body) {
    if (!request.headers.get("content-type")?.startsWith("application/json")) {
      return Response.json({ detail: "Expected JSON." }, { status: 415 });
    }
    try { JSON.parse(body); } catch { return Response.json({ detail: "Invalid JSON." }, { status: 400 }); }
  }
  return backend(path, { method: request.method, ...(body ? { body } : {}) }, { timeoutMs });
}
