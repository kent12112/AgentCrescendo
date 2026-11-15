// Learn: Import these module exports for use below: import { backend } from "../backend";. Named imports use braces; a default import has no braces.
import { backend } from "../backend";

// Learn: Define an async function returning a Promise: export async function GET() {. Its body executes when called/rendered.
export async function GET() {
  // Learn: Forward this permitted API path through the server-only proxy, which attaches the local credential.
  return backend("/capabilities");
// Learn: Close the surrounding object, function, call, or type expression; delimiters determine which construct ends here.
}
