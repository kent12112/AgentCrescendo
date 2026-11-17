"""Job search storage (JOB-F07): companies, the last 30 days of postings, crawl runs."""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "job_companies",
        sa.Column("source", sa.String(20), primary_key=True),
        sa.Column("slug", sa.String(100), primary_key=True),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("open_postings", sa.Integer(), nullable=False),
        sa.CheckConstraint("status IN ('live', 'missing', 'error')", name="ck_job_companies_status"),
    )
    op.create_table(
        "job_postings",
        sa.Column("source", sa.String(20), primary_key=True),
        sa.Column("posting_id", sa.String(64), primary_key=True),
        sa.Column("company_slug", sa.String(100), nullable=False),
        sa.Column("company_name", sa.String(300), nullable=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("locations", sa.JSON(), nullable=False),
        sa.Column("countries", sa.JSON(), nullable=False),
        sa.Column("workplace", sa.String(20), nullable=True),
        sa.Column("department", sa.String(300), nullable=True),
        sa.Column("employment_type", sa.String(300), nullable=True),
        sa.Column("compensation", sa.String(300), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_job_postings_company", "job_postings", ["source", "company_slug"])
    op.create_index("ix_job_postings_published_at", "job_postings", ["published_at"])
    op.create_table(
        "job_crawl_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("companies", sa.Integer(), nullable=False),
        sa.Column("boards_failed", sa.Integer(), nullable=False),
        sa.Column("postings_seen", sa.Integer(), nullable=False),
        sa.Column("inserted", sa.Integer(), nullable=False),
        sa.Column("updated", sa.Integer(), nullable=False),
        sa.Column("closed", sa.Integer(), nullable=False),
        sa.Column("deleted", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.CheckConstraint("status IN ('running', 'ok', 'failed')", name="ck_job_crawl_runs_status"),
    )


def downgrade():
    op.drop_table("job_crawl_runs")
    op.drop_index("ix_job_postings_published_at", table_name="job_postings")
    op.drop_index("ix_job_postings_company", table_name="job_postings")
    op.drop_table("job_postings")
    op.drop_table("job_companies")
