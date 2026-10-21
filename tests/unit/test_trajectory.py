from pathlib import Path

import pytest

from agentbenchkit.exceptions import BenchKitError
from agentbenchkit.trajectory.parser import load_trajectory, parse_trajectory

EXAMPLES = Path(__file__).resolve().parents[2] / "examples" / "trajectories"


def event(**overrides):
    e = {
        "id": "step1",
        "sequence": 1,
        "timestamp": "2026-10-21T05:00:00Z",
        "tool": "terminal",
        "arguments": {"command": "echo OK"},
        "result": {"status": "success", "exit_code": 0},
    }
    e.update(overrides)
    return e


def test_successful_trajectory_parsed_and_normalized():
    trajectory = load_trajectory(EXAMPLES / "success.json")
    assert trajectory.events[0].kind.value == "terminal"
    assert trajectory.events[1].kind.value == "editor"
    assert len(trajectory.events) == 3


@pytest.mark.parametrize(
    "events,fragment",
    [
        (
            [event(id="same"), event(id="same", sequence=2)],
            "duplicate event id",
        ),
        (
            [event(sequence=2), event(id="step2", sequence=1)],
            "sequence must strictly increase",
        ),
        ([event(timestamp="2026-10-21T05:00:00")], "timezone"),
        (
            [
                event(),
                event(id="step2", sequence=2, timestamp="2026-10-20T05:00:00Z"),
            ],
            "timestamp precedes",
        ),
        ([event(tool="unknown")], "unknown tool"),
        ([event(kind="filesystem")], "kind"),
        ([event(arguments=[])], "arguments"),
        ([], "at least 1 item"),
    ],
)
def test_rejects_invalid_events(events, fragment):
    with pytest.raises(BenchKitError) as exc:
        parse_trajectory({"task_id": "demo", "events": events})
    assert fragment.lower() in str(exc.value).lower()


def test_explicit_kind_allows_custom_tool_identifier():
    trajectory = parse_trajectory(
        {
            "task_id": "demo",
            "events": [event(kind="terminal", tool="my_terminal")],
        }
    )
    assert trajectory.events[0].tool == "my_terminal"


def test_event_payload_extra_field_rejected():
    with pytest.raises(BenchKitError, match="Extra inputs are not permitted"):
        parse_trajectory(
            {"task_id": "demo", "events": [event(undocumented=True)]}
        )


def test_missing_input_file():
    with pytest.raises(BenchKitError, match="Cannot load trajectory"):
        load_trajectory(Path("/nonexistent/trajectory.json"))


def test_invalid_root_type(tmp_path):
    invalid = tmp_path / "trajectory.json"
    invalid.write_text("[]")
    with pytest.raises(BenchKitError, match="root must be a JSON object"):
        load_trajectory(invalid)
