"""Typer command-line interface; all executable repository actions require explicit policy."""

import json
import shlex
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from agentbenchkit import __version__
from agentbenchkit.benchmark import default_cases_dir, list_cases, run_case, summary, write_summary
from agentbenchkit.config import load_config
from agentbenchkit.exceptions import BenchKitError
from agentbenchkit.patches.evaluate import evaluate_patch
from agentbenchkit.quality.analyzer import analyze_tests, mutation_summary
from agentbenchkit.reports.render import compare_evaluations, write_reports
from agentbenchkit.repository.inspect import inspect_repo
from agentbenchkit.repository.runner import LocalRunner, test_result
from agentbenchkit.sandbox.docker import DockerRunner, docker_status
from agentbenchkit.scoring.evaluator import evaluate
from agentbenchkit.trajectory.parser import load_trajectory

app = typer.Typer(help="Evidence-backed evaluation of coding-agent tool use and code patches.",
                  no_args_is_help=True)
traj_app = typer.Typer(help="Validate and evaluate recorded agent trajectories.")
repo_app = typer.Typer(help="Inspect repositories and run baselines.")
patch_app = typer.Typer(help="Evaluate patches in disposable repository copies.")
bench_app = typer.Typer(help="Run included reproducible bug benchmarks.")
quality_app = typer.Typer(help="Read coverage and test quality signals.")
sandbox_app = typer.Typer(help="Inspect Docker sandbox availability.")
app.add_typer(traj_app, name="trajectory")
app.add_typer(repo_app, name="repo")
app.add_typer(patch_app, name="patch")
app.add_typer(bench_app, name="benchmark")
app.add_typer(quality_app, name="quality")
app.add_typer(sandbox_app, name="sandbox")


class Engine(StrEnum):
    DOCKER = "docker"
    LOCAL = "local"


def _runner(engine: Engine, allow_local: bool, image: str = "python:3.11-slim"):
    if engine == Engine.LOCAL:
        return LocalRunner(allowed=allow_local)
    return DockerRunner(image=image)


def _dump(data: object) -> None:
    typer.echo(json.dumps(data, indent=2, default=str))


@app.callback(invoke_without_command=True)
def main(version: Annotated[bool, typer.Option("--version", help="Show version and exit")] = False) -> None:
    if version:
        typer.echo(__version__)
        raise typer.Exit()


@traj_app.command("validate")
def trajectory_validate(path: Path) -> None:
    trajectory = load_trajectory(path)
    _dump({"valid": True, "task_id": trajectory.task_id,
           "events": len(trajectory.events), "schema_version": trajectory.schema_version})


@traj_app.command("score")
def trajectory_score(path: Path,
                     config: Annotated[Path | None, typer.Option(help="Scoring config JSON")] = None,
                     output: Annotated[Path | None, typer.Option(help="Output prefix (.json/.md/.html)")] = None) -> None:
    scored = evaluate(load_trajectory(path), load_config(config))
    _dump(scored.model_dump(mode="json"))
    if output:
        for file in write_reports(scored, output):
            typer.echo(f"Wrote {file}", err=True)


@repo_app.command("inspect")
def repo_inspect(path: Path = Path(".")) -> None:
    _dump(inspect_repo(path))


