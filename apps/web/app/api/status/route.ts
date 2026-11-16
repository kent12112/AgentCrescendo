// Import { backend } from "../backend".
import { backend } from "../backend";

// Define export async function GET() {
export async function GET() {
  // Forward this permitted API path through the server-only proxy, which attaches the local
  // credential.
  return backend("/capabilities");
}
