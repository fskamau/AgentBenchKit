# Build verification record — 2026-10-21 (UTC)

This record reflects checks executed in the project creation environment, not a hosted CI result or fabricated historical milestone data.

## Executed successfully

- Runtime: Python 3.13.5; Git 2.47.3; installed Pydantic 2.13.5 and Typer 0.26.3.
- Editable package installation: `python -m pip install --no-index --no-build-isolation -e .` succeeded using already installed build/runtime dependencies.
- Wheel build: `python -m pip wheel --no-index --no-build-isolation --no-deps . --wheel-dir /tmp/agentbenchkit-wheel` succeeded, producing `agentbenchkit-0.1.0-py3-none-any.whl`.
- CLI: `agentbenchkit --version`, `--help`, trajectory validation, scoring, repo inspection and real benchmark execution checked.
- Test command: `python -m pytest tests -q --cov=agentbenchkit --cov-report=term-missing --cov-report=json:coverage.json`.
- **73 passed, 0 failed, 0 skipped** (as recorded before final archive packaging).
- Coverage: **83.43%** total measured statements (745/893); trajectory parser ~94.9%, scoring evaluator ~94.2%, patch evaluator ~84.6%. The generated detailed report is `examples/reports/coverage.json`.
- Benchmark suite: **6 cases**, 5 `verified_by_tests` and 1 intentionally `incomplete_fix`; no inflated correctness claim. See `examples/reports/suite/suite-summary.json`.
- JSON, Markdown and HTML sample reports regenerated from real framework executions, not illustrative invented scores.
- Python source bytecode compilation executed successfully with `python -m compileall -q src`.

## Not independently verified here

- Docker binary/daemon were unavailable; runtime Docker smoke execution and container restrictions were reviewed in code and tested with mocks, but not executed against a real daemon.
- Ruff, mypy and the Python `build` frontend were unavailable in the environment; GitHub Actions config includes Ruff lint/format checks, mypy, tests, coverage, Python 3.11–3.13 and a Docker smoke job, but these hosted checks **have not yet run**.
- Fresh dependency installation in a completely isolated, dependency-free virtual environment could not be verified without package index access. Package installation with existing dependencies and an offline wheel build both succeeded.
- Large real-world Python repositories, non-Python languages, untrusted hostile code workloads and multi-node remote execution have not been benchmarked.

See `docs/development-roadmap.md` and `docs/docker-security.md` for scope and remaining limitations. Exact Git history and the ZIP extraction smoke test are verified during final packaging.
