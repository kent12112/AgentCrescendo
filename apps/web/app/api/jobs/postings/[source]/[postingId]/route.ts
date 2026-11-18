import { backend } from "../../../../backend";
import { POSTING_ID, SOURCE } from "../../../guard";

export async function GET(_request: Request, context: { params: Promise<{ source: string; postingId: string }> }) {
  const { source, postingId } = await context.params;
  if (!SOURCE.test(source) || !POSTING_ID.test(postingId)) {
    return Response.json({ detail: "Malformed posting reference." }, { status: 422 });
  }
  return backend(`/jobs/postings/${source}/${postingId}`);
}
