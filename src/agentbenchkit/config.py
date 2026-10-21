"""Validated evaluator configuration."""

import json
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator

from agentbenchkit.exceptions import BenchKitError

DIMENSIONS = (
    "selection",
    "arguments",
    "sequencing",
    "interpretation",
    "recovery",
    "efficiency",
    "safety",
    "contribution",
)


class ScoreConfig(BaseModel):
    """Weights control aggregation; unobservable dimensions require human review."""

    weights: dict[str, float] = Field(
        default_factory=lambda: {k: 1.0 for k in DIMENSIONS}
    )
    allowed_tools: set[str] = Field(default_factory=set)
    expected_tools: set[str] = Field(default_factory=set)
    max_repetitions: int = Field(default=2, ge=1)
    forbidden_command_patterns: list[str] = Field(
        default_factory=lambda: [
            r"(?i)\brm\s+-rf\b",
            r"(?i)\bgit\s+push\s+--force\b",
        ]
    )

    @field_validator("weights")
    @classmethod
    def validate_weights(cls, value: dict[str, float]) -> dict[str, float]:
        if set(value) != set(DIMENSIONS):
            raise ValueError(
                f"weights must have exactly: {', '.join(DIMENSIONS)}"
            )
        if any(not (0 <= weight < float("inf")) for weight in value.values()):
            raise ValueError("weights must be finite and non-negative")
        if not any(value.values()):
            raise ValueError("at least one weight must be positive")
        return value

    @model_validator(mode="after")
    def validate_patterns(self) -> "ScoreConfig":
        import re

        for pattern in self.forbidden_command_patterns:
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ValueError(
                    f"invalid forbidden regex {pattern!r}: {exc}"
                ) from exc
        return self


def load_config(path: Path | None) -> ScoreConfig:
    if path is None:
        return ScoreConfig()
    try:
        return ScoreConfig.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BenchKitError(
            f"Cannot read scoring config {path}: {exc}", "config_invalid"
        ) from exc


def save_config(config: ScoreConfig, path: Path) -> None:
    path.write_text(
        json.dumps(config.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
