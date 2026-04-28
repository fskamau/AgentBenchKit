import json
from pathlib import Path

import pytest

from agentbenchkit.config import ScoreConfig, load_config, save_config
from agentbenchkit.exceptions import BenchKitError
from agentbenchkit.repository.inspect import inspect_repo


def test_repo_inspection_git_and_manifests():
    root = Path(__file__).resolve().parents[2]
    info = inspect_repo(root)
    assert info["git"]["available"]
    assert len(info["git"]["commit"]) == 40
    assert "pyproject.toml" in info["manifests"]
    assert info["compatible_python"]
    assert info["discovered_tests"]


def test_repo_inspection_missing_path(tmp_path):
    with pytest.raises(BenchKitError, match="does not exist"):
        inspect_repo(tmp_path / "missing")


def test_config_save_load(tmp_path):
    path = tmp_path / "custom.json"
    config = ScoreConfig(max_repetitions=4, allowed_tools={"bash"})
    save_config(config, path)
    assert load_config(path).max_repetitions == 4
    assert load_config(path).allowed_tools == {"bash"}
    path.write_text(json.dumps({"weights": {"a": 1}}))
    with pytest.raises(BenchKitError, match="Cannot read scoring config"):
        load_config(path)
