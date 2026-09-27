"""Pipeline states and approval contracts for the agency v1 workflow."""

from __future__ import annotations

PIPELINE_STATES: frozenset[str] = frozenset(
    {
        "INTAKE",
        "FACTS_EXTRACTED", "FACTS_APPROVED",
        "RESEARCHING", "RESEARCH_COMPLETE", "RESEARCH_APPROVED",
        "CONTENT_GENERATING", "CONTENT_COMPLETE", "CONTENT_APPROVED",
        "DESIGNING", "DESIGN_COMPLETE", "DESIGN_APPROVED",
        "BUILDING", "BUILD_COMPLETE", "BUILD_FAILED",
        "PREVIEW_READY", "PREVIEW_APPROVED",
        "PUBLISHING", "LIVE", "MAINTENANCE",
        "FAILED",
    }
)

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "INTAKE": frozenset({"FACTS_EXTRACTED"}),
    "FACTS_EXTRACTED": frozenset({"FACTS_APPROVED"}),
    "FACTS_APPROVED": frozenset({"RESEARCHING"}),
    "RESEARCHING": frozenset({"RESEARCH_COMPLETE"}),
    "RESEARCH_COMPLETE": frozenset({"RESEARCH_APPROVED"}),
    "RESEARCH_APPROVED": frozenset({"CONTENT_GENERATING", "DESIGNING"}),
    "CONTENT_GENERATING": frozenset({"CONTENT_COMPLETE", "FAILED"}),
    "CONTENT_COMPLETE": frozenset({"CONTENT_APPROVED"}),
    "CONTENT_APPROVED": frozenset({"DESIGNING"}),
    "DESIGNING": frozenset({"DESIGN_COMPLETE", "FAILED"}),
    "DESIGN_COMPLETE": frozenset({"DESIGN_APPROVED"}),
    "DESIGN_APPROVED": frozenset({"BUILDING"}),
    "BUILDING": frozenset({"BUILD_COMPLETE", "BUILD_FAILED"}),
    "BUILD_COMPLETE": frozenset({"PREVIEW_READY", "FAILED"}),
    "PREVIEW_READY": frozenset({"PREVIEW_APPROVED", "CONTENT_GENERATING", "DESIGNING"}),
    "PREVIEW_APPROVED": frozenset({"PUBLISHING"}),
    "PUBLISHING": frozenset({"LIVE", "FAILED"}),
    "LIVE": frozenset({"MAINTENANCE", "PUBLISHING"}),
    "MAINTENANCE": frozenset({"BUILDING", "PUBLISHING"}),
}

APPROVAL_CONTRACT: dict[str, tuple[str, str]] = {
    "FACTS": ("FACTS_EXTRACTED", "FACTS_APPROVED"),
    "RESEARCH": ("RESEARCH_COMPLETE", "RESEARCH_APPROVED"),
    "CONTENT": ("CONTENT_COMPLETE", "CONTENT_APPROVED"),
    "PUBLISH": ("PREVIEW_READY", "PREVIEW_APPROVED"),
}

APPROVAL_GATE_STATES: frozenset[str] = frozenset(
    to_state for _, to_state in APPROVAL_CONTRACT.values()
)


def is_valid_state(state: str) -> bool:
    return state in PIPELINE_STATES


def is_valid_transition(from_state: str, to_state: str) -> bool:
    return to_state in ALLOWED_TRANSITIONS.get(from_state, frozenset())
