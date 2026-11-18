import { backend } from "../../../backend";
import { letterWrite, UUID } from "../../letter-proxy";

type Context = { params: Promise<{ segments: string[] }> };

export async function GET(_request: Request, { params }: Context) {
  const { segments } = await params;
  if (!UUID.test(segments[0])) return new Response(null, { status: 404 });
  if (segments.length === 1) return backend(`/jobs/writer-exports/${segments[0]}`);
  if (segments.length === 2 && segments[1] === "pdf") return backend(`/jobs/writer-exports/${segments[0]}/pdf`, undefined, { pdfDownload: true });
  return new Response(null, { status: 404 });
}

export async function POST(request: Request, { params }: Context) {
  const { segments } = await params;
  if (segments.length !== 2 || !UUID.test(segments[0]) || !["begin", "cancel"].includes(segments[1])) return new Response(null, { status: 404 });
  return letterWrite(request, `/jobs/writer-exports/${segments[0]}/${segments[1]}`);
}
