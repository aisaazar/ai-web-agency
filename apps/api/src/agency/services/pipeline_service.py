"""Pure pipeline transition service.

Persistence belongs to the application/API layer; this service only validates transitions.
"""

from dataclasses import dataclass

from agency.domain.pipeline_definition import is_valid_state, is_valid_transition


class PipelineError(ValueError):
    """Raised when a requested pipeline transition is invalid."""


@dataclass(frozen=True)
class PipelineTransition:
    from_state: str
    to_state: str


def transition(from_state: str, to_state: str) -> PipelineTransition:
    """Validate and return an explicit transition; never silently coerce state."""
    if not is_valid_state(from_state):
        raise PipelineError(f"Unknown pipeline state: {from_state}")
    if not is_valid_state(to_state):
        raise PipelineError(f"Unknown pipeline state: {to_state}")
    if not is_valid_transition(from_state, to_state):
        raise PipelineError(f"Invalid pipeline transition: {from_state} -> {to_state}")
    return PipelineTransition(from_state=from_state, to_state=to_state)
