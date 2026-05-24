# Architecture and data boundaries

## Layout

- `src/agentbenchkit/models.py`: Pydantic v2 contracts for trajectories, findings, process/test results, patch results, benchmark manifests and quality signals.
- `config.py`: validated scoring weights, allowed/expected tool lists, repetition and forbidden-command rules.
- `trajectory/parser.py`: reads UTF-8 JSON, normalizes known tool aliases and validates timestamp, unique ID and strict ordering.
- `scoring/evaluator.py`: pure deterministic per-event findings and weighted aggregate. Findings have references to concrete event IDs.
- `repository/inspect.py`: read-only manifest and Git discovery; test files and environment information.
- `repository/runner.py`: argv-only subprocess execution, opt-in local policy, timeout and test-result classification.
- `sandbox/docker.py`: restrictive Docker command generator, runtime check, optional offline wheel dependencies, per-run cleanup.
- `patches/evaluate.py`: path validation, independent temporary workspace construction, patch check/application, baseline vs candidate vs oracle comparison and edge checklist results.
- `quality/analyzer.py`: AST-based test/assertion inspection, coverage.py JSON and optional mutation report ingestion.
- `reports/render.py`: JSON schema serialization, Markdown and safely escaped HTML; comparable multiple attempts.
- `benchmark.py`: manifest validation and reproducible six-case suite.
- `cli.py`: Typer presentation and opt-in execution flags. Functional code does not depend on CLI global state.

## Trust boundaries

A trajectory JSON file is **data** and is never executed by the scoring engine. A patch is **untrusted text**: its paths are parsed and checked before Git applies it to a **copy**. A repository's tests are **arbitrary executable code**, and therefore run in Docker by default; local execution is an explicit, visible opt-in for trusted fixtures only. Regression oracle files are copied into the candidate workspace only **after** application of the patch. Output paths for reports are outside disposable workspaces.

`git apply` does not invoke a shell. Process execution takes an argv array, never interpolates a shell command. Malformed input and subprocess failures are represented as explicit diagnostic errors/result records. Standard output/error are bounded to avoid arbitrary-size reports.

## Key decisions

1. **No LLM grader required.** Deterministic rules can be independently inspected and replayed. Unobservable questions are preserved as review flags rather than filled in with guessed semantics.
2. **Copy-based isolation, not direct worktree mutation.** Every evaluation allocates two separate temporary directory trees, even if the source repository is Git-backed. The source repository's `.git` metadata is inspected but not copied into the staged execution workspace. This avoids changes to the source worktree but may cost more disk/time for large repositories.
3. **Separate oracle test source.** A candidate sees the original test suite while the oracle is introduced post-patch. The oracle is still just an additional test suite, not an absolute truth source.
4. **No uncontrolled dependency installation.** Docker defaults to network-disabled execution. Optional wheelhouse support installs dependencies into the ephemeral workspace only.
5. **Interchange formats are explicit.** Schema version `1.0`; Pydantic enforces types. Scores and classification are serialized with evidence, not summary-only prose.

## Extending to other languages

`Runner` exposes `run(argv, cwd, timeout) -> ProcessResult`; other language adapters can supply an appropriately packaged image, a test-command argv, a failure-output classifier and oracle tests. The current `test_result` output parser recognizes Python unittest/pytest-style failures and is not a general Java/Go/Rust result parser. Preserve setup-failure distinctions for new adapters.
