# Contributing

Contributions should improve correctness, reproducibility, evidence quality or security without inflating benchmark claims. Use Python 3.11+ and create a virtual environment.

```bash
python -m pip install -e ".[dev]"
python -m pytest tests -q
ruff check src tests
ruff format --check src tests
mypy src
```

Keep source modules focused and typed. Introduce a failing test before bug fixes where feasible. For new tool-use rules, document exactly what observable evidence supports the deduction and add at least one counterexample. Do not equate tool errors with agent errors without cause evidence. For new benchmark cases, provide a minimal original repository, a public failing regression where feasible, an independent oracle, a correct patch, a partially correct patch, a regression patch and a non-applicable patch. Tests must have meaningful assertions and must not rely on live network access or credentials.

Security contributions should include a threat-model update in `docs/docker-security.md`. A Docker container is not a hostile-code isolation guarantee. Please never commit API keys, account details or confidential agent trajectories.

Use descriptive conventional commits such as `fix: classify timeout as infrastructure failure`, `test: cover invalid patch traversal` and `docs: explain scoring blind spots`. Submit a focused change with tests and a short description of any new limitations. MIT license applies.
