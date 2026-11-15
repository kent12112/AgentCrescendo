# Learn: From alembic, import command (a dependency used below).
from alembic import command
# Learn: From alembic.config, import Config (a dependency used below).
from alembic.config import Config
# Learn: From sqlalchemy, import create_engine (constructs a database connection-pool manager); inspect (a
# dependency used below).
from sqlalchemy import create_engine, inspect

# Learn: From crescendo_api.config, import get_settings (loads and caches validated local configuration).
from crescendo_api.config import get_settings


# Learn: Test initial migration can upgrade and downgrade. pytest supplies named fixtures and checks
# assertions below.
def test_initial_migration_can_upgrade_and_downgrade(tmp_path, monkeypatch):
    # tmp_path supplies a disposable directory. Apply the actual migration rather
    # than creating tables from ORM metadata, which could hide a broken migration.
    # Learn: Temporarily set an environment variable for this test on monkeypatch; inputs: 'DEV_API_TOKEN',
    # 'migration-test-token-with-at-least-32-characters'.
    monkeypatch.setenv("DEV_API_TOKEN", "migration-test-token-with-at-least-32-characters")
    # Learn: Set url to an f-string that substitutes the expressions in {...} into the text; the destination
    # or current page address.
    url = f"sqlite:///{tmp_path / 'migration.db'}"
    # Learn: Temporarily set an environment variable for this test on monkeypatch; inputs: 'DATABASE_URL',
    # url.
    monkeypatch.setenv("DATABASE_URL", url)
    # Learn: Clear cached configuration so this test reads its own environment on get_settings.
    get_settings.cache_clear()
    # Learn: Set config to Config('alembic.ini').
    config = Config("alembic.ini")
    # Learn: Set engine to create_engine(url); the SQLAlchemy connection-pool manager, not a permanently
    # open transaction.
    engine = create_engine(url)
    # Learn: Try the following operations; matching except clauses handle failures. The finally block runs
    # on every exit.
    try:
        # Learn: Call command.upgrade with the arguments shown.
        command.upgrade(config, "head")
        # Learn: Assert that 'runs' is in inspect(engine).get_table_names(). If false, this check fails with
        # AssertionError.
        assert "runs" in inspect(engine).get_table_names()
        # Learn: Assert that the number of items/characters in inspect(engine).get_check_constraints('runs')
        # equals 5. If false, this check fails with AssertionError.
        assert len(inspect(engine).get_check_constraints("runs")) == 5
        # Compare the migrated schema with ORM metadata to detect schema drift.
        # Learn: Call command.check with the arguments shown.
        command.check(config)
        # Exercise reversal only against this disposable test database.
        # Learn: Call command.downgrade with the arguments shown.
        command.downgrade(config, "base")
        # Learn: Assert that 'runs' is not in inspect(engine).get_table_names(). If false, this check fails
        # with AssertionError.
        assert "runs" not in inspect(engine).get_table_names()
    # Learn: Always run cleanup, whether the operation succeeds, returns, or raises.
    finally:
        # Learn: Call engine.dispose with no arguments.
        engine.dispose()
        # Learn: Clear cached configuration so this test reads its own environment on get_settings.
        get_settings.cache_clear()
