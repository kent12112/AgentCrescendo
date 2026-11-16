## The generated migration docstring comes from the supplied revision message.
"""${message}"""
## Import Alembic schema operations in the generated file.
from alembic import op
## Import SQLAlchemy types for the historical migration schema.
import sqlalchemy as sa
## Insert generated imports, or an empty string when no extra imports are needed.
${imports if imports else ""}

## Substitute the new revision identifier as a valid Python literal.
revision = ${repr(up_revision)}
## Substitute the parent revision so Alembic knows migration order.
down_revision = ${repr(down_revision)}
## Substitute optional branch labels as a valid Python literal.
branch_labels = ${repr(branch_labels)}
## Substitute optional revision dependencies as a valid Python literal.
depends_on = ${repr(depends_on)}


## Define the forward schema transition in the generated migration.
def upgrade():
## Insert generated upgrade operations, or pass for an empty transition.
    ${upgrades if upgrades else "pass"}


## Define the reverse schema transition in the generated migration.
def downgrade():
## Insert generated downgrade operations, or pass for an empty transition.
    ${downgrades if downgrades else "pass"}
