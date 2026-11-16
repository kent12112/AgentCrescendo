# Import from alembic: command (a dependency used below).
from alembic import command
# Import from alembic.config: Config (a dependency used below).
from alembic.config import Config
# Import from sqlalchemy: create_engine (constructs a database connection-pool manager); inspect (a
# dependency used below).
from sqlalchemy import create_engine, inspect

# Import from crescendo_api.config: get_settings (loads and caches validated local configuration).
from crescendo_api.config import get_settings


# Define test_initial_migration_can_upgrade_and_downgrade with parameters tmp_path, monkeypatch.
def test_initial_migration_can_upgrade_and_downgrade(tmp_path, monkeypatch):
    # tmp_path supplies a disposable directory. Apply the actual migration rather
    # than creating tables from ORM metadata, which could hide a broken migration.
    # Call monkeypatch.setenv with 'DEV_API_TOKEN',
    # 'migration-test-token-with-at-least-32-characters'.
    monkeypatch.setenv("DEV_API_TOKEN", "migration-test-token-with-at-least-32-characters")
    # Set url to f"sqlite:///{tmp_path / 'migration.db'}".
    url = f"sqlite:///{tmp_path / 'migration.db'}"
    # Call monkeypatch.setenv with 'DATABASE_URL', url.
    monkeypatch.setenv("DATABASE_URL", url)
    # Call get_settings.cache_clear with no arguments.
    get_settings.cache_clear()
    # Set config to Config('alembic.ini').
    config = Config("alembic.ini")
    # Set engine to create_engine(url).
    engine = create_engine(url)
    # Try the following operations; matching except clauses handle failures. The finally block runs
    # on every exit.
    try:
        # Call command.upgrade with config, 'head'.
        command.upgrade(config, "head")
        # Assert that 'runs' is in inspect(engine).get_table_names(). If false, this check fails
        # with AssertionError.
        assert "runs" in inspect(engine).get_table_names()
        # Assert that the number of items/characters in
        # inspect(engine).get_check_constraints('runs') equals 5. If false, this check fails with
        # AssertionError.
        assert len(inspect(engine).get_check_constraints("runs")) == 5
        # Compare the migrated schema with ORM metadata to detect schema drift.
        # Call command.check with config.
        command.check(config)
        # Exercise reversal only against this disposable test database.
        # Call command.downgrade with config, 'base'.
        command.downgrade(config, "base")
        # Assert that 'runs' is not in inspect(engine).get_table_names(). If false, this check fails
        # with AssertionError.
        assert "runs" not in inspect(engine).get_table_names()
    # Always run cleanup, whether the operation succeeds, returns, or raises.
    finally:
        # Call engine.dispose with no arguments.
        engine.dispose()
        # Call get_settings.cache_clear with no arguments.
        get_settings.cache_clear()
