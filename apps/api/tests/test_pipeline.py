import pytest

from agency.domain.pipeline_definition import (
    ALLOWED_TRANSITIONS,
    APPROVAL_CONTRACT,
    APPROVAL_GATE_STATES,
    PIPELINE_STATES,
    is_valid_state,
    is_valid_transition,
)
from agency.services.pipeline_service import PipelineError, transition


def test_pipeline_states_match_transition_graph():
    assert PIPELINE_STATES
    assert all(is_valid_state(state) for state in PIPELINE_STATES)
    assert all(to_state in PIPELINE_STATES for values in ALLOWED_TRANSITIONS.values() for to_state in values)


def test_approval_contract_has_four_gates():
    assert set(APPROVAL_CONTRACT) == {"FACTS", "RESEARCH", "CONTENT", "PUBLISH"}
    assert APPROVAL_GATE_STATES == {to_state for _, to_state in APPROVAL_CONTRACT.values()}


@pytest.mark.parametrize(
    ("from_state", "to_state"),
    [
        ("INTAKE", "FACTS_EXTRACTED"),
        ("FACTS_EXTRACTED", "FACTS_APPROVED"),
        ("RESEARCH_APPROVED", "CONTENT_GENERATING"),
        ("RESEARCH_APPROVED", "DESIGNING"),
        ("PREVIEW_READY", "CONTENT_GENERATING"),
        ("PREVIEW_READY", "DESIGNING"),
        ("LIVE", "PUBLISHING"),
    ],
)
def test_allowed_transition(from_state, to_state):
    assert is_valid_transition(from_state, to_state)
    assert transition(from_state, to_state).to_state == to_state


@pytest.mark.parametrize(
    ("from_state", "to_state"),
    [
        ("INTAKE", "CONTENT_APPROVED"),
        ("FACTS_APPROVED", "CONTENT_GENERATING"),
        ("BUILD_FAILED", "PREVIEW_READY"),
        ("PREVIEW_APPROVED", "CONTENT_GENERATING"),
    ],
)
def test_invalid_transition_is_rejected(from_state, to_state):
    with pytest.raises(PipelineError, match="Invalid pipeline transition"):
        transition(from_state, to_state)


def test_unknown_state_is_rejected():
    with pytest.raises(PipelineError, match="Unknown pipeline state"):
        transition("NOPE", "INTAKE")
