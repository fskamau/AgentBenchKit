from pathlib import Path

import pytest

from agentbenchkit.exceptions import BenchKitError
from agentbenchkit.models import ProcessResult
from agentbenchkit.sandbox import docker as docker_module


def test_missing_docker_fails_cleanly(monkeypatch):
    monkeypatch.setattr(docker_module.shutil, "which", lambda _: None)
    with pytest.raises(BenchKitError, match="Docker binary unavailable"):
        docker_module.DockerRunner()


def test_flags_enforce_resource_policy(monkeypatch, tmp_path):
    monkeypatch.setattr(docker_module.shutil, "which", lambda _: "/usr/bin/docker")
    runner = docker_module.DockerRunner()
    argv = runner._argv(["python", "--version"], tmp_path, "abk-test")
    assert "--network=none" in argv
    assert "--cap-drop=ALL" in argv
    assert "--read-only" in argv
    assert argv[argv.index("--user") + 1] == "65534:65534"
    assert "--memory" in argv and "--cpus" in argv
    assert "--rm" in argv
    assert argv[-2:] == ["python", "--version"]


def test_cleanup_attempted_even_after_timeout(monkeypatch, tmp_path):
    monkeypatch.setattr(docker_module.shutil, "which", lambda _: "/usr/bin/docker")
    calls = []
    def fake_execute(argv, cwd, timeout):
        calls.append(argv)
        return ProcessResult(argv=argv, exit_code=None if "run" in argv else 0,
                             stdout="", stderr="", timed_out="run" in argv,
                             duration_seconds=0.01)
    monkeypatch.setattr(docker_module, "execute", fake_execute)
    docker_module.DockerRunner().run(["python", "--version"], tmp_path, 1)
    assert any(argv[0:3] == ["docker", "rm", "-f"] for argv in calls)


def test_status_reports_missing_binary(monkeypatch):
    monkeypatch.setattr(docker_module.shutil, "which", lambda _: None)
    assert docker_module.docker_status() == {"binary": False, "daemon": False,
                                               "image_cached": False}
