"""Actual end-to-end tests of temporary repository copies and independent oracles."""

import pytest

from agentbenchkit.benchmark import list_cases, run_case
from agentbenchkit.repository.runner import LocalRunner


@pytest.mark.integration
@pytest.mark.parametrize("case_id", [
    "slug-normalization", "pagination-boundary", "nested-config-merge",
    "retry-backoff", "numeric-version-order",
])
def test_correct_patches_fix_reproduced_defects(case_dir, case_id):
    report = run_case(case_dir, case_id, candidate="correct", runner=LocalRunner(True), engine="local")
    assert report.baseline.classification == "failed"
    assert report.patched.classification == "passed"
    assert report.oracle.classification == "passed"
    assert all(value == "passed" for value in report.edge_case_results.values())
    assert report.classification == "verified_by_tests"


@pytest.mark.integration
def test_detects_deceptive_suite(case_dir):
    result = run_case(case_dir, "deceptive-test-suite", candidate="partial",
                      runner=LocalRunner(True), engine="local")
    assert result.baseline.classification == "passed"
    assert result.patched.classification == "passed"
    assert result.oracle.classification == "failed"
    assert any(status == "failed" for status in result.edge_case_results.values())
    assert result.classification == "incomplete_fix"


@pytest.mark.integration
def test_regression_detected(case_dir):
    result = run_case(case_dir, "slug-normalization", candidate="regression",
                      runner=LocalRunner(True), engine="local")
    assert result.classification == "regression_detected"
    assert "test_plain" in result.patched.failed_tests


@pytest.mark.integration
def test_nonapplicable_patch_is_rejected(case_dir):
    result = run_case(case_dir, "slug-normalization", candidate="does-not-apply",
                      runner=LocalRunner(True), engine="local")
    assert not result.patch_applied
    assert result.application_error
    assert result.classification == "rejected"
    assert result.patched is None


@pytest.mark.integration
def test_six_case_manifests_are_loaded(case_dir):
    assert len(list_cases(case_dir)) == 6
