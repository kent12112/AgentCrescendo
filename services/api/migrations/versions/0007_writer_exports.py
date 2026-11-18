"""Approved-version desktop exports and verified PDFs."""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("writer_exports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("letter_id", sa.String(36), nullable=False),
        sa.Column("letter_version", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("characters_typed", sa.Integer(), nullable=False),
        sa.Column("pdf", sa.LargeBinary(), nullable=True),
        sa.Column("error", sa.String(300), nullable=True),
        sa.Column("cleanup_confirmed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("letter_id", "letter_version", name="uq_writer_export_version"),
        sa.ForeignKeyConstraint(["letter_id"], ["cover_letters.id"], ondelete="CASCADE", name="fk_writer_export_letter"),
        sa.CheckConstraint("status IN ('starting', 'preparing', 'waiting_viewer', 'typing', 'exporting', 'cancelling', 'saved', 'failed', 'cancelled')", name="ck_writer_export_status"))
    op.create_index("ix_writer_exports_letter_id", "writer_exports", ["letter_id"])


def downgrade():
    op.drop_table("writer_exports")
