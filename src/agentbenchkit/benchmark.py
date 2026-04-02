"""Loading and executing committed benchmark fixtures."""

import json
from pathlib import Path

from pydantic import ValidationError

from agentbenchkit.exceptions import BenchKitError
from agentbenchkit.models import BenchmarkCase, PatchReport
from agentbenchkit.patches.evaluate import evaluate_patch
from agentbenchkit.repository.runner import Runner


def default_cases_dir() -> Path:
    candidates = [Path.cwd() / "benchmarks" / "cases",
                  Path(__file__).resolve().parents[2] / "benchmarks" / "cases"]
    for path in candidates:
        if path.is_dir():
            return path
    raise BenchKitError("Benchmark fixtures unavailable; run from the source checkout "
                        "or supply --cases-dir", "benchmarks_missing")


def list_cases(cases_dir: Path) -> list[BenchmarkCase]:
    if not cases_dir.is_dir():
        raise BenchKitError(f"Benchmark directory missing: {cases_dir}", "benchmarks_missing")
    cases = []
    for path in sorted(cases_dir.glob("*/case.json")):
        try:
            case = BenchmarkCase.model_validate_json(path.read_text(encoding="utf-8"))
        except (ValidationError, OSError) as exc:
            raise BenchKitError(f"Invalid benchmark {path}: {exc}", "benchmark_invalid") from exc
        if case.id != path.parent.name:
            raise BenchKitError(f"Case ID mismatches directory name: {path}", "benchmark_invalid")
        cases.append(case)
    return cases


def run_case(cases_dir: Path, case_id: str, *, candidate: str, runner: Runner,
             engine: str) -> PatchReport:
    if "/" in case_id or "\\" in case_id or case_id in (".", ".."):
        raise BenchKitError("Invalid case ID", "benchmark_invalid")
    case_path = cases_dir / case_id
    manifest = case_path / "case.json"
    if not manifest.is_file():
        raise BenchKitError(f"Unknown benchmark case: {case_id}", "benchmark_missing")
    case = BenchmarkCase.model_validate_json(manifest.read_text(encoding="utf-8"))
    if case.id != case_id:
        raise BenchKitError("Case manifest ID mismatch", "benchmark_invalid")
    if candidate not in ("correct", "partial", "regression", "does-not-apply"):
        raise BenchKitError("Candidate must be correct, partial, regression or does-not-apply",
                            "candidate_invalid")
    return evaluate_patch(case_path / "repo", case_path / "patches" / f"{candidate}.diff",
                          case_id=case.id, test_command=case.test_command,
                          oracle_dir=case_path / "oracle", oracle_command=case.oracle_command,
                          allowed_files=case.allowed_changed_files, runner=runner,
                          timeout=case.timeout_seconds, engine=engine, edge_cases=case.edge_cases)


def summary(reports: list[PatchReport]) -> dict[str, object]:
    counts: dict[str, int] = {}
    for report in reports:
        counts[report.classification] = counts.get(report.classification, 0) + 1
    return {"total_cases": len(reports), "classification_counts": counts,
            "cases": [{"id": report.case_id, "classification": report.classification,
                       "baseline": report.baseline.classification if report.baseline else None,
                       "patched": report.patched.classification if report.patched else None,
                       "oracle": report.oracle.classification if report.oracle else None}
                      for report in reports],
            "warning": "The benchmark suite is synthetic; do not extrapolate to real agent quality."}


def write_summary(data: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
