"""Process execution is argv-only; host execution requires explicit caller opt-in."""

import os
import re
import subprocess
import time
from pathlib import Path
from typing import Protocol

from agentbenchkit.exceptions import BenchKitError, ExecutionDenied
from agentbenchkit.models import ProcessResult, TestResult

MAX_OUTPUT_CHARS = 100_000


class Runner(Protocol):
    def run(
        self, argv: list[str], cwd: Path, timeout: int
    ) -> ProcessResult: ...


class LocalRunner:
    """Local execution is NOT isolation; only activate with explicit consent."""

    def __init__(self, allowed: bool = False) -> None:
        if not allowed:
            raise ExecutionDenied(
                "Host execution denied; use --engine docker or --allow-local"
            )

    def run(
        self, argv: list[str], cwd: Path, timeout: int = 30
    ) -> ProcessResult:
        return execute(argv, cwd, timeout)


def execute(argv: list[str], cwd: Path, timeout: int = 30) -> ProcessResult:
    if not argv or any(not isinstance(arg, str) or not arg for arg in argv):
        raise BenchKitError(
            "Command must be a nonempty argv list", "command_invalid"
        )
    started = time.monotonic()
    try:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
            check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        return ProcessResult(
            argv=argv,
            exit_code=completed.returncode,
            stdout=completed.stdout[-MAX_OUTPUT_CHARS:],
            stderr=completed.stderr[-MAX_OUTPUT_CHARS:],
            duration_seconds=round(time.monotonic() - started, 4),
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or b""
        stderr = exc.stderr or b""
        return ProcessResult(
            argv=argv,
            exit_code=None,
            stdout=(
                stdout.decode("utf-8", "replace")
                if isinstance(stdout, bytes)
                else stdout
            )[-MAX_OUTPUT_CHARS:],
            stderr=(
                stderr.decode("utf-8", "replace")
                if isinstance(stderr, bytes)
                else stderr
            )[-MAX_OUTPUT_CHARS:],
            duration_seconds=round(time.monotonic() - started, 4),
            timed_out=True,
        )
    except (OSError, ValueError) as exc:
        return ProcessResult(
            argv=argv,
            exit_code=None,
            stdout="",
            stderr="",
            duration_seconds=round(time.monotonic() - started, 4),
            infrastructure_error=f"{type(exc).__name__}: {exc}",
        )


def test_result(result: ProcessResult) -> TestResult:
    """Conservative classification: test failures require recognizable test output."""
    output = result.stdout + "\n" + result.stderr
    failed: set[str] = set()
    for match in re.finditer(r"(?m)^\s*(?:FAIL|ERROR): (test\w+)\s*\(", output):
        failed.add(match.group(1))
    for match in re.finditer(
        r"(?m)^\s*(test\w+)\s+\([^\n]+\)\s+\.\.\.\s+(?:FAIL|ERROR)", output
    ):
        failed.add(match.group(1))
    for match in re.finditer(r"(?m)^FAILED\s+\S+::(test\w+)", output):
        failed.add(match.group(1))
    if result.timed_out:
        classification = "timeout"
    elif result.infrastructure_error is not None:
        classification = "infrastructure_error"
    elif result.exit_code == 0:
        classification = "passed"
    elif failed or re.search(
        r"(?mi)^FAILED \(|^FAILED tests?|^FAIL: |^FAILED \S+::", output
    ):
        classification = "failed"
    elif re.search(r"(?mi)^FAILED \(failures=|^FAILED \(errors=", output):
        classification = "failed"
    elif re.search(r"(?mi)^=+ .*failed.* =+$", output):
        classification = "failed"
    else:
        classification = "setup_error"
    return TestResult(
        process=result,
        classification=classification,
        failed_tests=sorted(failed),
    )
