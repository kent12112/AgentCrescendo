# Learn: Document this module, class, or function with a docstring; it is not an action or a model
# instruction.
"""Liveness and supported dashboard capabilities."""
# Learn: From fastapi, import APIRouter (groups related HTTP endpoints before app registration); Depends
# (declares a dependency FastAPI resolves for each request).
from fastapi import APIRouter, Depends

# Learn: From ..auth, import require_local_token (rejects absent/incorrect development credentials before
# endpoint execution).
from ..auth import require_local_token

# Learn: Set router to APIRouter().
router = APIRouter()


# Learn: Register this function as the route for the indicated HTTP method or WebSocket path; dependencies
# enforce the configured boundary.
@router.get("/health")
# Learn: Define health(). The body runs when called, not when defined.
def health():
    # Liveness only: this proves the API answers, not that PostgreSQL is ready.
    # Learn: Return a new dictionary with keys 'status', 'service' to the caller and stop this function.
    return {"status": "ok", "service": "agent-crescendo-api"}


# Learn: Register this function as the route for the indicated HTTP method or WebSocket path; dependencies
# enforce the configured boundary.
@router.get("/capabilities", dependencies=[Depends(require_local_token)])
# Learn: Define capabilities(). The body runs when called, not when defined.
def capabilities():
    # Report implemented behavior honestly; saving a draft never starts an agent.
    # Learn: Return a new dictionary with keys 'mode', 'drafts', 'execution', 'reason', 'max_workers',
    # 'max_timeout_seconds' to the caller and stop this function.
    return {
        # Learn: Define this named mapping field: "mode": "local-development",. The key selects the
        # schema/configuration value.
        "mode": "local-development",
        # Learn: Define this named mapping field: "drafts": True,. The key selects the schema/configuration
        # value.
        "drafts": True,
        # Learn: Define this named mapping field: "execution": False,. The key selects the
        # schema/configuration value.
        "execution": False,
        # Learn: Define this named mapping field: "reason": "Desktop permissions and network enforcement are
        # not connected yet.",. The key selects the schema/configuration value.
        "reason": "Desktop permissions and network enforcement are not connected yet.",
        # Learn: Define this named mapping field: "max_workers": 3,. The key selects the
        # schema/configuration value.
        "max_workers": 3,
        # Learn: Define this named mapping field: "max_timeout_seconds": 600,. The key selects the
        # schema/configuration value.
        "max_timeout_seconds": 600,
    # Learn: Close this dict literal; delimiters group the values into one object.
    }


