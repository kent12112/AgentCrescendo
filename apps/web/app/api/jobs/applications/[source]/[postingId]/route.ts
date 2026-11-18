import { backend } from "../../../../backend";
import { POSTING_ID, SOURCE, crossOriginWrite } from "../../../guard";
import { letterWrite } from "../../../letter-proxy";

type Context = { params: Promise<{ source: string; postingId: string }> };

async function path(context: Context) {
  const { source, postingId } = await context.params;
  return SOURCE.test(source) && POSTING_ID.test(postingId) ? `/jobs/applications/${source}/${postingId}` as const : null;
}

export async function PUT(request: Request, context: Context) {
  const target = await path(context);
  if (!target) return new Response(null, { status: 404 });
  return letterWrite(request, target);
}

export async function DELETE(request: Request, context: Context) {
  const refused = crossOriginWrite(request);
  if (refused) return refused;
  const target = await path(context);
  if (!target) return new Response(null, { status: 404 });
  const version = new URL(request.url).searchParams.get("version") ?? "";
  if (!/^[1-9]\d{0,9}$/.test(version)) return new Response(null, { status: 422 });
  return backend(`${target}?version=${version}`, { method: "DELETE" });
}
