# Learn: Document this module, class, or function with a docstring; it is not an action or a model
# instruction.
"""Persisted draft endpoints; these routes do not execute agents."""
# Learn: From typing, import Annotated (attaches framework metadata, such as Depends, to a Python type).
from typing import Annotated
# Learn: From uuid, import UUID (parses/types UUID identifiers so malformed route IDs are rejected).
from uuid import UUID

# Learn: From fastapi, import APIRouter (groups related HTTP endpoints before app registration); Depends
# (declares a dependency FastAPI resolves for each request); HTTPException (aborts an HTTP request with a
# chosen status and safe response detail); Response (constructs an explicit HTTP response, including empty
# deletion responses).
from fastapi import APIRouter, Depends, HTTPException, Response
# Learn: From sqlalchemy, import delete (builds a SQL DELETE statement); select (builds a SQL SELECT query).
from sqlalchemy import delete, select
# Learn: From sqlalchemy.orm, import Session (groups SQLAlchemy database work and transaction state).
from sqlalchemy.orm import Session

# Learn: From ..auth, import require_local_token (rejects absent/incorrect development credentials before
# endpoint execution).
from ..auth import require_local_token
# Learn: From ..database, import get_session (yields a request-scoped database unit of work).
from ..database import get_session
# Learn: From ..models, import Run (maps the persisted draft row).
from ..models import Run
# Learn: From ..schemas, import RunCreate (validates incoming draft JSON and limits); RunRead (serializes
# persisted drafts with generated IDs and timestamps).
from ..schemas import RunCreate, RunRead

# Learn: Set router to APIRouter(dependencies=[Depends(require_local_token)]).
router = APIRouter(dependencies=[Depends(require_local_token)])
# Learn: Set SessionDep to Annotated[Session, Depends(get_session)].
SessionDep = Annotated[Session, Depends(get_session)]


# Learn: Register this function as the route for the indicated HTTP method or WebSocket path; dependencies
# enforce the configured boundary.
@router.post("/runs", response_model=RunRead, status_code=201)
# Learn: Define create_run(body, session). The body runs when called, not when defined.
def create_run(body: RunCreate, session: SessionDep):
    # Pydantic has already validated body. model_dump converts it to a dictionary;
    # ** unpacks the fields into the SQLAlchemy object's constructor.
    # Learn: Set run to Run(**body.model_dump()); the persisted task draft or returned draft representation.
    run = Run(**body.model_dump())
    # add stages the new object; commit inserts it and makes the transaction durable.
    # Learn: Stage an object or add a value to this collection on session; inputs: run.
    session.add(run)
    # Learn: Commit this database transaction so successful writes become durable on session.
    session.commit()
    # Reload the stored values before FastAPI serializes them using RunRead.
    # Learn: Reload generated/stored row values before serialization on session; inputs: run.
    session.refresh(run)
    # Learn: Return run to the caller and stop this function.
    return run


# Learn: Register this function as the route for the indicated HTTP method or WebSocket path; dependencies
# enforce the configured boundary.
@router.get("/runs", response_model=list[RunRead])
# Learn: Define list_runs(session). The body runs when called, not when defined.
def list_runs(session: SessionDep):
    # Newest first, capped at 25. The ID is a tiebreaker for equal timestamps.
    # scalars returns mapped Run objects rather than SQL result-row wrappers.
    # Learn: Return session.scalars(select(Run).order_by(Run.created_at.desc(),
    # Run.id.desc()).limit(25)).all() to the caller and stop this function.
    return session.scalars(select(Run).order_by(Run.created_at.desc(), Run.id.desc()).limit(25)).all()


# Learn: Register this function as the route for the indicated HTTP method or WebSocket path; dependencies
# enforce the configured boundary.
@router.get("/runs/{run_id}", response_model=RunRead)
# Learn: Define get_run(run_id, session). The body runs when called, not when defined.
def get_run(run_id: UUID, session: SessionDep):
    # FastAPI rejects malformed UUIDs before this function. get looks up a primary
    # key; a well-formed ID with no matching row gets HTTP 404 instead of null.
    # Learn: Set run to session[Run] with str(run_id) as the missing-key default; the persisted task draft
    # or returned draft representation. Read a key/row, using the supplied default when applicable.
    run = session.get(Run, str(run_id))
    # Learn: Take this branch only if run is None (no value).
    if run is None:
        # Learn: Raise HTTPException(status_code=404, detail='Run not found') to stop the normal path.
        raise HTTPException(status_code=404, detail="Run not found")
    # Learn: Return run to the caller and stop this function.
    return run


# Learn: Register this function as the route for the indicated HTTP method or WebSocket path; dependencies
# enforce the configured boundary.
@router.delete("/runs/{run_id}", status_code=204)
# Learn: Define delete_run(run_id, session). The body runs when called, not when defined.
def delete_run(run_id: UUID, session: SessionDep):
    # Delete only the requested draft. A single statement avoids a gap between
    # checking existence and deleting; RETURNING tells us whether a row matched.
    # Learn: Set deleted_id to session.execute(delete(Run).where(Run.id == str(run_id), Run.status ==
    # 'draft').returning(Run.id)).scalar_one_or_none().
    deleted_id = session.execute(
        # Learn: Call delete(Run).where(Run.id == str(run_id), Run.status == 'draft').returning with the
        # arguments shown.
        delete(Run).where(Run.id == str(run_id), Run.status == "draft").returning(Run.id)
    # Learn: Supply the next argument to session.execute(delete(Run).where(Run.id == str(run_id), Run.status
    # == 'draft').returning(Run.id)).scalar_one_or_none: ).scalar_one_or_none().
    ).scalar_one_or_none()
    # Learn: Take this branch only if deleted_id is None (no value).
    if deleted_id is None:
        # Learn: Raise HTTPException(status_code=404, detail='Draft not found') to stop the normal path.
        raise HTTPException(status_code=404, detail="Draft not found")
    # Learn: Commit this database transaction so successful writes become durable on session.
    session.commit()
    # Learn: Return Response(status_code=204) to the caller and stop this function.
    return Response(status_code=204)

