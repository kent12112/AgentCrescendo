"""Job picker (JOB-F03): choose up to 3 ranked postings to research and write for.

Reads the ranked list that ``scripts/find_jobs.py --json`` saves and produces a small
selection the later steps use (company research, JOB-F04; cover letter, JOB-F05).
See decision 0009: at most 3 letters per session, one per job the user picks.

The ranked file holds untrusted page data (titles, companies, locations come from
job boards). So:

- every text field is cleaned before it is printed: control characters (which could
  drive the terminal, e.g. ANSI escapes) are removed and length is bounded;
- a posting is pickable only if its URL has exactly one of the three ATS shapes and
  rebuilding it from the extracted board and ID gives the same URL. The board and ID
  are what later steps use to fetch the posting again, so they must be trustworthy.

Local and deterministic: nothing here touches the network.
"""
from dataclasses import dataclass
import re
from urllib.parse import urlsplit

from .job_sources import DIGITS, POSTING_URLS, UUID, CompanyBoard

MAX_PICKS = 3
MAX_TEXT = 120

# The path after the host, per source, with the slug and ID captured.
_POSTING_PATHS = {
    "greenhouse": ("job-boards.greenhouse.io", re.compile(r"^/([^/]+)/jobs/([^/]+)$"), DIGITS),
    "lever": ("jobs.lever.co", re.compile(r"^/([^/]+)/([^/]+)$"), UUID),
    "ashby": ("jobs.ashbyhq.com", re.compile(r"^/([^/]+)/([^/]+)$"), UUID),
}
_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f​-‏‪-‮⁦-⁩]")


class PickError(ValueError):
    """The user's choice could not be accepted; the message is safe to show."""


@dataclass(frozen=True)
class PostingRef:
    """A checked pointer to one posting: enough to fetch it again from its ATS."""

    source: str
    board: str
    posting_id: str

    @property
    def url(self) -> str:
        return POSTING_URLS[self.source].format(slug=self.board, id=self.posting_id)


@dataclass(frozen=True)
class Candidate:
    """One ranked row as shown to the user. ``ref`` is None when the URL failed checks."""

    rank: int
    score: int
    title: str
    company: str
    where: str
    pay: str
    have: tuple[str, ...]
    gaps: tuple[str, ...]
    ref: PostingRef | None

    def as_dict(self) -> dict:
        return {"rank": self.rank, "score": self.score, "title": self.title,
                "company": self.company, "where": self.where, "pay": self.pay,
                "matched_skills": list(self.have), "missing_skills": list(self.gaps),
                "source": self.ref.source, "board": self.ref.board,
                "posting_id": self.ref.posting_id, "url": self.ref.url}


def clean(value, limit: int = MAX_TEXT) -> str:
    """Printable, single-line, bounded text from an untrusted value."""
    text = _CONTROL.sub(" ", str(value if value is not None else ""))
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def posting_ref(url) -> PostingRef | None:
    """Board and ID from a posting URL, or None unless it is exactly a known ATS shape."""
    if not isinstance(url, str):
        return None
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.query or parts.fragment or parts.port or parts.username:
        return None
    for source, (host, path, id_pattern) in _POSTING_PATHS.items():
        match = path.match(parts.path) if parts.hostname == host else None
        if not match:
            continue
        slug, posting_id = match.groups()
        try:
            CompanyBoard.parse(f"{source}:{slug}")
        except ValueError:
            return None
        if not id_pattern.match(posting_id):
            return None
        ref = PostingRef(source, slug, posting_id)
        return ref if ref.url == url else None
    return None


def candidates(ranked: dict) -> list[Candidate]:
    """Rows of a ``find_jobs.py --json`` file, in ranked order. Raises PickError."""
    results = ranked.get("results") if isinstance(ranked, dict) else None
    if not isinstance(results, list):
        raise PickError("This is not a find_jobs.py --json file (no results list).")
    rows = []
    for rank, row in enumerate(results, start=1):
        if not isinstance(row, dict):
            continue
        try:
            score = int(row.get("score", 0))
        except (TypeError, ValueError):
            score = 0
        places = row.get("locations") if isinstance(row.get("locations"), list) else []
        where = "; ".join(clean(place, 40) for place in places[:2])
        if len(places) > 2:
            where += f" (+{len(places) - 2})"
        if row.get("workplace"):
            where = ", ".join(x for x in (where, clean(row["workplace"], 20)) if x)

        def skills(key):
            value = row.get(key)
            return tuple(clean(skill, 30) for skill in value[:12]) if isinstance(value, list) else ()

        rows.append(Candidate(rank=rank, score=max(0, min(score, 100)),
                              title=clean(row.get("title")) or "(untitled)",
                              company=clean(row.get("company"), 60) or "(unknown company)",
                              where=where, pay=clean(row.get("compensation"), 60),
                              have=skills("matched_skills"), gaps=skills("missing_skills"),
                              ref=posting_ref(row.get("url"))))
    return rows


def parse_choice(text: str, shown: list[Candidate], max_picks: int = MAX_PICKS) -> list[Candidate]:
    """The rows a typed choice like "1 4 7" or "1,4" selects. Empty means none.

    Raises PickError for anything ambiguous: not a number, not shown, picked twice,
    too many, or a row whose URL failed checks.
    """
    tokens = [token for token in re.split(r"[\s,]+", text.strip()) if token]
    if not tokens:
        return []
    # Checked first: "too many" is the most useful message when several things are wrong.
    if len(tokens) > max_picks:
        raise PickError(f"Pick at most {max_picks} jobs (one cover letter each); you picked {len(tokens)}.")
    by_number = {row.rank: row for row in shown}
    picked = []
    for token in tokens:
        if not token.isdigit():
            raise PickError(f"{token!r} is not a number from the list.")
        number = int(token)
        if number not in by_number:
            raise PickError(f"{number} is not in the list shown.")
        row = by_number[number]
        if row in picked:
            raise PickError(f"{number} was picked twice.")
        if row.ref is None:
            raise PickError(f"{number} has a link that failed checks and cannot be picked.")
        picked.append(row)
    return picked


def format_row(row: Candidate) -> str:
    """Three lines for the terminal; every value was cleaned in ``candidates``."""
    facts = " | ".join(x for x in (row.where, row.pay) if x) or "-"
    mark = "" if row.ref else "  (link failed checks; not pickable)"
    return (f"{row.rank:>2}. [{row.score:>3}] {row.title} — {row.company}{mark}\n"
            f"      {facts}\n"
            f"      have: {', '.join(row.have) or '-'} | gaps: {', '.join(row.gaps) or '-'}")


def selection(ranked: dict, ranked_file: str, picked: list[Candidate], picked_at: str) -> dict:
    """What the next steps read: the search, where it came from, and the picked jobs."""
    return {"search": clean(ranked.get("search"), 80), "ranked_file": ranked_file,
            "picked_at": picked_at, "jobs": [row.as_dict() for row in picked]}
