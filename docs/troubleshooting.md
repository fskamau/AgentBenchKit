# Troubleshooting

| Symptom | Cause | Action |
| --- | --- | --- |
| `command not found: agentbenchkit` | Package or entrypoint not installed in active interpreter | Activate venv; `python -m pip install -e .`; or `python -m agentbenchkit.cli --help` from `PYTHONPATH=src` |
| `No module named pydantic` or `typer` | Runtime dependencies unavailable | Install project dependencies from your package index or wheelhouse |
| `pip install` tries to download build requirements while offline | Pip isolated build requires a build backend | If setuptools is already installed, use `python -m pip install --no-index --no-build-isolation -e .` |
| `Docker binary unavailable` | Docker not installed in PATH | Install/start Docker or, for trusted fixtures only, use `--engine local --allow-local` |
| `pull access denied` / image not found | Default Docker runner uses `--pull=never` | `docker pull python:3.11-slim` beforehand or supply cached `--image` |
| `Cannot connect to Docker daemon` | Daemon not started/accessible | Check Docker service, permissions and `docker info` |
| `permission denied` in Docker copy | Non-root UID cannot write a particular file | Ensure staged copy has appropriate permissions; avoid file-level writes outside allocated test output directory |
| `inconclusive_environment` | Failed setup, timeout, missing command/dependency | Inspect `*.json` test `process` fields; do not label agent unsuccessful without review |
| `git apply failed` | Context mismatch, malformed patch or file not present | Confirm patch was generated for the original case's file version; use `git apply --check` in a throwaway copy |
| `rejected` | Non-applicable, binary, unsafe or non-allowlisted patch | Inspect `application_error`, `changed_files`, and allowlist |
| `not_reproduced` | Baseline tests did not fail | Add a failing reproduction and independent oracle before interpreting patch success |
| `incomplete_fix` | Public tests pass but independent tests fail | Inspect oracle stderr and edge-case results; improve patch rather than trusting public green status |
| Benchmark fixtures missing | Installed binary invoked outside source checkout | Change to checkout root or specify `--cases-dir /path/to/benchmarks/cases` |
| No coverage percentage | No coverage JSON supplied | Run `pytest --cov=agentbenchkit --cov-report=json:coverage.json`, then `quality analyze . --coverage-json coverage.json` |

For any unexpected result, keep the JSON report and the original case ID/patch digest. It includes command arguments, exit codes, stderr and reproducibility metadata sufficient for targeted review of the toy fixtures.
