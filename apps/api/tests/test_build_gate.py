import pytest

from agency.services.build_gate import BuildGateError, REQUIRED_CHECKS, ValidationResult, evaluate_build_gate


def passing_results():
    return [ValidationResult(name, True) for name in REQUIRED_CHECKS]


def test_complete_validation_set_opens_gate():
    evaluate_build_gate(passing_results())


def test_missing_check_blocks_gate():
    results = passing_results()[:-1]
    with pytest.raises(BuildGateError, match="missing=seo_manifest"):
        evaluate_build_gate(results)


def test_failed_required_check_blocks_gate():
    results = passing_results()
    results[2] = ValidationResult("claims_policy", False, "disallowed claim")
    with pytest.raises(BuildGateError, match="failed=claims_policy"):
        evaluate_build_gate(results)


def test_nonblocking_extra_warning_does_not_block_gate():
    evaluate_build_gate(passing_results() + [ValidationResult("advisory", False, blocking=False)])
