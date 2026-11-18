"""Token-protected, single-user answer sessions; model calls require preview consent.

Research (public company facts only) runs before consent and changes the preview's
digest; drafting (resume + posting + notes + verified research) runs after consent.
"""
import copy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update

from ..auth import require_local_token
from ..config import get_settings
from ..company_research import ResearchUnavailable, research_company
from ..letters import DraftUnavailable, LetterInputError, digest, generate_draft, prepare_inputs
from ..models import CoverLetter, JobPosting, JobResume, LetterSession, WriterExport, WRITER_ACTIVE
from .jobs import PickRef, SessionDep

router = APIRouter(prefix="/jobs", dependencies=[Depends(require_local_token)])


class Selection(PickRef):
    model_config = ConfigDict(extra="forbid")
    company_notes: str = Field(default="", max_length=4000)


class PreviewBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=3, max_length=120, pattern=r"^[^\n\r\[\]<>]+$")
    picks: list[Selection] = Field(min_length=1, max_length=3)


class ConfirmBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    input_digest: str = Field(pattern=r"^[a-f0-9]{64}$")


class EditBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=40, max_length=16000)
    version: int = Field(ge=1)
    approve: bool = False
    reviewed: bool = False


def now():
    return datetime.now(timezone.utc)


def iso(value):
    return value.replace(tzinfo=timezone.utc).isoformat() if value and value.tzinfo is None else value.isoformat() if value else None


def get_letter(session, letter_id):
    letter = session.get(CoverLetter, str(letter_id))
    if letter is None:
        raise HTTPException(404, "Letter not found.")
    return letter


def read_letter(letter):
    return {"id": letter.id, "session_id": letter.session_id, "posting": letter.posting,
            "status": letter.status, "text": letter.text, "checks": letter.checks, "turns": letter.turns or [],
            "error": letter.error, "version": letter.version,
            "created_at": iso(letter.created_at), "updated_at": iso(letter.updated_at)}


def read_session(session, row):
    letters = session.scalars(select(CoverLetter).where(CoverLetter.session_id == row.id)
                              .order_by(CoverLetter.created_at, CoverLetter.id)).all()
    return {"id": row.id, "inputs": row.inputs, "input_digest": row.input_digest,
            "confirmed_at": iso(row.confirmed_at), "created_at": iso(row.created_at),
            "letters": [read_letter(letter) for letter in letters]}


@router.post("/letter-sessions", status_code=201)
def preview(body: PreviewBody, session: SessionDep):
    """Local preparation only. No model call, even if the provider is configured."""
    if len(body.name.strip()) < 3:
        raise HTTPException(422, "Enter your full name before preparing letters.")
    resume = session.get(JobResume, 1)
    if resume is None:
        raise HTTPException(409, "Upload your resume before preparing letters.")
    settings = get_settings()
    postings, seen = [], set()
    for pick in body.picks:
        key = (pick.source, pick.posting_id)
        if key in seen:
            raise HTTPException(422, "Choose each posting only once.")
        seen.add(key)
        posting = session.get(JobPosting, key)
        if posting is None or posting.closed_at is not None:
            raise HTTPException(422, "A selected posting has closed or is no longer stored. Update your picks.")
        postings.append({"source": posting.source, "posting_id": posting.posting_id,
                         "company": posting.company_name or posting.company_slug,
                         "title": posting.title, "url": posting.url,
                         "description": posting.description, "company_notes": pick.company_notes})
    try:
        inputs = prepare_inputs(resume.text, body.name.strip(), postings, settings.letter_model)
    except LetterInputError as error:
        raise HTTPException(422, str(error)) from None
    row = LetterSession(inputs=inputs, input_digest=digest(inputs), identity={"name": body.name.strip()})
    session.add(row)
    session.flush()
    for posting in inputs["jobs"]:
        session.add(CoverLetter(session_id=row.id, posting=posting))
    session.commit()
    return read_session(session, row)


@router.get("/letter-sessions/{session_id}")
def get_letter_session(session_id: UUID, session: SessionDep):
    row = session.get(LetterSession, str(session_id))
    if row is None:
        raise HTTPException(404, "Letter session not found.")
    return read_session(session, row)


