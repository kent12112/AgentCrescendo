from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    # SQLAlchemy collects table definitions here; Alembic compares this metadata
    # with the database when checking for missing migrations.
    pass


class Run(Base):
    """An ORM mapping: Python attributes correspond to columns in the runs table."""

    __tablename__ = "runs"
    # A second boundary: these checks run inside the database, including when
    # writes bypass our HTTP request schema. They do not execute agent limits.
    __table_args__ = (
        CheckConstraint("max_workers BETWEEN 1 AND 3"),
        CheckConstraint("timeout_seconds BETWEEN 30 AND 600"),
        CheckConstraint("model_budget_cents BETWEEN 1 AND 500"),
        CheckConstraint("status = 'draft'"),
    )

    # The primary key identifies a row. A UUID avoids needing a central ID counter.
    # default receives a callable so each new row gets a fresh ID at insertion.
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    goal: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    max_workers: Mapped[int] = mapped_column(Integer)
    timeout_seconds: Mapped[int] = mapped_column(Integer)
    model_budget_cents: Mapped[int] = mapped_column(Integer)
    # Store an explicit UTC timestamp; PostgreSQL supports timezone-aware storage.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

