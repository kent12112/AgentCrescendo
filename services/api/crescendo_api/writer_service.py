"""Bounded local desktop ownership for live drafts and approved-letter exports.

The database holds snapshots/results; live capabilities exist only in this API
process. This bridge is not durable scheduling. A restart expires viewer access;
the provider kill timer bounds abandoned desktops before another attempt starts.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import threading
import time
from uuid import uuid4

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from crescendo_agent.writer import MAX_WRITER_CHARACTERS, OfflineWriter, WriterFailure, WRITER_LIFETIME, safe_writer_failure

from .database import get_engine
from .models import CoverLetter, WriterExport, WRITER_ACTIVE
from .letters import DraftUnavailable


def now():
    return datetime.now(timezone.utc)


def aware(moment):
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


class WriterRequestError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


class ExportCancelled(Exception):
    pass


@dataclass(repr=False)
class ActiveExport:
    attempt: int
    stop: threading.Event = field(default_factory=threading.Event)
    begin: threading.Event = field(default_factory=threading.Event)
    desktop: object = None
    thread: threading.Thread | None = None
    deadline: float = field(default_factory=lambda: time.monotonic() + WRITER_LIFETIME)


class WriterManager:
    def __init__(self, sessions, factory=OfflineWriter):
        self.sessions = sessions
        self.factory = factory
        self.owner_id = str(uuid4())
        self.lock = threading.RLock()
        self.active: dict[str, ActiveExport] = {}
        self.closed = False

    def start(self, session: Session, letter_id: str, version: int, api_key: str, *, generate=None):
        with self.lock:
            purpose = "draft" if generate is not None else "export"
            # This row lock also serializes against edits/approval in routes/letters.py.
            letter = session.scalar(select(CoverLetter).where(CoverLetter.id == letter_id).with_for_update())
            if letter is None:
                raise WriterRequestError(404, "Letter not found.")
            if letter.version != version:
                raise WriterRequestError(409, "This letter changed. Refresh before starting Writer.")
            if purpose == "export" and letter.status != "approved":
                raise WriterRequestError(409, "Approve and save the current letter before opening Writer.")
            if purpose == "draft" and letter.status == "approved":
                raise WriterRequestError(409, "This letter is already approved. Review it or export the final version.")
            if len(letter.text) > MAX_WRITER_CHARACTERS:
                raise WriterRequestError(422, "Live Writer supports letters up to 6,000 characters. Shorten and approve the letter, or download its text.")
            row = session.scalar(select(WriterExport).where(WriterExport.letter_id == letter.id,
                                  WriterExport.letter_version == version))
            if purpose == "draft" and letter.status == "draft" and (row is None or row.purpose != "draft" or row.text != letter.text):
                raise WriterRequestError(409, "Review your saved draft directly. Live drafting starts with a new draft; edited text can be exported after approval.")
            if purpose == "draft" and letter.status == "generating" and row is None and aware(letter.updated_at) > now() - timedelta(seconds=120):
                raise WriterRequestError(409, "This letter is already being drafted. Refresh its progress before retrying.")
            if row and row.status == "saved":
                return self.info(row)
            if row and row.id in self.active:
                # The final DB write can precede thread teardown. Don't replace
                # its registry entry until that attempt has released ownership.
                return self.info(row)
            if row and row.status in ("failed", "cancelled") and not row.cleanup_confirmed and aware(row.expires_at) > now():
                raise WriterRequestError(409, "Wait for the previous desktop lease to expire before retrying; cleanup was not confirmed.")
            if row and row.status in WRITER_ACTIVE:
                if row.id in self.active:
                    return self.info(row)
                if aware(row.expires_at) > now():
                    raise WriterRequestError(409, "The API restarted during this export. Wait until the previous desktop lease expires before retrying.")
            blocked = session.scalar(select(WriterExport.id).where(WriterExport.letter_id == letter.id,
                WriterExport.cleanup_confirmed.is_(False), WriterExport.expires_at > now()).limit(1))
            if blocked:
                raise WriterRequestError(409, "Wait for the previous Writer desktop to close or its lease to expire before starting another.")
            leased = session.scalar(select(func.count()).select_from(WriterExport).where(
                WriterExport.cleanup_confirmed.is_(False), WriterExport.expires_at > now()))
            if self.closed or max(len(self.active), leased) >= 3:
                raise WriterRequestError(409, "Three Writer desktops are already active, or the API is shutting down. Finish or stop an export before retrying.")
            if not api_key:
                raise WriterRequestError(409, "Set E2B_API_KEY in the backend's local .env and restart the API to open live Writer.")
            if purpose == "draft":
                # Claim generation under the same lock/transaction as the desktop.
                # Existing generated text is reused on a desktop-only retry.
                if not letter.text:
                    letter.version += 1
                    version = letter.version
                    row = None
                letter.status, letter.error, letter.updated_at = "generating", None, now()
            if row is None:
                row = WriterExport(letter_id=letter.id, letter_version=version, text=letter.text,
                                   purpose=purpose, owner_id=self.owner_id, expires_at=now() + timedelta(seconds=WRITER_LIFETIME + 60))
                session.add(row)
                session.flush()
            else:
                row.attempt += 1
                row.status, row.owner_id = "starting", self.owner_id
                row.pdf, row.error, row.characters_typed = None, None, 0
                row.diagnostics = {}
                row.cleanup_confirmed = False
                row.expires_at = now() + timedelta(seconds=WRITER_LIFETIME + 60)
                row.updated_at = now()
            session.commit()
            export_id, attempt, text = row.id, row.attempt, row.text
            live = ActiveExport(attempt=attempt)
            self.active[export_id] = live
            thread = threading.Thread(target=self._run, args=(export_id, live, text, api_key, generate),
                                      name="letter-writer-export", daemon=True)
            live.thread = thread
            try:
                thread.start()
            except Exception:
                self.active.pop(export_id, None)
                row.status, row.error, row.cleanup_confirmed = "failed", "Could not start the export worker. Retry the export.", True
                if purpose == "draft":
                    letter.status = "draft" if letter.text else "failed"
                    letter.error = None if letter.text else row.error
                session.commit()
                raise WriterRequestError(409, row.error) from None
            return self.info(row)

    def _update(self, export_id, attempt, **values):
        with self.sessions() as session:
            session.execute(update(WriterExport).where(WriterExport.id == export_id,
                WriterExport.attempt == attempt).values(**values, updated_at=now()))
            session.commit()

    def _run(self, export_id: str, live: ActiveExport, text: str, api_key: str, generate=None):
        desktop = None
        pdf, error, status = None, None, "failed"
        started = phase_started = time.monotonic()
        phase = "opening"
        phase_seconds = {}
        diagnostics = {}
        last_typed = 0

        def mark_phase(next_phase):
            nonlocal phase, phase_started
            if next_phase != phase:
                phase_seconds[phase] = round(phase_seconds.get(phase, 0) + time.monotonic() - phase_started, 3)
                phase, phase_started = next_phase, time.monotonic()

        def checkpoint():
            if live.stop.is_set():
                raise ExportCancelled()
            if time.monotonic() >= live.deadline:
                raise WriterFailure("The Writer export reached its time limit. Retry the export.")

        def progress(phase, typed=0):
            nonlocal last_typed
            checkpoint()
            mark_phase(phase)
            last_typed = typed
            with self.sessions() as session:
                session.execute(update(WriterExport).where(WriterExport.id == export_id,
                    WriterExport.attempt == live.attempt, WriterExport.status != "cancelling")
                    .values(status=phase, characters_typed=typed, updated_at=now()))
                session.commit()

        try:
            checkpoint()
            desktop = self.factory(api_key)
            with self.lock:
                live.desktop = desktop
            desktop.open()
            progress("preparing")
            desktop.prepare(checkpoint)
            progress("waiting_viewer")
            viewer_deadline = min(live.deadline, time.monotonic() + 90)
            while not (live.begin.is_set() and desktop.viewer.connected.is_set()):
                checkpoint()
                if time.monotonic() >= viewer_deadline:
                    raise WriterFailure("The viewer was not started within 90 seconds. Reopen Writer and click Start typing when the desktop is visible.")
                time.sleep(0.1)
            if generate is not None and not text:
                progress("drafting")
                desktop.operation = "drafting"
                try:
                    text, checks = generate()
                except DraftUnavailable as failure:
                    raise WriterFailure(str(failure), code="draft_unavailable", operation="drafting") from None
                # Save a completed model result even if Stop was pressed during the
                # bounded model request. It remains reviewable; no typing follows Stop.
                with self.sessions() as session:
                    row = session.get(WriterExport, export_id)
                    session.execute(update(CoverLetter).where(CoverLetter.id == row.letter_id,
                        CoverLetter.version == row.letter_version).values(text=text, checks=checks, updated_at=now()))
                    row.text = text
                    session.commit()
                checkpoint()
            pdf = desktop.write_pdf(text, progress, checkpoint)
            checkpoint()
            status = "saved"
        except ExportCancelled:
            status = "cancelled"
        except WriterFailure as failure:
            error = str(failure)
            diagnostics.update(failure_code=failure.code, failure_operation=failure.operation or getattr(desktop, "operation", phase))
        except Exception as failure:
            # SDK exception bodies/command errors can contain letter text or stream credentials.
            safe = safe_writer_failure(failure, getattr(desktop, "operation", phase))
            error = str(safe)
            diagnostics.update(failure_code=safe.code, failure_operation=safe.operation)
        finally:
            mark_phase("cleanup")
            try:
                cleanup = desktop.close() if desktop is not None else True
            except Exception:
                cleanup = False
            if not cleanup:
                saved = "Draft saved" if generate is not None else "PDF saved"
                error = f"{saved}; desktop cleanup could not be confirmed. Its provider timer will stop it." if pdf else ((error or "Writer stopped.") + " Cleanup is unconfirmed; wait for lease expiry before retrying.")[:300]
            if live.stop.is_set():
                status, pdf = "cancelled", None
            try:
                mark_phase("finished")
                typing_seconds = phase_seconds.get("typing", 0)
                diagnostics.update(phase_seconds=phase_seconds, total_seconds=round(time.monotonic() - started, 3),
                                   characters_per_second=round(last_typed / typing_seconds, 1) if typing_seconds else 0)
                self._update(export_id, live.attempt, status=status, pdf=pdf if status == "saved" and generate is None else None,
                             error=error, cleanup_confirmed=cleanup, diagnostics=diagnostics)
                if generate is not None:
                    with self.sessions() as session:
                        row = session.get(WriterExport, export_id)
                        # The reviewed draft survives desktop/PDF errors or cancellation.
                        session.execute(update(CoverLetter).where(CoverLetter.id == row.letter_id,
                            CoverLetter.version == row.letter_version, CoverLetter.status == "generating")
                            .values(status="draft" if row.text else "failed", error=None if row.text else (error or "Live drafting stopped. Retry when ready."), updated_at=now()))
                        session.commit()
            except Exception:
                # Database exceptions may include PDF parameters. The remaining lease
                # reports interruption, and the provider timer still bounds cleanup.
                pass
            finally:
                with self.lock:
                    if self.active.get(export_id) is live:
                        self.active.pop(export_id, None)

    def info(self, row: WriterExport):
        with self.lock:
            live = self.active.get(row.id)
            viewer = getattr(live.desktop, "viewer", None) if live else None
            active = row.status in WRITER_ACTIVE
            status, error = row.status, row.error
            if active and live is None:
                status = "interrupted"
                error = "This API process no longer owns the live desktop. Retry after its lease expires; your saved text is kept."
            can_retry = (row.status in ("failed", "cancelled") or status == "interrupted") and live is None
            # If cleanup wasn't confirmed, the provider kill timer must expire before reuse.
            if can_retry and not row.cleanup_confirmed and aware(row.expires_at) > now():
                can_retry = False
            return {"id": row.id, "letter_id": row.letter_id, "letter_version": row.letter_version,
                    "status": status, "error": error, "characters_typed": row.characters_typed,
                    "purpose": row.purpose,
                    "total_characters": len(row.text), "pdf_ready": row.purpose == "export" and row.status == "saved" and row.pdf is not None,
                    "cleanup_confirmed": row.cleanup_confirmed, "can_retry": can_retry,
                    "diagnostics": row.diagnostics or {},
                    "viewer_connected": bool(viewer and viewer.connected.is_set()),
                    # Do not persist, log, or include this capability in ordinary letter payloads.
                    "viewer_url": viewer.url if viewer and active and not live.stop.is_set() else None,
                    "expires_at": aware(row.expires_at).isoformat(), "created_at": aware(row.created_at).isoformat()}

    def begin(self, session: Session, export_id: str):
        with self.lock:
            row = session.get(WriterExport, export_id)
            if row is None:
                raise WriterRequestError(404, "Writer export not found.")
            live = self.active.get(export_id)
            if live and row.status in ("drafting", "typing", "exporting"):
                return self.info(row)
            viewer = getattr(live.desktop, "viewer", None) if live else None
            if row.status != "waiting_viewer" or not viewer or not viewer.connected.is_set():
                raise WriterRequestError(409, "Wait until the live desktop is connected and visible before starting typing.")
            live.begin.set()
            return self.info(row)

    def cancel(self, session: Session, export_id: str):
        with self.lock:
            row = session.get(WriterExport, export_id)
            if row is None:
                raise WriterRequestError(404, "Writer export not found.")
            if row.status not in WRITER_ACTIVE:
                return self.info(row)
            live = self.active.get(export_id)
            if live is None:
                raise WriterRequestError(409, "The API no longer owns this desktop. Its provider lease will expire automatically.")
            live.stop.set()
            row.status = "cancelling"
            session.commit()
            return self.info(row)

    def shutdown(self):
        with self.lock:
            self.closed = True
            runs = list(self.active.values())
            for live in runs:
                live.stop.set()
        deadline = time.monotonic() + 5
        for live in runs:
            if live.thread:
                live.thread.join(timeout=max(0, deadline - time.monotonic()))


@lru_cache
def get_writer_manager():
    return WriterManager(lambda: Session(get_engine()))


def close_writer_manager():
    if get_writer_manager.cache_info().currsize:
        get_writer_manager().shutdown()
        get_writer_manager.cache_clear()
