"""Real HTTP/database/thread lifecycle; substitute only the E2B desktop adapter."""
from datetime import datetime, timedelta, timezone
import threading
import time
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from crescendo_agent.writer import WriterFailure
from crescendo_api.config import get_settings
from crescendo_api.database import get_session
from crescendo_api.main import app
from crescendo_api.models import Base, CoverLetter, LetterSession, WriterExport
from crescendo_api.routes.letters import draft_generator
from crescendo_api.writer_service import WriterManager, get_writer_manager

TOKEN = "test-only-writer-token-at-least-32-characters"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
LETTER = "Dear Hiring Team,\n\nI built Python interfaces for Fictional Co.\n\nSincerely,\nAlex Example"
PDF = b"%PDF-1.4\nfictional bytes from fake verified desktop boundary"


class FakeDesktop:
    def __init__(self, key):
        self.viewer = SimpleNamespace(url="http://127.0.0.1:12345/watch/" + "a" * 40, connected=threading.Event())
        self.viewer.connected.set()
        self.fail = False
        self.cleanup = True
        self.closed = False
        self.sent = None
        self.hold = threading.Event()
        self.hold.set()

    def open(self):
        pass

    def prepare(self, checkpoint):
        checkpoint()
        if self.fail:
            raise WriterFailure("Controlled offline network check failure. No letter was typed.")

    def write_pdf(self, text, progress, checkpoint):
        self.sent = text
        progress("typing", len(text) // 2)
        while not self.hold.wait(0.01):
            checkpoint()
        checkpoint()
        progress("exporting", len(text))
        return PDF

    def close(self):
        self.closed = True
        return self.cleanup


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setenv("DEV_API_TOKEN", TOKEN)
    monkeypatch.setenv("E2B_API_KEY", "fake-no-network-key")
    get_settings.cache_clear()
    engine = create_engine(f"sqlite:///{tmp_path / 'writer.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    desktops = []

    def factory(key):
        desktop = FakeDesktop(key)
        desktops.append(desktop)
        return desktop

    manager = WriterManager(lambda: Session(engine), factory)

    def sessions():
        with Session(engine) as session:
            yield session

    with Session(engine) as session:
        letter = CoverLetter(session_id="fixture-session", posting={"company": "Fictional Co"},
                             status="approved", text=LETTER, version=3)
        session.add(letter); session.commit()
        letter_id = letter.id
    app.dependency_overrides[get_session] = sessions
    app.dependency_overrides[get_writer_manager] = lambda: manager
    with TestClient(app) as client:
        yield client, engine, manager, desktops, letter_id
    manager.shutdown()
    app.dependency_overrides.clear()
    get_settings.cache_clear()
    engine.dispose()


def start(client, letter_id):
    response = client.post(f"/jobs/letters/{letter_id}/writer", headers=AUTH, json={"version": 3})
    assert response.status_code == 202, response.text
    return response.json()


def wait_state(client, export_id, wanted):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        row = client.get(f"/jobs/writer-exports/{export_id}", headers=AUTH).json()
        if row["status"] in wanted:
            return row
        time.sleep(0.01)
    pytest.fail(f"Export did not reach {wanted}; last status {row['status']}")


def draft_fixture(setup, monkeypatch):
    client, engine, manager, desktops, letter_id = setup
    monkeypatch.setenv("GROQ_API_KEY", "fake-model-key"); get_settings.cache_clear()
    calls = []
    text = LETTER.replace("Alex Example", "[NAME]")
    with Session(engine) as session:
        session.add(LetterSession(id="fixture-session", inputs={"resume": "redacted resume"},
            input_digest="a" * 64, identity={"name": "Alex Example"}, confirmed_at=datetime.now(timezone.utc)))
        letter = session.get(CoverLetter, letter_id)
        letter.status, letter.text = "pending", ""
        session.commit()

    def generator(inputs, posting, key):
        calls.append((inputs, posting))
        assert desktops[0].viewer.connected.is_set()
        return text, [{"source": "resume", "text": text, "flags": []}]

    app.dependency_overrides[draft_generator] = lambda: generator
    return calls, text


def test_live_draft_opens_before_model_and_stays_unapproved(setup, monkeypatch):
    calls, text = draft_fixture(setup, monkeypatch)
    client, engine, manager, desktops, letter_id = setup
    path = f"/jobs/letters/{letter_id}/draft-writer"
    row = client.post(path, headers=AUTH, json={"version": 3}).json()
    ready = wait_state(client, row["id"], {"waiting_viewer"})
    assert ready["purpose"] == "draft" and not calls and desktops[0].sent is None
    assert client.post(path, headers=AUTH, json={"version": 4}).json()["id"] == row["id"]
    assert client.post(f"/jobs/letters/{letter_id}/generate", headers=AUTH).status_code == 409
    live = manager.active[row["id"]]
    client.post(f"/jobs/writer-exports/{row['id']}/begin", headers=AUTH)
    done = wait_state(client, row["id"], {"saved"})
    # Registry teardown/letter completion can follow the terminal export write.
    live.thread.join(2)
    letter = client.get(f"/jobs/letters/{letter_id}", headers=AUTH).json()
    assert letter["status"] == "draft" and letter["text"] == text and "[NAME]" in desktops[0].sent
    assert len(calls) == 1 and "drafting" in done["diagnostics"]["phase_seconds"]
    assert done["cleanup_confirmed"] and not done["pdf_ready"]
    assert client.get(f"/jobs/writer-exports/{row['id']}/pdf", headers=AUTH).status_code == 409
    assert client.get(f"/jobs/letters/{letter_id}/download", headers=AUTH).status_code == 409
    with Session(engine) as session:
        assert session.get(WriterExport, row["id"]).pdf is None


def test_live_draft_requires_confirmed_inputs_keys_and_current_version(setup, monkeypatch):
    calls, text = draft_fixture(setup, monkeypatch)
    client, engine, manager, desktops, letter_id = setup
    path = f"/jobs/letters/{letter_id}/draft-writer"
    assert client.post(path, json={"version": 3}).status_code == 401
    assert client.post(path, headers=AUTH, json={"version": 2}).status_code == 409
    with Session(engine) as session:
        session.get(LetterSession, "fixture-session").confirmed_at = None; session.commit()
    assert client.post(path, headers=AUTH, json={"version": 3}).status_code == 409
    with Session(engine) as session:
        session.get(LetterSession, "fixture-session").confirmed_at = datetime.now(timezone.utc); session.commit()
    monkeypatch.setenv("E2B_API_KEY", ""); get_settings.cache_clear()
    assert client.post(path, headers=AUTH, json={"version": 3}).status_code == 409
    assert not calls and not desktops
    with Session(engine) as session:
        assert session.get(CoverLetter, letter_id).status == "pending"


def test_stopping_before_drafting_never_calls_model(setup, monkeypatch):
    calls, text = draft_fixture(setup, monkeypatch)
    client, engine, manager, desktops, letter_id = setup
    row = client.post(f"/jobs/letters/{letter_id}/draft-writer", headers=AUTH, json={"version": 3}).json()
    wait_state(client, row["id"], {"waiting_viewer"})
    client.post(f"/jobs/writer-exports/{row['id']}/cancel", headers=AUTH)
    wait_state(client, row["id"], {"cancelled"})
    assert not calls and desktops[0].sent is None and desktops[0].closed


def test_live_draft_does_not_send_manually_edited_identity_before_approval(setup, monkeypatch):
    calls, text = draft_fixture(setup, monkeypatch)
    client, engine, manager, desktops, letter_id = setup
    with Session(engine) as session:
        letter = session.get(CoverLetter, letter_id)
        letter.status, letter.text = "draft", LETTER
        session.commit()
    response = client.post(f"/jobs/letters/{letter_id}/draft-writer", headers=AUTH, json={"version": 3})
    assert response.status_code == 409 and not calls and not desktops


def test_desktop_failure_keeps_draft_and_retry_does_not_regenerate(setup, monkeypatch):
    calls, text = draft_fixture(setup, monkeypatch)
    client, engine, manager, desktops, letter_id = setup
    original = manager.factory

    def fail_typing(key):
        desktop = original(key)
        desktop.write_pdf = lambda *args: (_ for _ in ()).throw(WriterFailure("Controlled typing failure."))
        return desktop

    manager.factory = fail_typing
    path = f"/jobs/letters/{letter_id}/draft-writer"
    row = client.post(path, headers=AUTH, json={"version": 3}).json()
    wait_state(client, row["id"], {"waiting_viewer"})
    live = manager.active[row["id"]]
    client.post(f"/jobs/writer-exports/{row['id']}/begin", headers=AUTH)
    wait_state(client, row["id"], {"failed"}); live.thread.join(2)
    assert client.get(f"/jobs/letters/{letter_id}", headers=AUTH).json()["status"] == "draft"
    manager.factory = original
    retry = client.post(path, headers=AUTH, json={"version": 4}).json()
    assert retry["id"] == row["id"]
    wait_state(client, row["id"], {"waiting_viewer"})
    client.post(f"/jobs/writer-exports/{row['id']}/begin", headers=AUTH)
    wait_state(client, row["id"], {"saved"})
    assert len(calls) == 1 and desktops[-1].sent == text


def test_stop_during_model_keeps_completed_text_without_typing(setup, monkeypatch):
    calls, text = draft_fixture(setup, monkeypatch)
    client, engine, manager, desktops, letter_id = setup
    entered, release = threading.Event(), threading.Event()

    def delayed(*args):
        entered.set()
        assert release.wait(3)
        return text, []

    app.dependency_overrides[draft_generator] = lambda: delayed
    row = client.post(f"/jobs/letters/{letter_id}/draft-writer", headers=AUTH, json={"version": 3}).json()
    wait_state(client, row["id"], {"waiting_viewer"})
    live = manager.active[row["id"]]
    client.post(f"/jobs/writer-exports/{row['id']}/begin", headers=AUTH)
    assert entered.wait(2)
    assert client.get(f"/jobs/writer-exports/{row['id']}", headers=AUTH).json()["status"] == "drafting"
    client.post(f"/jobs/writer-exports/{row['id']}/cancel", headers=AUTH)
    release.set()
    wait_state(client, row["id"], {"cancelled"}); live.thread.join(2)
    letter = client.get(f"/jobs/letters/{letter_id}", headers=AUTH).json()
    assert letter["text"] == text and letter["status"] == "draft"
    assert desktops[0].sent is None and desktops[0].closed


def test_model_failure_closes_preview_and_can_retry(setup, monkeypatch):
    from crescendo_api.letters import DraftUnavailable
    calls, text = draft_fixture(setup, monkeypatch)
    client, engine, manager, desktops, letter_id = setup
    original = app.dependency_overrides[draft_generator]()

    def unavailable(*args):
        raise DraftUnavailable("Controlled provider failure. Retry this letter.")

    app.dependency_overrides[draft_generator] = lambda: unavailable
    path = f"/jobs/letters/{letter_id}/draft-writer"
    row = client.post(path, headers=AUTH, json={"version": 3}).json()
    wait_state(client, row["id"], {"waiting_viewer"})
    live = manager.active[row["id"]]
    client.post(f"/jobs/writer-exports/{row['id']}/begin", headers=AUTH)
    failed = wait_state(client, row["id"], {"failed"}); live.thread.join(2)
    assert failed["diagnostics"]["failure_code"] == "draft_unavailable"
    assert client.get(f"/jobs/letters/{letter_id}", headers=AUTH).json()["status"] == "failed"
    assert desktops[0].closed and desktops[0].sent is None
    app.dependency_overrides[draft_generator] = lambda: original
    retry = client.post(path, headers=AUTH, json={"version": 4}).json()
    wait_state(client, retry["id"], {"waiting_viewer"})
    client.post(f"/jobs/writer-exports/{retry['id']}/begin", headers=AUTH)
    wait_state(client, retry["id"], {"saved"})
    assert len(calls) == 1 and desktops[-1].sent == text


def test_approved_snapshot_waits_for_begin_saves_pdf_and_is_idempotent(setup):
    client, engine, manager, desktops, letter_id = setup
    row = start(client, letter_id)
    ready = wait_state(client, row["id"], {"waiting_viewer"})
    assert ready["viewer_url"] and ready["viewer_connected"]
    assert desktops[0].sent is None
    assert start(client, letter_id)["id"] == row["id"] and len(desktops) == 1
    assert client.get(f"/jobs/writer-exports/{row['id']}/pdf", headers=AUTH).status_code == 409
    assert client.post(f"/jobs/writer-exports/{row['id']}/begin", headers=AUTH).status_code == 200
    saved = wait_state(client, row["id"], {"saved"})
    assert saved["pdf_ready"] and saved["cleanup_confirmed"] and not saved["viewer_url"]
    assert "typing" in saved["diagnostics"]["phase_seconds"] and saved["diagnostics"]["total_seconds"] >= 0
    assert desktops[0].closed and desktops[0].sent == LETTER
    result = client.get(f"/jobs/writer-exports/{row['id']}/pdf", headers=AUTH)
    assert result.content == PDF and result.headers["content-type"] == "application/pdf"
    assert result.headers["cache-control"] == "no-store" and "attachment" in result.headers["content-disposition"]
    assert start(client, letter_id)["id"] == row["id"] and len(desktops) == 1
    # Ordinary letter/library responses must not contain live capabilities or export text.
    assert "viewer_url" not in client.get(f"/jobs/letters/{letter_id}", headers=AUTH).json()
    assert client.get(f"/jobs/letters/{letter_id}/writer", headers=AUTH).json()["export"]["status"] == "saved"


def test_requires_approval_matching_version_key_and_auth(setup, monkeypatch):
    client, engine, manager, desktops, letter_id = setup
    path = f"/jobs/letters/{letter_id}/writer"
    assert client.post(path, json={"version": 3}).status_code == 401
    assert client.post(path, headers=AUTH, json={"version": 2}).status_code == 409
    monkeypatch.setenv("E2B_API_KEY", ""); get_settings.cache_clear()
    assert client.post(path, headers=AUTH, json={"version": 3}).status_code == 409
    monkeypatch.setenv("E2B_API_KEY", "fake"); get_settings.cache_clear()
    with Session(engine) as session:
        session.get(CoverLetter, letter_id).status = "draft"; session.commit()
    assert client.post(path, headers=AUTH, json={"version": 3}).status_code == 409
    assert not desktops


def test_begin_requires_connected_viewer_and_edits_are_blocked_until_stop(setup):
    client, engine, manager, desktops, letter_id = setup
    row = start(client, letter_id)
    wait_state(client, row["id"], {"waiting_viewer"})
    desktops[0].viewer.connected.clear()
    assert client.post(f"/jobs/writer-exports/{row['id']}/begin", headers=AUTH).status_code == 409
    assert client.put(f"/jobs/letters/{letter_id}", headers=AUTH, json={"text": LETTER + " edited", "version": 3}).status_code == 409
    assert client.post(f"/jobs/writer-exports/{row['id']}/cancel", headers=AUTH).status_code == 200
    stopped = wait_state(client, row["id"], {"cancelled"})
    assert stopped["cleanup_confirmed"] and not stopped["pdf_ready"] and not stopped["viewer_url"]
    assert desktops[0].closed and desktops[0].sent is None
    assert client.put(f"/jobs/letters/{letter_id}", headers=AUTH, json={"text": LETTER + " edited", "version": 3}).status_code == 200


def test_cancel_during_typing_cleans_up_without_publishing_pdf(setup):
    client, engine, manager, desktops, letter_id = setup
    row = start(client, letter_id); wait_state(client, row["id"], {"waiting_viewer"})
    desktops[0].hold.clear()
    client.post(f"/jobs/writer-exports/{row['id']}/begin", headers=AUTH)
    wait_state(client, row["id"], {"typing"})
    client.post(f"/jobs/writer-exports/{row['id']}/cancel", headers=AUTH)
    stopped = wait_state(client, row["id"], {"cancelled"})
    assert stopped["cleanup_confirmed"] and not stopped["pdf_ready"]
    assert desktops[0].closed


def test_network_failure_prevents_typing_and_retry_keeps_same_snapshot(setup):
    client, engine, manager, desktops, letter_id = setup
    original = manager.factory

    def failing(key):
        desktop = original(key); desktop.fail = True; return desktop

    manager.factory = failing
    row = start(client, letter_id)
    failed = wait_state(client, row["id"], {"failed"})
    assert "offline network" in failed["error"] and failed["can_retry"]
    assert desktops[0].sent is None and desktops[0].closed
    manager.factory = original
    retried = start(client, letter_id)
    assert retried["id"] == row["id"]
    wait_state(client, row["id"], {"waiting_viewer"})
    client.post(f"/jobs/writer-exports/{row['id']}/begin", headers=AUTH)
    wait_state(client, row["id"], {"saved"})
    assert desktops[1].sent == LETTER


def test_restart_hides_viewer_and_waits_for_lease_before_replacement(setup):
    client, engine, manager, desktops, letter_id = setup
    with Session(engine) as session:
        row = WriterExport(letter_id=letter_id, letter_version=3, text=LETTER, owner_id="old-process",
                           status="typing", expires_at=datetime.now(timezone.utc) + timedelta(minutes=5))
        session.add(row); session.commit(); export_id = row.id
    interrupted = client.get(f"/jobs/writer-exports/{export_id}", headers=AUTH).json()
    assert interrupted["status"] == "interrupted" and not interrupted["viewer_url"] and not interrupted["can_retry"]
    assert client.post(f"/jobs/letters/{letter_id}/writer", headers=AUTH, json={"version": 3}).status_code == 409
    with Session(engine) as session:
        session.get(WriterExport, export_id).expires_at = datetime.now(timezone.utc) - timedelta(seconds=1); session.commit()
    assert start(client, letter_id)["id"] == export_id
    wait_state(client, export_id, {"waiting_viewer"})


def test_uncertain_cleanup_waits_for_expiry_and_consumes_capacity(setup):
    client, engine, manager, desktops, letter_id = setup
    original = manager.factory

    def failed_cleanup(key):
        desktop = original(key); desktop.fail = True; desktop.cleanup = False; return desktop

    manager.factory = failed_cleanup
    row = start(client, letter_id)
    failed = wait_state(client, row["id"], {"failed"})
    assert not failed["cleanup_confirmed"] and not failed["can_retry"]
    assert client.post(f"/jobs/letters/{letter_id}/writer", headers=AUTH, json={"version": 3}).status_code == 409
    with Session(engine) as session:
        for i in range(2):
            session.add(WriterExport(letter_id=letter_id, letter_version=10+i, text=LETTER, owner_id="old",
                status="failed", cleanup_confirmed=False, expires_at=datetime.now(timezone.utc) + timedelta(minutes=5)))
        other = CoverLetter(session_id="fixture-session", posting={}, status="approved", text=LETTER, version=3)
        session.add(other); session.commit(); other_id = other.id
    assert client.post(f"/jobs/letters/{other_id}/writer", headers=AUTH, json={"version": 3}).status_code == 409
    assert len(desktops) == 1


def test_deadline_cancels_waiting_desktop_and_saved_pdf_survives_process_change(setup):
    client, engine, manager, desktops, letter_id = setup
    row = start(client, letter_id); wait_state(client, row["id"], {"waiting_viewer"})
    with manager.lock:
        manager.active[row["id"]].deadline = time.monotonic() - 1
    failed = wait_state(client, row["id"], {"failed"})
    assert "time limit" in failed["error"] and desktops[0].closed
    start(client, letter_id); wait_state(client, row["id"], {"waiting_viewer"})
    client.post(f"/jobs/writer-exports/{row['id']}/begin", headers=AUTH)
    wait_state(client, row["id"], {"saved"})
    replacement = WriterManager(lambda: Session(engine), manager.factory)
    with Session(engine) as session:
        assert replacement.info(session.get(WriterExport, row["id"]))["pdf_ready"]


def test_typing_failure_saves_safe_operation_without_exception_text(setup):
    client, engine, manager, desktops, letter_id = setup
    original = manager.factory

    def factory(key):
        desktop = original(key)
        desktop.operation = "typing"

        def fail(*args):
            raise type("TimeoutException", (Exception,), {})("PRIVATE LETTER AND CONNECTION TOKEN")

        desktop.write_pdf = fail
        return desktop

    manager.factory = factory
    row = start(client, letter_id); wait_state(client, row["id"], {"waiting_viewer"})
    client.post(f"/jobs/writer-exports/{row['id']}/begin", headers=AUTH)
    failed = wait_state(client, row["id"], {"failed"})
    assert failed["diagnostics"]["failure_code"] == "desktop_timeout"
    assert failed["diagnostics"]["failure_operation"] == "typing"
    assert "PRIVATE" not in failed["error"] and failed["cleanup_confirmed"]
