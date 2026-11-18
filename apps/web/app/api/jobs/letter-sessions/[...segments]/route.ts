import { backend } from "../../../backend";
import { letterWrite, UUID } from "../../letter-proxy";

type Context = { params: Promise<{ segments: string[] }> };

export async function GET(_request: Request, { params }: Context) {
  const { segments } = await params;
  if (segments.length !== 1 || !UUID.test(segments[0])) return new Response(null, { status: 404 });
  return backend(`/jobs/letter-sessions/${segments[0]}`);
}

export async function POST(request: Request, { params }: Context) {
  const { segments } = await params;
  if (segments.length !== 2 || !UUID.test(segments[0]) || !["confirm", "research"].includes(segments[1])) return new Response(null, { status: 404 });
  // Research runs up to three companies at once: one search request plus page checks each.
  return letterWrite(request, `/jobs/letter-sessions/${segments[0]}/${segments[1]}`, segments[1] === "research" ? 180_000 : 5000);
}
