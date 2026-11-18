"""Web job search (JOB-F08): the uploaded resume text and up to 3 picked postings."""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "job_resume",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("skills", sa.JSON(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_job_resume_single"),
    )
    op.create_table(
        "job_picks",
        sa.Column("source", sa.String(20), primary_key=True),
        sa.Column("posting_id", sa.String(64), primary_key=True),
        sa.Column("picked_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source", "posting_id"], ["job_postings.source", "job_postings.posting_id"],
                                name="fk_job_picks_posting", ondelete="CASCADE"),
    )


def downgrade():
    op.drop_table("job_picks")
    op.drop_table("job_resume")
