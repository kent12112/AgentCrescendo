"""Offline tests for JOB-F08: web job search, posting details, resume upload, picks."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from crescendo_api import job_search
from crescendo_api.config import get_settings
from crescendo_api.database import get_session
from crescendo_api.job_search import skill_segments
from crescendo_api.main import app
from crescendo_api.models import Base, JobCrawlRun, JobPosting

TOKEN = "test-only-token-with-more-than-32-characters"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
NOW = datetime.now(timezone.utc)
UUIDS = [f"00000000-0000-4000-8000-{n:012d}" for n in range(10)]
RESUME = "Python, TypeScript, LLMs, AI agents, PostgreSQL. Built RAG pipelines."


def posting_row(n, title="AI Engineer", *, countries=("United States",), locations=("New York",),
                days_old=2, description="Python and LLMs. Kubernetes a plus.", closed=False):
    return JobPosting(source="ashby", posting_id=UUIDS[n], company_slug=f"co{n}", company_name=f"Company {n}",
                      title=title, url=f"https://jobs.ashbyhq.com/co{n}/{UUIDS[n]}", locations=list(locations),
                      countries=list(countries), workplace="hybrid", compensation="$150K – $200K",
                      description=description, published_at=NOW - timedelta(days=days_old),
                      first_seen_at=NOW - timedelta(days=days_old), last_seen_at=NOW,
                      closed_at=NOW if closed else None)


@pytest.fixture
def engine():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def client(monkeypatch, engine):
    monkeypatch.setenv("DEV_API_TOKEN", TOKEN)
    get_settings.cache_clear()
    job_search.reset_index()

    def session_override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    job_search.reset_index()
    get_settings.cache_clear()


def seed(engine, *rows, crawl_id=1):
    with Session(engine) as session:
        session.add_all(rows)
        session.add(JobCrawlRun(id=crawl_id, started_at=NOW, finished_at=NOW, status="ok", companies=1,
                                boards_failed=0, postings_seen=len(rows), inserted=len(rows), updated=0,
                                closed=0, deleted=0))
        session.commit()


def upload(client, body=RESUME.encode(), content_type="text/plain", filename="resume.txt"):
    return client.put("/jobs/resume", content=body, headers={**AUTH, "Content-Type": content_type,
                                                             "X-Filename": filename})


# --- Access and resume ---


def test_every_job_route_needs_the_token(client):
    for method, path in [("get", "/jobs/search?q=ai"), ("get", "/jobs/resume"), ("get", "/jobs/picks"),
                         ("get", f"/jobs/postings/ashby/{UUIDS[0]}"), ("delete", "/jobs/resume")]:
        assert getattr(client, method)(path).status_code == 401
    assert client.put("/jobs/picks", json={"picks": []}).status_code == 401


def test_resume_upload_store_and_delete(client):
    assert client.get("/jobs/resume", headers=AUTH).json() == {"resume": None}
    response = upload(client, filename="../../etc/My Resume.txt")
    assert response.status_code == 200
    info = response.json()["resume"]
    assert info["filename"] == "My Resume.txt"                        # path parts dropped
    encoded = upload(client, filename="%E5%B1%A5%E6%AD%B4%E6%9B%B8.pdf.txt").json()["resume"]  # proxy-encoded
    assert encoded["filename"] == "履歴書.pdf.txt"
    assert {"Python", "TypeScript", "LLMs", "AI agents", "RAG", "PostgreSQL"} <= set(info["skills"])
    assert "text" not in info                                         # the text never goes back to the browser
    assert client.get("/jobs/resume", headers=AUTH).json()["resume"]["characters"] == len(RESUME)
    assert client.delete("/jobs/resume", headers=AUTH).status_code == 204
    assert client.get("/jobs/resume", headers=AUTH).json() == {"resume": None}


def test_resume_upload_rejections(client, monkeypatch):
    assert upload(client, content_type="application/msword").status_code == 415
    response = upload(client, body=b"not a pdf", content_type="application/pdf")
    assert response.status_code == 422 and "could not be read" in response.json()["detail"]
    assert upload(client, body=b"   ").status_code == 422                       # no text
    monkeypatch.setattr("crescendo_api.routes.jobs.MAX_BYTES", 10)
    assert upload(client, body=b"x" * 11).status_code == 413


# --- Search ---


def test_search_needs_a_resume_then_ranks_and_explains(client, engine):
    seed(engine,
         posting_row(0, "AI Engineer", description="Python, LLMs, AI agents and TypeScript."),
         posting_row(1, "Senior AI Engineer"),
         posting_row(2, "AI Engineer", countries=("United Kingdom",), locations=("London",)),
         posting_row(3, "AI Engineer II", description="5+ years of experience with Python."),
         posting_row(4, "Account Executive"),
         posting_row(5, "AI Engineer III", days_old=20),
         posting_row(6, "AI Engineer IV", closed=True))
    params = {"q": "ai engineer", "country": "united states", "no_senior": "true", "max_years": "3"}
    assert client.get("/jobs/search", params=params, headers=AUTH).status_code == 409
    upload(client)
    page = client.get("/jobs/search", params=params, headers=AUTH).json()
    assert [r["posting_id"] for r in page["results"]] == [UUIDS[0], UUIDS[5]]
    assert page["total"] == 2 and page["postings_searched"] == 6           # the closed one is not searched
    assert page["hidden"] == {"country": 1, "location": 0, "senior": 1, "years": 1, "age": 0}
    assert page["crawl"]["status"] == "ok"
    top = page["results"][0]
    assert top["score"] > page["results"][1]["score"]
    assert {"Python", "LLMs", "AI agents", "TypeScript"} <= set(top["matched_skills"])
    assert top["company"] == "Company 0" and top["compensation"] == "$150K – $200K"
    assert top["age_days"] == 2 and top["country_known"] and top["picked"] is False
    assert "description" not in top                                      # details load on demand

    young = client.get("/jobs/search", params={**params, "max_age_days": 10}, headers=AUTH).json()
    assert young["total"] == 1 and young["hidden"]["age"] == 1           # only relevant titles counted
    paged = client.get("/jobs/search", params={**params, "offset": 1, "limit": 1}, headers=AUTH).json()
    assert [r["posting_id"] for r in paged["results"]] == [UUIDS[5]] and paged["total"] == 2


@pytest.mark.parametrize("params", [{"q": ""}, {"q": "x" * 101}, {"q": "ai", "limit": 0},
                                    {"q": "ai", "limit": 101}, {"q": "ai", "max_age_days": 31},
                                    {"q": "ai", "location": ["a", "b", "c", "d", "e", "f"]}])
def test_search_parameter_limits(client, params):
    upload(client)
    assert client.get("/jobs/search", params=params, headers=AUTH).status_code == 422


def test_search_of_only_stop_words_is_rejected(client, engine):
    seed(engine, posting_row(0))
    upload(client)
    response = client.get("/jobs/search", params={"q": "the and"}, headers=AUTH)
    assert response.status_code == 422 and "at least one word" in response.json()["detail"]


def test_index_reloads_after_a_new_crawl(client, engine):
    seed(engine, posting_row(0))
    upload(client)
    assert client.get("/jobs/search", params={"q": "ai engineer"}, headers=AUTH).json()["total"] == 1
    seed(engine, posting_row(1, "ML Engineer"), crawl_id=2)
    page = client.get("/jobs/search", params={"q": "ai engineer"}, headers=AUTH).json()
    assert page["total"] == 2 and page["crawl"]["id"] == 2


# --- Details ---


def test_posting_detail_with_highlights(client, engine):
    seed(engine, posting_row(0, description="We use Python daily. Kubernetes is a plus."))
    upload(client)
    detail = client.get(f"/jobs/postings/ashby/{UUIDS[0]}", headers=AUTH).json()
    assert detail["matched_skills"] == ["Python"] and detail["missing_skills"] == ["Kubernetes"]  # IMPLIES is resume-side only
    marked = [(s["text"], s.get("kind")) for s in detail["segments"] if s.get("kind")]
    assert marked == [("Python", "have"), ("Kubernetes", "gap")]
    assert "".join(s["text"] for s in detail["segments"]) == detail["description"]
    assert detail["closed_at"] is None and detail["first_seen"]
    assert client.get(f"/jobs/postings/ashby/{UUIDS[9]}", headers=AUTH).status_code == 404
    assert client.get("/jobs/postings/ashby/bad%20id", headers=AUTH).status_code == 422
    assert client.get(f"/jobs/postings/workday/{UUIDS[0]}", headers=AUTH).status_code == 422


def test_skill_segments_keep_text_intact_with_emoji_and_overlaps():
    text = "🚀 Ship LLMs and large language models with Python 🐍"
    segments = skill_segments(text, {"LLMs", "Python"}, set())
    assert "".join(s["text"] for s in segments) == text
    assert [s["text"] for s in segments if s.get("kind")] == ["LLMs", "large language models", "Python"]


# --- Picks ---


def test_picks_replace_limit_and_validation(client, engine):
    seed(engine, *(posting_row(n) for n in range(4)), posting_row(5, closed=True))
    upload(client)
    ref = lambda n: {"source": "ashby", "posting_id": UUIDS[n]}
    response = client.put("/jobs/picks", json={"picks": [ref(0), ref(1), ref(0)]}, headers=AUTH)
    assert response.status_code == 200 and [p["posting_id"] for p in response.json()["picks"]] == UUIDS[:2]
    assert response.json()["max"] == 3 and response.json()["picks"][0]["title"] == "AI Engineer"
    assert client.put("/jobs/picks", json={"picks": [ref(0), ref(1), ref(2), ref(3)]},
                      headers=AUTH).status_code == 422                     # a 4th is refused by the server
    assert client.put("/jobs/picks", json={"picks": [ref(5)]}, headers=AUTH).status_code == 422  # closed
    assert client.put("/jobs/picks", json={"picks": [ref(9)]}, headers=AUTH).status_code == 422  # unknown
    assert client.put("/jobs/picks", json={"picks": [{"source": "x", "posting_id": "1"}]},
                      headers=AUTH).status_code == 422
    assert [p["posting_id"] for p in client.get("/jobs/picks", headers=AUTH).json()["picks"]] == UUIDS[:2]
    page = client.get("/jobs/search", params={"q": "ai engineer"}, headers=AUTH).json()
    assert {r["posting_id"] for r in page["results"] if r["picked"]} == set(UUIDS[:2])
    assert client.put("/jobs/picks", json={"picks": []}, headers=AUTH).json()["picks"] == []