@repo_app.command("baseline")
def repo_baseline(path: Path,
                  command: Annotated[str, typer.Option(help="Argv command, e.g. 'python -m pytest -q'")],
                  engine: Engine = Engine.DOCKER,
                  allow_local: Annotated[bool, typer.Option("--allow-local", help="Consent to execute tests on host")] = False,
                  timeout: int = 30) -> None:
    # The repository is copied, so tests do not operate on its original files.
    import shutil
    import tempfile

    with tempfile.TemporaryDirectory(prefix="abk-baseline-") as tmp:
        staging = Path(tmp) / "repo"
        shutil.copytree(path.resolve(), staging,
                        ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__"))
        runner = _runner(engine, allow_local)
        result = test_result(runner.run(shlex.split(command), staging, timeout))
        _dump(result.model_dump(mode="json"))


@patch_app.command("evaluate")
def patch_evaluate(repo: Path, patch: Path,
                   command: Annotated[str, typer.Option(help="Test argv, such as 'python -m unittest discover -s tests -v'")],
                   oracle_dir: Annotated[Path | None, typer.Option(help="Separate independent tests directory")] = None,
                   oracle_command: Annotated[str, typer.Option(help="Independent test argv")] = "python -m unittest discover -s oracle_tests -v",
                   allowed_file: Annotated[list[str] | None, typer.Option(help="Allowlisted files, repeatable")] = None,
                   engine: Engine = Engine.DOCKER,
                   allow_local: Annotated[bool, typer.Option("--allow-local")] = False,
                   timeout: int = 30,
                   output: Annotated[Path | None, typer.Option(help="Output prefix")] = None) -> None:
    report = evaluate_patch(repo, patch, case_id=repo.name, test_command=shlex.split(command),
                            oracle_dir=oracle_dir, oracle_command=shlex.split(oracle_command),
                            allowed_files=allowed_file, runner=_runner(engine, allow_local),
                            timeout=timeout, engine=engine.value)
    _dump(report.model_dump(mode="json"))
    if output:
        for file in write_reports(report, output):
            typer.echo(f"Wrote {file}", err=True)


@bench_app.command("list")
def benchmark_list(cases_dir: Annotated[Path | None, typer.Option()] = None) -> None:
    _dump([{"id": case.id, "description": case.description} for case in
           list_cases(cases_dir or default_cases_dir())])


@bench_app.command("run")
def benchmark_run(case_id: str,
                  candidate: Annotated[str, typer.Option()] = "correct",
                  engine: Engine = Engine.DOCKER,
                  allow_local: Annotated[bool, typer.Option("--allow-local")] = False,
                  output: Annotated[Path | None, typer.Option(help="Output prefix")] = None,
                  cases_dir: Annotated[Path | None, typer.Option()] = None) -> None:
    result = run_case(cases_dir or default_cases_dir(), case_id, candidate=candidate,
                      runner=_runner(engine, allow_local), engine=engine.value)
    _dump(result.model_dump(mode="json"))
    if output:
        for file in write_reports(result, output):
            typer.echo(f"Wrote {file}", err=True)


@bench_app.command("suite")
def benchmark_suite(engine: Engine = Engine.DOCKER,
                    allow_local: Annotated[bool, typer.Option("--allow-local")] = False,
                    output: Annotated[Path, typer.Option(help="Output directory")] = Path("reports-out/suite"),
                    cases_dir: Annotated[Path | None, typer.Option()] = None) -> None:
    source = cases_dir or default_cases_dir()
    runner = _runner(engine, allow_local)
    reports = []
    for case in list_cases(source):
        # The sixth fixture demonstrates a deceptively successful public suite.
        candidate = "partial" if case.id == "deceptive-test-suite" else "correct"
        report = run_case(source, case.id, candidate=candidate,
                          runner=runner, engine=engine.value)
        reports.append(report)
        write_reports(report, output / case.id)
    result = summary(reports)
    write_summary(result, output / "suite-summary.json")
    _dump(result)


@quality_app.command("analyze")
def quality_analyze(path: Path,
                    coverage_json: Annotated[Path | None, typer.Option()] = None,
                    mutations: Annotated[Path | None, typer.Option()] = None) -> None:
    report = analyze_tests(path, coverage_json)
    result = report.model_dump(mode="json")
    if mutations:
        result["mutation_testing"] = mutation_summary(mutations)
    _dump(result)


@sandbox_app.command("status")
def sandbox_status(image: str = "python:3.11-slim") -> None:
    _dump(docker_status(image))


@app.command("compare")
def compare(reports: Annotated[list[Path], typer.Argument(help="Two or more JSON evaluation reports")]) -> None:
    try:
        _dump(compare_evaluations(reports))
    except (OSError, ValueError, KeyError) as exc:
        raise BenchKitError(f"Cannot compare reports: {exc}", "comparison_invalid") from exc




def run() -> None:
    """Console entry point that formats expected errors without a Python traceback."""
    try:
        app()
    except BenchKitError as exc:
        typer.echo(f"Error [{exc.code}]: {exc}", err=True)
        raise SystemExit(2) from exc

if __name__ == "__main__":
    run()
