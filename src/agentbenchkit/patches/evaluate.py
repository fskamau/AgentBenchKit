"""Apply untrusted unified diffs exclusively to temporary copies of a repository."""

import hashlib
import re
import shutil
import subprocess
import tempfile
from pathlib import Path, PurePosixPath

from agentbenchkit.exceptions import BenchKitError, InvalidPatch
from agentbenchkit.models import PatchReport, TestResult
from agentbenchkit.repository.inspect import inspect_repo
from agentbenchkit.repository.runner import Runner, test_result

MAX_PATCH_BYTES = 2_000_000


def _safe_relative(value: str) -> bool:
    path = PurePosixPath(value)
    return (bool(value) and not path.is_absolute() and not any(
        part in ("..", "", ".git") for part in path.parts
    ) and "\\" not in value and not value.startswith("-"))


def changed_paths(patch: bytes) -> list[str]:
    if len(patch) > MAX_PATCH_BYTES:
        raise InvalidPatch(f"Patch exceeds size limit of {MAX_PATCH_BYTES} bytes")
    try:
        source = patch.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InvalidPatch("Patch must be UTF-8 text; binary diffs are unsupported") from exc
    # For consistent path validation, reject Git's quoted special-filename syntax.
    if re.search(r'(?m)^diff --git "', source):
        raise InvalidPatch("Quoted Git filenames in diff headers are unsupported")
    paths: list[str] = []
    for line in source.splitlines():
        if line.startswith("diff --git "):
            match = re.fullmatch(r"diff --git a/(.*?) b/(.*?)", line)
            if not match or not all(_safe_relative(name) for name in match.groups()):
                raise InvalidPatch(f"Unsafe or malformed diff header: {line}")
            if match.group(1) != match.group(2):
                raise InvalidPatch("Renames are intentionally unsupported")
            paths.append(match.group(2))
        if line.startswith(("+++ ", "--- ")):
            token = line[4:].split("\t", 1)[0]
            if token != "/dev/null":
                if not token.startswith(("a/", "b/")) or not _safe_relative(token[2:]):
                    raise InvalidPatch(f"Unsafe patch path: {token}")
        if line.startswith(("GIT binary patch", "Binary files ")):
            raise InvalidPatch("Binary patches are unsupported")
    if not paths:
        raise InvalidPatch("No Git unified-diff file headers found")
    return sorted(set(paths))


def _staged_copy(source: Path, target: Path) -> None:
    if target.exists():
        raise BenchKitError(f"Destination already exists: {target}")
    shutil.copytree(source, target, symlinks=True,
                    ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache",
                                                   ".mypy_cache", ".ruff_cache", ".venv"))
    if any(item.is_symlink() for item in target.rglob("*")):
        raise BenchKitError("Repository contains symlinks; refusing staging for host safety",
                            "repository_symlink")


def _apply_patch(workspace: Path, patch_file: Path) -> str | None:
    for flags in (["--check"], []):
        proc = subprocess.run(["git", "apply", *flags, str(patch_file)],
                              cwd=workspace, capture_output=True, text=True, check=False,
                              timeout=20)
        if proc.returncode:
            return (proc.stderr or proc.stdout).strip() or "git apply failed"
    return None


def _run_test(command: list[str], cwd: Path, runner: Runner, timeout: int) -> TestResult:
    return test_result(runner.run(command, cwd, timeout))


def _prepare_deps(runner: Runner, cwd: Path) -> str | None:
    installer = getattr(runner, "install_offline_requirements", None)
    if installer is None:
        return None
    install_result = installer(cwd)
    if install_result is not None and install_result.exit_code != 0:
        return f"Offline dependency install failed: {install_result.stderr or install_result.stdout}"
    return None


