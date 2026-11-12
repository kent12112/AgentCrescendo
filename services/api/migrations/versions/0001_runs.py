"""Create constrained draft runs."""
from alembic import op
import sqlalchemy as sa

# Alembic stores the applied revision in its version table. No parent means this
# is the first migration. Future model changes need a new migration file.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Snapshot the schema at this revision; do not import the evolving ORM model.
    op.create_table(
        "runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("max_workers", sa.Integer(), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("model_budget_cents", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("max_workers BETWEEN 1 AND 3"),
        sa.CheckConstraint("timeout_seconds BETWEEN 30 AND 600"),
        sa.CheckConstraint("model_budget_cents BETWEEN 1 AND 500"),
        sa.CheckConstraint("status = 'draft'"),
    )


def downgrade():
    # Reverting this migration deletes the table AND its rows. Use with care.
    op.drop_table("runs")

