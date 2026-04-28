import json
from pathlib import Path

from typer.testing import CliRunner

from agentbenchkit.cli import app

runner = CliRunner()
ROOT = Path(__file__).resolve().parents[2]


def test_cli_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "benchmark" in result.stdout


def test_cli_trajectory_validate():
    result = runner.invoke(app, ["trajectory", "validate",
                                 str(ROOT / "examples/trajectories/success.json")])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["events"] == 3


def test_cli_trajectory_score_with_written_files(tmp_path):
    result = runner.invoke(app, ["trajectory", "score",
                                 str(ROOT / "examples/trajectories/failure.json"),
                                 "--output", str(tmp_path / "scored")])
    assert result.exit_code == 0, result.output
    assert json.loads((tmp_path / "scored.json").read_text())["task_id"]


def test_cli_list_benchmarks():
    result = runner.invoke(app, ["benchmark", "list", "--cases-dir",
                                 str(ROOT / "benchmarks/cases")])
    assert result.exit_code == 0
    assert len(json.loads(result.stdout)) == 6


def test_cli_end_to_end_benchmark(tmp_path):
    result = runner.invoke(app, ["benchmark", "run", "retry-backoff", "--engine", "local",
                                 "--allow-local", "--output", str(tmp_path / "report")])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["classification"] == "verified_by_tests"
    assert (tmp_path / "report.html").is_file()


def test_cli_denies_host_execution_without_flag():
    result = runner.invoke(app, ["benchmark", "run", "slug-normalization", "--engine", "local"])
    assert result.exit_code != 0
    assert "Host execution denied" in result.output or isinstance(result.exception, Exception)
