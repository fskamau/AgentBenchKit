import sys

from agentbenchkit.models import ProcessResult
from agentbenchkit.repository.runner import LocalRunner, execute, test_result as classify_test
from agentbenchkit.exceptions import ExecutionDenied

import pytest


def test_host_requires_opt_in():
    with pytest.raises(ExecutionDenied):
        LocalRunner()


def test_argv_is_not_shell_expanded(tmp_path):
    test = LocalRunner(allowed=True).run([sys.executable, "-c", "import sys;print(sys.argv[1])", "$(touch hacked)"], tmp_path, 5)
    assert test.exit_code == 0
    assert "$(touch hacked)" in test.stdout
    assert not (tmp_path / "hacked").exists()


def test_missing_executable_is_infrastructure_failure(tmp_path):
    result = execute(["this-executable-does-not-exist-agentbenchkit"], tmp_path, 5)
    assert result.infrastructure_error
    assert result.exit_code is None


def test_timeout_is_reported(tmp_path):
    result = execute([sys.executable, "-c", "import time;time.sleep(5)"], tmp_path, 1)
    assert result.timed_out
    assert classify_test(result).classification == "timeout"


def test_failing_unittest_output_is_classified(tmp_path):
    result = ProcessResult(argv=["python"], exit_code=1, stdout="",
                           stderr="test_bug (tests.TestBug.test_bug) ... FAIL\nFAILED (failures=1)",
                           duration_seconds=0.1)
    classified = classify_test(result)
    assert classified.classification == "failed"
    assert classified.failed_tests == ["test_bug"]


def test_missing_import_yields_setup_error():
    result = ProcessResult(argv=["pytest"], exit_code=4, stdout="",
                           stderr="ImportError: missing dependency", duration_seconds=0)
    assert classify_test(result).classification == "setup_error"


def test_invalid_command_denied(tmp_path):
    with pytest.raises(Exception, match="nonempty argv"):
        execute([], tmp_path)
