"""Rank stored job postings against the uploaded resume for the web app (JOB-F08).

The daily crawl (JOB-F07) fills ``job_postings``; this module serves searches over it
with the same ranking as ``scripts/find_jobs.py`` (crescendo_agent.job_match), so the
web page and the CLI agree.

Speed: loading ~20k postings takes a few seconds, so the open postings are kept in
memory and reloaded only when a new crawl finishes (``PostingIndex.key``). Extracting
skills is the slow part of ranking (~90 patterns per description), so it is done
lazily, once per posting, the first time a search finds that posting's title relevant.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock

from sqlalchemy import func, select

from crescendo_agent.job_match import (_SKILL_PATTERNS, age_days, company_label, posting_analysis,
                                       posting_countries, rank, title_match)
from crescendo_agent.job_sources import Posting

from .job_store import last_crawl, open_postings
from .models import JobPosting
from .application_models import JobApplication

HIDDEN_REASONS = ("country", "location", "senior", "years", "age")


def _iso(moment: datetime | None) -> str | None:
    if moment is None:
        return None
    moment = moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)  # SQLite returns naive UTC
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def to_posting(row: JobPosting) -> Posting:
    return Posting(source=row.source, company=row.company_slug, posting_id=row.posting_id, title=row.title,
                   url=row.url, locations=tuple(row.locations or ()), workplace=row.workplace,
                   department=row.department, employment_type=row.employment_type,
                   published_at=_iso(row.published_at), compensation=row.compensation,
                   description=row.description or "", company_name=row.company_name,
                   countries=tuple(row.countries or ()))


@dataclass
class PostingIndex:
    key: tuple
    postings: list[Posting]
    first_seen: dict[tuple, str | None]
    crawl: dict | None
    _analysis: dict = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)

    def analysis(self, posting: Posting):
        """Memoized job_match.posting_analysis (skills named, years asked)."""
        key = (posting.source, posting.posting_id)
        found = self._analysis.get(key)
        if found is None:
            found = posting_analysis(posting)
            with self._lock:
                self._analysis[key] = found
        return found


_index: PostingIndex | None = None
_index_lock = Lock()


def current_index(session) -> PostingIndex:
    """The in-memory index, reloaded when the latest crawl or the open-posting count changes."""
    global _index
    run = last_crawl(session)
    count = session.scalar(select(func.count()).select_from(JobPosting).where(
        JobPosting.source == "ashby", JobPosting.closed_at.is_(None)))
    key = (run.id if run else None, run.status if run else None, count)
    with _index_lock:
        if _index is not None and _index.key == key:
            return _index
        rows = open_postings(session)
        crawl = None if run is None else {"id": run.id, "status": run.status, "started_at": _iso(run.started_at),
                                          "finished_at": _iso(run.finished_at)}
        _index = PostingIndex(key=key, postings=[to_posting(r) for r in rows],
                              first_seen={(r.source, r.posting_id): _iso(r.first_seen_at) for r in rows},
                              crawl=crawl)
        return _index


def reset_index() -> None:
    """Forget the cached index (tests)."""
    global _index
    with _index_lock:
        _index = None


def search(session, resume_skills: set[str], *, query: str, country: str | None = None, locations=(),
           remote: bool = False, no_senior: bool = False, max_years: int | None = None,
           max_age_days: int = 30, offset: int = 0, limit: int = 50,
           source: str | None = None, hide_applied: bool = False) -> dict:
    """One page of ranked postings plus totals and why other relevant postings were hidden."""
    index = current_index(session)
    hidden = dict.fromkeys(HIDDEN_REASONS, 0)
    # Read tracker state for each request; changing an application must not stale the crawl cache.
    applications = {(a.source, a.posting_id): a for a in session.scalars(select(JobApplication))}
    fresh = []
    for posting in index.postings:
        if source and posting.source != source:
            continue
        application = applications.get((posting.source, posting.posting_id))
        if hide_applied and application and (application.applied_on or application.status != "ready"):
            continue
        age = age_days(posting.published_at)
        if age is not None and age > max_age_days:
            if title_match(query, posting.title) >= 0.6:  # same relevance bar as rank()
                hidden["age"] += 1
            continue
        fresh.append(posting)
    matches = rank(fresh, resume_skills, query, location=list(locations) or None, remote=remote,
                   max_years=max_years, no_senior=no_senior, country=country, analysis=index.analysis,
                   dropped=hidden)
    rows = []
    for match in matches[offset:offset + limit]:
        posting = match.posting
        row = match.as_dict()
        row.update(posting_id=posting.posting_id, age_days=age_days(posting.published_at),
                   first_seen=index.first_seen.get((posting.source, posting.posting_id)),
                   country_known=bool(posting_countries(posting)))
        application = applications.get((posting.source, posting.posting_id))
        row["application"] = None if application is None else {
            "status": application.status,
            "applied_on": application.applied_on.isoformat() if application.applied_on else None}
        rows.append(row)
    return {"total": len(matches), "offset": offset, "limit": limit, "hidden": hidden,
            "postings_searched": sum(1 for p in index.postings if not source or p.source == source),
            "crawl": index.crawl, "results": rows}


def posting_detail(session, source: str, posting_id: str, resume_skills: set[str] | None) -> dict | None:
    """Everything shown when a card is expanded, including closed postings still stored."""
    row = session.get(JobPosting, (source, posting_id))
    if row is None:
        return None
    posting = to_posting(row)
    skills, asked = posting_analysis(posting)
    have = resume_skills or set()
    return {"source": row.source, "posting_id": row.posting_id, "title": row.title, "url": row.url,
            "company": company_label(posting), "description": row.description,
            "locations": list(row.locations or ()), "countries": sorted(posting_countries(posting)),
            "workplace": row.workplace, "department": row.department, "employment_type": row.employment_type,
            "compensation": row.compensation, "posted": _iso(row.published_at), "age_days": age_days(posting.published_at),
            "first_seen": _iso(row.first_seen_at), "last_seen": _iso(row.last_seen_at),
            "closed_at": _iso(row.closed_at), "years_asked": asked,
            "matched_skills": sorted(skills & have), "missing_skills": sorted(skills - have),
            "segments": skill_segments(row.description or "", skills & have, skills - have)}


def skill_segments(text: str, have: set[str], gaps: set[str], limit: int = 400) -> list[dict]:
    """Split text into plain and skill-mention segments for highlighting.

    The page renders segments instead of re-running Python's patterns in JavaScript,
    whose string offsets differ from Python's for characters outside the BMP.
    Overlapping mentions keep the earliest; at most ``limit`` highlights.
    """
    spans = []
    for name in have | gaps:
        pattern = _SKILL_PATTERNS.get(name)
        if pattern is not None:
            spans += [(m.start(), m.end(), name) for m in pattern.finditer(text) if m.end() > m.start()]
    spans.sort()
    segments, cursor = [], 0
    for start, end, name in spans:
        if start < cursor or len(segments) >= 2 * limit:
            continue
        if start > cursor:
            segments.append({"text": text[cursor:start]})
        segments.append({"text": text[start:end], "skill": name, "kind": "have" if name in have else "gap"})
        cursor = end
    if cursor < len(text):
        segments.append({"text": text[cursor:]})
    return segments
