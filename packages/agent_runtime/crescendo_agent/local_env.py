"""Load the git-ignored repository .env for local demo scripts."""
import os
from pathlib import Path

from dotenv import load_dotenv

ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


def load_local_env() -> None:
    # Terminal exports win; tests must never pick up a developer's real keys.
    if "PYTEST_CURRENT_TEST" in os.environ:
        return
    load_dotenv(ENV_FILE, override=False)
