# Learn: From datetime, import datetime (represents timestamps).
from datetime import datetime
# Learn: From typing, import Literal (restricts a type annotation to explicit known values).
from typing import Literal
# Learn: From uuid, import UUID (parses/types UUID identifiers so malformed route IDs are rejected).
from uuid import UUID

# Learn: From pydantic, import BaseModel (defines Pydantic-validated request/response data); ConfigDict
# (configures Pydantic validation and attribute reading); Field (specifies validation constraints and
# defaults); field_validator (attaches custom normalization or validation to a schema field).
from pydantic import BaseModel, ConfigDict, Field, field_validator


# Learn: Define RunCreate inheriting BaseModel. Indented methods and attributes belong to this class.
class RunCreate(BaseModel):
    # Learn: Document this module, class, or function with a docstring; it is not an action or a model
    # instruction.
    """The incoming JSON contract. FastAPI validates it before calling the endpoint."""

    # Reject unknown keys instead of silently accepting fields such as permissions.
    # Strip whitespace before checking the goal's length, so spaces are not a task.
    # Learn: Set model_config to ConfigDict(extra='forbid', str_strip_whitespace=True).
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    # Learn: Set goal to Field(min_length=10, max_length=4000); the user task text. Set the Pydantic default
    # and validation limits for this field.
    goal: str = Field(min_length=10, max_length=4000)
    # ge/le mean greater-than-or-equal / less-than-or-equal. strict=True prevents
    # coercing values such as true or "3" into integers. These are saved settings;
    # runtime enforcement will be implemented when agents can execute.
    # Learn: Set max_workers to Field(default=3, ge=1, le=3, strict=True); the saved worker-count limit;
    # saving a draft does not launch workers. Set the Pydantic default and validation limits for this field.
    max_workers: int = Field(default=3, ge=1, le=3, strict=True)
    # Learn: Set timeout_seconds to Field(default=600, ge=30, le=600, strict=True). Set the Pydantic default
    # and validation limits for this field.
    timeout_seconds: int = Field(default=600, ge=30, le=600, strict=True)
    # Integer cents avoid floating-point rounding when representing money.
    # Learn: Set model_budget_cents to Field(default=100, ge=1, le=500, strict=True); the saved model budget
    # in integer US cents to avoid floating-point money. Set the Pydantic default and validation limits for
    # this field.
    model_budget_cents: int = Field(default=100, ge=1, le=500, strict=True)
    # Learn: Set constraints to Field(default=None, max_length=1000); optional user requirements; empty text
    # is normalized to None. Set the Pydantic default and validation limits for this field.
    constraints: str | None = Field(default=None, max_length=1000)
    # Learn: Register field validation/normalization to run during Pydantic model validation.
    @field_validator("constraints")
    # Learn: Bind the method to the class (cls), rather than an instance (self).
    @classmethod
    # Learn: Define validate_constraints(value). The body runs when called, not when defined.
    def validate_constraints(cls, value):
        # Learn: Return None (no value) when value equals '', otherwise value to the caller and stop this
        # function.
        return None if value == "" else value

# Learn: Define RunRead inheriting RunCreate. Indented methods and attributes belong to this class.
class RunRead(RunCreate):
    # Learn: Document this module, class, or function with a docstring; it is not an action or a model
    # instruction.
    """The outgoing contract: validated task fields plus database-generated fields."""

    # Read SQLAlchemy object attributes rather than requiring a plain dictionary.
    # Learn: Set model_config to ConfigDict(from_attributes=True).
    model_config = ConfigDict(from_attributes=True)

    # Learn: Declare id with type UUID.
    id: UUID
    # Learn: Declare status with type Literal['draft']; the draft or agent termination state returned to the
    # caller.
    status: Literal["draft"]
    # Learn: Declare created_at with type datetime; the row creation timestamp generated in UTC.
    created_at: datetime

