# Import from datetime: datetime (represents timestamps); timezone (provides an explicit UTC
# timezone).
from datetime import datetime, timezone
# Import from uuid: uuid4 (generates independent random UUID identifiers).
from uuid import uuid4

# Import from sqlalchemy: CheckConstraint (adds a condition the database enforces on stored rows);
# DateTime (declares a timestamp column, optionally with timezone support); Integer (declares an
# integer column for exact counts and cents); String (declares bounded-length textual column data);
# Text (declares variable-length text column data).
from sqlalchemy import JSON, CheckConstraint, DateTime, Index, Integer, String, Text, UniqueConstraint
# Import from sqlalchemy.orm: DeclarativeBase (collects ORM mappings and table metadata); Mapped
# (marks a typed SQLAlchemy-mapped attribute); mapped_column (defines a mapped database column and
# its options).
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# Lifecycle states stored so far. W2-F01 adds only the start handshake:
# draft -> starting (start command persisted) -> started (Temporal accepted it).
# Execution progress itself lives in Temporal until W2-F03 persists run state.
RUN_STATUSES = ("draft", "starting", "started")
# SQL text for the status check, shared with migration 0003.
RUN_STATUS_CHECK = "status IN ('draft', 'starting', 'started')"


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
        # Only the known lifecycle states; named so later migrations can find it.
        CheckConstraint(RUN_STATUS_CHECK, name="ck_runs_status"),
        # Require the database to reject rows that violate this SQL condition; inputs:
        # 'length(constraints) <= 1000'.
        CheckConstraint("length(constraints) <= 1000"),
        # One run maps to one workflow ID and no two runs may share one.
        UniqueConstraint("workflow_id", name="uq_runs_workflow_id"),
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
    # The persisted start command: the stable workflow ID chosen when the run left
    # draft. Storing it means a retry or a reconciler reuses exactly this ID even
    # if the derivation rule changes later. NULL while the run is a draft.
    workflow_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # When the start was first requested (UTC); used to find stuck starts.
    start_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# --- Job search storage (JOB-F07) -------------------------------------------------
# The daily Ashby crawl (scripts/crawl_jobs_daily.py) keeps the last 30 days of public
# job postings here so a search reads Postgres instead of refetching ~3,000 boards.
# Everything below is public job-board data; no resume text is ever stored.

JOB_COMPANY_STATUS_CHECK = "status IN ('live', 'missing', 'error')"
JOB_CRAWL_STATUS_CHECK = "status IN ('running', 'ok', 'failed')"


class JobCompany(Base):
    """One company board found by discovery, with the result of its latest check."""

    __tablename__ = "job_companies"
    __table_args__ = (CheckConstraint(JOB_COMPANY_STATUS_CHECK, name="ck_job_companies_status"),)

    # (source, slug) is the board's identity, e.g. ("ashby", "openai").
    source: Mapped[str] = mapped_column(String(20), primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), primary_key=True)
    # live = the board answered; missing = HTTP 404 (company left the ATS);
    # error = a temporary failure (timeout, 5xx); its postings are left untouched.
    status: Mapped[str] = mapped_column(String(10))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Open postings inside the 30-day window after the latest check.
    open_postings: Mapped[int] = mapped_column(Integer, default=0)


class JobPosting(Base):
    """One posting seen on a live board. Text fields are untrusted page data."""

    __tablename__ = "job_postings"
    __table_args__ = (
        Index("ix_job_postings_company", "source", "company_slug"),
        Index("ix_job_postings_published_at", "published_at"),
    )

    source: Mapped[str] = mapped_column(String(20), primary_key=True)
    posting_id: Mapped[str] = mapped_column(String(64), primary_key=True)  # checked UUID / digits
    company_slug: Mapped[str] = mapped_column(String(100))
    company_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    title: Mapped[str] = mapped_column(String(300))
    url: Mapped[str] = mapped_column(String(500))  # rebuilt from slug + ID, never copied from a response
    locations: Mapped[list] = mapped_column(JSON, default=list)
    countries: Mapped[list] = mapped_column(JSON, default=list)
    workplace: Mapped[str | None] = mapped_column(String(20), nullable=True)
    department: Mapped[str | None] = mapped_column(String(300), nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(300), nullable=True)
    compensation: Mapped[str | None] = mapped_column(String(300), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # History the file cache could not keep: when we first and last saw the posting,
    # and when it disappeared from a board that still answered (NULL while open).
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class JobCrawlRun(Base):
    """One daily crawl: evidence that it ran and what it changed."""

    __tablename__ = "job_crawl_runs"
    __table_args__ = (CheckConstraint(JOB_CRAWL_STATUS_CHECK, name="ck_job_crawl_runs_status"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(10), default="running")
    companies: Mapped[int] = mapped_column(Integer, default=0)
    boards_failed: Mapped[int] = mapped_column(Integer, default=0)
    postings_seen: Mapped[int] = mapped_column(Integer, default=0)
    inserted: Mapped[int] = mapped_column(Integer, default=0)
    updated: Mapped[int] = mapped_column(Integer, default=0)
    closed: Mapped[int] = mapped_column(Integer, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
