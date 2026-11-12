from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from .config import get_settings


@lru_cache
def get_engine():
    # Reuse one connection-pool manager per process, not one database connection
    # forever. pre_ping checks that a pooled connection is alive before reuse.
    return create_engine(get_settings().database_url, pool_pre_ping=True)


def get_session():
    # FastAPI injects this per-request unit of database work. Code after yield
    # runs when the request finishes; the context manager closes the session.
    # Endpoints explicitly commit successful writes. Closing rolls back pending work.
    with Session(get_engine()) as session:
        yield session

