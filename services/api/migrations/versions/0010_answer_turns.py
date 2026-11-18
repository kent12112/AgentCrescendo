"""Save the Thinker/Worker/Verifier trace for each drafted answer."""
from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("cover_letters") as batch:
        batch.add_column(sa.Column("turns", sa.JSON(), nullable=False, server_default="[]"))


def downgrade():
    with op.batch_alter_table("cover_letters") as batch:
        batch.drop_column("turns")
