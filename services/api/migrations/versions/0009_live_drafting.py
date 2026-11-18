"""Distinguish live draft previews from approved PDF exports."""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

OLD = "status IN ('starting', 'preparing', 'waiting_viewer', 'typing', 'exporting', 'cancelling', 'saved', 'failed', 'cancelled')"
NEW = "status IN ('starting', 'preparing', 'waiting_viewer', 'drafting', 'typing', 'exporting', 'cancelling', 'saved', 'failed', 'cancelled')"


def upgrade():
    with op.batch_alter_table("writer_exports") as batch:
        batch.add_column(sa.Column("purpose", sa.String(10), nullable=False, server_default="export"))
        batch.drop_constraint("ck_writer_export_status", type_="check")
        batch.create_check_constraint("ck_writer_export_status", NEW)


def downgrade():
    op.execute("UPDATE writer_exports SET status = 'failed' WHERE status = 'drafting'")
    with op.batch_alter_table("writer_exports") as batch:
        batch.drop_constraint("ck_writer_export_status", type_="check")
        batch.create_check_constraint("ck_writer_export_status", OLD)
        batch.drop_column("purpose")
