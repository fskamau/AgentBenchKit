"""Load a strict JSON trajectory and normalize compatible tool-call records."""

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from agentbenchkit.exceptions import BenchKitError
from agentbenchkit.models import Trajectory

TOOL_ALIASES: dict[str, str] = {
    "bash": "terminal",
    "shell": "terminal",
    "exec": "terminal",
    "terminal": "terminal",
    "write_file": "editor",
    "edit_file": "editor",
    "editor": "editor",
    "git": "git",
    "browser": "browser",
    "navigate": "browser",
    "click": "browser",
}


def normalize_tool_record(record: dict[str, Any]) -> dict[str, Any]:
    """Normalize known tool names without silently accepting an unknown event kind."""
    converted = dict(record)
    tool = converted.get("tool")
    if "kind" not in converted and isinstance(tool, str):
        if tool not in TOOL_ALIASES:
            raise BenchKitError(
                f"event {converted.get('id', '<missing>')}: unknown tool {tool!r}; "
                "supply an explicit supported kind",
                "unsupported_tool",
            )
        converted["kind"] = TOOL_ALIASES[tool]
    if "arguments" not in converted:
        converted["arguments"] = {}
    return converted


def parse_trajectory(payload: dict[str, Any]) -> Trajectory:
    try:
        normalized = dict(payload)
        events = normalized.get("events")
        if not isinstance(events, list):
            raise BenchKitError(
                "trajectory.events must be a list", "trajectory_invalid"
            )
        normalized["events"] = [
            normalize_tool_record(event) if isinstance(event, dict) else event
            for event in events
        ]
        return Trajectory.model_validate(normalized)
    except ValidationError as exc:
        problems = []
        for error in exc.errors():
            loc = ".".join(str(value) for value in error["loc"])
            problems.append(f"{loc}: {error['msg']}")
        raise BenchKitError(
            "Invalid trajectory:\n" + "\n".join(problems), "trajectory_invalid"
        ) from exc


def load_trajectory(path: Path) -> Trajectory:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BenchKitError(
            f"Cannot load trajectory {path}: {exc}", "trajectory_invalid"
        ) from exc
    if not isinstance(raw, dict):
        raise BenchKitError(
            "Trajectory root must be a JSON object", "trajectory_invalid"
        )
    return parse_trajectory(raw)
