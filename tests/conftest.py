"""Tests intentionally opt into host execution only for committed toy fixtures."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def case_dir() -> Path:
    return ROOT / "benchmarks" / "cases"
