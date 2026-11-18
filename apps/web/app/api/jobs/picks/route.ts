import { backend } from "../../backend";
import { crossOriginWrite } from "../guard";

export async function GET() {
  return backend("/jobs/picks");
}

export async function PUT(request: Request) {
  const refused = crossOriginWrite(request);
  if (refused) return refused;
  if (!request.headers.get("content-type")?.startsWith("application/json")) {
    return Response.json({ detail: "Expected JSON." }, { status: 415 });
  }
  const body = await request.text();
  if (body.length > 2_000) return Response.json({ detail: "Request is too large." }, { status: 413 });
  try { JSON.parse(body); } catch { return Response.json({ detail: "Invalid JSON." }, { status: 400 }); }
  // The API enforces the 3-pick limit and checks every posting; this route only forwards.
  return backend("/jobs/picks", { method: "PUT", body });
}
