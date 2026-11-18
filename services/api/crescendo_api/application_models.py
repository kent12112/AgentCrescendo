"""Manual application history, independent of the crawl's expiring postings."""
from datetime import date, datetime, timezone

from sqlalchemy import JSON, CheckConstraint, Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base

APPLICATION_STATUSES = ("ready", "applied", "interviewing", "offer", "rejected", "withdrawn")
STATUS_CHECK = "status IN ('ready', 'applied', 'interviewing', 'offer', 'rejected', 'withdrawn')"


class JobApplication(Base):
    __tablename__ = "job_applications"
    __table_args__ = (CheckConstraint(STATUS_CHECK, name="ck_job_applications_status"),)

    source: Mapped[str] = mapped_column(String(20), primary_key=True)
    posting_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    # No posting FK: a daily crawl can delete the original without deleting history.
    posting: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="applied")
    applied_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    follow_up_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
