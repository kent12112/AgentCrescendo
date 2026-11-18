import { backend } from "../../backend";
import { crossOriginWrite } from "../guard";

const TYPES = new Set(["application/pdf", "text/plain", "text/markdown"]);
const MAX_BYTES = 10 * 1024 * 1024;

export async function GET() {
  return backend("/jobs/resume");
}

// Body: the resume file's bytes. The API extracts text, stores it in local Postgres, and
// discards the file (decision 0010). The text is never sent back to the browser.
export async function PUT(request: Request) {
  const refused = crossOriginWrite(request);
  if (refused) return refused;
  const type = (request.headers.get("content-type") ?? "").split(";")[0].trim().toLowerCase();
  if (!TYPES.has(type)) return Response.json({ detail: "Upload a PDF, .txt, or .md resume." }, { status: 415 });
  const declared = Number(request.headers.get("content-length") ?? "0");
  if (declared > MAX_BYTES) return Response.json({ detail: "The resume file is larger than 10 MB." }, { status: 413 });
  const body = await request.arrayBuffer();
  if (body.byteLength > MAX_BYTES) return Response.json({ detail: "The resume file is larger than 10 MB." }, { status: 413 });
  // Header values must be ASCII; the browser sends the name URI-encoded and it is decoded here.
  let filename = "resume";
  try { filename = decodeURIComponent(request.headers.get("x-filename") ?? "resume"); } catch { /* keep default */ }
  return backend("/jobs/resume", { method: "PUT", body }, {
    timeoutMs: 30_000,
    headers: { "Content-Type": type, "X-Filename": encodeURIComponent(filename).slice(0, 600) },
  });
}

export async function DELETE(request: Request) {
  const refused = crossOriginWrite(request);
  if (refused) return refused;
  return backend("/jobs/resume", { method: "DELETE" });
}
