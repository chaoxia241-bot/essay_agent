"""Enumerations shared by the domain model."""

from enum import StrEnum


class ReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class EvidenceType(StrEnum):
    TEXT = "text"
    TABLE = "table"
    FIGURE = "figure"


class EvidenceValidationStatus(StrEnum):
    PENDING = "pending"
    PASSED = "passed"
    PARTIAL = "partial"
    FAILED = "failed"


class ClaimType(StrEnum):
    DEFINITION = "definition"
    PERFORMANCE = "performance"
    METHOD_RELATION = "method_relation"
    LIMITATION = "limitation"
    DATASET_USAGE = "dataset_usage"
    RESULT = "result"
    OTHER = "other"


class ExtractionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class SourceKind(StrEnum):
    PARSER = "parser"
    LLM = "llm"
    RULE = "rule"
    HUMAN = "human"
