"""Safe operation/timing diagnostics for Writer exports; no source text in diagnostics."""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("writer_exports", sa.Column("diagnostics", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("writer_exports", "diagnostics")
