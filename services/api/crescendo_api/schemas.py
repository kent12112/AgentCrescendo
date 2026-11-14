from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RunCreate(BaseModel):
    """The incoming JSON contract. FastAPI validates it before calling the endpoint."""

    # Reject unknown keys instead of silently accepting fields such as permissions.
    # Strip whitespace before checking the goal's length, so spaces are not a task.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    goal: str = Field(min_length=10, max_length=4000)
    # ge/le mean greater-than-or-equal / less-than-or-equal. strict=True prevents
    # coercing values such as true or "3" into integers. These are saved settings;
    # runtime enforcement will be implemented when agents can execute.
    max_workers: int = Field(default=3, ge=1, le=3, strict=True)
    timeout_seconds: int = Field(default=600, ge=30, le=600, strict=True)
    # Integer cents avoid floating-point rounding when representing money.
    model_budget_cents: int = Field(default=100, ge=1, le=500, strict=True)
    constraints: str | None = Field(default=None, max_length=1000)
    @field_validator("constraints")
    @classmethod
    def validate_constraints(cls, value):
        return None if value == "" else value

class RunRead(RunCreate):
    """The outgoing contract: validated task fields plus database-generated fields."""

    # Read SQLAlchemy object attributes rather than requiring a plain dictionary.
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: Literal["draft"]
    created_at: datetime

