"""Load the git-ignored repository .env for local demo scripts."""
# Import os: reads process environment/configuration and OS facilities.
import os
# Import from pathlib: Path (represents filesystem paths and explicit file operations).
from pathlib import Path

# Import from dotenv: load_dotenv (loads .env configuration without overwriting existing process
# values).
from dotenv import load_dotenv

# Set ENV_FILE to Path(__file__).resolve().parents[3] divided by '.env'.
ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


# Define load_local_env with no parameters.
def load_local_env() -> None:
    # Terminal exports win; tests must never pick up a developer's real keys.
    # Check whether 'PYTEST_CURRENT_TEST' is in os.environ.
    if "PYTEST_CURRENT_TEST" in os.environ:
        # Return without a value.
        return
    # Call load_dotenv with ENV_FILE.
    load_dotenv(ENV_FILE, override=False)
