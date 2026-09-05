"""Deterministic identifiers and content hashes."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

_PREFIX_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def stable_id(prefix: str, *parts: object, digest_length: int = 20) -> str:
    """Create a stable prefixed ID from normalized values."""
    if not _PREFIX_PATTERN.fullmatch(prefix):
        raise ValueError("prefix must contain lowercase letters, digits, or underscores")
    if not 8 <= digest_length <= 64:
        raise ValueError("digest_length must be between 8 and 64")
    normalized_parts = [str(part).strip() for part in parts]
    if not normalized_parts or not any(normalized_parts):
        raise ValueError("at least one non-empty ID part is required")
    normalized = "\x1f".join(normalized_parts)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:digest_length]
    return f"{prefix}:{digest}"


def content_sha256(content: str | bytes) -> str:
    payload = content.encode("utf-8") if isinstance(content, str) else content
    return hashlib.sha256(payload).hexdigest()


def file_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while block := file.read(chunk_size):
            digest.update(block)
    return digest.hexdigest()
