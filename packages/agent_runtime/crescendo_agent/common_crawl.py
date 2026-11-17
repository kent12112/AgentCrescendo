"""Company boards from the Common Crawl URL index (JOB-F06). Host-side, no key.

Common Crawl is a public web archive. Its CDX index answers "which URLs under
this prefix were crawled?". Asking for ``jobs.ashbyhq.com/*`` returns posting
URLs such as ``https://jobs.ashbyhq.com/1password/<uuid>?utm_source=...``; the
first path segment is the company's board slug. The posting itself may be old,
which does not matter: the live Ashby API (job_sources) says what is open now.

Measured November 17, 2026: one monthly crawl (CC-MAIN-2026-43) held one index
page, ~3,800 Ashby URLs, ~944 companies. Each crawl samples different pages, so
coverage grows by reading several recent crawls, not more pages of one.

The index server sheds load with 502/503/504 and timeouts (seen live the same
day), so requests are sequential, paused, and retried with growing waits. Index
text is untrusted: only slugs that pass ``CompanyBoard.parse`` are kept.
"""
from dataclasses import dataclass, field
import json
import re
import time
from urllib.parse import urlparse

from .job_sources import CompanyBoard

COLLECTIONS_URL = "https://index.commoncrawl.org/collinfo.json"
INDEX_URL = "https://index.commoncrawl.org/{index}-index"
INDEX_ID = re.compile(r"^CC-MAIN-\d{4}-\d{2}$")

HOSTS = {"ashby": "jobs.ashbyhq.com"}
# First path segments on jobs.ashbyhq.com that are Ashby's own routes, not companies.
RESERVED_PATHS = {"ashby": {"api", "b", "embed", "meeting"}}

MAX_BYTES = 32 * 1024 * 1024  # One Ashby index page was ~0.4 MB.
TIMEOUT_SECONDS = 60.0
RETRY_STATUSES = {429, 500, 502, 503, 504}
RETRY_WAITS = (15.0, 30.0, 60.0)  # seconds before attempts 2, 3, 4
MAX_RETRY_AFTER = 120.0
MAX_PAGES_PER_CRAWL = 10
MAX_CRAWLS = 12


class CrawlError(Exception):
    """The index could not be read; the message is safe to show."""


@dataclass
class CrawlResult:
    boards: list[CompanyBoard] = field(default_factory=list)  # sorted, distinct
    indexes_read: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)  # one per crawl that failed


