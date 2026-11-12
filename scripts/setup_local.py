"""Create local-only environment files without printing credentials or overwriting files."""
from pathlib import Path
import secrets


def main():
    root = Path(__file__).resolve().parents[1]
    paths = [root / ".env", root / "apps/web/.env.local"]
    if any(path.exists() for path in paths):
        raise SystemExit("Environment file already exists. Keep the same DEV_API_TOKEN in both files; no files changed.")
    # Generate unpredictable bytes, encoded as environment-file-safe text. The
    # same token lets the Next.js server authenticate to the FastAPI backend.
    token = secrets.token_urlsafe(32)
    content = (
        f"DEV_API_TOKEN={token}\n"
        "DATABASE_URL=postgresql+psycopg://crescendo:crescendo@127.0.0.1:5432/crescendo\n"
        "API_BASE_URL=http://127.0.0.1:8000\n"
    )
    for path in paths:
        # Exclusive creation (x) fails if a file already exists. chmod 0600 grants
        # read/write to its owner only, before credential contents are written.
        descriptor = path.open("x", encoding="utf-8")
        try:
            path.chmod(0o600)
            descriptor.write(content)
        finally:
            descriptor.close()
    print("Created .env and apps/web/.env.local. Credentials were not printed.")


if __name__ == "__main__":
    main()
