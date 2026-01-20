"""Docker runner with non-root runtime and intentionally restrictive defaults.

Containers are defense-in-depth, NOT sufficient isolation for arbitrary hostile code.
"""

import os
import shutil
from pathlib import Path

from agentbenchkit.exceptions import BenchKitError
from agentbenchkit.models import ProcessResult
from agentbenchkit.repository.runner import execute


class DockerRunner:
    def __init__(self, image: str = "python:3.11-slim", *,
                 memory: str = "512m", cpus: float = 1.0,
                 wheelhouse: Path | None = None) -> None:
        if not shutil.which("docker"):
            raise BenchKitError("Docker binary unavailable; install Docker or explicitly use --allow-local",
                                "docker_missing")
        self.image = image
        self.memory = memory
        self.cpus = cpus
        self.wheelhouse = wheelhouse.resolve() if wheelhouse else None
        if self.wheelhouse is not None and not self.wheelhouse.is_dir():
            raise BenchKitError("Wheelhouse directory not found", "wheelhouse_missing")

    def _argv(self, argv: list[str], cwd: Path) -> list[str]:
        cwd = cwd.resolve()
        command = [
            "docker", "run", "--rm", "--pull=never", "--network=none",
            "--cap-drop=ALL", "--security-opt=no-new-privileges", "--pids-limit=128",
            "--read-only", "--tmpfs", "/tmp:rw,nosuid,nodev,size=64m",
            "--memory", self.memory, "--cpus", str(self.cpus),
            "--user", "65534:65534", "--env", "HOME=/tmp",
            "--env", "PYTHONDONTWRITEBYTECODE=1",
            "--env", "PYTHONPATH=/workspace/.deps:/workspace",
            "--volume", f"{cwd}:/workspace:rw", "--workdir", "/workspace",
        ]
        if self.wheelhouse:
            command += ["--volume", f"{self.wheelhouse}:/wheelhouse:ro"]
        return command + [self.image] + argv

    def run(self, argv: list[str], cwd: Path, timeout: int = 30) -> ProcessResult:
        # Staged workspaces are ephemeral. Enable non-root container processes to
        # write temporary test artifacts without giving them ownership of host files.
        for parent, dirs, _ in os.walk(cwd):
            os.chmod(parent, 0o777)
            for directory in dirs:
                dirpath = Path(parent) / directory
                if not dirpath.is_symlink():
                    os.chmod(dirpath, 0o777)
        result = execute(self._argv(argv, cwd), cwd, timeout)
        # Return the requested argv, not the verbose docker invocation.
        return result.model_copy(update={"argv": argv})

    def install_offline_requirements(self, cwd: Path, timeout: int = 120) -> ProcessResult | None:
        """Install from explicitly supplied wheels, never the network."""
        if not (cwd / "requirements.txt").is_file() or self.wheelhouse is None:
            return None
        result = self.run([
            "python", "-m", "pip", "install", "--no-index", "--disable-pip-version-check",
            "--find-links=/wheelhouse", "--target=/workspace/.deps", "-r", "requirements.txt",
        ], cwd, timeout)
        return result


def docker_status(image: str = "python:3.11-slim") -> dict[str, object]:
    if not shutil.which("docker"):
        return {"binary": False, "daemon": False, "image_cached": False}
    daemon = execute(["docker", "info", "--format", "{{.ServerVersion}}"], Path.cwd(), 8)
    if daemon.exit_code:
        return {"binary": True, "daemon": False, "image_cached": False,
                "error": daemon.stderr.strip()}
    cached = execute(["docker", "image", "inspect", image], Path.cwd(), 8)
    return {"binary": True, "daemon": True, "image_cached": cached.exit_code == 0,
            "image": image}
