"""Deterministic claims policy for German health-site content."""

from __future__ import annotations

import re


FORBIDDEN_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\b100\s*%\b", "absolute success claim"),
    (r"garantiert(?:e|en|er)?\b", "guarantee claim"),
    (r"\bgarantie\b", "guarantee claim"),
    (r"\bbeste(?:r|s|n|m)?\b", "unsubstantiated superlative"),
    (r"\b(?:heilt|heilung)\b", "medical cure claim"),
    (r"\bohne\s+risiko\b", "risk-free medical claim"),
)


def find_claim_violations(texts: list[str]) -> list[str]:
    violations: list[str] = []
    for text in texts:
        for pattern, reason in FORBIDDEN_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                violations.append(reason)
    return sorted(set(violations))


def assert_claims_allowed(texts: list[str]) -> None:
    violations = find_claim_violations(texts)
    if violations:
        raise ValueError("claims policy blocked content: " + ", ".join(violations))
