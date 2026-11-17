# Import from datetime: datetime (represents timestamps).
from datetime import datetime
# Import from typing: Literal (restricts a type annotation to explicit known values).
from typing import Literal
# Import from uuid: UUID (parses/types UUID identifiers so malformed route IDs are rejected).
from uuid import UUID

# Import from pydantic: BaseModel (defines Pydantic-validated request/response data); ConfigDict
# (configures Pydantic validation and attribute reading); Field (specifies validation constraints
# and defaults); field_validator (attaches custom normalization or validation to a schema field).
from pydantic import BaseModel, ConfigDict, Field, field_validator


# Define RunCreate as a subclass of BaseModel.
class RunCreate(BaseModel):
    """The incoming JSON contract. FastAPI validates it before calling the endpoint."""

    # Reject unknown keys instead of silently accepting fields such as permissions.
    # Strip whitespace before checking the goal's length, so spaces are not a task.
    # Set model_config to ConfigDict(extra='forbid', str_strip_whitespace=True).
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    # Define goal with these defaults and validation rules: min_length=10, max_length=4000.
    goal: str = Field(min_length=10, max_length=4000)
    # ge/le mean greater-than-or-equal / less-than-or-equal. strict=True prevents
    # coercing values such as true or "3" into integers. These are saved settings;
    # runtime enforcement will be implemented when agents can execute.
    # Define max_workers with these defaults and validation rules: default=3, ge=1, le=3,
    # strict=True.
    max_workers: int = Field(default=3, ge=1, le=3, strict=True)
    # Define timeout_seconds with these defaults and validation rules: default=600, ge=30, le=600,
    # strict=True.
    timeout_seconds: int = Field(default=600, ge=30, le=600, strict=True)
    # Integer cents avoid floating-point rounding when representing money.
    # Define model_budget_cents with these defaults and validation rules: default=100, ge=1, le=500,
    # strict=True.
    model_budget_cents: int = Field(default=100, ge=1, le=500, strict=True)
    # Define constraints with these defaults and validation rules: default=None, max_length=1000.
    constraints: str | None = Field(default=None, max_length=1000)
    # Register field validation/normalization to run during Pydantic model validation.
    @field_validator("constraints")
    # Bind the method to the class (cls), rather than an instance (self).
    @classmethod
    # Define validate_constraints with parameters cls, value.
    def validate_constraints(cls, value):
        # Return None if value equals '', otherwise value.
        return None if value == "" else value

# Define RunRead as a subclass of RunCreate.
class RunRead(RunCreate):
    """The outgoing contract: validated task fields plus database-generated fields."""

    # Read SQLAlchemy object attributes rather than requiring a plain dictionary.
    # Set model_config to ConfigDict(from_attributes=True).
    model_config = ConfigDict(from_attributes=True)

    # Declare id with type UUID.
    id: UUID
    # Lifecycle state; keep in sync with models.RUN_STATUSES.
    status: Literal["draft", "starting", "started"]
    # Declare created_at with type datetime.
    created_at: datetime
    # Stable Temporal workflow ID; null until a start is requested.
    workflow_id: str | None = None
    # When the start was first requested; null for drafts.
    start_requested_at: datetime | None = None

