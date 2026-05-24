# AgentBenchKit

**Evidence-linked evaluation of coding-agent tool trajectories, Python repository defects, and candidate patches.**

AgentBenchKit is a Python 3.11+ command-line tool for inspecting coding workflows, checking their recorded tool use, reproducing failing tests, applying proposed fixes in disposable workspaces, running independent regression tests, and writing reviewable JSON, Markdown, and HTML reports. It does not require an LLM API, credentials, or paid services.

The framework distinguishes **observed tool behavior**, **infrastructure/tool failures**, **test evidence**, and **human judgments that automation cannot justify**. A zero exit code, an agent's self-reported success, or even a passing test suite is not treated as formal proof of correct behavior.

## What problem does it solve?

Agent coding demos often report only whether an agent produced a patch or whether its final test command exited successfully. This can conceal tool mistakes, incorrect assumptions, repeated failed calls, unintended file changes, inadequate tests, and environmental failures. AgentBenchKit records reproducible observable evidence, keeps test execution separate from the supplied repository, and surfaces limitations explicitly.

## Capabilities

| Component | Available functionality |
| --- | --- |
| Repository inspection | Detect Git commit/branch/status, package manifests, build-system hints, Python compatibility, Python test files |
| Trajectory ingestion | Strict Pydantic v2 JSON schema, normalized tool aliases, validation of event IDs, sequence, timezone and event kind |
| Tool-use assessment | Configurable weighted dimensions for selection, arguments, sequencing, interpretation, recovery, efficiency, safety and contribution; evidence IDs and human-review flags |
| Defect reproduction | Run specified Python test command in a disposable baseline copy; distinguish test failures, setup errors, timeouts and infrastructure failures |
| Patch evaluation | Validate unified diffs; allowlist paths; run `git apply --check`; test candidate in a second disposable copy; preserve original source |
| Regression verification | Independently supplied oracle tests, public-baseline comparison, regression failure detection, edge-case checklist |
| Execution environments | Restricted Docker runner (default) or explicitly opted-in local runner; optional offline dependency wheelhouse |
| Test-quality signals | AST test/assertion discovery, coverage.py JSON ingestion, optional mutation-test summary, missing-evidence warnings |
| Reports and comparison | Pydantic evaluation schemas; JSON, Markdown and escaped HTML reports; compare attempts for the same task/case |
| Fixtures | Six executable Python benchmark cases and four patch variants per case; examples of successful/failed/malformed trajectories |
| Engineering | `src/` package, typed models, automated pytest suite, GitHub Actions matrix, developer tooling, documentation and changelog |

## Architecture

```text
CLI (Typer)
 ├─ trajectory/parser.py → Pydantic events → scoring/evaluator.py
 │                                  └───────→ reports/render.py
 ├─ repository/inspect.py
 ├─ patches/evaluate.py → disposable baseline and candidate repositories
 │     └─ repository/runner.py or sandbox/docker.py → unittest/other argv
 │                                             └────→ reports/render.py
 ├─ benchmark.py → benchmarks/cases/*/{case.json,repo,oracle,patches}
 └─ quality/analyzer.py → coverage and mutation JSON / test AST
```

For detailed boundaries and file responsibilities, see [architecture](docs/architecture.md).

## Install

From this repository's root:

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
agentbenchkit --version
agentbenchkit --help
```

Requires Python 3.11 or later and `git` on PATH for patch checks. Pydantic and Typer are the only mandatory Python runtime dependencies. Developer extras add pytest, pytest-cov, Ruff, mypy and build. **Offline installation:** when the dependencies are already installed locally, use `python -m pip install --no-index --no-build-isolation -e .`; a fresh environment requires packages from an accessible index or local wheel cache.

## Quick start

```bash
# Analyze recorded tool events (no code execution)
agentbenchkit trajectory validate examples/trajectories/success.json
agentbenchkit trajectory score examples/trajectories/failure.json --output reports-out/trajectory

# Inspect a Git/Python repository without executing its code
agentbenchkit repo inspect .

# Enumerate the built-in evaluation cases
agentbenchkit benchmark list

# Default execution policy: Docker, network disabled, non-root, resource limits.
docker pull python:3.11-slim
agentbenchkit benchmark run pagination-boundary --candidate correct \
  --engine docker --output reports-out/pagination

# Only for trusted example code: explicit local execution on the host
agentbenchkit benchmark run pagination-boundary --candidate correct \
  --engine local --allow-local --output reports-out/pagination-local
