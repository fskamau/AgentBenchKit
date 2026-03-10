# Reproducible micro-benchmarks

Six independent Python bug cases are provided. Each case contains a deliberately
flawed `repo/`, public tests, separate `oracle/` regression tests, `case.json`,
and candidate `patches/` (`correct`, `partial`, `regression`, `does-not-apply`).
The original `repo/` is never modified by the evaluation engine.

Five cases deliberately fail their public baseline. `deceptive-test-suite` has
an **inadequate public suite that passes before any fix**; its zero-division defect
is exposed by the independent oracle. This demonstrates why public-test success
is insufficient to establish patch correctness. `partial.diff` in this case
passes public tests and fails oracle tests.

Run from the repository root after installation:

```bash
agentbenchkit benchmark list
agentbenchkit benchmark run pagination-boundary --candidate correct --engine local --allow-local --output reports-out/pagination
agentbenchkit benchmark suite --engine local --allow-local --output reports-out/suite
```

Use `--engine docker` (the default) to run untrusted code in a limited container.
Ensure the `python:3.11-slim` image has been pulled before offline execution.

These are *small deterministic examples*, not a representative sample of real
coding-agent repository complexity. Their results must not be generalized as
agent performance statistics.
