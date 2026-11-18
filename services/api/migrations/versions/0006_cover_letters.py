"""Consented letter input snapshots and saved drafts (no dependency on live postings)."""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("letter_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("input_digest", sa.String(64), nullable=False),
        sa.Column("inputs", sa.JSON(), nullable=False),
        sa.Column("identity", sa.JSON(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("cover_letters",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("posting", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("checks", sa.JSON(), nullable=False),
        sa.Column("error", sa.String(300), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'generating', 'failed', 'draft', 'approved')",
                           name="ck_cover_letters_status"))
    op.create_index("ix_cover_letters_session_id", "cover_letters", ["session_id"])


def downgrade():
    op.drop_table("cover_letters")
    op.drop_table("letter_sessions")
