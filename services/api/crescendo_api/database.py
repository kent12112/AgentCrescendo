# Learn: From functools, import lru_cache (caches process-level settings or connection-manager
# construction).
from functools import lru_cache

# Learn: From sqlalchemy, import create_engine (constructs a database connection-pool manager).
from sqlalchemy import create_engine
# Learn: From sqlalchemy.orm, import Session (groups SQLAlchemy database work and transaction state).
from sqlalchemy.orm import Session

# Learn: From .config, import get_settings (loads and caches validated local configuration).
from .config import get_settings


# Learn: Cache calls by arguments so settings/engine construction is reused within this process.
@lru_cache
# Learn: Define get_engine(). The body runs when called, not when defined.
def get_engine():
    # Reuse one connection-pool manager per process, not one database connection
    # forever. pre_ping checks that a pooled connection is alive before reuse.
    # Learn: Return create_engine(get_settings().database_url, pool_pre_ping=True) to the caller and stop
    # this function.
    return create_engine(get_settings().database_url, pool_pre_ping=True)


# Learn: Define get_session(). The body runs when called, not when defined.
def get_session():
    # FastAPI injects this per-request unit of database work. Code after yield
    # runs when the request finishes; the context manager closes the session.
    # Endpoints explicitly commit successful writes. Closing rolls back pending work.
    # Learn: Enter Session(get_engine()) as session. The context manager controls setup/exit; inspect it for
    # the actual cleanup behavior.
    with Session(get_engine()) as session:
        # Learn: Yield session to the with-block/request; resume here for cleanup afterward.
        yield session

