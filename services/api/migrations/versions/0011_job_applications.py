"""Keep manual application history after a posting expires."""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "job_applications",
        sa.Column("source", sa.String(20), primary_key=True),
        sa.Column("posting_id", sa.String(64), primary_key=True),
        sa.Column("posting", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("applied_on", sa.Date(), nullable=True),
        sa.Column("follow_up_on", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('ready', 'applied', 'interviewing', 'offer', 'rejected', 'withdrawn')",
                           name="ck_job_applications_status"),
    )


def downgrade():
    op.drop_table("job_applications")
