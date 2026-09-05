from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from litagent.domain import (
    BoundingBox,
    CharSpan,
    Chunk,
    Claim,
    ClaimType,
    Evidence,
    EvidenceType,
    ExtractionRun,
    ExtractionStatus,
    Paper,
    ReviewStatus,
    content_sha256,
    stable_id,
)


def test_stable_id_is_deterministic() -> None:
    first = stable_id("paper", "A Paper", "2026")
    second = stable_id("paper", "A Paper", "2026")

    assert first == second
    assert first.startswith("paper:")


def test_stable_id_rejects_empty_parts() -> None:
    with pytest.raises(ValueError):
        stable_id("paper", "", " ")


def test_paper_requires_prefixed_id_and_sha256() -> None:
    paper = Paper(
        paper_id=stable_id("paper", "sample.pdf"),
        title="Sample Paper",
        authors=["Alice", "Alice", "Bob"],
        year=2026,
        document_uri="papers/sample.pdf",
        sha256=content_sha256(b"pdf"),
    )

    assert paper.authors == ["Alice", "Bob"]
    assert paper.review_status == ReviewStatus.PENDING


def test_chunk_rejects_reversed_page_range() -> None:
    with pytest.raises(ValidationError):
        Chunk(
            chunk_id=stable_id("chunk", "paper:1", 0),
            paper_id="paper:1",
            order_index=0,
            content="text",
            content_hash=content_sha256("text"),
            token_count=1,
            page_start=2,
            page_end=1,
        )


def test_text_evidence_requires_char_span() -> None:
    with pytest.raises(ValidationError):
        Evidence(
            evidence_id="ev:1",
            paper_id="paper:1",
            evidence_type=EvidenceType.TEXT,
            page=1,
            chunk_id="chunk:1",
            content="evidence",
            confidence=0.9,
            extraction_run_id="run:1",
        )


def test_table_evidence_accepts_bbox() -> None:
    evidence = Evidence(
        evidence_id="ev:1",
        paper_id="paper:1",
        evidence_type=EvidenceType.TABLE,
        page=3,
        bbox=BoundingBox(x0=10, y0=20, x1=100, y1=200),
        chunk_id="chunk:1",
        content="| Metric | Value |",
        confidence=0.9,
        extraction_run_id="run:1",
    )

    assert evidence.page == 3


def test_claim_requires_at_least_one_evidence() -> None:
    with pytest.raises(ValidationError):
        Claim(
            claim_id="claim:1",
            paper_id="paper:1",
            statement="A claim",
            claim_type=ClaimType.DEFINITION,
            evidence_ids=[],
            confidence=0.8,
            extraction_run_id="run:1",
        )


def test_claim_deduplicates_evidence_ids() -> None:
    claim = Claim(
        claim_id="claim:1",
        paper_id="paper:1",
        statement="A claim",
        claim_type=ClaimType.DEFINITION,
        evidence_ids=["ev:1", "ev:1"],
        confidence=0.8,
        extraction_run_id="run:1",
    )

    assert claim.evidence_ids == ["ev:1"]


def test_failed_extraction_requires_error() -> None:
    now = datetime.now(UTC)
    with pytest.raises(ValidationError):
        ExtractionRun(
            extraction_run_id="run:1",
            paper_id="paper:1",
            model="test-model",
            prompt_version="v1",
            status=ExtractionStatus.FAILED,
            input_hash=content_sha256("input"),
            started_at=now,
            finished_at=now,
        )


def test_char_span_must_have_positive_length() -> None:
    with pytest.raises(ValidationError):
        CharSpan(start=10, end=10)
