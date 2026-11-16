"""Liveness and supported dashboard capabilities."""
# Import from fastapi: APIRouter (groups related HTTP endpoints before app registration); Depends
# (declares a dependency FastAPI resolves for each request).
from fastapi import APIRouter, Depends

# Import from ..auth: require_local_token (rejects absent/incorrect development credentials before
# endpoint execution).
from ..auth import require_local_token

# Set router to APIRouter().
router = APIRouter()


# Register this function as the route for the indicated HTTP method or WebSocket path; dependencies
# enforce the configured boundary.
@router.get("/health")
# Define health with no parameters.
def health():
    # Liveness only: this proves the API answers, not that PostgreSQL is ready.
    # Return {'status': 'ok', 'service': 'agent-crescendo-api'}.
    return {"status": "ok", "service": "agent-crescendo-api"}


# Register this function as the route for the indicated HTTP method or WebSocket path; dependencies
# enforce the configured boundary.
@router.get("/capabilities", dependencies=[Depends(require_local_token)])
# Define capabilities with no parameters.
def capabilities():
    # Report implemented behavior honestly; saving a draft never starts an agent.
    # Return a new dictionary with keys 'mode', 'drafts', 'execution', 'reason', 'max_workers',
    # 'max_timeout_seconds'.
    return {
        # Include mode in this dictionary.
        "mode": "local-development",
        # Include drafts in this dictionary.
        "drafts": True,
        # Include execution in this dictionary.
        "execution": False,
        # Include reason in this dictionary.
        "reason": "Desktop permissions and network enforcement are not connected yet.",
        # Include max_workers in this dictionary.
        "max_workers": 3,
        # Include max_timeout_seconds in this dictionary.
        "max_timeout_seconds": 600,
    }


