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
        # 0003: start-command columns exist and the status check is the new one.
        columns = {column["name"] for column in inspect(engine).get_columns("runs")}
        assert {"workflow_id", "start_requested_at"} <= columns
        checks = {check["sqltext"] for check in inspect(engine).get_check_constraints("runs")}
        assert "status IN ('draft', 'starting', 'started')" in checks
        assert "status = 'draft'" not in checks
        # 0004: job search tables exist; stepping back to 0003 removes only them.
        job_tables = {"job_companies", "job_postings", "job_crawl_runs"}
        assert job_tables <= set(inspect(engine).get_table_names())
        assert {"ix_job_postings_company", "ix_job_postings_published_at"} <= {
            index["name"] for index in inspect(engine).get_indexes("job_postings")}
        command.downgrade(config, "0003")
        assert not job_tables & set(inspect(engine).get_table_names())
        assert "workflow_id" in {column["name"] for column in inspect(engine).get_columns("runs")}
        # Step back to 0002: the old status check returns and the columns go.
        command.downgrade(config, "0002")
        checks = {check["sqltext"] for check in inspect(engine).get_check_constraints("runs")}
        assert "status = 'draft'" in checks and len(checks) == 5
        assert "workflow_id" not in {column["name"] for column in inspect(engine).get_columns("runs")}
        command.upgrade(config, "head")
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
