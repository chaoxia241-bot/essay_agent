"""Extraction-run and human-review records."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator, model_validator

from litagent.domain.common import DomainModel, NonEmptyText, TimestampedModel, require_prefix
from litagent.domain.enums import ExtractionStatus, ReviewStatus


class TokenUsage(DomainModel):
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_total(self) -> TokenUsage:
        expected = self.prompt_tokens + self.completion_tokens
        if self.total_tokens not in (0, expected):
            raise ValueError("total_tokens must equal prompt_tokens + completion_tokens")
        if self.total_tokens == 0:
            object.__setattr__(self, "total_tokens", expected)
        return self


class ExtractionRun(TimestampedModel):
    extraction_run_id: NonEmptyText
    paper_id: NonEmptyText
    model: NonEmptyText
    prompt_version: NonEmptyText
    status: ExtractionStatus = ExtractionStatus.PENDING
    input_hash: NonEmptyText
    output_refs: list[NonEmptyText] = Field(default_factory=list)
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    attempt: int = Field(default=1, ge=1)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None

    @field_validator("extraction_run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        return require_prefix(value, "run")

    @field_validator("paper_id")
    @classmethod
    def validate_paper_id(cls, value: str) -> str:
        return require_prefix(value, "paper")

    @model_validator(mode="after")
    def validate_lifecycle(self) -> ExtractionRun:
        if self.finished_at and not self.started_at:
            raise ValueError("finished_at requires started_at")
        if self.started_at and self.finished_at and self.finished_at < self.started_at:
            raise ValueError("finished_at cannot be earlier than started_at")
        if self.status == ExtractionStatus.FAILED and not self.error:
            raise ValueError("failed extraction requires an error")
        return self


class ReviewItem(TimestampedModel):
    review_item_id: NonEmptyText
    object_type: NonEmptyText
    object_id: NonEmptyText
    reason: NonEmptyText
    status: ReviewStatus = ReviewStatus.PENDING
    reviewer: str | None = None
    reviewed_at: datetime | None = None
    notes: str | None = None

    @field_validator("review_item_id")
    @classmethod
    def validate_review_id(cls, value: str) -> str:
        return require_prefix(value, "review")

    @model_validator(mode="after")
    def validate_decision(self) -> ReviewItem:
        decided = self.status in (ReviewStatus.APPROVED, ReviewStatus.REJECTED)
        if decided and (not self.reviewer or not self.reviewed_at):
            raise ValueError("approved/rejected review requires reviewer and reviewed_at")
        return self
