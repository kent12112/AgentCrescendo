# Learn: Document this module, class, or function with a docstring; it is not an action or a model
# instruction.
"""Create local-only environment files without printing credentials or overwriting files."""
# Learn: From pathlib, import Path (represents filesystem paths and explicit file operations).
from pathlib import Path
# Learn: Import secrets: use this module through its namespace.
import secrets


# Learn: Define main(). The body runs when called, not when defined.
def main():
    # Learn: Set root to Path(__file__).resolve().parents[1].
    root = Path(__file__).resolve().parents[1]
    # Learn: Set paths to a new list containing root divided by '.env', root divided by
    # 'apps/web/.env.local'.
    paths = [root / ".env", root / "apps/web/.env.local"]
    # Learn: Take this branch only if any((path.exists() for path in paths)).
    if any(path.exists() for path in paths):
        # Learn: Raise SystemExit('Environment file already exists. Keep the same DEV_API_TOKEN in both
        # files; no files changed.') to stop the normal path.
        raise SystemExit("Environment file already exists. Keep the same DEV_API_TOKEN in both files; no files changed.")
    # Generate unpredictable bytes, encoded as environment-file-safe text. The
    # same token lets the Next.js server authenticate to the FastAPI backend.
    # Learn: Set token to secrets.token_urlsafe(32); the shared local-development API credential; never send
    # it to browser code.
    token = secrets.token_urlsafe(32)
    # Learn: Set content to an f-string that substitutes the expressions in {...} into the text; the
    # selected page region or content to write.
    content = (
        # Learn: Supply literal text 'DEV_API_TOKEN='; adjacent string literals are concatenated without
        # adding whitespace.
        f"DEV_API_TOKEN={token}\n"
        # Learn: Continue the expression
        # "DATABASE_URL=postgresql+psycopg://crescendo:crescendo@127.0.0.1:5432/crescendo\n"; brackets keep
        # it part of the statement above.
        "DATABASE_URL=postgresql+psycopg://crescendo:crescendo@127.0.0.1:5432/crescendo\n"
        # Learn: Continue the expression "API_BASE_URL=http://127.0.0.1:8000\n"; brackets keep it part of
        # the statement above.
        "API_BASE_URL=http://127.0.0.1:8000\n"
    # Learn: Close the multi-line expression; indentation inside brackets is for readability, not a new
    # block.
    )
    # Learn: Iterate over paths, binding path for each item.
    for path in paths:
        # Exclusive creation (x) fails if a file already exists. chmod 0600 grants
        # read/write to its owner only, before credential contents are written.
        # Learn: Set descriptor to path.open('x', encoding='utf-8').
        descriptor = path.open("x", encoding="utf-8")
        # Learn: Try the following operations; matching except clauses handle failures. The finally block
        # runs on every exit.
        try:
            # Learn: Set filesystem permissions; 0o600 restricts the credential file to its owner on path;
            # inputs: 384.
            path.chmod(0o600)
            # Learn: Write this text or byte sequence to the already-open output on descriptor; inputs:
            # content.
            descriptor.write(content)
        # Learn: Always run cleanup, whether the operation succeeds, returns, or raises.
        finally:
            # Learn: Close this owned connection, stream, file, or browser resource on descriptor.
            descriptor.close()
    # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs: 'Created
    # .env and apps/web/.env.local. Credentials were not printed.'.
    print("Created .env and apps/web/.env.local. Credentials were not printed.")


# Learn: Take this branch only if __name__ equals '__main__'. The __main__ guard keeps imports from
# launching the CLI.
if __name__ == "__main__":
    # Learn: Call main with no arguments.
    main()
