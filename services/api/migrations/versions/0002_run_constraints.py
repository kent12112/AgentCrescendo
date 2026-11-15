# Learn: Document this module, class, or function with a docstring; it is not an action or a model
# instruction.
"""Add optional user constraints to runs."""
# Learn: From alembic, import op (Alembic operations that change the schema during explicit
# upgrades/downgrades).
from alembic import op
# Learn: Import sqlalchemy as sa: defines and accesses relational database tables.
import sqlalchemy as sa

# Learn: Set revision to '0002'; this migration identifier stored by Alembic.
revision = "0002"
# Learn: Set down_revision to '0001'; the preceding migration identifier; None means the first migration.
down_revision = "0001"  # this migration runs after 0001
# Learn: Set branch_labels to None (no value); optional Alembic branch metadata.
branch_labels = None
# Learn: Set depends_on to None (no value); optional dependencies on other Alembic revisions.
depends_on = None


# Learn: Define _existing_checks(). The body runs when called, not when defined.
def _existing_checks():
    # SQLite batch mode rebuilds the table and silently drops the unnamed CHECK
    # constraints from 0001, so restate them. PostgreSQL alters in place and
    # ignores table_args. Lesson: name constraints so they can be reflected.
    # Learn: Return the tuple (sa.CheckConstraint('max_workers BETWEEN 1 AND 3'),
    # sa.CheckConstraint('timeout_seconds BETWEEN 30 AND 600'), sa.CheckConstraint('mo... (positional
    # values) to the caller and stop this function.
    return (
        # Learn: Require the database to reject rows that violate this SQL condition on sa; inputs:
        # 'max_workers BETWEEN 1 AND 3'.
        sa.CheckConstraint("max_workers BETWEEN 1 AND 3"),
        # Learn: Require the database to reject rows that violate this SQL condition on sa; inputs:
        # 'timeout_seconds BETWEEN 30 AND 600'.
        sa.CheckConstraint("timeout_seconds BETWEEN 30 AND 600"),
        # Learn: Require the database to reject rows that violate this SQL condition on sa; inputs:
        # 'model_budget_cents BETWEEN 1 AND 500'.
        sa.CheckConstraint("model_budget_cents BETWEEN 1 AND 500"),
        # Learn: Require the database to reject rows that violate this SQL condition on sa; inputs: "status
        # = 'draft'".
        sa.CheckConstraint("status = 'draft'"),
    # Learn: Close this tuple literal; delimiters group the values into one object.
    )


# Learn: Define upgrade(). The body runs when called, not when defined.
def upgrade():
    # SQLite cannot add a CHECK constraint to an existing table with ALTER TABLE.
    # batch_alter_table rebuilds the table on SQLite and uses plain ALTER on PostgreSQL.
    # Learn: Enter op.batch_alter_table('runs', table_args=_existing_checks()) as batch. The context manager
    # controls setup/exit; inspect it for the actual cleanup behavior.
    with op.batch_alter_table("runs", table_args=_existing_checks()) as batch:
        # Nullable with no default: existing drafts get NULL, meaning "no constraints".
        # Learn: Call batch.add_column with the arguments shown.
        batch.add_column(sa.Column("constraints", sa.Text(), nullable=True))
        # Learn: Add the named database CHECK constraint on batch; inputs: 'ck_runs_constraints_length',
        # 'length(constraints) <= 1000'.
        batch.create_check_constraint("ck_runs_constraints_length", "length(constraints) <= 1000")


# Learn: Define downgrade(). The body runs when called, not when defined.
def downgrade():
    # Dropping the column deletes any saved constraints text.
    # Learn: Enter op.batch_alter_table('runs', table_args=_existing_checks()) as batch. The context manager
    # controls setup/exit; inspect it for the actual cleanup behavior.
    with op.batch_alter_table("runs", table_args=_existing_checks()) as batch:
        # Learn: Remove the named constraint as part of reversing the migration on batch; inputs:
        # 'ck_runs_constraints_length'.
        batch.drop_constraint("ck_runs_constraints_length", type_="check")
        # Learn: Remove this column and its stored values during downgrade on batch; inputs: 'constraints'.
        batch.drop_column("constraints")
