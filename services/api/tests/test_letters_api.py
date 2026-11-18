"""Offline letter flow: real database/HTTP, fake provider at the paid boundary."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from crescendo_api.config import get_settings
from crescendo_api.database import get_session
from crescendo_api.letters import Draft, DraftUnavailable, check_draft, redact
from crescendo_api.main import app
from crescendo_api.models import Base, CoverLetter, JobPosting, JobResume, LetterSession
from crescendo_api.company_research import ResearchUnavailable
from crescendo_api.routes.letters import company_researcher, draft_generator

TOKEN = "test-only-letter-token-at-least-32-characters"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
NOW = datetime.now(timezone.utc)
RESUME = "Alex Middle Example\nalex@example.com | +1 (212) 555-0123 | https://github.com/alex\n123 Main Street, New York\nBuilt Python data pipelines for 3 years. Reduced latency by 25%."
POSTING_ID = "00000000-0000-4000-8000-000000000001"
REF = {"source": "ashby", "posting_id": POSTING_ID}
RAW = {"paragraphs": [[{"text": "I built Python data pipelines for 3 years.", "source": "resume",
                         "quote": "Built Python data pipelines for 3 years."}],
                      [{"text": "Your team builds tools for developers.", "source": "posting",
                        "quote": "We build tools for developers."}]]}


@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setenv("DEV_API_TOKEN", TOKEN)
    monkeypatch.setenv("GROQ_API_KEY", "fake-test-key")
    get_settings.cache_clear()
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(JobResume(id=1, filename="resume.txt", text=RESUME, skills=["Python"], uploaded_at=NOW))
        session.add(JobPosting(**REF, company_slug="sample", company_name="Sample Co", title="AI Engineer",
                               url=f"https://jobs.ashbyhq.com/sample/{POSTING_ID}",
                               description="We build tools for developers. Python required.",
                               locations=["New York"], countries=["United States"],
                               first_seen_at=NOW, last_seen_at=NOW))
        session.commit()

    def sessions():
        with Session(engine) as session:
            yield session

    calls = []

    def fake(inputs, posting, key, on_turn=None):
        calls.append((inputs, posting))
        assert key == "fake-test-key"
        if on_turn:  # The route persists each finished turn before the final result.
            on_turn([{"turn": 1, "role": "thinker", "status": "done", "seconds": 0.1, "summary": "plan", "detail": {}}])
        return check_draft(Draft.model_validate(RAW), inputs["resume"], posting)

    app.dependency_overrides[get_session] = sessions
    app.dependency_overrides[draft_generator] = lambda: fake
    with TestClient(app) as client:
        yield client, engine, calls
    app.dependency_overrides.clear()
    get_settings.cache_clear()
    engine.dispose()


def preview(client):
    response = client.post("/jobs/letter-sessions", json={"name": "Alex Example", "picks": [{**REF, "company_notes": "Their developer tooling interests me."}]}, headers=AUTH)
    assert response.status_code == 201, response.text
    return response.json()


def confirm(client, row):
    response = client.post(f"/jobs/letter-sessions/{row['id']}/confirm", json={"input_digest": row["input_digest"]}, headers=AUTH)
    assert response.status_code == 200, response.text


def test_preview_removes_identity_and_never_calls_provider(setup):
    client, engine, calls = setup
    row = preview(client)
    text = row["inputs"]["resume"]
    for private in ["Alex", "Middle", "Example", "alex@example.com", "212", "github", "123 Main"]:
        assert private.casefold() not in text.casefold()
    assert "25%" in text and "3 years" in text and "Python" in text
    assert row["confirmed_at"] is None and not calls
    assert "identity" not in row
    with Session(engine) as session:
        assert session.get(LetterSession, row["id"]).identity == {"name": "Alex Example"}


def test_confirm_is_bound_to_snapshot_and_key_is_required(setup, monkeypatch):
    client, _, calls = setup
    row = preview(client)
    path = f"/jobs/letter-sessions/{row['id']}/confirm"
    assert client.post(path, headers=AUTH, json={"input_digest": "0" * 64}).status_code == 409
    monkeypatch.setenv("GROQ_API_KEY", "")
    get_settings.cache_clear()
    assert client.post(path, headers=AUTH, json={"input_digest": row["input_digest"]}).status_code == 409
    assert not calls


def test_full_flow_uses_snapshot_and_is_idempotent(setup):
    client, engine, calls = setup
    row = preview(client)
    letter = row["letters"][0]
    path = f"/jobs/letters/{letter['id']}"
    assert client.post(path + "/generate", headers=AUTH).status_code == 409
    assert not calls
    confirm(client, row)
    with Session(engine) as session:
        session.get(JobResume, 1).text = "PRIVATE NEW RESUME"
        session.execute(delete(JobPosting))
        session.commit()
    draft = client.post(path + "/generate", headers=AUTH).json()
    assert draft["status"] == "draft" and len(calls) == 1
    assert [turn["role"] for turn in draft["turns"]] == ["thinker"]
    assert not draft["text"].startswith("Dear") and "[NAME]" not in draft["text"]
    assert "PRIVATE" not in calls[0][0]["resume"]
    assert all(check["quote_found"] for check in draft["checks"])
    assert client.post(path + "/generate", headers=AUTH).json()["text"] == draft["text"]
    assert len(calls) == 1
    assert client.get(path + "/download", headers=AUTH).status_code == 409
    assert client.put(path, headers=AUTH, json={"text": draft["text"], "version": draft["version"], "approve": True}).status_code == 422
    approved = client.put(path, headers=AUTH, json={"text": draft["text"], "version": draft["version"], "approve": True, "reviewed": True}).json()
    assert approved["status"] == "approved" and approved["text"] == draft["text"]
    download = client.get(path + "/download", headers=AUTH)
    assert download.text == approved["text"] and "attachment" in download.headers["content-disposition"]
    assert download.headers["cache-control"] == "no-store"
    assert client.put(path, headers=AUTH, json={"text": draft["text"], "version": draft["version"]}).status_code == 409
    assert client.get("/jobs/letters", headers=AUTH).json()["letters"][0]["status"] == "approved"


def test_edits_warn_about_old_checks(setup):
    client, _, _ = setup
    row = preview(client); confirm(client, row)
    path = f"/jobs/letters/{row['letters'][0]['id']}"
    letter = client.post(path + "/generate", headers=AUTH).json()
    updated = client.put(path, headers=AUTH, json={"text": letter["text"] + "\nMy manual edit.", "version": letter["version"]}).json()
    assert updated["status"] == "draft" and updated["checks"][-1]["source"] == "user_edit"
    assert client.get(path + "/download", headers=AUTH).status_code == 409


def test_provider_failure_is_persisted_and_retryable(setup):
    client, engine, calls = setup
    row = preview(client); confirm(client, row)
    path = f"/jobs/letters/{row['letters'][0]['id']}"

    def fail(*args, **kwargs):
        raise DraftUnavailable("Drafting failed. Retry this letter.")

    original = app.dependency_overrides[draft_generator]
    app.dependency_overrides[draft_generator] = lambda: fail
    failed = client.post(path + "/generate", headers=AUTH).json()
    assert failed["status"] == "failed" and "Retry" in failed["error"]
    app.dependency_overrides[draft_generator] = original
    assert client.post(path + "/generate", headers=AUTH).json()["status"] == "draft"
    assert len(calls) == 1


def test_active_request_is_not_duplicated_and_stale_request_recovers(setup):
    client, engine, calls = setup
    row = preview(client); confirm(client, row)
    letter_id = row["letters"][0]["id"]
    path = f"/jobs/letters/{letter_id}/generate"
    with Session(engine) as session:
        letter = session.get(CoverLetter, letter_id)
        letter.status, letter.updated_at = "generating", NOW
        session.commit()
    assert client.post(path, headers=AUTH).status_code == 409 and not calls
    with Session(engine) as session:
        session.get(CoverLetter, letter_id).updated_at = NOW - timedelta(seconds=130)
        session.commit()
    assert client.post(path, headers=AUTH).json()["status"] == "draft"


def test_bad_picks_and_auth_do_not_send_data(setup):
    client, engine, calls = setup
    body = {"name": "Alex Example", "picks": [REF] * 4}
    assert client.post("/jobs/letter-sessions", json=body, headers=AUTH).status_code == 422
    body["picks"] = [REF, REF]
    assert client.post("/jobs/letter-sessions", json=body, headers=AUTH).status_code == 422
    body["picks"] = [REF]
    assert client.post("/jobs/letter-sessions", json=body).status_code == 401
    assert client.get("/jobs/letters").status_code == 401
    with Session(engine) as session:
        session.get(JobPosting, ("ashby", POSTING_ID)).closed_at = NOW
        session.commit()
    assert client.post("/jobs/letter-sessions", json=body, headers=AUTH).status_code == 422
    assert not calls


def test_claim_flags_for_invented_numbers_quotes_and_unsourced_text():
    raw = {"paragraphs": [[{"text": "I reduced latency by 99%.", "source": "resume", "quote": "Reduced latency by 25%."}],
                           [{"text": "You have 10 million users.", "source": "posting", "quote": "A quote that is absent."},
                            {"text": "Thank you for considering me.", "source": "none", "quote": ""}]]}
    _, checks = check_draft(Draft.model_validate(raw), RESUME, {"description": "Python required.", "company_notes": ""})
    assert any("number" in flag for flag in checks[0]["flags"])
    assert any("wording differs" in flag for flag in checks[0]["flags"])
    assert not checks[1]["quote_found"] and checks[1]["flags"]
    assert checks[2]["flags"]


@pytest.mark.parametrize("primary", ["resume", "posting"])
def test_connected_claim_checks_both_quotes_without_hiding_invented_numbers(primary):
    quotes = {"resume": "Reduced latency by 25%.", "posting": "We build tools for developers."}
    other = "posting" if primary == "resume" else "resume"
    raw = {"paragraphs": [[{
        "text": "My work reducing latency by 99% is relevant to your tools for developers.",
        "source": primary, "quote": quotes[primary],
        "supporting_quotes": [{"source": other, "quote": quotes[other]}],
    }], RAW["paragraphs"][1]]}
    _, checks = check_draft(Draft.model_validate(raw), RESUME,
                            {"description": quotes["posting"], "company_notes": ""})
    connection = checks[0]
    assert connection["quote_found"] and connection["supporting_quotes"][0]["quote_found"]
    assert any("number" in flag for flag in connection["flags"])
    assert any("Review the connection" in flag for flag in connection["flags"])
    assert not any("not attributed" in flag for flag in connection["flags"])


def test_additional_context_is_checked_and_user_notes_stay_labeled():
    raw = {"paragraphs": [[{
        "text": "My pipeline experience would inform your team's documented decisions.",
        "source": "resume", "quote": "Built Python data pipelines for 3 years.",
        "supporting_quotes": [
            {"source": "company_notes", "quote": "The team documents design decisions."},
            {"source": "posting", "quote": "This invented excerpt is not present."},
        ],
    }], RAW["paragraphs"][1]]}
    _, checks = check_draft(Draft.model_validate(raw), RESUME, {
        "description": "We build tools for developers.",
        "company_notes": "The team documents design decisions.",
    })
    assert [q["quote_found"] for q in checks[0]["supporting_quotes"]] == [True, False]
    assert any("Additional posting quote was not found" in flag for flag in checks[0]["flags"])
    assert any("supplied by you" in flag for flag in checks[0]["flags"])


def test_connected_evidence_survives_save_reload_and_approval(setup):
    client, _, _ = setup
    row = preview(client)
    confirm(client, row)
    path = f"/jobs/letters/{row['letters'][0]['id']}"

    def connected(inputs, posting, key, on_turn=None):
        raw = {"paragraphs": [[{
            "text": "My Python pipeline work is relevant to your developer tools.",
            "source": "resume", "quote": "Built Python data pipelines for 3 years.",
            "supporting_quotes": [{"source": "posting", "quote": "We build tools for developers."}],
        }], RAW["paragraphs"][1]]}
        return check_draft(Draft.model_validate(raw), inputs["resume"], posting)

    app.dependency_overrides[draft_generator] = lambda: connected
    draft = client.post(path + "/generate", headers=AUTH).json()
    loaded = client.get(path, headers=AUTH).json()
    assert loaded["checks"] == draft["checks"]
    assert loaded["checks"][0]["supporting_quotes"][0]["quote_found"]
    approved = client.put(path, headers=AUTH, json={
        "text": draft["text"], "version": draft["version"], "approve": True, "reviewed": True,
    }).json()
    assert approved["status"] == "approved"
    assert approved["checks"] == draft["checks"]


def test_redaction_handles_repeated_names_bare_links_and_dates():
    value = redact("Jane Doe: Jane built systems in 2021-2024; jane@sample.org github.com/jane", "Jane Doe")
    assert "Jane" not in value and "sample.org" not in value and "github" not in value
    assert "2021-2024" in value


FACT = {"topic": "product", "claim": "Ships a profiler.", "quote": "We ship a profiler for developers.",
        "url": "https://sample.example/about"}


def test_research_before_consent_changes_snapshot_and_reaches_drafting(setup):
    client, _, calls = setup
    seen = []

    def researcher(job, key, model):
        seen.append((job["company"], key, model))
        return {"status": "done", "model": model, "facts": [FACT], "excluded": [], "open_questions": []}

    app.dependency_overrides[company_researcher] = lambda: researcher
    row = preview(client)
    response = client.post(f"/jobs/letter-sessions/{row['id']}/research", headers=AUTH)
    assert response.status_code == 200, response.text
    data = response.json()
    assert seen == [("Sample Co", "fake-test-key", get_settings().research_model)] and not calls
    assert data["input_digest"] != row["input_digest"]
    assert data["inputs"]["jobs"][0]["company_research"]["facts"] == [FACT]
    assert data["letters"][0]["posting"]["company_research"]["facts"] == [FACT]
    # Consent given to the pre-research preview no longer matches.
    stale = client.post(f"/jobs/letter-sessions/{row['id']}/confirm", json={"input_digest": row["input_digest"]}, headers=AUTH)
    assert stale.status_code == 409
    confirm(client, data)
    again = client.post(f"/jobs/letter-sessions/{row['id']}/research", headers=AUTH)
    assert again.status_code == 409 and len(seen) == 1
    client.post(f"/jobs/letters/{data['letters'][0]['id']}/generate", headers=AUTH)
    assert calls[0][1]["company_research"]["facts"] == [FACT]


def test_research_failure_is_recorded_without_blocking_the_preview(setup, monkeypatch):
    client, _, _ = setup

    def researcher(job, key, model):
        raise ResearchUnavailable("Groq's rate limit was reached. Wait 5 seconds, then retry this company research.")

    app.dependency_overrides[company_researcher] = lambda: researcher
    row = preview(client)
    data = client.post(f"/jobs/letter-sessions/{row['id']}/research", headers=AUTH).json()
    result = data["inputs"]["jobs"][0]["company_research"]
    assert result["status"] == "failed" and "rate limit" in result["error"] and result["facts"] == []
    monkeypatch.setenv("GROQ_API_KEY", "")
    get_settings.cache_clear()
    assert client.post(f"/jobs/letter-sessions/{row['id']}/research", headers=AUTH).status_code == 409
