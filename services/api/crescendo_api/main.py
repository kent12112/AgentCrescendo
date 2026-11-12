from secrets import compare_digest
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_session
from .models import Run
from .schemas import RunCreate, RunRead

# FastAPI registers the decorated functions below as HTTP endpoints and generates
# /docs and /openapi.json from their request and response schemas.
app = FastAPI(title="AgentCrescendo", version="0.1.0")
# Parse Authorization: Bearer <token>; our dependency supplies the rejection logic.
bearer = HTTPBearer(auto_error=False)


def require_local_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
):
    # Depends asks FastAPI to supply parsed credentials. compare_digest avoids
    # a comparison that exits at the first mismatching character. This shared
    # development token is not a user identity or production authorization system.
    expected = get_settings().dev_api_token.get_secret_value()
    if credentials is None or not compare_digest(credentials.credentials.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Invalid local API token", headers={"WWW-Authenticate": "Bearer"})


# Annotated combines the Python type with instructions for FastAPI to inject
# the request's session. Tests can replace get_session without changing endpoints.
SessionDep = Annotated[Session, Depends(get_session)]


@app.get("/health")
def health():
    # Liveness only: this proves the API answers, not that PostgreSQL is ready.
    return {"status": "ok", "service": "agent-crescendo-api"}


@app.get("/capabilities", dependencies=[Depends(require_local_token)])
def capabilities():
    # Report implemented behavior honestly; saving a draft never starts an agent.
    return {
        "mode": "local-development",
        "drafts": True,
        "execution": False,
        "reason": "Desktop permissions and network enforcement are not connected yet.",
        "max_workers": 3,
        "max_timeout_seconds": 600,
    }


@app.post("/runs", response_model=RunRead, status_code=201, dependencies=[Depends(require_local_token)])
def create_run(body: RunCreate, session: SessionDep):
    # Pydantic has already validated body. model_dump converts it to a dictionary;
    # ** unpacks the fields into the SQLAlchemy object's constructor.
    run = Run(**body.model_dump())
    # add stages the new object; commit inserts it and makes the transaction durable.
    session.add(run)
    session.commit()
    # Reload the stored values before FastAPI serializes them using RunRead.
    session.refresh(run)
    return run


@app.get("/runs", response_model=list[RunRead], dependencies=[Depends(require_local_token)])
def list_runs(session: SessionDep):
    # Newest first, capped at 25. The ID is a tiebreaker for equal timestamps.
    # scalars returns mapped Run objects rather than SQL result-row wrappers.
    return session.scalars(select(Run).order_by(Run.created_at.desc(), Run.id.desc()).limit(25)).all()


@app.get("/runs/{run_id}", response_model=RunRead, dependencies=[Depends(require_local_token)])
def get_run(run_id: UUID, session: SessionDep):
    # FastAPI rejects malformed UUIDs before this function. get looks up a primary
    # key; a well-formed ID with no matching row gets HTTP 404 instead of null.
    run = session.get(Run, str(run_id))
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run

