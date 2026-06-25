"""Expression safety validation."""

from __future__ import annotations

import re

from csv_data_transformer.exceptions import TransformError

_FORBIDDEN_PATTERNS = (
    re.compile(r"\.\s*__"),
    re.compile(r";"),
    re.compile(r"\bimport\b", re.IGNORECASE),
    re.compile(r"\beval\b", re.IGNORECASE),
    re.compile(r"\bexec\b", re.IGNORECASE),
)


def validate_expression_safety(expression: str) -> None:
    """Reject unsafe expression constructs before evaluation."""
    for pattern in _FORBIDDEN_PATTERNS:
        if pattern.search(expression):
            raise TransformError(
                message=f"Unsafe expression rejected: {expression}",
                gate="G2",
                phase="expressions",
                expression=expression,
            )
