"""Shared local-development authentication dependency."""
# Import from secrets: compare_digest (compares credential bytes without an early exit on a matching
# prefix).
from secrets import compare_digest
# Import from typing: Annotated (attaches framework metadata, such as Depends, to a Python type).
from typing import Annotated

# Import from fastapi: Depends (declares a dependency FastAPI resolves for each request);
# HTTPException (aborts an HTTP request with a chosen status and safe response detail).
from fastapi import Depends, HTTPException
# Import from fastapi.security: HTTPAuthorizationCredentials (types the parsed authorization scheme
# and token); HTTPBearer (parses the Authorization: Bearer header).
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Import from .config: get_settings (loads and caches validated local configuration).
from .config import get_settings

# Set bearer to HTTPBearer(auto_error=False).
bearer = HTTPBearer(auto_error=False)


# Define require_local_token with parameters credentials.
def require_local_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
):
    # Depends asks FastAPI to supply parsed credentials. compare_digest avoids
    # a comparison that exits at the first mismatching character. This shared
    # development token is not a user identity or production authorization system.
    # Set expected to get_settings().dev_api_token.get_secret_value().
    expected = get_settings().dev_api_token.get_secret_value()
    # Check whether credentials is None or not (compare_digest(credentials.credentials.encode(),
    # expected.encode())).
    if credentials is None or not compare_digest(credentials.credentials.encode(), expected.encode()):
        # Raise HTTPException(status_code=401, detail='Invalid local API token',
        # headers={'WWW-Authenticate': 'Bearer'}) to stop the normal path.
        raise HTTPException(status_code=401, detail="Invalid local API token", headers={"WWW-Authenticate": "Bearer"})


