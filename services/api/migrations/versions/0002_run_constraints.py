"""Add optional user constraints to runs."""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"  # this migration runs after 0001
branch_labels = None
depends_on = None


def _existing_checks():
    # SQLite batch mode rebuilds the table and silently drops the unnamed CHECK
    # constraints from 0001, so restate them. PostgreSQL alters in place and
    # ignores table_args. Lesson: name constraints so they can be reflected.
    return (
        sa.CheckConstraint("max_workers BETWEEN 1 AND 3"),
        sa.CheckConstraint("timeout_seconds BETWEEN 30 AND 600"),
        sa.CheckConstraint("model_budget_cents BETWEEN 1 AND 500"),
        sa.CheckConstraint("status = 'draft'"),
    )


def upgrade():
    # SQLite cannot add a CHECK constraint to an existing table with ALTER TABLE.
    # batch_alter_table rebuilds the table on SQLite and uses plain ALTER on PostgreSQL.
    with op.batch_alter_table("runs", table_args=_existing_checks()) as batch:
        # Nullable with no default: existing drafts get NULL, meaning "no constraints".
        batch.add_column(sa.Column("constraints", sa.Text(), nullable=True))
        batch.create_check_constraint("ck_runs_constraints_length", "length(constraints) <= 1000")


def downgrade():
    # Dropping the column deletes any saved constraints text.
    with op.batch_alter_table("runs", table_args=_existing_checks()) as batch:
        batch.drop_constraint("ck_runs_constraints_length", type_="check")
        batch.drop_column("constraints")
