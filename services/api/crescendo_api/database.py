# Import from functools: lru_cache (caches process-level settings or connection-manager
# construction).
from functools import lru_cache

# Import from sqlalchemy: create_engine (constructs a database connection-pool manager).
from sqlalchemy import create_engine
# Import from sqlalchemy.orm: Session (groups SQLAlchemy database work and transaction state).
from sqlalchemy.orm import Session

# Import from .config: get_settings (loads and caches validated local configuration).
from .config import get_settings


# Cache calls by arguments so settings/engine construction is reused within this process.
@lru_cache
# Define get_engine with no parameters.
def get_engine():
    # Reuse one connection-pool manager per process, not one database connection
    # forever. pre_ping checks that a pooled connection is alive before reuse.
    # Return create_engine(get_settings().database_url, pool_pre_ping=True).
    return create_engine(get_settings().database_url, pool_pre_ping=True)


# Define get_session with no parameters.
def get_session():
    # FastAPI injects this per-request unit of database work. Code after yield
    # runs when the request finishes; the context manager closes the session.
    # Endpoints explicitly commit successful writes. Closing rolls back pending work.
    # Use Session(get_engine()) as session; leave the context and run its cleanup when this block
    # ends.
    with Session(get_engine()) as session:
        # Give session to the caller and pause here until execution resumes.
        yield session

