"""Paper, section, and retrieval-chunk models."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from pydantic import Field, field_validator, model_validator

from litagent.domain.common import CharSpan, NonEmptyText, TimestampedModel, require_prefix
from litagent.domain.enums import EvidenceType, ReviewStatus

Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
MAX_PUBLICATION_YEAR = datetime.now(UTC).year + 1


class Paper(TimestampedModel):
    paper_id: NonEmptyText
    title: NonEmptyText
    authors: list[NonEmptyText] = Field(default_factory=list)
    year: int | None = Field(default=None, ge=1400, le=MAX_PUBLICATION_YEAR)
    venue: str | None = None
    abstract: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    document_uri: NonEmptyText
    parse_uri: str | None = None
    sha256: Sha256
    parse_version: NonEmptyText = "unparsed"
    review_status: ReviewStatus = ReviewStatus.PENDING

    @field_validator("paper_id")
    @classmethod
    def validate_paper_id(cls, value: str) -> str:
        return require_prefix(value, "paper")

    @field_validator("authors")
    @classmethod
    def deduplicate_authors(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(values))


class Section(TimestampedModel):
    section_id: NonEmptyText
    paper_id: NonEmptyText
    title: NonEmptyText
    section_path: NonEmptyText
    order_index: int = Field(ge=0)
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)

    @field_validator("section_id")
    @classmethod
    def validate_section_id(cls, value: str) -> str:
        return require_prefix(value, "section")

    @field_validator("paper_id")
    @classmethod
    def validate_paper_id(cls, value: str) -> str:
        return require_prefix(value, "paper")

    @model_validator(mode="after")
    def validate_pages(self) -> Section:
        if self.page_end < self.page_start:
            raise ValueError("page_end cannot be earlier than page_start")
        return self


class Chunk(TimestampedModel):
    chunk_id: NonEmptyText
    paper_id: NonEmptyText
    section_id: str | None = None
    section_path: str | None = None
    order_index: int = Field(ge=0)
    chunk_type: EvidenceType = EvidenceType.TEXT
    content: NonEmptyText
    content_hash: Sha256
    token_count: int = Field(ge=1)
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    char_span: CharSpan | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("chunk_id")
    @classmethod
    def validate_chunk_id(cls, value: str) -> str:
        return require_prefix(value, "chunk")

    @field_validator("paper_id")
    @classmethod
    def validate_paper_id(cls, value: str) -> str:
        return require_prefix(value, "paper")

    @field_validator("section_id")
    @classmethod
    def validate_section_id(cls, value: str | None) -> str | None:
        return require_prefix(value, "section") if value else value

    @model_validator(mode="after")
    def validate_pages(self) -> Chunk:
        if self.page_end < self.page_start:
            raise ValueError("page_end cannot be earlier than page_start")
        return self
