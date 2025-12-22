"""Shared pytest fixtures for swarm-deployments tests."""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to the fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_deployments_json(fixtures_dir: Path) -> Dict[str, Any]:
    """Load and return the sample deployments.json fixture."""
    with open(fixtures_dir / "sample_deployments.json") as f:
        return json.load(f)


@pytest.fixture
def sample_block_timestamps_json(fixtures_dir: Path) -> Dict[str, Any]:
    """Load and return the sample block_timestamps.json fixture."""
    with open(fixtures_dir / "sample_block_timestamps.json") as f:
        return json.load(f)


@pytest.fixture
def temp_cache_dir(tmp_path: Path) -> Path:
    """Create a temporary cache directory for tests."""
    cache_dir = tmp_path / ".ethswarm-deployments"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


@pytest.fixture
def temp_deployments_cache(temp_cache_dir: Path, sample_deployments_json: Dict[str, Any]) -> Path:
    """Create a temporary deployments.json file with sample data."""
    deployments_path = temp_cache_dir / "deployments.json"
    with open(deployments_path, "w") as f:
        json.dump(sample_deployments_json, f, indent=2)
    return deployments_path


@pytest.fixture
def temp_timestamps_cache(
    temp_cache_dir: Path, sample_block_timestamps_json: Dict[str, Any]
) -> Path:
    """Create a temporary block_timestamps.json file with sample data."""
    timestamps_path = temp_cache_dir / "block_timestamps.json"
    with open(timestamps_path, "w") as f:
        json.dump(sample_block_timestamps_json, f, indent=2)
    return timestamps_path


@pytest.fixture
def hardhat_deploy_sample(fixtures_dir: Path) -> Path:
    """Return path to sample hardhat-deploy JSON file."""
    return fixtures_dir / "hardhat_deploy" / "StakeRegistry.json"


@pytest.fixture
def legacy_deploy_sample(fixtures_dir: Path) -> Path:
    """Return path to sample legacy deployment JSON file."""
    return fixtures_dir / "legacy" / "mainnet_deployed.json"
