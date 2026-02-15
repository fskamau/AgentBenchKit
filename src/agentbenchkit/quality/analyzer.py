"""Coverage ingestion and lightweight, explicitly non-authoritative test heuristics."""

import ast
import json
from pathlib import Path

from agentbenchkit.exceptions import BenchKitError
from agentbenchkit.models import QualityReport


def analyze_tests(repo: Path, coverage_json: Path | None = None) -> QualityReport:
    sources = [p for p in repo.rglob("*.py") if ".venv" not in p.parts and ".git" not in p.parts]
    tests = [p for p in sources if p.name.startswith("test_") or "tests" in p.parts]
    assertion_calls = 0
    test_functions = 0
    problems: list[str] = []
    for path in tests:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (UnicodeError, OSError, SyntaxError) as exc:
            problems.append(f"Cannot parse {path}: {exc}")
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                test_functions += 1
            if isinstance(node, ast.Assert):
                assertion_calls += 1
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr.startswith("assert"):
                    assertion_calls += 1
    covered = None
    if coverage_json:
        try:
            data = json.loads(coverage_json.read_text(encoding="utf-8"))
            covered = float(data["totals"]["percent_covered"])
        except (ValueError, OSError, KeyError, TypeError) as exc:
            raise BenchKitError(f"Invalid coverage JSON {coverage_json}: {exc}",
                                "coverage_invalid") from exc
    if not tests:
        problems.append("No Python tests discovered.")
    if covered is None:
        problems.append("Coverage unavailable; no coverage JSON was provided.")
    problems.append("Assertion counts and coverage alone do not establish test quality.")
    return QualityReport(source_files=len(sources) - len(tests), test_files=len(tests),
                         test_functions=test_functions, assertion_calls=assertion_calls,
                         coverage_percent=covered, findings=problems)


def mutation_summary(path: Path) -> dict[str, int | float]:
    """Optional adapter for a JSON {killed, survived, timeout} mutation report."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        killed, survived = int(raw["killed"]), int(raw["survived"])
        timeout = int(raw.get("timeout", 0))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        raise BenchKitError(f"Invalid mutation summary: {exc}", "mutation_invalid") from exc
    if min(killed, survived, timeout) < 0:
        raise BenchKitError("Mutation counts must be nonnegative", "mutation_invalid")
    total = killed + survived + timeout
    return {"killed": killed, "survived": survived, "timeout": timeout,
            "mutation_score_percent": round(100 * killed / total, 2) if total else 0.0}
