"""Tracker behavior with a real disposable database; no providers or job submissions."""
from sqlalchemy import delete
from sqlalchemy.orm import Session

from crescendo_api.models import JobPosting
from test_jobs_api import AUTH, UUIDS, client, engine, posting_row, seed, upload


def path(number=0):
    return f"/jobs/applications/ashby/{UUIDS[number]}"


def test_tracker_needs_token_and_valid_input(client, engine):
    seed(engine, posting_row(0))
    assert client.get("/jobs/applications").status_code == 401
    assert client.put(path(), json={}).status_code == 401
    assert client.delete(path() + "?version=1").status_code == 401
    for body in ({"status": "submitted"}, {"notes": "x" * 8001}, {"version": 0},
                 {"applied_on": "yesterday"}, {"unknown": True}):
        assert client.put(path(), json=body, headers=AUTH).status_code == 422
    assert client.put(path(9), json={}, headers=AUTH).status_code == 404
    assert client.put("/jobs/applications/workday/123", json={}, headers=AUTH).status_code == 422


def test_applied_snapshot_survives_closed_and_deleted_posting(client, engine):
    seed(engine, posting_row(0, closed=True))
    # Tracking requires no resume or generated letter.
    created = client.put(path(), json={"applied_on": "2026-11-12", "notes": "Referral from a friend"}, headers=AUTH)
    assert created.status_code == 200
    saved = created.json()
    assert saved["status"] == "applied" and saved["version"] == 1
    assert saved["posting"]["description"] == "Python and LLMs. Kubernetes a plus."
    assert saved["posting_state"] == "closed"
    with Session(engine) as session:
        session.execute(delete(JobPosting))
        session.commit()
    rows = client.get("/jobs/applications", headers=AUTH).json()["applications"]
    assert len(rows) == 1 and rows[0]["posting_state"] == "expired"
    assert rows[0]["notes"] == "Referral from a friend"
    updated = client.put(path(), json={"version": 1, "status": "interviewing", "applied_on": "2026-11-12",
        "follow_up_on": "2026-11-22", "notes": "Interview scheduled"}, headers=AUTH).json()
    assert updated["version"] == 2 and updated["status"] == "interviewing"
    assert updated["posting"] == saved["posting"] and updated["follow_up_on"] == "2026-11-22"


def test_duplicate_create_and_stale_edits_never_reset_progress(client, engine):
    seed(engine, posting_row(0))
    created = client.put(path(), json={"status": "offer", "applied_on": "2026-10-20", "notes": "Keep this"}, headers=AUTH).json()
    duplicate = client.put(path(), json={}, headers=AUTH).json()
    assert duplicate == created
    assert client.put(path(), json={"version": 1, "status": "withdrawn", "notes": "Final notes"}, headers=AUTH).status_code == 200
    assert client.put(path(), json={"version": 1, "notes": "Stale"}, headers=AUTH).status_code == 409
    assert client.delete(path() + "?version=1", headers=AUTH).status_code == 409
    saved = client.get("/jobs/applications", headers=AUTH).json()["applications"][0]
    assert saved["notes"] == "Final notes" and saved["applied_on"] == "2026-10-20"
    assert client.delete(path() + "?version=2", headers=AUTH).status_code == 204
    assert client.get("/jobs/applications", headers=AUTH).json()["applications"] == []
    assert client.put(path(), json={"version": 2}, headers=AUTH).status_code == 409


def test_search_badges_hide_applied_and_pagination_refresh_without_recrawl(client, engine):
    seed(engine, *(posting_row(n) for n in range(4)))
    upload(client)
    params = {"q": "ai engineer", "limit": 1}
    first = client.get("/jobs/search", params=params, headers=AUTH).json()
    assert first["total"] == 4 and first["results"][0]["application"] is None
    client.put(path(), json={"applied_on": "2026-11-17"}, headers=AUTH)
    client.put(path(1), json={"status": "ready"}, headers=AUTH)
    badged = client.get("/jobs/search", params={"q": "ai engineer"}, headers=AUTH).json()
    rows = {r["posting_id"]: r for r in badged["results"]}
    assert rows[UUIDS[0]]["application"] == {"status": "applied", "applied_on": "2026-11-17"}
    hidden = client.get("/jobs/search", params={**params, "hide_applied": True}, headers=AUTH).json()
    assert hidden["total"] == 3 and hidden["results"][0]["posting_id"] != UUIDS[0]
    next_page = client.get("/jobs/search", params={**params, "hide_applied": True, "offset": 1}, headers=AUTH).json()
    assert next_page["total"] == 3 and next_page["results"][0]["posting_id"] != hidden["results"][0]["posting_id"]
    client.put(path(1), json={"version": 1, "status": "interviewing"}, headers=AUTH)
    assert client.get("/jobs/search", params={**params, "hide_applied": True}, headers=AUTH).json()["total"] == 2


def test_ashby_is_default_source_and_other_sources_still_explicitly_searchable(client, engine):
    ashby = posting_row(0)
    lever = posting_row(1)
    lever.source = "lever"
    seed(engine, ashby, lever)
    upload(client)
    assert client.get("/jobs/search?q=ai+engineer", headers=AUTH).json()["total"] == 1
    page = client.get("/jobs/search?q=ai+engineer&source=lever", headers=AUTH).json()
    assert page["total"] == 1 and page["results"][0]["source"] == "lever"
    assert client.get("/jobs/search?q=ai&source=unknown", headers=AUTH).status_code == 422
