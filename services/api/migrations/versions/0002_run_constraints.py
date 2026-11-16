"""Add optional user constraints to runs."""
# Import from alembic: op (Alembic operations that change the schema during explicit
# upgrades/downgrades).
from alembic import op
# Import sqlalchemy as sa: defines and accesses relational database tables.
import sqlalchemy as sa

# Set revision to '0002'.
revision = "0002"
# Set down_revision to '0001'.
down_revision = "0001"  # this migration runs after 0001
# Set branch_labels to None.
branch_labels = None
# Set depends_on to None.
depends_on = None


# Define _existing_checks with no parameters.
def _existing_checks():
    # SQLite batch mode rebuilds the table and silently drops the unnamed CHECK
    # constraints from 0001, so restate them. PostgreSQL alters in place and
    # ignores table_args. Lesson: name constraints so they can be reflected.
    return (
        # Require the database to reject rows that violate this SQL condition on sa; inputs:
        # 'max_workers BETWEEN 1 AND 3'.
        sa.CheckConstraint("max_workers BETWEEN 1 AND 3"),
        # Require the database to reject rows that violate this SQL condition on sa; inputs:
        # 'timeout_seconds BETWEEN 30 AND 600'.
        sa.CheckConstraint("timeout_seconds BETWEEN 30 AND 600"),
        # Require the database to reject rows that violate this SQL condition on sa; inputs:
        # 'model_budget_cents BETWEEN 1 AND 500'.
        sa.CheckConstraint("model_budget_cents BETWEEN 1 AND 500"),
        # Require the database to reject rows that violate this SQL condition on sa; inputs: "status
        # = 'draft'".
        sa.CheckConstraint("status = 'draft'"),
    )


# Define upgrade with no parameters.
def upgrade():
    # SQLite cannot add a CHECK constraint to an existing table with ALTER TABLE.
    # batch_alter_table rebuilds the table on SQLite and uses plain ALTER on PostgreSQL.
    # Use op.batch_alter_table('runs', table_args=_existing_checks()) as batch; leave the context
    # and run its cleanup when this block ends.
    with op.batch_alter_table("runs", table_args=_existing_checks()) as batch:
        # Nullable with no default: existing drafts get NULL, meaning "no constraints".
        # Call batch.add_column with sa.Column('constraints', sa.Text(), nullable=True).
        batch.add_column(sa.Column("constraints", sa.Text(), nullable=True))
        # Call batch.create_check_constraint with 'ck_runs_constraints_length', 'length(constraints)
        # <= 1000'.
        batch.create_check_constraint("ck_runs_constraints_length", "length(constraints) <= 1000")


# Define downgrade with no parameters.
def downgrade():
    # Dropping the column deletes any saved constraints text.
    # Use op.batch_alter_table('runs', table_args=_existing_checks()) as batch; leave the context
    # and run its cleanup when this block ends.
    with op.batch_alter_table("runs", table_args=_existing_checks()) as batch:
        # Call batch.drop_constraint with 'ck_runs_constraints_length'.
        batch.drop_constraint("ck_runs_constraints_length", type_="check")
        # Call batch.drop_column with 'constraints'.
        batch.drop_column("constraints")
