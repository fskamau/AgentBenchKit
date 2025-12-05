"""Machine-readable interchange schemas for trajectories and evaluations."""

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class EventKind(StrEnum):
    TERMINAL = "terminal"
    EDITOR = "editor"
    GIT = "git"
    BROWSER = "browser"


class ToolStatus(StrEnum):
    SUCCESS = "success"
    ERROR = "error"
    INFRA_FAILURE = "infra_failure"
    TIMEOUT = "timeout"


class ToolResult(BaseModel):
    status: ToolStatus
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    error_type: str | None = None
    duration_ms: int | None = Field(default=None, ge=0)


class TrajectoryEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    sequence: int = Field(ge=0)
    timestamp: datetime
    kind: EventKind
    tool: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: ToolResult | None = None
    agent_observation: str | None = None
    purpose: str | None = None

    @field_validator("timestamp")
    @classmethod
    def ensure_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include a timezone offset")
        return value


class Trajectory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    task_id: str = Field(min_length=1)
    events: list[TrajectoryEvent] = Field(min_length=1)
    declared_outcome: Literal["success", "failure", "unknown"] = "unknown"

    @model_validator(mode="after")
    def validate_event_order(self) -> "Trajectory":
        ids = set()
        previous_sequence = -1
        previous_time: datetime | None = None
        for event in self.events:
            if event.id in ids:
                raise ValueError(f"event {event.id}: duplicate event id")
            if event.sequence <= previous_sequence:
                raise ValueError(f"event {event.id}: sequence must strictly increase")
            if previous_time and event.timestamp < previous_time:
                raise ValueError(f"event {event.id}: timestamp precedes previous event")
            ids.add(event.id)
            previous_sequence = event.sequence
            previous_time = event.timestamp
        return self


class Finding(BaseModel):
    dimension: str
    severity: Literal["info", "low", "medium", "high", "critical", "review"]
    message: str
    evidence_ids: list[str] = Field(min_length=1)
    deduction: float = Field(default=0, ge=0)
    category: Literal["agent", "infrastructure", "uncertain", "observation"] = "agent"


class Evaluation(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    task_id: str
    total_score: float
    dimension_scores: dict[str, float | None]
    findings: list[Finding]
    review_required: list[str]
    evidence_count: int


class ProcessResult(BaseModel):
    argv: list[str]
    exit_code: int | None
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False
    infrastructure_error: str | None = None


class TestResult(BaseModel):
    process: ProcessResult
    classification: Literal["passed", "failed", "setup_error", "timeout", "infrastructure_error"]
    failed_tests: list[str] = Field(default_factory=list)


class PatchReport(BaseModel):
    case_id: str
    base_commit: str | None
    patch_sha256: str
    changed_files: list[str]
    unexpected_files: list[str] = Field(default_factory=list)
    patch_applied: bool
    application_error: str | None = None
    baseline: TestResult | None = None
    patched: TestResult | None = None
    oracle: TestResult | None = None
    classification: str
    evidence: list[str] = Field(default_factory=list)
    engine: Literal["local", "docker"]


class BenchmarkCase(BaseModel):
    id: str
    description: str
    test_command: list[str] = Field(min_length=1)
    oracle_command: list[str] = Field(min_length=1)
    allowed_changed_files: list[str] = Field(min_length=1)
    timeout_seconds: int = Field(default=30, ge=1, le=3600)


class QualityReport(BaseModel):
    source_files: int
    test_files: int
    test_functions: int
    assertion_calls: int
    coverage_percent: float | None = None
    findings: list[str] = Field(default_factory=list)
