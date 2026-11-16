# Import from datetime: datetime (represents timestamps); timezone (provides an explicit UTC
# timezone).
from datetime import datetime, timezone
# Import from uuid: uuid4 (generates independent random UUID identifiers).
from uuid import uuid4

# Import from sqlalchemy: CheckConstraint (adds a condition the database enforces on stored rows);
# DateTime (declares a timestamp column, optionally with timezone support); Integer (declares an
# integer column for exact counts and cents); String (declares bounded-length textual column data);
# Text (declares variable-length text column data).
from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text
# Import from sqlalchemy.orm: DeclarativeBase (collects ORM mappings and table metadata); Mapped
# (marks a typed SQLAlchemy-mapped attribute); mapped_column (defines a mapped database column and
# its options).
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# Define Base as a subclass of DeclarativeBase.
class Base(DeclarativeBase):
    # SQLAlchemy collects table definitions here; Alembic compares this metadata
    # with the database when checking for missing migrations.
    pass


# Define Run as a subclass of Base.
class Run(Base):
    """An ORM mapping: Python attributes correspond to columns in the runs table."""

    # Set __tablename__ to 'runs'.
    __tablename__ = "runs"
    # A second boundary: these checks run inside the database, including when
    # writes bypass our HTTP request schema. They do not execute agent limits.
    # Build __table_args__ from the entries below.
    __table_args__ = (
        # Require the database to reject rows that violate this SQL condition; inputs: 'max_workers
        # BETWEEN 1 AND 3'.
        CheckConstraint("max_workers BETWEEN 1 AND 3"),
        # Require the database to reject rows that violate this SQL condition; inputs:
        # 'timeout_seconds BETWEEN 30 AND 600'.
        CheckConstraint("timeout_seconds BETWEEN 30 AND 600"),
        # Require the database to reject rows that violate this SQL condition; inputs:
        # 'model_budget_cents BETWEEN 1 AND 500'.
        CheckConstraint("model_budget_cents BETWEEN 1 AND 500"),
        # Require the database to reject rows that violate this SQL condition; inputs: "status =
        # 'draft'".
        CheckConstraint("status = 'draft'"),
        # Require the database to reject rows that violate this SQL condition; inputs:
        # 'length(constraints) <= 1000'.
        CheckConstraint("length(constraints) <= 1000"),
    )

    # The primary key identifies a row. A UUID avoids needing a central ID counter.
    # default receives a callable so each new row gets a fresh ID at insertion.
    # Map id to a database column; String(36) with primary_key=True, default=lambda : str(uuid4()).
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    # Map goal to a database column; Text.
    goal: Mapped[str] = mapped_column(Text)
    # Map status to a database column; String(20) with default='draft'.
    status: Mapped[str] = mapped_column(String(20), default="draft")
    # Map max_workers to a database column; Integer.
    max_workers: Mapped[int] = mapped_column(Integer)
    # Map timeout_seconds to a database column; Integer.
    timeout_seconds: Mapped[int] = mapped_column(Integer)
    # Map model_budget_cents to a database column; Integer.
    model_budget_cents: Mapped[int] = mapped_column(Integer)
    # Map constraints to a database column; Text with nullable=True.
    constraints: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Store an explicit UTC timestamp; PostgreSQL supports timezone-aware storage.
    # Map created_at to a database column; DateTime(timezone=True) with default=lambda :
    # datetime.now(timezone.utc).
    created_at: Mapped[datetime] = mapped_column(
        # Pass keyword default = lambda : datetime.now(timezone.utc).
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

