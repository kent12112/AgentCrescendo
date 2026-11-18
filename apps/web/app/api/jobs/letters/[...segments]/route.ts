import { backend } from "../../../backend";
import { letterWrite, UUID } from "../../letter-proxy";

type Context = { params: Promise<{ segments: string[] }> };

export async function GET(_request: Request, { params }: Context) {
  const { segments } = await params;
  if (!UUID.test(segments[0])) return new Response(null, { status: 404 });
  if (segments.length === 1) return backend(`/jobs/letters/${segments[0]}`);
  if (segments.length === 2 && segments[1] === "writer") return backend(`/jobs/letters/${segments[0]}/writer`);
  if (segments.length === 2 && segments[1] === "download") {
    return backend(`/jobs/letters/${segments[0]}/download`, undefined, { textDownload: true });
  }
  return new Response(null, { status: 404 });
}

export async function POST(request: Request, { params }: Context) {
  const { segments } = await params;
  if (segments.length !== 2 || !UUID.test(segments[0]) || !["generate", "writer", "draft-writer"].includes(segments[1])) return new Response(null, { status: 404 });
  return letterWrite(request, `/jobs/letters/${segments[0]}/${segments[1]}`, segments[1] === "generate" ? 300_000 : 5000);
}

export async function PUT(request: Request, { params }: Context) {
  const { segments } = await params;
  if (segments.length !== 1 || !UUID.test(segments[0])) return new Response(null, { status: 404 });
  return letterWrite(request, `/jobs/letters/${segments[0]}`);
}
