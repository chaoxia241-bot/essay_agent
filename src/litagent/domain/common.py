"""Shared types and validation rules for LitAgent domain objects."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from litagent.domain.enums import ReviewStatus

Confidence = Annotated[float, Field(ge=0.0, le=1.0)]
NonEmptyText = Annotated[str, Field(min_length=1)]


def utc_now() -> datetime:
    return datetime.now(UTC)


def require_prefix(value: str, prefix: str) -> str:
    if not value.startswith(f"{prefix}:") or len(value) <= len(prefix) + 1:
        raise ValueError(f"ID must start with '{prefix}:' and include a value")
    return value


class DomainModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class TimestampedModel(DomainModel):
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_timestamps(self) -> TimestampedModel:
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot be earlier than created_at")
        return self


class ExtractedModel(TimestampedModel):
    confidence: Confidence
    extraction_run_id: NonEmptyText
    review_status: ReviewStatus = ReviewStatus.PENDING

    @field_validator("extraction_run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        return require_prefix(value, "run")


class CharSpan(DomainModel):
    start: int = Field(ge=0)
    end: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_order(self) -> CharSpan:
        if self.end <= self.start:
            raise ValueError("char span end must be greater than start")
        return self


class BoundingBox(DomainModel):
    x0: float = Field(ge=0)
    y0: float = Field(ge=0)
    x1: float = Field(ge=0)
    y1: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_order(self) -> BoundingBox:
        if self.x1 <= self.x0 or self.y1 <= self.y0:
            raise ValueError("bbox must have positive width and height")
        return self
