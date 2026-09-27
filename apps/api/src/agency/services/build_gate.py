"""Deterministic build-gate decision logic."""

from __future__ import annotations

from dataclasses import dataclass


REQUIRED_CHECKS: tuple[str, ...] = (
    "content_schema",
    "facts_provenance",
    "claims_policy",
    "required_legal_pages",
    "typecheck",
    "next_build",
    "linkcheck",
    "a11y_budget",
    "perf_budget",
    "playwright_smoke",
    "seo_manifest",
)


@dataclass(frozen=True)
class ValidationResult:
    check_name: str
    passed: bool
    detail: str = ""
    blocking: bool = True


class BuildGateError(RuntimeError):
    """Raised when a site version does not have a complete passing validation set."""


def evaluate_build_gate(results: list[ValidationResult]) -> None:
    by_name = {result.check_name: result for result in results}
    missing = [name for name in REQUIRED_CHECKS if name not in by_name]
    failed = [name for name in REQUIRED_CHECKS if name in by_name and not by_name[name].passed]
    blocking_warnings = [
        result.check_name for result in results
        if result.check_name not in REQUIRED_CHECKS and result.blocking and not result.passed
    ]
    if missing or failed or blocking_warnings:
        reasons = []
        if missing:
            reasons.append(f"missing={','.join(missing)}")
        if failed:
            reasons.append(f"failed={','.join(failed)}")
        if blocking_warnings:
            reasons.append(f"blocking={','.join(blocking_warnings)}")
        raise BuildGateError("build validation failed: " + "; ".join(reasons))
