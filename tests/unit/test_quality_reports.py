import json

import pytest

from agentbenchkit.exceptions import BenchKitError
from agentbenchkit.quality.analyzer import analyze_tests, mutation_summary
from agentbenchkit.reports.render import compare_evaluations, write_reports
from agentbenchkit.scoring.evaluator import evaluate
from agentbenchkit.trajectory.parser import parse_trajectory


def test_coverage_and_assertion_ingestion(tmp_path):
    (tmp_path / "core.py").write_text("def x(): return 1\n")
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_core.py").write_text("def test_core():\n    assert True\n")
    coverage = tmp_path / "coverage.json"
    coverage.write_text(json.dumps({"totals": {"percent_covered": 81.2}}))
    result = analyze_tests(tmp_path, coverage)
    assert result.source_files == 1
    assert result.test_functions == 1
    assert result.assertion_calls == 1
    assert result.coverage_percent == 81.2


def test_invalid_coverage_report_fails(tmp_path):
    source = tmp_path / "coverage.json"
    source.write_text("{}")
    with pytest.raises(BenchKitError, match="Invalid coverage JSON"):
        analyze_tests(tmp_path, source)


def test_mutation_summary(tmp_path):
    report = tmp_path / "mutations.json"
    report.write_text('{"killed":8,"survived":2,"timeout":0}')
    assert mutation_summary(report)["mutation_score_percent"] == 80.0
    report.write_text('{"killed":-1,"survived":2}')
    with pytest.raises(BenchKitError):
        mutation_summary(report)


def _example_evaluation():
    trajectory = parse_trajectory({"task_id": "demo", "events": [
        {"id":"1","sequence":1,"timestamp":"2026-10-21T00:00:00Z",
         "tool":"terminal","arguments":{"command":"echo <script>alert(1)</script>"},
         "result":{"status":"success","exit_code":0}}]})
    return evaluate(trajectory)


def test_writes_json_markdown_and_escaped_html(tmp_path):
    report = _example_evaluation()
    paths = write_reports(report, tmp_path / "evaluation")
    assert len(paths) == 3 and all(p.exists() for p in paths)
    assert json.loads(paths[0].read_text())["task_id"] == "demo"
    content = paths[2].read_text()
    assert "<script>" not in content
    assert "<main>" in content


def test_compare_trajectories(tmp_path):
    report = _example_evaluation()
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text(report.model_dump_json())
    b.write_text(report.model_dump_json())
    result = compare_evaluations([a, b])
    assert result["kind"] == "trajectory"
    assert len(result["ranking_by_observable_score"]) == 2


def test_compare_requires_same_task(tmp_path):
    report = _example_evaluation().model_dump(mode="json")
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text(json.dumps(report))
    report["task_id"] = "different"
    b.write_text(json.dumps(report))
    with pytest.raises(ValueError, match="same task"):
        compare_evaluations([a, b])


def test_compare_requires_two_attempts(tmp_path):
    with pytest.raises(ValueError, match="at least two"):
        compare_evaluations([tmp_path / "nothing"])
