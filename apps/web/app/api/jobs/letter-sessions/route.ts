import { letterWrite } from "../letter-proxy";

export async function POST(request: Request) {
  return letterWrite(request, "/jobs/letter-sessions");
}
