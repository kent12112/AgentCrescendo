# Learn: Document this module, class, or function with a docstring; it is not an action or a model
# instruction.
"""Shared local-development authentication dependency."""
# Learn: From secrets, import compare_digest (compares credential bytes without an early exit on a matching
# prefix).
from secrets import compare_digest
# Learn: From typing, import Annotated (attaches framework metadata, such as Depends, to a Python type).
from typing import Annotated

# Learn: From fastapi, import Depends (declares a dependency FastAPI resolves for each request);
# HTTPException (aborts an HTTP request with a chosen status and safe response detail).
from fastapi import Depends, HTTPException
# Learn: From fastapi.security, import HTTPAuthorizationCredentials (types the parsed authorization scheme
# and token); HTTPBearer (parses the Authorization: Bearer header).
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Learn: From .config, import get_settings (loads and caches validated local configuration).
from .config import get_settings

# Learn: Set bearer to HTTPBearer(auto_error=False); the HTTP bearer parser; rejection is handled by our
# dependency.
bearer = HTTPBearer(auto_error=False)


# Learn: Define require_local_token(credentials). The body runs when called, not when defined.
def require_local_token(
    # Learn: Parameters: credentials has type Annotated[HTTPAuthorizationCredentials | None,
    # Depends(bearer)] (the parsed bearer credentials; they can be absent on an unauthenticated request).
    # Type hints do not enforce types by themselves.
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
# Learn: Finish the function signature; -> declares the return type and the following indented lines form
# the function body.
):
    # Depends asks FastAPI to supply parsed credentials. compare_digest avoids
    # a comparison that exits at the first mismatching character. This shared
    # development token is not a user identity or production authorization system.
    # Learn: Set expected to get_settings().dev_api_token.get_secret_value(); the expected credential or
    # fixture result used in this comparison. Access the underlying credential only at the authentication
    # boundary.
    expected = get_settings().dev_api_token.get_secret_value()
    # Learn: Take this branch only if credentials is None (no value) OR not
    # (compare_digest(credentials.credentials.encode(), expected.encode())).
    if credentials is None or not compare_digest(credentials.credentials.encode(), expected.encode()):
        # Learn: Raise HTTPException(status_code=401, detail='Invalid local API token',
        # headers={'WWW-Authenticate': 'Bearer'}) to stop the normal path.
        raise HTTPException(status_code=401, detail="Invalid local API token", headers={"WWW-Authenticate": "Bearer"})