@router.post("/letter-sessions/{session_id}/confirm")
def confirm(session_id: UUID, body: ConfirmBody, session: SessionDep):
    row = session.get(LetterSession, str(session_id))
    if row is None:
        raise HTTPException(404, "Letter session not found.")
    if row.input_digest != body.input_digest:
        raise HTTPException(409, "The preview changed. Review the current inputs before confirming.")
    if not get_settings().groq_api_key:
        raise HTTPException(409, "Letter drafting needs GROQ_API_KEY in the backend's local .env. Restart the API after setting it.")
    row.confirmed_at = row.confirmed_at or now()
    session.commit()
    return read_session(session, row)


def company_researcher():
    return research_company


@router.post("/letter-sessions/{session_id}/research")
def research(session_id: UUID, session: SessionDep, researcher: Annotated[object, Depends(company_researcher)]):
    """Research every selected company before consent. Sends public posting facts only."""
    row = session.get(LetterSession, str(session_id))
    if row is None:
        raise HTTPException(404, "Session not found.")
    if row.confirmed_at is not None:
        raise HTTPException(409, "These inputs are already approved. Prepare a new preview to research again.")
    settings = get_settings()
    if not settings.groq_api_key:
        raise HTTPException(409, "Company research needs GROQ_API_KEY in the backend's local .env. Restart the API after setting it.")
    key, model, started_digest = settings.groq_api_key.get_secret_value(), settings.research_model, row.input_digest
    jobs = copy.deepcopy(row.inputs["jobs"])
    session.rollback()  # Hold no transaction open during the network work.

    def one(job):
        try:
            return researcher(job, key, model)
        except ResearchUnavailable as error:
            return {"status": "failed", "model": model, "error": str(error), "facts": [], "excluded": [], "open_questions": []}

    # Companies are independent; at most three run at once (one per selected job).
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(one, jobs))
    row = session.scalar(select(LetterSession).where(LetterSession.id == str(session_id)).with_for_update())
    if row.confirmed_at is not None or row.input_digest != started_digest:
        raise HTTPException(409, "The preview changed during research. Reload it and research again.")
    for job, result in zip(jobs, results):
        job["company_research"] = result
    inputs = {**row.inputs, "jobs": jobs}
    row.inputs, row.input_digest = inputs, digest(inputs)
    by_key = {(job["source"], job["posting_id"]): job for job in jobs}
    for letter in session.scalars(select(CoverLetter).where(CoverLetter.session_id == row.id)):
        letter.posting = by_key[(letter.posting["source"], letter.posting["posting_id"])]
    session.commit()
    return read_session(session, row)


def draft_generator():
    return generate_draft


@router.post("/letters/{letter_id}/generate")
def generate(letter_id: UUID, session: SessionDep, generator: Annotated[object, Depends(draft_generator)]):
    letter = session.scalar(select(CoverLetter).where(CoverLetter.id == str(letter_id)).with_for_update())
    if letter is None:
        raise HTTPException(404, "Letter not found.")
    row = session.get(LetterSession, letter.session_id)
    if row is None or row.confirmed_at is None:
        raise HTTPException(409, "Review and confirm the redacted inputs first.")
    settings = get_settings()
    if not settings.groq_api_key:
        raise HTTPException(409, "Configure GROQ_API_KEY in the backend and restart it.")
    # Return a completed result without another model request, including after a lost response.
    if letter.status in ("draft", "approved"):
        return read_letter(letter)
    if session.scalar(select(WriterExport.id).where(WriterExport.letter_id == letter.id,
        WriterExport.status.in_(WRITER_ACTIVE), WriterExport.expires_at > now()).limit(1)):
        raise HTTPException(409, "Live Writer is already drafting this letter. Watch its progress or stop it before retrying.")
    # A process interrupted during generation can be retried after the bounded request expires.
    stale = now() - timedelta(seconds=120)
    claimed = session.execute(update(CoverLetter).where(
        CoverLetter.id == letter.id,
        ((CoverLetter.status.in_(["pending", "failed"])) |
         ((CoverLetter.status == "generating") & (CoverLetter.updated_at < stale)))
    ).values(status="generating", error=None, turns=[], updated_at=now(), version=CoverLetter.version + 1)
      .returning(CoverLetter.version).execution_options(synchronize_session=False)).scalar_one_or_none()
    session.commit()
    if claimed is None:
        raise HTTPException(409, "This letter is already being drafted. Refresh to see its progress; retry after two minutes if interrupted.")
    # Commit before the network request so another tab sees real persisted progress.
    def save_turns(turns):
        # Each finished turn refreshes updated_at, so a long multi-turn run is not stale.
        session.execute(update(CoverLetter).where(CoverLetter.id == letter.id, CoverLetter.version == claimed)
                        .values(turns=turns, updated_at=now()).execution_options(synchronize_session=False))
        session.commit()

    try:
        text, checks = generator(row.inputs, letter.posting, settings.groq_api_key.get_secret_value(), on_turn=save_turns)
        values = {"status": "draft", "text": text, "checks": checks, "error": None}
    except DraftUnavailable as error:
        values = {"status": "failed", "error": str(error)}
    session.execute(update(CoverLetter).where(CoverLetter.id == letter.id, CoverLetter.version == claimed)
                    .values(**values, updated_at=now(), version=CoverLetter.version + 1))
    session.commit()
    session.expire_all()
    return read_letter(get_letter(session, letter_id))


