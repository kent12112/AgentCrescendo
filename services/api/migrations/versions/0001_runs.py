"""Create constrained draft runs."""
# Import from alembic: op (Alembic operations that change the schema during explicit
# upgrades/downgrades).
from alembic import op
# Import sqlalchemy as sa: defines and accesses relational database tables.
import sqlalchemy as sa

# Alembic stores the applied revision in its version table. No parent means this
# is the first migration. Future model changes need a new migration file.
# Set revision to '0001'.
revision = "0001"
# Set down_revision to None.
down_revision = None
# Set branch_labels to None.
branch_labels = None
# Set depends_on to None.
depends_on = None


# Define upgrade with no parameters.
def upgrade():
    # Snapshot the schema at this revision; do not import the evolving ORM model.
    # Call op.create_table with 'runs', sa.Column('id', sa.String(36), primary_key=True),
    # sa.Column('goal', sa.Text(), nullable=False), sa.Column('status', sa.String(20),
    # nullable=False), sa.Column('max_workers', sa.Integer(), nullable=False),
    # sa.Column('timeout_seconds', sa.Integer(), nullable=False), sa.Column('model_budget_cents',
    # sa.Integer(), nullable=False), sa.Column('created_at', sa.DateTime(timezone=True),
    # nullable=False), sa.CheckConstraint('max_workers BETWEEN 1 AND 3'),
    # sa.CheckConstraint('timeout_seconds BETWEEN 30 AND 600'),
    # sa.CheckConstraint('model_budget_cents BETWEEN 1 AND 500'), sa.CheckConstraint("status =
    # 'draft'").
    op.create_table(
        "runs",
        # Pass keyword primary_key = True.
        sa.Column("id", sa.String(36), primary_key=True),
        # Pass keyword nullable = False.
        sa.Column("goal", sa.Text(), nullable=False),
        # Pass keyword nullable = False.
        sa.Column("status", sa.String(20), nullable=False),
        # Pass keyword nullable = False.
        sa.Column("max_workers", sa.Integer(), nullable=False),
        # Pass keyword nullable = False.
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        # Pass keyword nullable = False.
        sa.Column("model_budget_cents", sa.Integer(), nullable=False),
        # Pass keyword nullable = False.
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
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


# Define downgrade with no parameters.
def downgrade():
    # Reverting this migration deletes the table AND its rows. Use with care.
    # Call op.drop_table with 'runs'.
    op.drop_table("runs")

