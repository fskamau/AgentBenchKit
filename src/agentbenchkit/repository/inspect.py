"""Read-only inspection of Python repositories and Git provenance."""

import json
import platform
from pathlib import Path
from typing import Any

from agentbenchkit.exceptions import BenchKitError
from agentbenchkit.repository.runner import execute

MANIFESTS = (
    "pyproject.toml", "requirements.txt", "setup.py", "Pipfile", "poetry.lock",
    "uv.lock", "environment.yml", "package.json", "Cargo.toml", "go.mod",
)


def inspect_repo(path: Path) -> dict[str, Any]:
    path = path.resolve()
    if not path.is_dir():
        raise BenchKitError(f"Repository path does not exist: {path}", "repository_missing")
    manifests = [name for name in MANIFESTS if (path / name).is_file()]
    if (path / "pyproject.toml").is_file():
        build_system = "pyproject"
    elif (path / "setup.py").is_file():
        build_system = "setuptools"
    elif (path / "CMakeLists.txt").is_file():
        build_system = "cmake"
    else:
        build_system = "unknown"
    framework = "pytest" if (path / "pytest.ini").exists() or (path / "conftest.py").exists() else "unittest/undetermined"
    if (path / "tests").is_dir():
        test_files = sorted(p.relative_to(path).as_posix() for p in (path / "tests").rglob("test_*.py"))
    else:
        test_files = []
    commit = execute(["git", "rev-parse", "HEAD"], path, 5)
    branch = execute(["git", "branch", "--show-current"], path, 5)
    git_present = commit.exit_code == 0
    return {
        "path": str(path), "python_runtime": platform.python_version(),
        "compatible_python": tuple(map(int, platform.python_version_tuple()[:2])) >= (3, 11),
        "manifests": manifests, "build_system": build_system,
        "test_framework_hint": framework, "discovered_tests": test_files,
        "git": {"available": git_present,
                "commit": commit.stdout.strip() if git_present else None,
                "branch": branch.stdout.strip() if git_present else None,
                "dirty": (execute(["git", "status", "--porcelain"], path, 5).stdout.strip() != "")
                if git_present else None},
    }


def write_inspection(path: Path, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(inspect_repo(path), indent=2) + "\n", encoding="utf-8")