def slug_from_url(source: str, url: str) -> str | None:
    """The board slug a crawled URL points at, lowercased, or None."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or (parsed.hostname or "").lower() != HOSTS[source]:
        return None
    segments = [part for part in parsed.path.split("/") if part]
    if not segments:
        return None
    slug = segments[0].lower()
    if slug in RESERVED_PATHS[source]:
        return None
    try:
        return CompanyBoard.parse(f"{source}:{slug}").slug
    except ValueError:
        return None


def slugs_in_index_text(source: str, text: str) -> set[str]:
    """Slugs from CDX output: 'urlkey timestamp {json}' lines, JSON lines, or bare URLs."""
    slugs = set()
    for line in (text or "").splitlines():
        line = line.strip()
        start = line.find("{")
        url = None
        if start >= 0:
            try:
                record = json.loads(line[start:])
            except ValueError:
                record = None
            if isinstance(record, dict) and isinstance(record.get("url"), str):
                url = record["url"]
        elif line.startswith(("http://", "https://")):
            url = line
        slug = slug_from_url(source, url) if url else None
        if slug:
            slugs.add(slug)
    return slugs


def _get(client, url, params=None, *, sleep=time.sleep) -> bytes | None:
    """GET with retries for load shedding. Returns None for 404 (no captures). Raises CrawlError."""
    import httpx

    problem = "no attempt"
    for attempt in range(len(RETRY_WAITS) + 1):
        wait = None
        try:
            with client.stream("GET", url, params=params, timeout=TIMEOUT_SECONDS,
                               follow_redirects=False) as response:
                if response.status_code == 404:
                    return None
                if response.status_code == 200:
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) > MAX_BYTES:
                            raise CrawlError("Common Crawl response is larger than the size limit.")
                    return bytes(body)
                problem = f"HTTP {response.status_code}"
                if response.status_code not in RETRY_STATUSES:
                    raise CrawlError(f"Common Crawl answered {problem}.")
                retry_after = response.headers.get("retry-after", "")
                if retry_after.isdigit():
                    wait = min(float(retry_after), MAX_RETRY_AFTER)
        except httpx.TimeoutException:
            problem = "timeout"
        except httpx.HTTPError as error:
            problem = f"network error ({type(error).__name__})"
        if attempt < len(RETRY_WAITS):
            sleep(wait if wait is not None else RETRY_WAITS[attempt])
    raise CrawlError(f"Common Crawl kept failing ({problem}) after {len(RETRY_WAITS) + 1} attempts.")


def latest_indexes(client, count: int, *, sleep=time.sleep) -> list[str]:
    """IDs of the newest ``count`` crawls, newest first. Raises CrawlError."""
    body = _get(client, COLLECTIONS_URL, sleep=sleep)
    try:
        collections = json.loads(body or b"null")
    except ValueError:
        raise CrawlError("Common Crawl's crawl list was not valid JSON.") from None
    if not isinstance(collections, list):
        raise CrawlError("Common Crawl's crawl list had an unexpected shape.")
    ids = [c.get("id") for c in collections if isinstance(c, dict)]
    ids = [i for i in ids if isinstance(i, str) and INDEX_ID.match(i)]
    if not ids:
        raise CrawlError("Common Crawl listed no crawls.")
    return ids[:count]


def crawl_boards(client, source: str = "ashby", *, crawls: int = 6, sleep=time.sleep,
                 pause: float = 2.0, progress=None, budget_seconds: float | None = None,
                 clock=time.monotonic, skip=()) -> CrawlResult:
    """Distinct company boards for ``source`` seen in the latest ``crawls`` monthly crawls.

    One crawl's failure is recorded and the others still count. Never raises for
    network or data errors; if nothing could be read, ``boards`` is empty and
    ``errors`` says why. ``progress(message)`` is called after each crawl.

    ``skip`` lists crawl IDs already read (an incremental refresh reads only new ones).
    ``budget_seconds`` is checked before each crawl starts: once spent, the rest are
    recorded as skipped and what was found is kept. Live, one overloaded crawl took
    ~6 minutes to fail (4 attempts of up to 60 s plus 15/30/60 s waits).
    """
    started = clock()
    if source not in HOSTS:
        raise ValueError(f"Common Crawl discovery supports {', '.join(HOSTS)}; got {source!r}.")
    if type(crawls) is not int or not 1 <= crawls <= MAX_CRAWLS:
        raise ValueError(f"crawls must be an integer from 1 to {MAX_CRAWLS}.")
    result = CrawlResult()
    try:
        indexes = [i for i in latest_indexes(client, crawls, sleep=sleep) if i not in set(skip)]
    except CrawlError as error:
        result.errors.append(str(error))
        return result
    if not indexes and progress:
        progress(f"all of the latest {crawls} crawls were already read")
    slugs: set[str] = set()
    query = {"url": f"{HOSTS[source]}/*"}
    for number, index in enumerate(indexes):
        if budget_seconds is not None and clock() - started >= budget_seconds:
            skipped = indexes[number:]
            result.errors.append(f"time budget ({budget_seconds:g} s) spent; skipped {', '.join(skipped)}")
            if progress:
                progress(f"time budget spent; skipped {len(skipped)} crawls")
            break
        url = INDEX_URL.format(index=index)
        before = len(slugs)
        try:
            sleep(pause)
            info = _get(client, url, {**query, "showNumPages": "true"}, sleep=sleep)
            pages = 0
            if info is not None:
                try:
                    pages = int(json.loads(info).get("pages", 0))
                except (ValueError, AttributeError, TypeError):
                    raise CrawlError("page count was not valid JSON") from None
            for page in range(min(max(pages, 0), MAX_PAGES_PER_CRAWL)):
                sleep(pause)
                body = _get(client, url, {**query, "output": "json", "fl": "url", "page": str(page)},
                            sleep=sleep)
                slugs |= slugs_in_index_text(source, (body or b"").decode("utf-8", errors="replace"))
        except CrawlError as error:
            result.errors.append(f"{index}: {error}")
            if progress:
                progress(f"{index}: failed ({error})")
            continue
        result.indexes_read.append(index)
        if progress:
            progress(f"{index}: {len(slugs) - before} new companies ({len(slugs)} total)")
    result.boards = [CompanyBoard(source, slug) for slug in sorted(slugs)]
    return result