```

The local-execution mode is **not** a sandbox. Never apply `--allow-local` to a repository you do not trust. Docker containers also have material security limitations: see [Docker security](docs/docker-security.md).

## CLI command reference

| Command | Purpose |
| --- | --- |
| `agentbenchkit --version` | Print package version |
| `agentbenchkit repo inspect PATH` | Detect repository structure, Git metadata and test files |
| `agentbenchkit repo baseline PATH --command 'python -m pytest -q' [--engine docker]` | Execute a command in an ephemeral copy, using the chosen runner |
| `agentbenchkit trajectory validate FILE.json` | Validate trajectory schema and event chronology |
| `agentbenchkit trajectory score FILE.json [--config weights.json] [--output PREFIX]` | Produce evidence-linked deterministic findings |
| `agentbenchkit patch evaluate REPO PATCH --command 'python -m pytest -q' [--oracle-dir PATH] [--allowed-file FILE] [--output PREFIX]` | Test a unified diff in an isolated copy |
| `agentbenchkit benchmark list [--cases-dir DIR]` | Discover supplied benchmark cases |
| `agentbenchkit benchmark run CASE --candidate correct [--engine docker] [--output PREFIX]` | Run one case and candidate patch |
| `agentbenchkit benchmark suite [--engine docker] [--output DIR]` | Run all six included cases and save individual reports plus summary |
| `agentbenchkit quality analyze PATH [--coverage-json coverage.json] [--mutations mutations.json]` | Compute lightweight test-quality signals |
| `agentbenchkit compare REPORT_1.json REPORT_2.json [...]` | Compare multiple runs of the same kind/task |
| `agentbenchkit sandbox status` | Check Docker client, daemon and cached image availability |

Use `agentbenchkit COMMAND --help` for complete options. `--engine docker` is the default for all commands executing repository code. Local execution needs both `--engine local` and `--allow-local`. Docker commands accept `--image` to use an existing runtime image and `--wheelhouse DIR` to install `requirements.txt` offline from wheels to the ephemeral workspace. Docker does not pull images during benchmark execution (`--pull=never`).

A direct patch example:

```bash
agentbenchkit patch evaluate \
  benchmarks/cases/slug-normalization/repo \
  benchmarks/cases/slug-normalization/patches/correct.diff \
  --command 'python -m unittest discover -s tests -v' \
  --oracle-dir benchmarks/cases/slug-normalization/oracle \
  --oracle-command 'python -m unittest discover -s oracle_tests -v' \
  --allowed-file slug.py \
  --engine local --allow-local --output reports-out/slug
```

For non-Python test frameworks or repositories, use the `--command` option with an argv-safe command and an appropriately prepared Docker image.

## Supported agent trajectory schema

Events have explicit IDs, strictly increasing sequence numbers and timezone-aware timestamps. Normalized tools support terminal, file editor, Git and browser-style actions. Unknown tool names must have an explicit supported `kind`; unknown event kinds are rejected.

```json
{
  "schema_version": "1.0",
  "task_id": "example-task",
  "declared_outcome": "unknown",
  "events": [
    {
      "id": "step-1",
      "sequence": 1,
      "timestamp": "2026-10-21T05:00:00Z",
      "kind": "terminal",
      "tool": "bash",
      "arguments": {"command": ["python", "-m", "pytest", "-q"]},
      "result": {"status": "error", "exit_code": 1, "stderr": "1 failed"},
      "purpose": "Reproduce existing failure"
    }
  ]
}
```

Tool result statuses: `success`, `error`, `infra_failure`, `timeout`. Tool results can be absent; these require human review rather than assumed success. `agent_observation` provides optional agent interpretation for contradiction checks. Full examples are in `examples/trajectories/`.

### Scoring semantics

All observable dimension scores begin at 100 and receive deterministic rule-based deductions, capped at zero. Configurable nonnegative weights aggregate only dimensions with observable evidence. An absent/unverifiable dimension is **`null`**, appears in `review_required`, and is excluded from the score denominator. Every finding carries source event IDs. Therefore, `100/100` is only a score of **observable checks**, not a verdict of task correctness. Default safety patterns flag commands such as `rm -rf` and `git push --force`; they are not a comprehensive policy engine.

To set weights and controls, supply JSON matching `ScoreConfig` in `src/agentbenchkit/config.py`. Example:

```json
{
  "weights": {"selection": 1, "arguments": 1, "sequencing": 1,
              "interpretation": 1, "recovery": 1, "efficiency": 0.5,
              "safety": 2, "contribution": 1},
  "allowed_tools": ["bash", "editor", "git"],
  "expected_tools": ["bash"],
  "max_repetitions": 2,
  "forbidden_command_patterns": ["(?i)\\brm\\s+-rf\\b"]
}
```

The scoring engine does **not** infer the semantic appropriateness of a tool from its name, exit status or command alone. More detailed rules are in [evaluation methodology](docs/evaluation-methodology.md).

## Benchmark workflow

Each case includes `repo/` (known bug and public tests), independent `oracle/` tests, patch variants (`correct`, `partial`, `regression`, `does-not-apply`), a manifest, and a named edge-case checklist. The runner:

1. Copies the original twice into disposable, disjoint workspaces.
2. Runs a pre-patch baseline test suite in the baseline copy.
3. Validates patch paths and uses `git apply --check` before applying the diff in the candidate copy.
4. Runs post-patch public tests, then copies in oracle tests that were not available for the patching step.
5. Classifies outcomes; records stdout/stderr, exit code, failed test IDs, patch SHA-256, changed paths, per-edge-check status and environment errors.
6. Deletes temporary workspaces; writes reports outside them if requested.

Candidate classifications include `verified_by_tests`, `incomplete_fix`, `regression_detected`, `unresolved`, `not_reproduced`, `tests_pass_oracle_missing`, `inconclusive_environment`, and `rejected`. These are descriptions of **test evidence**, not mathematical guarantees. See [benchmark design](docs/benchmark-design.md).

## Reports and examples

Reports save three sibling files: `PREFIX.json` (full machine-readable record), `PREFIX.md` (human summary) and `PREFIX.html` (escaped browser report with test logs). `examples/reports/` contains outputs generated by actual benchmark/trajectory executions and not fabricated static fixtures.

```bash
agentbenchkit benchmark suite --engine local --allow-local \
  --output reports-out/suite