@router.get("/letters")
def list_letters(session: SessionDep):
    return {"letters": [read_letter(letter) for letter in session.scalars(
        select(CoverLetter).order_by(CoverLetter.created_at.desc(), CoverLetter.id).limit(100))]}


@router.get("/letters/{letter_id}")
def letter_detail(letter_id: UUID, session: SessionDep):
    return read_letter(get_letter(session, letter_id))


@router.put("/letters/{letter_id}")
def edit_letter(letter_id: UUID, body: EditBody, session: SessionDep):
    letter = session.scalar(select(CoverLetter).where(CoverLetter.id == str(letter_id)).with_for_update())
    if letter is None:
        raise HTTPException(404, "Letter not found.")
    active_writer = session.scalar(select(WriterExport.id).where(WriterExport.letter_id == letter.id,
                                    WriterExport.status.in_(WRITER_ACTIVE), WriterExport.expires_at > now()).limit(1))
    if active_writer:
        raise HTTPException(409, "Stop the live Writer export before changing this letter.")
    if letter.status not in ("draft", "approved"):
        raise HTTPException(409, "Wait for drafting to finish before editing.")
    if body.approve and not body.reviewed:
        raise HTTPException(422, "Review the draft and source flags before approving.")
    text = body.text.strip()
    checks = list(letter.checks)
    if text != letter.text.strip() and not any(c["source"] == "user_edit" for c in checks):
        checks.append({"text": "This letter was edited after generation.", "source": "user_edit", "quote": "",
                       "quote_found": False, "flags": ["Source checks below describe the generated draft; review your edits separately."]})
    if body.approve:
        row = session.get(LetterSession, letter.session_id)
        text = text.replace("[NAME]", row.identity["name"])
        if any(placeholder in text for placeholder in ("[EMAIL]", "[PHONE]", "[ADDRESS]", "[LINK]")):
            raise HTTPException(422, "Replace remaining contact placeholders in the editor before approving.")
    updated = session.execute(update(CoverLetter).where(CoverLetter.id == letter.id,
                              CoverLetter.version == body.version)
        .values(text=text, checks=checks, status="approved" if body.approve else "draft",
                version=CoverLetter.version + 1, updated_at=now()).returning(CoverLetter.id)).scalar_one_or_none()
    if updated is None:
        raise HTTPException(409, "This letter changed in another tab. Reload it before saving.")
    session.commit()
    session.expire_all()
    return read_letter(get_letter(session, letter_id))


@router.get("/letters/{letter_id}/download")
def download(letter_id: UUID, session: SessionDep):
    letter = get_letter(session, letter_id)
    if letter.status != "approved":
        raise HTTPException(409, "Approve this letter before downloading the final version.")
    return Response(letter.text, media_type="text/plain; charset=utf-8", headers={
        "Content-Disposition": f'attachment; filename="cover-letter-{letter.id}.txt"',
        "Cache-Control": "no-store"})
