"""Persisted draft endpoints; these routes do not execute agents."""
# Import from typing: Annotated (attaches framework metadata, such as Depends, to a Python type).
from typing import Annotated
# Import from uuid: UUID (parses/types UUID identifiers so malformed route IDs are rejected).
from uuid import UUID

# Import from fastapi: APIRouter (groups related HTTP endpoints before app registration); Depends
# (declares a dependency FastAPI resolves for each request); HTTPException (aborts an HTTP request
# with a chosen status and safe response detail); Response (constructs an explicit HTTP response,
# including empty deletion responses).
from fastapi import APIRouter, Depends, HTTPException, Response
# Import from sqlalchemy: delete (builds a SQL DELETE statement); select (builds a SQL SELECT
# query).
from sqlalchemy import delete, select
# Import from sqlalchemy.orm: Session (groups SQLAlchemy database work and transaction state).
from sqlalchemy.orm import Session

# Import from ..auth: require_local_token (rejects absent/incorrect development credentials before
# endpoint execution).
from ..auth import require_local_token
# Import from ..database: get_session (yields a request-scoped database unit of work).
from ..database import get_session
# Import from ..models: Run (maps the persisted draft row).
from ..models import Run
# Import from ..schemas: RunCreate (validates incoming draft JSON and limits); RunRead (serializes
# persisted drafts with generated IDs and timestamps).
from ..schemas import RunCreate, RunRead

# Set router to APIRouter(dependencies=[Depends(require_local_token)]).
router = APIRouter(dependencies=[Depends(require_local_token)])
# Set SessionDep to Annotated[Session, Depends(get_session)].
SessionDep = Annotated[Session, Depends(get_session)]


# Register this function as the route for the indicated HTTP method or WebSocket path; dependencies
# enforce the configured boundary.
@router.post("/runs", response_model=RunRead, status_code=201)
# Define create_run with parameters body, session.
def create_run(body: RunCreate, session: SessionDep):
    # Pydantic has already validated body. model_dump converts it to a dictionary;
    # ** unpacks the fields into the SQLAlchemy object's constructor.
    # Set run to Run(**body.model_dump()).
    run = Run(**body.model_dump())
    # add stages the new object; commit inserts it and makes the transaction durable.
    # Add run to session.
    session.add(run)
    # Commit this session’s transaction so its changes are saved in the database.
    session.commit()
    # Reload the stored values before FastAPI serializes them using RunRead.
    # Reload run from the database.
    session.refresh(run)
    # Return run.
    return run


# Register this function as the route for the indicated HTTP method or WebSocket path; dependencies
# enforce the configured boundary.
@router.get("/runs", response_model=list[RunRead])
# Define list_runs with parameters session.
def list_runs(session: SessionDep):
    # Newest first, capped at 25. The ID is a tiebreaker for equal timestamps.
    # scalars returns mapped Run objects rather than SQL result-row wrappers.
    # Return session.scalars(select(Run).order_by(Run.created_at.desc(),
    # Run.id.desc()).limit(25)).all().
    return session.scalars(select(Run).order_by(Run.created_at.desc(), Run.id.desc()).limit(25)).all()


# Register this function as the route for the indicated HTTP method or WebSocket path; dependencies
# enforce the configured boundary.
@router.get("/runs/{run_id}", response_model=RunRead)
# Define get_run with parameters run_id, session.
def get_run(run_id: UUID, session: SessionDep):
    # FastAPI rejects malformed UUIDs before this function. get looks up a primary
    # key; a well-formed ID with no matching row gets HTTP 404 instead of null.
    # Set run to session.get(Run, str(run_id)).
    run = session.get(Run, str(run_id))
    # Check whether run is None.
    if run is None:
        # Raise HTTPException(status_code=404, detail='Run not found') to stop the normal path.
        raise HTTPException(status_code=404, detail="Run not found")
    # Return run.
    return run


# Register this function as the route for the indicated HTTP method or WebSocket path; dependencies
# enforce the configured boundary.
@router.delete("/runs/{run_id}", status_code=204)
# Define delete_run with parameters run_id, session.
def delete_run(run_id: UUID, session: SessionDep):
    # Delete only the requested draft. A single statement avoids a gap between
    # checking existence and deleting; RETURNING tells us whether a row matched.
    # Set deleted_id to session.execute(delete(Run).where(Run.id == str(run_id), Run.status ==
    # 'draft').returning(Run.id)).scalar_one_or_none().
    deleted_id = session.execute(
        # Call delete(Run).where(Run.id == str(run_id), Run.status == 'draft').returning with
        # Run.id.
        delete(Run).where(Run.id == str(run_id), Run.status == "draft").returning(Run.id)
    ).scalar_one_or_none()
    # Check whether deleted_id is None.
    if deleted_id is None:
        # Raise HTTPException(status_code=404, detail='Draft not found') to stop the normal path.
        raise HTTPException(status_code=404, detail="Draft not found")
    # Commit this session’s transaction so its changes are saved in the database.
    session.commit()
    # Return Response(status_code=204).
    return Response(status_code=204)

