"""Job search endpoints for the web app (JOB-F08). Local, token-protected like /runs.

- GET  /jobs/search            ranked open postings for the stored resume, one page at a time
- GET  /jobs/postings/{s}/{id} one posting's details with skill highlights
- GET/PUT/DELETE /jobs/resume  the uploaded resume (text kept in local Postgres, file not kept)
- GET/PUT /jobs/picks          up to 3 postings chosen for cover letters (PUT replaces the set)

Nothing here contacts another service; the daily crawl (JOB-F07) fills the data.
"""
from datetime import datetime, timezone
from pathlib import PurePosixPath, PureWindowsPath
from typing import Annotated
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from crescendo_agent.job_match import company_label, resume_skills as skills_of
from crescendo_agent.resume import MAX_BYTES, ResumeError, resume_text_from_bytes

from ..auth import require_local_token
from ..database import get_session
from ..job_search import posting_detail, search, to_posting
from ..models import MAX_JOB_PICKS, JobPick, JobPosting, JobResume

router = APIRouter(prefix="/jobs", dependencies=[Depends(require_local_token)])
SessionDep = Annotated[Session, Depends(get_session)]

SOURCE = r"^(ashby|greenhouse|lever)$"
POSTING_ID = r"^[A-Za-z0-9-]{1,64}$"  # UUIDs (Ashby, Lever) or digits (Greenhouse)
RESUME_KINDS = {"application/pdf": "pdf", "text/plain": "txt", "text/markdown": "md"}


def _resume(session) -> JobResume | None:
    return session.get(JobResume, 1)


def _resume_info(resume: JobResume | None) -> dict | None:
    if resume is None:
        return None
    uploaded = resume.uploaded_at if resume.uploaded_at.tzinfo else resume.uploaded_at.replace(tzinfo=timezone.utc)
    return {"filename": resume.filename, "uploaded_at": uploaded.isoformat().replace("+00:00", "Z"),
            "skills": list(resume.skills or []), "characters": len(resume.text)}


# --- Search ---------------------------------------------------------------------------


@router.get("/search")
def search_jobs(
    session: SessionDep,
    q: Annotated[str, Query(min_length=1, max_length=100)],
    country: Annotated[str | None, Query(max_length=60)] = None,
    location: Annotated[list[str], Query(max_length=5)] = [],
    remote: bool = False,
    no_senior: bool = False,
    max_years: Annotated[int | None, Query(ge=0, le=30)] = None,
    max_age_days: Annotated[int, Query(ge=1, le=30)] = 30,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    source: Annotated[str, Query(pattern=SOURCE)] = "ashby",
    hide_applied: bool = False,
):
    resume = _resume(session)
    if resume is None:
        raise HTTPException(status_code=409, detail="Upload your resume first; scores compare jobs with it.")
    places = [place.strip()[:60] for place in location if place.strip()]
    try:
        page = search(session, set(resume.skills or []), query=q, country=country or None, locations=places,
                      remote=remote, no_senior=no_senior, max_years=max_years, max_age_days=max_age_days,
                      offset=offset, limit=limit, source=source, hide_applied=hide_applied)
    except ValueError as error:  # e.g. a search made only of stop words
        raise HTTPException(status_code=422, detail=str(error)) from None
    picked = {(p.source, p.posting_id) for p in session.scalars(select(JobPick))}
    for row in page["results"]:
        row["picked"] = (row["source"], row["posting_id"]) in picked
    return page


@router.get("/postings/{source}/{posting_id}")
def get_posting(session: SessionDep, source: Annotated[str, Path(pattern=SOURCE)],
                posting_id: Annotated[str, Path(pattern=POSTING_ID)]):
    resume = _resume(session)
    detail = posting_detail(session, source, posting_id, set(resume.skills or []) if resume else None)
    if detail is None:
        raise HTTPException(status_code=404, detail="That posting is not stored (it may be older than 30 days).")
    return detail


# --- Resume ---------------------------------------------------------------------------


def _safe_filename(raw: str | None) -> str:
    """Base name only, printable, at most 255 characters; 'resume' when unusable.

    The web proxy sends the name URI-encoded (header values must be ASCII).
    """
    name = PureWindowsPath(PurePosixPath(unquote(raw or "")).name).name
    name = "".join(ch for ch in name if ch.isprintable()).strip()[:255]
    return name or "resume"


@router.get("/resume")
def get_resume(session: SessionDep):
    return {"resume": _resume_info(_resume(session))}


@router.put("/resume")
async def put_resume(request: Request, session: SessionDep):
    """Body: the file bytes. Content-Type picks the reader; X-Filename names it."""
    kind = RESUME_KINDS.get((request.headers.get("content-type") or "").split(";")[0].strip().lower())
    if kind is None:
        raise HTTPException(status_code=415, detail="Upload a PDF, .txt, or .md resume.")
    body = bytearray()
    async for chunk in request.stream():  # stop reading at the limit instead of buffering it all
        body.extend(chunk)
        if len(body) > MAX_BYTES:
            raise HTTPException(status_code=413, detail="The resume file is larger than 10 MB.")
    try:
        text = resume_text_from_bytes(bytes(body), kind)
    except ResumeError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    resume = _resume(session) or JobResume(id=1)
    resume.filename = _safe_filename(request.headers.get("x-filename"))
    resume.text, resume.skills = text, sorted(skills_of(text))
    resume.uploaded_at = datetime.now(timezone.utc)
    session.add(resume)
    session.commit()
    return {"resume": _resume_info(resume)}


@router.delete("/resume", status_code=204)
def delete_resume(session: SessionDep):
    session.execute(delete(JobResume))
    session.commit()
    return Response(status_code=204)


# --- Picks ----------------------------------------------------------------------------


class PickRef(BaseModel):
    source: str = Field(pattern=SOURCE)
    posting_id: str = Field(pattern=POSTING_ID)


class PicksBody(BaseModel):
    picks: list[PickRef] = Field(max_length=MAX_JOB_PICKS)


def _picks(session) -> list[dict]:
    rows = session.execute(select(JobPick, JobPosting).join(
        JobPosting, (JobPosting.source == JobPick.source) & (JobPosting.posting_id == JobPick.posting_id))
        .order_by(JobPick.picked_at, JobPick.posting_id)).all()
    return [{"source": pick.source, "posting_id": pick.posting_id, "title": posting.title,
             "company": company_label(to_posting(posting)), "url": posting.url,
             "closed": posting.closed_at is not None} for pick, posting in rows]


@router.get("/picks")
def get_picks(session: SessionDep):
    return {"picks": _picks(session), "max": MAX_JOB_PICKS}


@router.put("/picks")
def put_picks(body: PicksBody, session: SessionDep):
    """Replace the whole selection (at most 3, each an open stored posting) in one transaction."""
    wanted = list(dict.fromkeys((p.source, p.posting_id) for p in body.picks))  # drop repeats, keep order
    for source, posting_id in wanted:
        posting = session.get(JobPosting, (source, posting_id))
        if posting is None or posting.closed_at is not None:
            raise HTTPException(status_code=422, detail="One of the picked postings is closed or no longer stored.")
    existing = {(p.source, p.posting_id): p.picked_at for p in session.scalars(select(JobPick))}
    session.execute(delete(JobPick))
    now = datetime.now(timezone.utc)
    for number, key in enumerate(wanted):
        # Keep the original pick time for postings already picked, so the order stays stable.
        session.add(JobPick(source=key[0], posting_id=key[1], picked_at=existing.get(key) or now))
    session.commit()
    return {"picks": _picks(session), "max": MAX_JOB_PICKS}
