"""Offline tests for JOB-F07: storing the daily Ashby crawl (SQLite stand-in for Postgres)."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from crescendo_agent.job_sources import BoardResult, CompanyBoard, Posting
from crescendo_api.job_store import open_postings, parse_time, sync_board_results
from crescendo_api.models import Base, JobCompany, JobPosting

DAY0 = datetime(2026, 11, 17, 8, 0, tzinfo=timezone.utc)
ACME = CompanyBoard("ashby", "acme")


def job(pid, days_old=1, title="AI Engineer", **kw):
    published = (DAY0 - timedelta(days=days_old)).isoformat().replace("+00:00", "Z") if days_old is not None else None
    values = dict(source="ashby", company="acme", posting_id=pid, title=title,
                  url=f"https://jobs.ashbyhq.com/acme/{pid}", locations=("New York",), countries=("United States",),
                  published_at=published, description="Python")
    values.update(kw)
    return Posting(**values)


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def sync(session, results, now=DAY0):
    stats = sync_board_results(session, results, now=now)
    session.commit()
    return stats


def rows(session):
    return {r.posting_id: r for r in session.scalars(select(JobPosting))}


def aware(moment):
    return moment if moment is None or moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def test_first_crawl_stores_only_the_window(session):
    stats = sync(session, [BoardResult(ACME, postings=[job("a"), job("b", days_old=29), job("old", days_old=31)])])
    assert set(rows(session)) == {"a", "b"}
    assert (stats.inserted, stats.updated, stats.postings_seen, stats.companies) == (2, 0, 2, 1)
    stored = rows(session)["a"]
    assert stored.locations == ["New York"] and stored.countries == ["United States"]
    assert aware(stored.first_seen_at) == aware(stored.last_seen_at) == DAY0 and stored.closed_at is None
    company = session.get(JobCompany, ("ashby", "acme"))
    assert company.status == "live" and company.open_postings == 2


def test_next_day_updates_closes_and_reopens(session):
    sync(session, [BoardResult(ACME, postings=[job("a"), job("b")])])
    day1 = DAY0 + timedelta(days=1)
    stats = sync(session, [BoardResult(ACME, postings=[job("a", title="AI Engineer II"), job("c")])], now=day1)
    stored = rows(session)
    assert (stats.inserted, stats.updated, stats.closed) == (1, 1, 1)
    assert stored["a"].title == "AI Engineer II"
    assert aware(stored["a"].first_seen_at) == DAY0 and aware(stored["a"].last_seen_at) == day1
    assert aware(stored["b"].closed_at) == day1                    # no longer listed
    sync(session, [BoardResult(ACME, postings=[job("a"), job("b"), job("c")])], now=day1 + timedelta(days=1))
    assert rows(session)["b"].closed_at is None                    # listed again: reopened


def test_temporary_failure_closes_nothing(session):
    sync(session, [BoardResult(ACME, postings=[job("a")])])
    stats = sync(session, [BoardResult(ACME, error="The job board API timed out.")], now=DAY0 + timedelta(days=1))
    assert rows(session)["a"].closed_at is None and stats.closed == 0 and stats.boards_failed == 1
    company = session.get(JobCompany, ("ashby", "acme"))
    assert company.status == "error" and company.last_error == "The job board API timed out."
    assert company.open_postings == 1                               # unchanged from the last good check


def test_missing_board_closes_its_postings(session):
    sync(session, [BoardResult(ACME, postings=[job("a")])])
    stats = sync(session, [BoardResult(ACME, error="No public job board with that name (HTTP 404).")],
                 now=DAY0 + timedelta(days=1))
    assert rows(session)["a"].closed_at is not None and stats.closed == 1
    assert session.get(JobCompany, ("ashby", "acme")).status == "missing"


def test_postings_older_than_the_window_are_deleted(session):
    # "fresh" is published at DAY0; "undated" has no date, so its age counts from first seen (DAY0).
    sync(session, [BoardResult(ACME, postings=[job("fresh", days_old=0), job("undated", days_old=None)])])
    stats = sync(session, [BoardResult(ACME, postings=[job("fresh", days_old=0), job("undated", days_old=None)])],
                 now=DAY0 + timedelta(days=29))
    assert set(rows(session)) == {"fresh", "undated"} and stats.deleted == 0
    stats = sync(session, [BoardResult(ACME, postings=[job("fresh", days_old=0)])], now=DAY0 + timedelta(days=31))
    assert rows(session) == {} and stats.deleted == 2               # both now 31 days old, still listed or not


def test_open_postings_excludes_closed_and_old(session):
    other = CompanyBoard("ashby", "beta")
    sync(session, [BoardResult(ACME, postings=[job("new", days_old=1), job("closing", days_old=2)]),
                   BoardResult(other, postings=[job("beta1", days_old=3, company="beta")])])
    sync(session, [BoardResult(ACME, postings=[job("new", days_old=1)])])
    assert [r.posting_id for r in open_postings(session, now=DAY0)] == ["new", "beta1"]  # newest first
    assert [r.posting_id for r in open_postings(session, now=DAY0, window_days=2)] == ["new"]


def test_untrusted_text_and_duplicates(session):
    stats = sync(session, [BoardResult(ACME, postings=[job("a", title="AI\x00 Engineer", description="Py\x00thon"),
                                                       job("a")])])
    stored = rows(session)["a"]
    assert stored.title == "AI Engineer" and stored.description == "Python"
    assert stats.inserted == 1                                      # the second copy was skipped


def test_board_slug_case_is_one_company(session):
    sync(session, [BoardResult(CompanyBoard("ashby", "Notion"), postings=[job("a", company="Notion")])])
    sync(session, [BoardResult(CompanyBoard("ashby", "notion"), postings=[job("a", company="notion")])])
    assert [c.slug for c in session.scalars(select(JobCompany))] == ["notion"]
    assert rows(session)["a"].company_slug == "notion"


@pytest.mark.parametrize("value, expected", [
    ("2026-11-16T08:00:00Z", datetime(2026, 11, 16, 8, tzinfo=timezone.utc)),
    ("2026-11-16T03:00:00-05:00", datetime(2026, 11, 16, 8, tzinfo=timezone.utc)),
    ("2026-11-16T08:00:00", None), ("garbage", None), ("", None), (None, None)])
def test_parse_time(value, expected):
    assert parse_time(value) == expected
