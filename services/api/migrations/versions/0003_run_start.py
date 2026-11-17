"""Allow runs to be started: start-command columns and new status values."""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

NEW_STATUS_CHECK = "status IN ('draft', 'starting', 'started')"
OLD_STATUS_CHECK = "status = 'draft'"


def _limit_checks():
    # Unnamed checks from 0001 that SQLite's table rebuild would otherwise drop
    # (see 0002). Named checks (ck_runs_constraints_length) survive the rebuild,
    # so restating them would duplicate them. PostgreSQL alters in place.
    return (
        sa.CheckConstraint("max_workers BETWEEN 1 AND 3"),
        sa.CheckConstraint("timeout_seconds BETWEEN 30 AND 600"),
        sa.CheckConstraint("model_budget_cents BETWEEN 1 AND 500"),
    )


def _is_sqlite():
    return op.get_bind().dialect.name == "sqlite"


def _batch(status_check, status_check_name):
    # SQLite cannot ALTER constraints, so batch mode rebuilds the table with
    # exactly these table_args (plus surviving named constraints). PostgreSQL
    # ignores table_args and alters in place (recreate="never").
    sqlite = _is_sqlite()
    table_args = _limit_checks() + (sa.CheckConstraint(status_check, name=status_check_name),) if sqlite else ()
    return op.batch_alter_table("runs", table_args=table_args, recreate="always" if sqlite else "never")


def _unnamed_status_check_name():
    # 0001 left the status check unnamed and PostgreSQL generated a name for it;
    # look it up instead of assuming "runs_status_check". PostgreSQL rewrites the
    # text (e.g. "(status)::text = 'draft'::text"), so match on the column name.
    for check in sa.inspect(op.get_bind()).get_check_constraints("runs"):
        if "status" in check["sqltext"] and check["name"] != "ck_runs_status":
            return check["name"]
    return None


def upgrade():
    old_name = None if _is_sqlite() else _unnamed_status_check_name()
    with _batch(NEW_STATUS_CHECK, "ck_runs_status") as batch:
        batch.add_column(sa.Column("workflow_id", sa.String(64), nullable=True))
        batch.add_column(sa.Column("start_requested_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_unique_constraint("uq_runs_workflow_id", ["workflow_id"])
        if not _is_sqlite():
            # On SQLite the rebuild already dropped the unnamed old check.
            if old_name:
                batch.drop_constraint(old_name, type_="check")
            batch.create_check_constraint("ck_runs_status", NEW_STATUS_CHECK)


def downgrade():
    # Fails (by design) while any run is not a draft: the old check rejects them.
    with _batch(OLD_STATUS_CHECK, "runs_status_check") as batch:
        # Named, so it survives a SQLite rebuild: drop it explicitly on both.
        batch.drop_constraint("ck_runs_status", type_="check")
        batch.drop_constraint("uq_runs_workflow_id", type_="unique")
        batch.drop_column("start_requested_at")
        batch.drop_column("workflow_id")
        if not _is_sqlite():
            batch.create_check_constraint("runs_status_check", OLD_STATUS_CHECK)
