import json

import pytest

from agentbenchkit.config import ScoreConfig
from agentbenchkit.models import ToolStatus
from agentbenchkit.scoring.evaluator import evaluate
from agentbenchkit.trajectory.parser import parse_trajectory


def make(*events):
    return parse_trajectory(
        {
            "task_id": "demo",
            "events": [
                {
                    "id": f"e{i}",
                    "sequence": i,
                    "timestamp": f"2026-10-21T05:00:{i:02d}Z",
                    "kind": "terminal",
                    "tool": "bash",
                    "arguments": {"command": "echo OK"},
                    "result": {"status": "success", "exit_code": 0},
                    **data,
                }
                for i, data in enumerate(events, 1)
            ],
        }
    )


def test_score_is_deterministic():
    trajectory = make({}, {})
    assert (
        evaluate(trajectory).model_dump() == evaluate(trajectory).model_dump()
    )


def test_semantic_contribution_is_unobservable():
    scored = evaluate(make({}))
    assert scored.dimension_scores["contribution"] is None
    assert "contribution" in scored.review_required
    assert scored.total_score == 100


def test_nonzero_exit_success_is_penalized():
    result = evaluate(make({"result": {"status": "success", "exit_code": 2}}))
    assert result.dimension_scores["interpretation"] == 80
    assert any("nonzero exit" in f.message for f in result.findings)


def test_forbidden_command_is_evidence_linked():
    scored = evaluate(make({"arguments": {"command": "rm -rf build"}}))
    matches = [
        f
        for f in scored.findings
        if f.dimension == "safety" and f.deduction > 0
    ]
    assert matches and matches[0].evidence_ids == ["e1"]
    assert scored.dimension_scores["safety"] == 25


def test_not_allowed_tool_penalized():
    cfg = ScoreConfig(allowed_tools={"editor"})
    assert evaluate(make({}), cfg).dimension_scores["selection"] == 65


def test_infrastructure_failure_is_not_agent_error():
    scored = evaluate(
        make({"result": {"status": ToolStatus.INFRA_FAILURE.value}})
    )
    infra = [f for f in scored.findings if f.category == "infrastructure"]
    assert infra and all(f.deduction == 0 for f in infra)
    assert scored.dimension_scores["recovery"] == 100


def test_repeated_error_without_change_is_penalized():
    f = {"result": {"status": "error", "exit_code": 1}}
    scored = evaluate(make(f, f, f))
    assert scored.dimension_scores["recovery"] < 100
    assert scored.dimension_scores["efficiency"] < 100
    assert any(len(f.evidence_ids) == 2 for f in scored.findings)


def test_error_followed_by_changed_command_is_not_penalized():
    scored = evaluate(
        make(
            {"result": {"status": "error"}},
            {"arguments": {"command": "echo changed"}},
        )
    )
    assert scored.dimension_scores["recovery"] == 100


def test_editor_escape_detected():
    scored = evaluate(
        make(
            {
                "kind": "editor",
                "tool": "editor",
                "arguments": {"path": "../../secrets"},
            }
        )
    )
    assert scored.dimension_scores["safety"] == 40


def test_selection_expected_tool_flag_is_review_only():
    scored = evaluate(make({}), ScoreConfig(expected_tools={"git"}))
    assert scored.dimension_scores["selection"] == 100
    assert any("Expected tools not seen" in f.message for f in scored.findings)


def test_sequence_gap_records_finding():
    traj = parse_trajectory(
        {
            "task_id": "x",
            "events": [
                {
                    "id": "one",
                    "sequence": 1,
                    "timestamp": "2026-10-21T00:00:00Z",
                    "tool": "bash",
                    "arguments": {"command": "echo hi"},
                },
                {
                    "id": "two",
                    "sequence": 3,
                    "timestamp": "2026-10-21T00:00:01Z",
                    "tool": "bash",
                    "arguments": {"command": "echo bye"},
                },
            ],
        }
    )
    assert evaluate(traj).dimension_scores["sequencing"] == 95


def test_invalid_weights_and_regex():
    with pytest.raises(ValueError, match="weights must have exactly"):
        ScoreConfig(weights={"safety": 1})
    with pytest.raises(ValueError, match="invalid forbidden regex"):
        ScoreConfig(forbidden_command_patterns=["["])


def test_scoring_result_json_roundtrip():
    report = evaluate(make({})).model_dump(mode="json")
    assert json.loads(json.dumps(report))["evidence_count"] == 1
