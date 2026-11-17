"""Job postings from ATS public job-board APIs (JOB-F00): Greenhouse, Lever, Ashby.

Host-side discovery. These are the companies' own published listing APIs: no key,
no login, intended for job boards. Fetching here, rather than through a search
engine, avoids bot challenges and terms-of-service problems (probed November 17,
2026: every consumer engine blocked or ignored automated queries).

Everything in a response is untrusted page data. Board names are validated
before they enter a URL; responses are size- and time-limited; each posting is
normalized into a `Posting` whose `url` is rebuilt from the validated board name
and a checked posting ID, never taken from the response. Malformed postings are
skipped and counted, not raised.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
import re

SOURCES = ("greenhouse", "lever", "ashby")
SLUG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$")
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
DIGITS = re.compile(r"^\d{1,20}$")

MAX_RESPONSE_BYTES = 32 * 1024 * 1024  # Largest seen: ~15 MB (Ashby, 840 postings).
TIMEOUT_SECONDS = 20.0
MAX_DESCRIPTION_CHARS = 20_000
MAX_FIELD_CHARS = 300

API_URLS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true",
    "lever": "https://api.lever.co/v0/postings/{slug}?mode=json",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true",
}
POSTING_URLS = {
    "greenhouse": "https://job-boards.greenhouse.io/{slug}/jobs/{id}",
    "lever": "https://jobs.lever.co/{slug}/{id}",
    "ashby": "https://jobs.ashbyhq.com/{slug}/{id}",
}


class SourceError(Exception):
    """A board could not be fetched or parsed; the message is safe to show."""


@dataclass(frozen=True)
class CompanyBoard:
    source: str  # one of SOURCES
    slug: str

    @classmethod
    def parse(cls, spec: str) -> "CompanyBoard":
        """Parse 'source:slug', e.g. 'lever:palantir'. Raises ValueError."""
        source, _, slug = (spec or "").strip().partition(":")
        source = source.lower()
        if source not in SOURCES or not SLUG.match(slug):
            raise ValueError(f"Board must be one of {', '.join(s + ':<company>' for s in SOURCES)}; "
                             f"got {spec!r}.")
        return cls(source, slug)

    @property
    def api_url(self) -> str:
        return API_URLS[self.source].format(slug=self.slug)


@dataclass(frozen=True)
class Posting:
    """One normalized job posting. All text fields are untrusted page data."""

    source: str
    company: str          # board slug
    posting_id: str
    title: str
    url: str              # rebuilt from slug + checked ID; the posting page on the ATS
    locations: tuple[str, ...] = ()
    workplace: str | None = None  # "remote", "hybrid", "onsite", or None if not stated
    department: str | None = None
    employment_type: str | None = None
    published_at: str | None = None  # ISO 8601 UTC
    compensation: str | None = None
    description: str = ""
    company_name: str | None = None
    # Countries from structured ATS data (Ashby addresses), normalized; empty if not given.
    countries: tuple[str, ...] = ()


# Spellings seen or expected in ATS country fields -> one name (JOB-F06).
COUNTRY_ALIASES = {
    "us": "United States", "usa": "United States", "u.s.": "United States", "u.s.a.": "United States",
    "united states": "United States", "united states of america": "United States", "america": "United States",
    "uk": "United Kingdom", "u.k.": "United Kingdom", "united kingdom": "United Kingdom",
    "great britain": "United Kingdom", "england": "United Kingdom", "gb": "United Kingdom",
}


def normalize_country(value) -> str | None:
    """'USA' / 'United States of America' -> 'United States'; other names kept as given."""
    name = _short(value)
    if not name:
        return None
    key = name.lower()
    return COUNTRY_ALIASES.get(key) or COUNTRY_ALIASES.get(key.strip(" .")) or name


@dataclass
class BoardResult:
    board: CompanyBoard
    postings: list[Posting] = field(default_factory=list)
    skipped: int = 0
    error: str | None = None


class _Text(HTMLParser):
    """Collect visible text from posting HTML; block tags become line breaks."""

    BLOCKS = {"p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "tr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.skip += 1
        elif tag in self.BLOCKS:
            self.parts.append("\n- " if tag == "li" else "\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self.skip:
            self.skip -= 1
        elif tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def html_to_text(markup: str) -> str:
    parser = _Text()
    parser.feed(markup or "")
    parser.close()
    lines = (" ".join(line.split()) for line in "".join(parser.parts).splitlines())
    text = "\n".join(line for line in lines if line)
    return text[:MAX_DESCRIPTION_CHARS]


def _short(value) -> str | None:
    if not isinstance(value, str):
        return None
    value = " ".join(value.split())
    return value[:MAX_FIELD_CHARS] or None


def _plain(value) -> str:
    if not isinstance(value, str):
        return ""
    lines = (" ".join(line.split()) for line in value.splitlines())
    return "\n".join(line for line in lines if line)[:MAX_DESCRIPTION_CHARS]


def _iso(value) -> str | None:
    """ISO string or epoch milliseconds -> ISO 8601 UTC, else None."""
    try:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            moment = datetime.fromtimestamp(value / 1000, tz=timezone.utc)
        elif isinstance(value, str):
            moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if moment.tzinfo is None:
                return None
        else:
            return None
    except (ValueError, OverflowError, OSError):
        return None
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _workplace(value) -> str | None:
    text = (value or "").lower().replace("-", "").replace(" ", "") if isinstance(value, str) else ""
    return {"remote": "remote", "hybrid": "hybrid", "onsite": "onsite", "inoffice": "onsite"}.get(text)


def _url(board: CompanyBoard, posting_id: str) -> str:
    return POSTING_URLS[board.source].format(slug=board.slug, id=posting_id)


def _greenhouse(board: CompanyBoard, item: dict) -> Posting | None:
    posting_id = str(item.get("id", ""))
    title = _short(item.get("title"))
    if not DIGITS.match(posting_id) or not title:
        return None
    location = _short((item.get("location") or {}).get("name"))
    workplace = None
    for meta in item.get("metadata") or []:
        if isinstance(meta, dict) and str(meta.get("name", "")).lower() in {"location type", "workplace type"}:
            workplace = _workplace(meta.get("value"))
    departments = [d.get("name") for d in item.get("departments") or [] if isinstance(d, dict)]
    return Posting(
        source="greenhouse", company=board.slug, posting_id=posting_id, title=title,
        url=_url(board, posting_id),
        locations=tuple(p.strip() for p in (location or "").split("|") if p.strip()),
        workplace=workplace, department=_short(departments[0]) if departments else None,
        published_at=_iso(item.get("first_published") or item.get("updated_at")),
        # Greenhouse sends HTML escaped once more as text.
        description=html_to_text(unescape(item.get("content") or "")),
        company_name=_short(item.get("company_name")))


def _lever(board: CompanyBoard, item: dict) -> Posting | None:
    posting_id = str(item.get("id", ""))
    title = _short(item.get("text"))
    if not UUID.match(posting_id) or not title:
        return None
    categories = item.get("categories") if isinstance(item.get("categories"), dict) else {}
    locations = categories.get("allLocations") or [categories.get("location")]
    parts = [_plain(item.get("descriptionPlain"))]
    for section in item.get("lists") or []:
        if isinstance(section, dict):
            parts.append(f"{_short(section.get('text')) or ''}\n{html_to_text(section.get('content') or '')}")
    parts.append(_plain(item.get("additionalPlain")))
    salary = item.get("salaryRange") if isinstance(item.get("salaryRange"), dict) else None
    compensation = None
    if salary and isinstance(salary.get("min"), (int, float)) and isinstance(salary.get("max"), (int, float)):
        compensation = _short(f"{salary.get('currency', '')} {salary['min']:,}–{salary['max']:,} "
                              f"{salary.get('interval', '')}".strip())
    return Posting(
        source="lever", company=board.slug, posting_id=posting_id, title=title, url=_url(board, posting_id),
        locations=tuple(loc for loc in (_short(l) for l in locations) if loc),
        workplace=_workplace(item.get("workplaceType")), department=_short(categories.get("team")),
        employment_type=_short(categories.get("commitment")), published_at=_iso(item.get("createdAt")),
        compensation=compensation, description="\n\n".join(p for p in parts if p.strip())[:MAX_DESCRIPTION_CHARS])


def _ashby(board: CompanyBoard, item: dict) -> Posting | None:
    posting_id = str(item.get("id", ""))
    title = _short(item.get("title"))
    if not UUID.match(posting_id) or not title or item.get("isListed") is False:
        return None
    secondary = item.get("secondaryLocations") if isinstance(item.get("secondaryLocations"), list) else []
    locations = [item.get("location")] + [loc.get("location") if isinstance(loc, dict) else loc
                                          for loc in secondary]
    countries = []
    for holder in [item] + [loc for loc in secondary if isinstance(loc, dict)]:
        address = holder.get("address") if isinstance(holder.get("address"), dict) else {}
        postal = address.get("postalAddress") if isinstance(address.get("postalAddress"), dict) else {}
        country = normalize_country(postal.get("addressCountry"))
        if country and country not in countries:
            countries.append(country)
    workplace = _workplace(item.get("workplaceType")) or ("remote" if item.get("isRemote") is True else None)
    compensation = (item.get("compensation") or {}) if isinstance(item.get("compensation"), dict) else {}
    description = _plain(item.get("descriptionPlain")) or html_to_text(item.get("descriptionHtml") or "")
    return Posting(
        source="ashby", company=board.slug, posting_id=posting_id, title=title, url=_url(board, posting_id),
        locations=tuple(loc for loc in (_short(l) for l in locations) if loc), workplace=workplace,
        department=_short(item.get("department")), employment_type=_short(item.get("employmentType")),
        published_at=_iso(item.get("publishedAt")),
        compensation=_short(compensation.get("compensationTierSummary")), description=description,
        countries=tuple(countries))


def normalize(board: CompanyBoard, data) -> BoardResult:
    """Turn one parsed API response into postings; malformed items are skipped and counted."""
    if board.source == "lever":
        items, parse = data, _lever
    elif isinstance(data, dict):
        items, parse = data.get("jobs"), _greenhouse if board.source == "greenhouse" else _ashby
    else:
        items = None
    if not isinstance(items, list):
        return BoardResult(board, error="The response did not contain a job list.")
    result = BoardResult(board)
    seen = set()
    for item in items:
        posting = parse(board, item) if isinstance(item, dict) else None
        if posting is None or posting.posting_id in seen:
            result.skipped += 1
            continue
        seen.add(posting.posting_id)
        result.postings.append(posting)
    return result


def fetch_board(board: CompanyBoard, client) -> BoardResult:
    """Fetch and normalize one board with an httpx.Client. Never raises for network/data errors."""
    import json

    import httpx

    try:
        with client.stream("GET", board.api_url, timeout=TIMEOUT_SECONDS,
                           headers={"Accept": "application/json"}, follow_redirects=False) as response:
            if response.status_code == 404:
                return BoardResult(board, error="No public job board with that name (HTTP 404).")
            if response.status_code != 200:
                return BoardResult(board, error=f"The job board API answered HTTP {response.status_code}.")
            declared = response.headers.get("content-length")
            if declared and declared.isdigit() and int(declared) > MAX_RESPONSE_BYTES:
                return BoardResult(board, error="The response is larger than the size limit.")
            body = bytearray()
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body) > MAX_RESPONSE_BYTES:
                    return BoardResult(board, error="The response is larger than the size limit.")
    except httpx.TimeoutException:
        return BoardResult(board, error="The job board API timed out.")
    except httpx.HTTPError as error:
        return BoardResult(board, error=f"Network error ({type(error).__name__}).")
    try:
        data = json.loads(body)
    except ValueError:
        return BoardResult(board, error="The response was not valid JSON.")
    return normalize(board, data)


def fetch_boards(boards, client=None, *, workers: int = 8) -> list[BoardResult]:
    """Fetch several boards, results in input order; one board's failure does not stop the others.

    Up to ``workers`` requests run at once (httpx.Client is thread-safe).
    """
    from concurrent.futures import ThreadPoolExecutor

    import httpx

    if type(workers) is not int or not 1 <= workers <= 16:
        raise ValueError("workers must be an integer from 1 to 16.")
    owned = client is None
    client = client or httpx.Client(headers={"User-Agent": "AgentCrescendo-job-sources/0.1"})
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            return list(pool.map(lambda board: fetch_board(board, client), boards))
    finally:
        if owned:
            client.close()
