## Learn: The generated migration docstring comes from the supplied revision message.
"""${message}"""
## Learn: Import Alembic schema operations in the generated file.
from alembic import op
## Learn: Import SQLAlchemy types for the historical migration schema.
import sqlalchemy as sa
## Learn: Insert generated imports, or an empty string when no extra imports are needed.
${imports if imports else ""}

## Learn: Substitute the new revision identifier as a valid Python literal.
revision = ${repr(up_revision)}
## Learn: Substitute the parent revision so Alembic knows migration order.
down_revision = ${repr(down_revision)}
## Learn: Substitute optional branch labels as a valid Python literal.
branch_labels = ${repr(branch_labels)}
## Learn: Substitute optional revision dependencies as a valid Python literal.
depends_on = ${repr(depends_on)}


## Learn: Define the forward schema transition in the generated migration.
def upgrade():
## Learn: Insert generated upgrade operations, or pass for an empty transition.
    ${upgrades if upgrades else "pass"}


## Learn: Define the reverse schema transition in the generated migration.
def downgrade():
## Learn: Insert generated downgrade operations, or pass for an empty transition.
    ${downgrades if downgrades else "pass"}
