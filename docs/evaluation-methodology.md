# Evaluation methodology

## Scope

AgentBenchKit is a deterministic **observable-behavior** tool-use evaluator and executable patch validator. It does not assign a probability of human-perceived semantic correctness. Each trajectory has a task ID, ordered events, tool requests and optional results/agent observations. Event IDs provide evidence links.

## Eight rubric dimensions

| Dimension | Observable rule examples | Limitation |
| --- | --- | --- |
| Selection | Tool outside configured allowlist | Does not automatically decide whether the chosen tool was optimal |
| Arguments | Terminal/Git command missing; editor target missing; browser target missing | Cannot know every tool's full argument schema |
| Sequencing | Gaps in recorded sequence IDs | A sequence gap could result from recording loss, not agent failure |
| Interpretation | A success result conflicts with exit code; agent observation claims success after explicit error | Agent observations are free text and can be ambiguous |
| Recovery | Failed identical command reissued with same arguments | Some repetitions are legitimate retries; infra failures are not agent mistakes by default |
| Efficiency | More than configured number of identical requests | Counts are proxy indicators; does not estimate token cost or real-world optimality |
| Safety | Forbidden-command regex and paths outside a relative editing workspace | Not a full security classifier |
| Contribution | No automatic semantic scoring without independent verified task outputs | Human review required by default |

Rules start with 100 for *observable* dimensions, subtract findings' explicit point deductions and floor at zero. Weights are nonnegative and sum only over observable dimensions:

`overall = sum(weight_i * observable_score_i) / sum(weight_i for observable i)`.

If a dimension has insufficient evidence, the result is `null` and requires human review. In particular, contribution is left unscored by default. For judging task completion, use independently reproduced tests plus a human reading of the actual requirements and resulting diff. Do not interpret a 100 observable score as proof that an agent solved the software engineering task.

## Findings and provenance

Each finding has `dimension`, `severity`, `message`, nonempty `evidence_ids`, `deduction` and `category`. Category distinguishes `agent`, `infrastructure`, `uncertain` and `observation`. A Docker service outage, missing executable, timeout, or network failure should not automatically be attributed to the agent. Missing results and incomplete semantic evidence generate review flags. Scoring is pure with respect to a validated trajectory and config.

## Patch classification rules

- **rejected**: patch malformed, changes forbidden files, or fails `git apply` checks.
- **inconclusive_environment**: test runner timed out, did not start, or setup failed.
- **regression_detected**: the modified suite has failed tests not seen among baseline failed-test identifiers.
- **unresolved**: patched public test suite still fails and no new recognizable failing test IDs are found.
- **incomplete_fix**: patched public tests pass, independently supplied oracle tests fail.
- **not_reproduced**: public tests already passed; candidate and oracle pass, but baseline defect was not reproduced.
- **tests_pass_oracle_missing**: baseline fails and patched public tests pass, but no independent oracle was supplied.
- **verified_by_tests**: baseline fails, patched public suite passes, and supplied oracle passes.

The names describe the *available test evidence*. Failing-test extraction is pattern-based for Python unittest and pytest. Other output formats can be classified as setup errors unless adapters are added. `verified_by_tests` is not a guarantee that all real-world edge cases have been captured.

## Consistency and comparison

The recorded trajectory score is reproducible under identical config and event JSON. Benchmarks record patch digest, original Git commit if available, test argv, classifications, stdout/stderr, timeout and duration. Timing is environmental and does not need to reproduce exactly. Multiple attempts may be compared only if their schema kind and task/case ID agree. Differences in the actual environment, test fixture versions or oracle adequacy should be reviewed before ranking attempts.
