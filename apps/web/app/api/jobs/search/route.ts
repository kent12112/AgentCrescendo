import { backend } from "../../backend";

// Only these query parameters reach the API; FastAPI validates their values and ranges.
const ALLOWED = ["q", "country", "location", "remote", "no_senior", "max_years", "max_age_days", "offset", "limit", "source", "hide_applied"];

export async function GET(request: Request) {
  const incoming = new URL(request.url).searchParams;
  const forwarded = new URLSearchParams();
  for (const key of ALLOWED) for (const value of incoming.getAll(key)) forwarded.append(key, value);
  // 30 s: the first search after a daily crawl loads ~20k postings into the API's index.
  return backend(`/jobs/search?${forwarded}`, undefined, { timeoutMs: 30_000 });
}