def evaluate_patch(source_repo: Path, patch_file: Path, *, case_id: str,
                   test_command: list[str], oracle_dir: Path | None,
                   oracle_command: list[str] | None, allowed_files: list[str] | None,
                   runner: Runner, timeout: int = 30, engine: str = "local") -> PatchReport:
    """Use disjoint baseline and candidate copies; independent tests are inserted post-patch."""
    source_repo, patch_file = source_repo.resolve(), patch_file.resolve()
    if not source_repo.is_dir():
        raise BenchKitError(f"Missing source repository {source_repo}", "repository_missing")
    try:
        payload = patch_file.read_bytes()
    except OSError as exc:
        raise BenchKitError(f"Cannot read patch {patch_file}: {exc}", "patch_missing") from exc
    digest = hashlib.sha256(payload).hexdigest()
    meta = inspect_repo(source_repo)
    base_commit = meta["git"]["commit"]
    try:
        files = changed_paths(payload)
    except InvalidPatch as exc:
        return PatchReport(case_id=case_id, base_commit=base_commit, patch_sha256=digest,
                           changed_files=[], patch_applied=False, application_error=str(exc),
                           classification="rejected", evidence=[str(exc)], engine=engine)  # type: ignore[arg-type]
    unexpected = sorted(set(files) - set(allowed_files)) if allowed_files is not None else []
    if unexpected:
        msg = "Patch touches files outside the allowlist: " + ", ".join(unexpected)
        return PatchReport(case_id=case_id, base_commit=base_commit, patch_sha256=digest,
                           changed_files=files, unexpected_files=unexpected, patch_applied=False,
                           application_error=msg, classification="rejected",
                           evidence=[msg], engine=engine)  # type: ignore[arg-type]
    with tempfile.TemporaryDirectory(prefix="agentbenchkit-") as temporary:
        parent = Path(temporary)
        baseline_repo, candidate_repo = parent / "baseline", parent / "candidate"
        _staged_copy(source_repo, baseline_repo)
        _staged_copy(source_repo, candidate_repo)
        dep_error = _prepare_deps(runner, baseline_repo)
        if dep_error:
            raise BenchKitError(dep_error, "dependency_install_failed")
        baseline = _run_test(test_command, baseline_repo, runner, timeout)
        error = _apply_patch(candidate_repo, patch_file)
        if error:
            return PatchReport(case_id=case_id, base_commit=base_commit, patch_sha256=digest,
                               changed_files=files, patch_applied=False, application_error=error,
                               baseline=baseline, classification="rejected", evidence=[
                                   "Patch rejected by git apply --check/apply", error],
                               engine=engine)  # type: ignore[arg-type]
        dep_error = _prepare_deps(runner, candidate_repo)
        if dep_error:
            raise BenchKitError(dep_error, "dependency_install_failed")
        patched = _run_test(test_command, candidate_repo, runner, timeout)
        oracle: TestResult | None = None
        if oracle_dir is not None:
            oracle_path = oracle_dir.resolve()
            if not oracle_path.is_dir() or not oracle_command:
                raise BenchKitError("Oracle tests requested but directory/command missing",
                                    "oracle_invalid")
            if (candidate_repo / "oracle_tests").exists():
                raise BenchKitError("Repository reserves oracle_tests directory", "oracle_collision")
            _staged_copy(oracle_path, candidate_repo / "oracle_tests")
            oracle = _run_test(oracle_command, candidate_repo, runner, timeout)

    evidence = [f"Baseline: {baseline.classification}", f"Patched: {patched.classification}"]
    if oracle:
        evidence.append(f"Independent oracle tests: {oracle.classification}")
    if patched.failed_tests:
        evidence.append("Patched failing tests: " + ", ".join(patched.failed_tests))
    if oracle and oracle.failed_tests:
        evidence.append("Oracle failing tests: " + ", ".join(oracle.failed_tests))
    if any(item.classification in {"setup_error", "timeout", "infrastructure_error"}
           for item in (baseline, patched, *([oracle] if oracle else []))):
        classification = "inconclusive_environment"
    elif patched.classification != "passed":
        introduced = set(patched.failed_tests) - set(baseline.failed_tests)
        classification = "regression_detected" if introduced else "unresolved"
    elif oracle and oracle.classification != "passed":
        classification = "incomplete_fix"
    elif baseline.classification == "passed":
        classification = "not_reproduced"
    elif oracle is None:
        classification = "tests_pass_oracle_missing"
    else:
        classification = "verified_by_tests"
    evidence.append("Passing tests do not constitute proof of semantic correctness.")
    return PatchReport(case_id=case_id, base_commit=base_commit, patch_sha256=digest,
                       changed_files=files, patch_applied=True, baseline=baseline,
                       patched=patched, oracle=oracle, classification=classification,
                       evidence=evidence, engine=engine)  # type: ignore[arg-type]
