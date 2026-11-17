"""Store the daily job crawl in Postgres (JOB-F07). Public job data only; no resume text.

``sync_board_results`` applies one crawl's board results:

- A board that answered: its postings published in the last ``window_days`` are
  inserted or updated (``last_seen_at`` = now, reopened if closed). Its stored
  postings that are no longer listed get ``closed_at`` = now.
- A board that returned HTTP 404: the company is marked ``missing`` and its open
  postings are closed (the company left Ashby or renamed its board).
- Any other failure (timeout, 5xx): the company is marked ``error`` and its postings
  are left as they were. A bad network day must not close real jobs.
- Finally, postings published (or, when no date is given, first seen) before the
  window are deleted, open or not.

Inputs are duck-typed (``.board.source/.slug``, ``.postings``, ``.error`` and the
fields of crescendo_agent's ``Posting``) so this module does not import the agent
runtime.
"""
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import delete, func, insert, or_, select, update

from .config import Settings
from .models import JobCompany, JobPosting

WINDOW_DAYS = 30
BATCH = 1000


class JobDbSettings(BaseSettings):
    """Only the database URL: job scripts must not need the API's DEV_API_TOKEN."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = Settings.model_fields["database_url"].default


@dataclass
class SyncStats:
    companies: int = 0
    boards_failed: int = 0
    postings_seen: int = 0
    inserted: int = 0
    updated: int = 0
    closed: int = 0
    deleted: int = 0

    def as_dict(self) -> dict:
        return asdict(self)


def parse_time(value) -> datetime | None:
    """ISO 8601 (as produced by job_sources) -> aware UTC datetime, else None."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not isinstance(value, str) or not value:
        return None
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment.astimezone(timezone.utc) if moment.tzinfo else None


def _clean(value):
    """PostgreSQL text cannot hold NUL characters; one in untrusted page text would fail a batch."""
    if isinstance(value, str):
        return value.replace("\x00", "")
    if isinstance(value, (list, tuple)):
        return [_clean(item) for item in value]
    return value


def _values(posting, published) -> dict:
    values = {"company_slug": posting.company.lower(), "company_name": posting.company_name,
              "title": posting.title, "url": posting.url, "locations": list(posting.locations),
              "countries": list(posting.countries), "workplace": posting.workplace,
              "department": posting.department, "employment_type": posting.employment_type,
              "compensation": posting.compensation, "description": posting.description or "",
              "published_at": published}
    return {key: _clean(value) for key, value in values.items()}


def _in_batches(session, statement, rows):
    for start in range(0, len(rows), BATCH):
        session.execute(statement, rows[start:start + BATCH])


def sync_board_results(session, results, *, now: datetime | None = None,
                       window_days: int = WINDOW_DAYS) -> SyncStats:
    """Apply one crawl's results. The caller commits."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=window_days)
    stats = SyncStats()

    # What is stored now, by company: {(source, slug): {posting_id: closed_at}}.
    stored: dict[tuple, dict] = {}
    for source, slug, posting_id, closed_at in session.execute(
            select(JobPosting.source, JobPosting.company_slug, JobPosting.posting_id, JobPosting.closed_at)):
        stored.setdefault((source, slug), {})[posting_id] = closed_at
    companies = {(c.source, c.slug): c for c in session.scalars(select(JobCompany))}

    inserts, updates, closes, seen_anywhere = [], [], [], set()
    for result in results:
        key = (result.board.source, result.board.slug.lower())
        if key in companies:
            company = companies[key]
        else:
            company = companies[key] = JobCompany(source=key[0], slug=key[1], status="live",
                                                  first_seen_at=now, open_postings=0)
            session.add(company)
        company.last_checked_at = now
        stats.companies += 1
        previous = stored.get(key, {})

        if result.error:
            stats.boards_failed += 1
            company.last_error = result.error
            if "HTTP 404" in result.error:
                company.status, company.open_postings = "missing", 0
                closes += [{"source": key[0], "posting_id": pid, "closed_at": now}
                           for pid, closed_at in previous.items() if closed_at is None]
            else:
                company.status = "error"
            continue

        company.status, company.last_error = "live", None
        listed = set()
        for posting in result.postings:
            published = parse_time(posting.published_at)
            if published is not None and published < cutoff:
                continue  # older than the window: not stored
            pid = posting.posting_id
            if (key[0], pid) in seen_anywhere:
                continue  # the same posting twice in one crawl
            seen_anywhere.add((key[0], pid))
            listed.add(pid)
            row = {"source": key[0], "posting_id": pid, "last_seen_at": now, **_values(posting, published)}
            if pid in previous:
                updates.append({**row, "closed_at": None})
            else:
                inserts.append({**row, "first_seen_at": now})
        stats.postings_seen += len(listed)
        company.open_postings = len(listed)
        closes += [{"source": key[0], "posting_id": pid, "closed_at": now}
                   for pid, closed_at in previous.items() if closed_at is None and pid not in listed]

    session.flush()  # new companies first
    _in_batches(session, insert(JobPosting), inserts)
    _in_batches(session, update(JobPosting), updates)  # ORM bulk UPDATE by primary key
    _in_batches(session, update(JobPosting), closes)
    stats.inserted, stats.updated, stats.closed = len(inserts), len(updates), len(closes)

    stale = func.coalesce(JobPosting.published_at, JobPosting.first_seen_at) < cutoff
    stats.deleted = session.execute(delete(JobPosting).where(stale)).rowcount or 0
    return stats


def last_crawl(session):
    """The most recent crawl run (any status), or None."""
    from .models import JobCrawlRun

    return session.scalars(select(JobCrawlRun).order_by(JobCrawlRun.id.desc()).limit(1)).first()


def open_postings(session, *, source: str = "ashby", now: datetime | None = None,
                  window_days: int = WINDOW_DAYS) -> list[JobPosting]:
    """Postings still open and inside the window, newest first."""
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=window_days)
    query = (select(JobPosting).where(JobPosting.source == source, JobPosting.closed_at.is_(None),
                                      or_(JobPosting.published_at >= cutoff,
                                          JobPosting.published_at.is_(None) & (JobPosting.first_seen_at >= cutoff)))
             .order_by(JobPosting.published_at.desc()))
    return list(session.scalars(query))
