import pytest

from agentbenchkit.exceptions import InvalidPatch
from agentbenchkit.patches.evaluate import changed_paths, evaluate_patch
from agentbenchkit.repository.runner import LocalRunner


def test_change_paths_accepts_unified_diff(case_dir):
    patch = (case_dir / "pagination-boundary/patches/correct.diff").read_bytes()
    assert changed_paths(patch) == ["pager.py"]


@pytest.mark.parametrize(
    "patch",
    [
        b"diff --git a/../../secret b/../../secret\n--- a/../../secret\n+++ b/../../secret\n",
        b"diff --git a/.git/config b/.git/config\n--- a/.git/config\n+++ b/.git/config\n",
        b"diff --git a/foo b/bar\n--- a/foo\n+++ b/bar\n",
        b"not a patch",
        b"\xff",
        b"diff --git a/foo b/foo\nGIT binary patch\n",
    ],
)
def test_change_paths_rejects_unsafe_or_invalid_patches(patch):
    with pytest.raises(InvalidPatch):
        changed_paths(patch)


def test_patch_does_not_modify_original_repo(case_dir):
    case = case_dir / "pagination-boundary"
    source = case / "repo/pager.py"
    prior = source.read_bytes()
    report = evaluate_patch(
        case / "repo",
        case / "patches/correct.diff",
        case_id="pagination",
        test_command=[
            "python",
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-v",
        ],
        oracle_dir=case / "oracle",
        oracle_command=[
            "python",
            "-m",
            "unittest",
            "discover",
            "-s",
            "oracle_tests",
            "-v",
        ],
        allowed_files=["pager.py"],
        runner=LocalRunner(True),
    )
    assert report.classification == "verified_by_tests"
    assert source.read_bytes() == prior


def test_unallowed_patch_rejected_before_execution(case_dir):
    case = case_dir / "pagination-boundary"
    report = evaluate_patch(
        case / "repo",
        case / "patches/correct.diff",
        case_id="deny",
        test_command=["nonexistent"],
        oracle_dir=None,
        oracle_command=None,
        allowed_files=["other.py"],
        runner=LocalRunner(True),
    )
    assert report.classification == "rejected"
    assert report.baseline is None
    assert report.unexpected_files == ["pager.py"]


def test_staging_temporary_directories_cleaned_up(case_dir, monkeypatch):
    from agentbenchkit.patches import evaluate as patch_module

    staged = []
    original = patch_module._staged_copy

    def observe(source, destination):
        staged.append(destination)
        return original(source, destination)

    monkeypatch.setattr(patch_module, "_staged_copy", observe)
    case = case_dir / "pagination-boundary"
    report = evaluate_patch(
        case / "repo",
        case / "patches/correct.diff",
        case_id="cleanup",
        test_command=[
            "python",
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-v",
        ],
        oracle_dir=case / "oracle",
        oracle_command=[
            "python",
            "-m",
            "unittest",
            "discover",
            "-s",
            "oracle_tests",
            "-v",
        ],
        allowed_files=["pager.py"],
        runner=LocalRunner(True),
    )
    assert report.classification == "verified_by_tests"
    assert len(staged) == 3
    assert all(not path.exists() for path in staged)
