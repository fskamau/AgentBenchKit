# Benchmark case design

## Case contract

`benchmarks/cases/<id>/case.json` declares `id`, `description`, `test_command` argv, `oracle_command` argv, `allowed_changed_files`, `edge_cases`, and `timeout_seconds`. Each case has a `repo/` tree, `oracle/` tree, and `patches/{correct,partial,regression,does-not-apply}.diff`.

The pipeline stages a baseline copy and an entirely separate candidate copy; runs the test command in baseline; validates and applies the patch only in the candidate; reruns public tests; copies the independent oracle into the candidate; and runs oracle tests. No source fixture is overwritten by evaluation. The format is designed to be reviewable: every defect and expected behavior is visible in actual source and tests.

## Included cases

| Case | Defect demonstrated | Oracle scenarios |
| --- | --- | --- |
| `slug-normalization` | Literal-space substitution fails whitespace/punctuation normalization | Punctuation, underscores and all-punctuation empty result |
| `pagination-boundary` | Floor division undercounts partial pages | One item, invalid size, negative item count |
| `nested-config-merge` | Shallow dict update deletes nested defaults | Third-level merge and input immutability |
| `retry-backoff` | One too many delays, final unnecessary wait | Zero attempts and invalid arguments |
| `numeric-version-order` | Lexicographic sort mishandles multi-digit version components | Patch component sort and invalid syntax |
| `deceptive-test-suite` | Broken zero-division behavior goes untested in public suite | Zero and zero-over-zero raise ZeroDivisionError |

The suite defaults to correct candidate patches for the first five and an intentionally partial candidate for `deceptive-test-suite`. Therefore, **an incomplete fix is an intentional, successful detection outcome**, not a framework failure. Candidate patches are supplied with the framework; no AI agent is invoked. For representative agent comparisons, gather real trajectories and candidate patches independently and run them against held-out tasks with sufficient independent tests.

## Interpretation

A successful reproduction is baseline public-test failure. A passing independent oracle increases confidence that the fix did not merely satisfy weak public tests, but does not prove full functional equivalence or hidden specification compliance. `edge_cases` names a checklist of oracle method IDs and reports `passed`, `failed` or `missing`. These statuses are based on recognized unittest method output; mismatches should be reviewed.

## Non-goals

The synthetic suite does not claim representative difficulty, adversarial robustness, statistically valid agent rankings, or state-of-the-art SWE-bench equivalence. It has no online score registry, external dependencies, or real agent API clients. New cases should be small enough to run deterministically, contain meaningful distinct regressions, and explicitly document known blind spots.
