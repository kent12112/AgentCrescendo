# Learn: From datetime, import datetime (represents timestamps); timezone (provides an explicit UTC
# timezone).
from datetime import datetime, timezone
# Learn: From uuid, import uuid4 (generates independent random UUID identifiers).
from uuid import uuid4

# Learn: From sqlalchemy, import CheckConstraint (adds a condition the database enforces on stored rows);
# DateTime (declares a timestamp column, optionally with timezone support); Integer (declares an integer
# column for exact counts and cents); String (declares bounded-length textual column data); Text (declares
# variable-length text column data).
from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text
# Learn: From sqlalchemy.orm, import DeclarativeBase (collects ORM mappings and table metadata); Mapped
# (marks a typed SQLAlchemy-mapped attribute); mapped_column (defines a mapped database column and its
# options).
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# Learn: Define Base inheriting DeclarativeBase. Indented methods and attributes belong to this class.
class Base(DeclarativeBase):
    # SQLAlchemy collects table definitions here; Alembic compares this metadata
    # with the database when checking for missing migrations.
    # Learn: No operation: this body intentionally needs no executable statement.
    pass


# Learn: Define Run inheriting Base. Indented methods and attributes belong to this class.
class Run(Base):
    # Learn: Document this module, class, or function with a docstring; it is not an action or a model
    # instruction.
    """An ORM mapping: Python attributes correspond to columns in the runs table."""

    # Learn: Set __tablename__ to 'runs'.
    __tablename__ = "runs"
    # A second boundary: these checks run inside the database, including when
    # writes bypass our HTTP request schema. They do not execute agent limits.
    # Learn: Set __table_args__ to the tuple (CheckConstraint('max_workers BETWEEN 1 AND 3'),
    # CheckConstraint('timeout_seconds BETWEEN 30 AND 600'), CheckConstraint('model_budge... (positional
    # values).
    __table_args__ = (
        # Learn: Require the database to reject rows that violate this SQL condition; inputs: 'max_workers
        # BETWEEN 1 AND 3'.
        CheckConstraint("max_workers BETWEEN 1 AND 3"),
        # Learn: Require the database to reject rows that violate this SQL condition; inputs:
        # 'timeout_seconds BETWEEN 30 AND 600'.
        CheckConstraint("timeout_seconds BETWEEN 30 AND 600"),
        # Learn: Require the database to reject rows that violate this SQL condition; inputs:
        # 'model_budget_cents BETWEEN 1 AND 500'.
        CheckConstraint("model_budget_cents BETWEEN 1 AND 500"),
        # Learn: Require the database to reject rows that violate this SQL condition; inputs: "status =
        # 'draft'".
        CheckConstraint("status = 'draft'"),
        # Learn: Require the database to reject rows that violate this SQL condition; inputs:
        # 'length(constraints) <= 1000'.
        CheckConstraint("length(constraints) <= 1000"),
    # Learn: Close this tuple literal; delimiters group the values into one object.
    )

    # The primary key identifies a row. A UUID avoids needing a central ID counter.
    # default receives a callable so each new row gets a fresh ID at insertion.
    # Learn: Set id to mapped_column(String(36), primary_key=True, default=lambda : str(uuid4())). Define
    # the stored column type and constraints for this ORM attribute.
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    # Learn: Set goal to mapped_column(Text); the user task text. Define the stored column type and
    # constraints for this ORM attribute.
    goal: Mapped[str] = mapped_column(Text)
    # Learn: Set status to mapped_column(String(20), default='draft'); the draft or agent termination state
    # returned to the caller. Define the stored column type and constraints for this ORM attribute.
    status: Mapped[str] = mapped_column(String(20), default="draft")
    # Learn: Set max_workers to mapped_column(Integer); the saved worker-count limit; saving a draft does
    # not launch workers. Define the stored column type and constraints for this ORM attribute.
    max_workers: Mapped[int] = mapped_column(Integer)
    # Learn: Set timeout_seconds to mapped_column(Integer). Define the stored column type and constraints
    # for this ORM attribute.
    timeout_seconds: Mapped[int] = mapped_column(Integer)
    # Learn: Set model_budget_cents to mapped_column(Integer); the saved model budget in integer US cents to
    # avoid floating-point money. Define the stored column type and constraints for this ORM attribute.
    model_budget_cents: Mapped[int] = mapped_column(Integer)
    # Learn: Set constraints to mapped_column(Text, nullable=True); optional user requirements; empty text
    # is normalized to None. Define the stored column type and constraints for this ORM attribute.
    constraints: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Store an explicit UTC timestamp; PostgreSQL supports timezone-aware storage.
    # Learn: Set created_at to mapped_column(DateTime(timezone=True), default=lambda :
    # datetime.now(timezone.utc)); the row creation timestamp generated in UTC. Define the stored column
    # type and constraints for this ORM attribute.
    created_at: Mapped[datetime] = mapped_column(
        # Learn: Pass keyword default = lambda : datetime.now(timezone.utc).
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    # Learn: Close the argument list for mapped_column; the grouped expression remains one call.
    )

