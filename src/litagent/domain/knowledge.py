"""Evidence-grounded objects used by extraction and later KG phases."""

from __future__ import annotations

from decimal import Decimal

from pydantic import Field, field_validator, model_validator

from litagent.domain.common import (
    BoundingBox,
    CharSpan,
    ExtractedModel,
    NonEmptyText,
    require_prefix,
)
from litagent.domain.enums import (
    ClaimType,
    EvidenceType,
    EvidenceValidationStatus,
    SourceKind,
)


def _deduplicate(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


class Evidence(ExtractedModel):
    evidence_id: NonEmptyText
    paper_id: NonEmptyText
    evidence_type: EvidenceType
    page: int = Field(ge=1)
    section: str | None = None
    char_span: CharSpan | None = None
    bbox: BoundingBox | None = None
    chunk_id: NonEmptyText
    content: NonEmptyText
    source_uri: str | None = None
    validation_status: EvidenceValidationStatus = EvidenceValidationStatus.PENDING

    @field_validator("evidence_id")
    @classmethod
    def validate_evidence_id(cls, value: str) -> str:
        return require_prefix(value, "ev")

    @field_validator("paper_id")
    @classmethod
    def validate_paper_id(cls, value: str) -> str:
        return require_prefix(value, "paper")

    @field_validator("chunk_id")
    @classmethod
    def validate_chunk_id(cls, value: str) -> str:
        return require_prefix(value, "chunk")

    @model_validator(mode="after")
    def validate_locator(self) -> Evidence:
        if self.evidence_type == EvidenceType.TEXT and self.char_span is None:
            raise ValueError("text evidence requires char_span")
        if (
            self.evidence_type != EvidenceType.TEXT
            and self.bbox is None
            and not self.source_uri
        ):
            raise ValueError("table/figure evidence requires bbox or source_uri")
        return self


class Claim(ExtractedModel):
    claim_id: NonEmptyText
    paper_id: NonEmptyText
    statement: NonEmptyText
    claim_type: ClaimType
    evidence_ids: list[NonEmptyText] = Field(min_length=1)
    condition_ids: list[NonEmptyText] = Field(default_factory=list)

    @field_validator("claim_id")
    @classmethod
    def validate_claim_id(cls, value: str) -> str:
        return require_prefix(value, "claim")

    @field_validator("paper_id")
    @classmethod
    def validate_paper_id(cls, value: str) -> str:
        return require_prefix(value, "paper")

    @field_validator("evidence_ids")
    @classmethod
    def validate_evidence_ids(cls, values: list[str]) -> list[str]:
        return _deduplicate([require_prefix(value, "ev") for value in values])

    @field_validator("condition_ids")
    @classmethod
    def validate_condition_ids(cls, values: list[str]) -> list[str]:
        return _deduplicate([require_prefix(value, "condition") for value in values])


class KnowledgeObject(ExtractedModel):
    canonical_name: NonEmptyText
    aliases: list[NonEmptyText] = Field(default_factory=list)
    description: str | None = None

    @field_validator("aliases")
    @classmethod
    def normalize_aliases(cls, values: list[str]) -> list[str]:
        return _deduplicate(values)


class Method(KnowledgeObject):
    method_id: NonEmptyText

    @field_validator("method_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return require_prefix(value, "method")


class Dataset(KnowledgeObject):
    dataset_id: NonEmptyText
    modality: list[NonEmptyText] = Field(default_factory=list)
    scale: str | None = None

    @field_validator("dataset_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return require_prefix(value, "dataset")


class Task(KnowledgeObject):
    task_id: NonEmptyText

    @field_validator("task_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return require_prefix(value, "task")


class Metric(KnowledgeObject):
    metric_id: NonEmptyText

    @field_validator("metric_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return require_prefix(value, "metric")


class ExperimentalCondition(ExtractedModel):
    condition_id: NonEmptyText
    key: NonEmptyText
    value: NonEmptyText
    normalized_value: str | None = None

    @field_validator("condition_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return require_prefix(value, "condition")


class Result(ExtractedModel):
    result_id: NonEmptyText
    paper_id: NonEmptyText
    evidence_id: NonEmptyText
    method_id: str | None = None
    dataset_id: str | None = None
    task_id: str | None = None
    metric_id: str | None = None
    raw_value: NonEmptyText
    numeric_value: Decimal | None = None
    unit: str | None = None
    split: str | None = None
    is_best: bool | None = None
    condition_ids: list[NonEmptyText] = Field(default_factory=list)

    @field_validator("result_id")
    @classmethod
    def validate_result_id(cls, value: str) -> str:
        return require_prefix(value, "result")

    @field_validator("paper_id")
    @classmethod
    def validate_paper_id(cls, value: str) -> str:
        return require_prefix(value, "paper")

    @field_validator("evidence_id")
    @classmethod
    def validate_evidence_id(cls, value: str) -> str:
        return require_prefix(value, "ev")

    @field_validator("method_id")
    @classmethod
    def validate_method_id(cls, value: str | None) -> str | None:
        return require_prefix(value, "method") if value else value

    @field_validator("dataset_id")
    @classmethod
    def validate_dataset_id(cls, value: str | None) -> str | None:
        return require_prefix(value, "dataset") if value else value

    @field_validator("task_id")
    @classmethod
    def validate_task_id(cls, value: str | None) -> str | None:
        return require_prefix(value, "task") if value else value

    @field_validator("metric_id")
    @classmethod
    def validate_metric_id(cls, value: str | None) -> str | None:
        return require_prefix(value, "metric") if value else value

    @field_validator("condition_ids")
    @classmethod
    def validate_condition_ids(cls, values: list[str]) -> list[str]:
        return _deduplicate([require_prefix(value, "condition") for value in values])


class Relation(ExtractedModel):
    relation_id: NonEmptyText
    subject_id: NonEmptyText
    predicate: NonEmptyText
    object_id: NonEmptyText
    evidence_ids: list[NonEmptyText] = Field(min_length=1)
    source: SourceKind

    @field_validator("relation_id")
    @classmethod
    def validate_relation_id(cls, value: str) -> str:
        return require_prefix(value, "rel")

    @field_validator("evidence_ids")
    @classmethod
    def validate_evidence_ids(cls, values: list[str]) -> list[str]:
        return _deduplicate([require_prefix(value, "ev") for value in values])
