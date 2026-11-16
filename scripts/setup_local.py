"""Create local-only environment files without printing credentials or overwriting files."""
# Import from pathlib: Path (represents filesystem paths and explicit file operations).
from pathlib import Path
# Import secrets: use this module through its namespace.
import secrets


# Define main with no parameters.
def main():
    # Set root to Path(__file__).resolve().parents[1].
    root = Path(__file__).resolve().parents[1]
    # Set paths to [root / '.env', root / 'apps/web/.env.local'].
    paths = [root / ".env", root / "apps/web/.env.local"]
    # Check whether any((path.exists() for path in paths)).
    if any(path.exists() for path in paths):
        # Raise SystemExit('Environment file already exists. Keep the same DEV_API_TOKEN in both
        # files; no files changed.') to stop the normal path.
        raise SystemExit("Environment file already exists. Keep the same DEV_API_TOKEN in both files; no files changed.")
    # Generate unpredictable bytes, encoded as environment-file-safe text. The
    # same token lets the Next.js server authenticate to the FastAPI backend.
    # Set token to secrets.token_urlsafe(32).
    token = secrets.token_urlsafe(32)
    # Set content to
    # f'DEV_API_TOKEN={token}\nDATABASE_URL=postgresql+psycopg://crescendo:crescendo@127.0.0.1:5432/crescendo\nAPI_BASE_URL=http://127.0.0.1:8000\n'.
    content = (
        f"DEV_API_TOKEN={token}\n"
        # Continue the expression
        # "DATABASE_URL=postgresql+psycopg://crescendo:crescendo@127.0.0.1:5432/crescendo\n";
        # brackets keep it part of the statement above.
        "DATABASE_URL=postgresql+psycopg://crescendo:crescendo@127.0.0.1:5432/crescendo\n"
        # Continue the expression "API_BASE_URL=http://127.0.0.1:8000\n"; brackets keep it part of
        # the statement above.
        "API_BASE_URL=http://127.0.0.1:8000\n"
    )
    # Iterate over paths, binding path for each item.
    for path in paths:
        # Exclusive creation (x) fails if a file already exists. chmod 0600 grants
        # read/write to its owner only, before credential contents are written.
        # Set descriptor to path.open('x', encoding='utf-8').
        descriptor = path.open("x", encoding="utf-8")
        # Try the following operations; matching except clauses handle failures. The finally block
        # runs on every exit.
        try:
            # Call path.chmod with 384.
            path.chmod(0o600)
            # Call descriptor.write with content.
            descriptor.write(content)
        # Always run cleanup, whether the operation succeeds, returns, or raises.
        finally:
            descriptor.close()
    # Print 'Created .env and apps/web/.env.local. Credentials were not printed.'.
    print("Created .env and apps/web/.env.local. Credentials were not printed.")


# Check whether __name__ equals '__main__'.
if __name__ == "__main__":
    # Call main with no arguments.
    main()
