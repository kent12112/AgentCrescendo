# Learn: Document this module, class, or function with a docstring; it is not an action or a model
# instruction.
"""Load the git-ignored repository .env for local demo scripts."""
# Learn: Import os: reads process environment/configuration and OS facilities.
import os
# Learn: From pathlib, import Path (represents filesystem paths and explicit file operations).
from pathlib import Path

# Learn: From dotenv, import load_dotenv (loads .env configuration without overwriting existing process
# values).
from dotenv import load_dotenv

# Learn: Set ENV_FILE to Path(__file__).resolve().parents[3] divided by '.env'.
ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


# Learn: Define load_local_env(). The body runs when called, not when defined.
def load_local_env() -> None:
    # Terminal exports win; tests must never pick up a developer's real keys.
    # Learn: Take this branch only if 'PYTEST_CURRENT_TEST' is in os.environ.
    if "PYTEST_CURRENT_TEST" in os.environ:
        # Learn: Return None (no value) to the caller and stop this function.
        return
    # Learn: Call load_dotenv with the arguments shown.
    load_dotenv(ENV_FILE, override=False)
