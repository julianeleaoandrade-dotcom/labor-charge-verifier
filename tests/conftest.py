from pathlib import Path

import pytest

from labor_charge_verifier.common import load_config

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def config():
    return load_config(ROOT / "config" / "settings.example.yaml")


@pytest.fixture
def sample_dir():
    return ROOT / "sample-data"
