# Historical-style capability roadmap and implementation status

**Provenance note:** December 2025–July 2026 are *roadmap phase labels supplied as requirements*, **not** Git commit dates. This implementation and its actual Git history were created in October 2026. Git author and committer timestamps have not been backdated. A completed capability below means its code and available local tests exist; it does not imply independent historical development in the named month.

| Label | Phase | Status | Evidence and qualifications |
| --- | --- | --- | --- |
| Dec 2025 | Package foundation | Implemented | Pydantic, Typer, `src/`, project metadata, Git inspection, pytest; lint/tool config (host tools may be unavailable) |
| Jan 2026 | Trajectory parsing | Implemented | Strict schema, aliases, order/timestamps, malformed fixtures, explicit error messages |
| Feb 2026 | Tool scoring | Partial | Deterministic observable rubrics and evidence IDs; true task contribution, full semantic tool appropriateness and intent remain human-review work |
| Mar 2026 | Repository baseline | Implemented for Python | Git/manifests/test discovery, argv-driven unittest/pytest output parsing, timeouts; arbitrary framework auto-discovery not implemented |
| Apr 2026 | Patch/regression | Implemented for text Git diffs | Disposable workspaces, `git apply --check`, public/oracle comparisons, regression and rejected-patch classification; no binary/rename patches |
| May 2026 | Docker isolation | Implemented; runtime unverified locally | Non-root/no-network/resource limits/cleanup, optional offline wheelhouse; Docker daemon unavailable in build environment |
| Jun 2026 | Test quality and reporting | Implemented with limitations | AST and JSON coverage/mutation signals, edge-case checklist, multi-attempt comparison, JSON/MD/HTML outputs; no fully automated test-quality proof |
| Jul 2026 | CI and release readiness | Implemented; hosted CI unverified | Linux multi-Python matrix, test/lint/type/coverage workflow, Docker smoke workflow, 6 benchmarks, docs, code/test/reports in one repository; workflow must be run in GitHub to confirm |

## Improvements for a research-grade release

1. Add trusted machine-readable test result adapters for Python, Rust, Go and JS rather than relying on stdout text matching.
2. Integrate formal per-task outcome rubrics with verifiable expected artifacts and human review sampling.
3. Evaluate agent resource/token efficiency using elapsed time and tool metadata while accounting for environmental variance.
4. Implement stricter patch file types, diff change scope and semantic restrictions via Git's plumbing and AST analysis.
5. Use dedicated hardened VM execution for hostile code and attest pinned container images.
6. Add held-out real-world repositories with provenance, environment lockfiles, permission to distribute and task-specific oracles.
7. Add calibration/inter-rater studies before making any claims about agreement with human evaluator ratings.
