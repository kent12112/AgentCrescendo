"""Token-protected manual application tracker for the single-user workspace."""
from datetime import date, datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..application_models import JobApplication
from ..applications import application_info
from ..auth import require_local_token
from ..database import get_session
from ..job_search import posting_detail
from ..models import JobPosting
from .jobs import POSTING_ID, SOURCE

router = APIRouter(prefix="/jobs/applications", dependencies=[Depends(require_local_token)])
SessionDep = Annotated[Session, Depends(get_session)]
Source = Annotated[str, Path(pattern=SOURCE)]
PostingId = Annotated[str, Path(pattern=POSTING_ID)]


class ApplicationBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["ready", "applied", "interviewing", "offer", "rejected", "withdrawn"] = "applied"
    applied_on: date | None = None
    follow_up_on: date | None = None
    notes: str = Field(default="", max_length=8000)
    version: int | None = Field(default=None, ge=1)


@router.get("")
def list_applications(session: SessionDep):
    # Outer join reports availability without coupling the saved snapshot's lifetime to the crawl.
    rows = session.execute(select(JobApplication, JobPosting).outerjoin(
        JobPosting, (JobPosting.source == JobApplication.source)
        & (JobPosting.posting_id == JobApplication.posting_id))
        .order_by(JobApplication.updated_at.desc(), JobApplication.source, JobApplication.posting_id)).all()
    return {"applications": [application_info(row, posting) for row, posting in rows]}


@router.put("/{source}/{posting_id}")
def save_application(source: Source, posting_id: PostingId, body: ApplicationBody, session: SessionDep):
    row = session.get(JobApplication, (source, posting_id))
    posting = session.get(JobPosting, (source, posting_id))
    if row and body.version is None:
        # Repeated "Mark applied" requests must not reset notes, status, or dates.
        return application_info(row, posting)
    now = datetime.now(timezone.utc)
    values = body.model_dump(exclude={"version"})
    if body.status != "ready" and body.applied_on is None:
        values["applied_on"] = row.applied_on if row and row.applied_on else now.date()
    values["updated_at"] = now
    if row:
        changed = session.execute(update(JobApplication).where(
            JobApplication.source == source, JobApplication.posting_id == posting_id,
            JobApplication.version == body.version).values(**values, version=JobApplication.version + 1))
        if changed.rowcount != 1:
            session.rollback()
            raise HTTPException(409, "This application changed in another tab. Reload before saving.")
    else:
        if body.version is not None:
            raise HTTPException(409, "This application was removed. Reload before saving.")
        if posting is None:
            raise HTTPException(404, "This posting is no longer stored. Only existing tracked jobs retain a snapshot.")
        snapshot = posting_detail(session, source, posting_id, None)
        snapshot.pop("segments", None)
        session.add(JobApplication(source=source, posting_id=posting_id, posting=snapshot,
                                   created_at=now, version=1, **values))
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        # A simultaneous first click may already have created this exact record.
        if body.version is not None or session.get(JobApplication, (source, posting_id)) is None:
            raise
    session.expire_all()
    return application_info(session.get(JobApplication, (source, posting_id)), posting)


@router.delete("/{source}/{posting_id}", status_code=204)
def remove_application(source: Source, posting_id: PostingId, session: SessionDep,
                       version: Annotated[int, Query(ge=1)]):
    result = session.execute(delete(JobApplication).where(JobApplication.source == source,
        JobApplication.posting_id == posting_id, JobApplication.version == version))
    if not result.rowcount:
        session.rollback()
        raise HTTPException(409, "This application changed or was removed. Reload before removing it.")
    session.commit()
    return Response(status_code=204)
