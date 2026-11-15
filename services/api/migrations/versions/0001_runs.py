# Learn: Document this module, class, or function with a docstring; it is not an action or a model
# instruction.
"""Create constrained draft runs."""
# Learn: From alembic, import op (Alembic operations that change the schema during explicit
# upgrades/downgrades).
from alembic import op
# Learn: Import sqlalchemy as sa: defines and accesses relational database tables.
import sqlalchemy as sa

# Alembic stores the applied revision in its version table. No parent means this
# is the first migration. Future model changes need a new migration file.
# Learn: Set revision to '0001'; this migration identifier stored by Alembic.
revision = "0001"
# Learn: Set down_revision to None (no value); the preceding migration identifier; None means the first
# migration.
down_revision = None
# Learn: Set branch_labels to None (no value); optional Alembic branch metadata.
branch_labels = None
# Learn: Set depends_on to None (no value); optional dependencies on other Alembic revisions.
depends_on = None


# Learn: Define upgrade(). The body runs when called, not when defined.
def upgrade():
    # Snapshot the schema at this revision; do not import the evolving ORM model.
    # Learn: Create the historical table schema for this migration revision on op; inputs: 'runs',
    # sa.Column('id', sa.String(36), primary_key=True), sa.Column('goal', sa.Text(), nullable=False),
    # sa.Column('status', sa.String(20), nullable=False), s....
    op.create_table(
        # Learn: Supply literal text 'runs'; adjacent string literals are concatenated without adding
        # whitespace.
        "runs",
        # Learn: Pass keyword primary_key = True.
        sa.Column("id", sa.String(36), primary_key=True),
        # Learn: Pass keyword nullable = False.
        sa.Column("goal", sa.Text(), nullable=False),
        # Learn: Pass keyword nullable = False.
        sa.Column("status", sa.String(20), nullable=False),
        # Learn: Pass keyword nullable = False.
        sa.Column("max_workers", sa.Integer(), nullable=False),
        # Learn: Pass keyword nullable = False.
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        # Learn: Pass keyword nullable = False.
        sa.Column("model_budget_cents", sa.Integer(), nullable=False),
        # Learn: Pass keyword nullable = False.
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
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
    # Learn: Close the argument list for op.create_table; the grouped expression remains one call.
    )


# Learn: Define downgrade(). The body runs when called, not when defined.
def downgrade():
    # Reverting this migration deletes the table AND its rows. Use with care.
    # Learn: Drop the table and its rows when reversing this migration on op; inputs: 'runs'.
    op.drop_table("runs")

