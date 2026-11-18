"""Private local live-writer commands and durable verified PDF access."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from ..auth import require_local_token
from ..config import get_settings
from ..models import CoverLetter, LetterSession, WriterExport
from .letters import draft_generator
from ..writer_service import WriterManager, WriterRequestError, get_writer_manager
from .jobs import SessionDep


def no_store(response: Response):
    response.headers["Cache-Control"] = "no-store"


router = APIRouter(prefix="/jobs", dependencies=[Depends(require_local_token), Depends(no_store)])
ManagerDep = Annotated[WriterManager, Depends(get_writer_manager)]


class StartBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(ge=1)


@router.post("/letters/{letter_id}/draft-writer", status_code=202)
def start_draft_writer(letter_id: UUID, body: StartBody, session: SessionDep,
                       manager: ManagerDep, generator: Annotated[object, Depends(draft_generator)]):
    letter = session.get(CoverLetter, str(letter_id))
    if letter is None:
        raise HTTPException(404, "Letter not found.")
    preview = session.get(LetterSession, letter.session_id)
    if preview is None or preview.confirmed_at is None:
        raise HTTPException(409, "Review and confirm the redacted inputs first.")
    settings = get_settings()
    if not settings.groq_api_key:
        raise HTTPException(409, "Configure GROQ_API_KEY in the backend and restart it.")
    inputs, posting = preview.inputs, letter.posting
    key = settings.groq_api_key.get_secret_value()
    desktop_key = settings.e2b_api_key.get_secret_value() if settings.e2b_api_key else ""
    try:
        return manager.start(session, str(letter_id), body.version, desktop_key,
            generate=lambda: generator(inputs, posting, key))
    except WriterRequestError as error:
        raise HTTPException(error.status, str(error)) from None


@router.post("/letters/{letter_id}/writer", status_code=202)
def start_writer(letter_id: UUID, body: StartBody, session: SessionDep, manager: ManagerDep):
    settings = get_settings()
    key = settings.e2b_api_key.get_secret_value() if settings.e2b_api_key else ""
    try:
        return manager.start(session, str(letter_id), body.version, key)
    except WriterRequestError as error:
        raise HTTPException(error.status, str(error)) from None


@router.get("/letters/{letter_id}/writer")
def latest_writer(letter_id: UUID, session: SessionDep, manager: ManagerDep):
    if session.get(CoverLetter, str(letter_id)) is None:
        raise HTTPException(404, "Letter not found.")
    row = session.scalar(select(WriterExport).where(WriterExport.letter_id == str(letter_id))
                         .order_by(WriterExport.created_at.desc(), WriterExport.id.desc()).limit(1))
    return {"export": manager.info(row) if row else None}


@router.get("/writer-exports/{export_id}")
def export_status(export_id: UUID, session: SessionDep, manager: ManagerDep):
    row = session.get(WriterExport, str(export_id))
    if row is None:
        raise HTTPException(404, "Writer export not found.")
    return manager.info(row)


@router.post("/writer-exports/{export_id}/begin")
def begin_writer(export_id: UUID, session: SessionDep, manager: ManagerDep):
    try:
        return manager.begin(session, str(export_id))
    except WriterRequestError as error:
        raise HTTPException(error.status, str(error)) from None


@router.post("/writer-exports/{export_id}/cancel")
def cancel_writer(export_id: UUID, session: SessionDep, manager: ManagerDep):
    try:
        return manager.cancel(session, str(export_id))
    except WriterRequestError as error:
        raise HTTPException(error.status, str(error)) from None


@router.get("/writer-exports/{export_id}/pdf")
def export_pdf(export_id: UUID, session: SessionDep):
    row = session.get(WriterExport, str(export_id))
    if row is None:
        raise HTTPException(404, "Writer export not found.")
    if row.purpose != "export" or row.status != "saved" or not row.pdf:
        raise HTTPException(409, "The verified PDF is not saved yet.")
    return Response(row.pdf, media_type="application/pdf", headers={
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
        "Content-Disposition": f'attachment; filename="cover-letter-{row.id}.pdf"'})