agentbenchkit compare examples/reports/suite/slug-normalization.json \
  examples/reports/suite/slug-normalization.json
```

The suite uses the intentionally partial fix for `deceptive-test-suite` to demonstrate a public-pass/oracle-fail outcome. The other five cases use their correct patches.

## Run project tests and checks

```bash
python -m pytest tests -q
python -m pytest tests -q --cov=agentbenchkit --cov-report=term-missing \
  --cov-report=json:coverage.json
ruff check src tests
ruff format --check src tests
mypy src
python -m compileall -q src
```

The GitHub Actions workflow runs these checks on Linux with Python 3.11, 3.12 and 3.13, and contains an independent Docker benchmark smoke test. For a source distribution, build with `python -m build`. Coverage targets apply primarily to core deterministic evaluation logic; actual measured percentages, not claims, should govern confidence.

## Docker and dependencies

Default container controls include `--network=none`, `--cap-drop=ALL`, `no-new-privileges`, read-only root filesystem, a tmpfs, user `65534:65534`, a pids limit, CPU and memory caps, and named-container cleanup. The **workspace is writable** by the non-root container user. Host inputs are copied into temporary directories before being mounted; original files are not mounted. Docker and the required image must be available locally. The `docker/Dockerfile` is a reproducible example of a non-root runtime (base image is versioned); runtime image digest pinning is recommended for serious comparisons. `--wheelhouse` supplies wheels for an offline `pip install --no-index --target=/workspace/.deps`; otherwise repository dependencies must already be in the selected image. The framework does not auto-install arbitrary requirements from the network.

## Known limitations

- Python is the primary supported language. Test command selection is explicit; discovery does not reliably infer every project's runner, dependencies or workflow.
- Trajectory analysis evaluates recorded tool events, not the agent's latent intent. It cannot reliably prove semantic correctness, tool suitability, or comprehensive safety.
- Git patch parser accepts ordinary text unified diffs; binary/rename/quoted-filename patches are unsupported. Symlinks in staged repositories are rejected.
- Benchmark fixtures are deliberately small, synthetic Python defects; six cases are not a representative research benchmark.
- Docker containers are not a full boundary against determined malicious code; use stronger isolation for untrusted adversarial workloads.
- Docker runtime behavior depends on the host daemon, cached image and available wheelhouse. Tests marked for host execution operate only on committed toy fixtures.
- The offline wheelhouse is optional; dependency resolution cannot be guaranteed for arbitrary external repositories.
- A conventional `coverage.json` / simple mutation-summary JSON is supported, not arbitrary third-party report formats.
- The framework compares observable outcomes; human reviewers remain responsible for task-level correctness and whether the tests are adequate.

## Documentation

[Architecture](docs/architecture.md) · [Evaluation methodology](docs/evaluation-methodology.md) · [Benchmark design](docs/benchmark-design.md) · [Docker security](docs/docker-security.md) · [Development roadmap](docs/development-roadmap.md) · [Troubleshooting](docs/troubleshooting.md)

See [CONTRIBUTING.md](CONTRIBUTING.md), [CHANGELOG.md](CHANGELOG.md), and [LICENSE](LICENSE).

## License

MIT. The included benchmark fixtures and test code are part of the same project license.
