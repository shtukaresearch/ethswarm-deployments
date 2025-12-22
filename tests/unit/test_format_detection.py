"""Unit tests for deployment format detection."""

from pathlib import Path

import pytest

from ethswarm_deployments.parsers import DeploymentFormat, detect_deployment_format


class TestDetectDeploymentFormat:
    """Test the detect_deployment_format function."""

    def test_detects_hardhat_deploy_format(self, tmp_path: Path):
        """Test detection of hardhat-deploy format."""
        # Create deployments/mainnet/ directory with .json files
        deployments_dir = tmp_path / "deployments" / "mainnet"
        deployments_dir.mkdir(parents=True)
        (deployments_dir / "Token.json").write_text("{}")
        (deployments_dir / "StakeRegistry.json").write_text("{}")

        result = detect_deployment_format(tmp_path, "mainnet")
        assert result == DeploymentFormat.HARDHAT_DEPLOY

    def test_detects_legacy_format(self, tmp_path: Path):
        """Test detection of legacy format."""
        # Create mainnet_deployed.json file
        (tmp_path / "mainnet_deployed.json").write_text("{}")

        result = detect_deployment_format(tmp_path, "mainnet")
        assert result == DeploymentFormat.LEGACY

    def test_detects_none_when_no_files_exist(self, tmp_path: Path):
        """Test returns None when no deployment files found."""
        result = detect_deployment_format(tmp_path, "mainnet")
        assert result is None

    def test_hardhat_deploy_priority_over_legacy(self, tmp_path: Path):
        """Test that hardhat-deploy format is checked first."""
        # Create both formats
        deployments_dir = tmp_path / "deployments" / "mainnet"
        deployments_dir.mkdir(parents=True)
        (deployments_dir / "Token.json").write_text("{}")
        (tmp_path / "mainnet_deployed.json").write_text("{}")

        # Should return hardhat-deploy since it has priority
        result = detect_deployment_format(tmp_path, "mainnet")
        assert result == DeploymentFormat.HARDHAT_DEPLOY

    def test_detects_testnet_hardhat_deploy(self, tmp_path: Path):
        """Test detection of hardhat-deploy format for testnet."""
        deployments_dir = tmp_path / "deployments" / "testnet"
        deployments_dir.mkdir(parents=True)
        (deployments_dir / "Token.json").write_text("{}")

        result = detect_deployment_format(tmp_path, "testnet")
        assert result == DeploymentFormat.HARDHAT_DEPLOY

    def test_detects_testnet_legacy(self, tmp_path: Path):
        """Test detection of legacy format for testnet."""
        (tmp_path / "testnet_deployed.json").write_text("{}")

        result = detect_deployment_format(tmp_path, "testnet")
        assert result == DeploymentFormat.LEGACY

    def test_empty_deployments_directory_returns_none(self, tmp_path: Path):
        """Test that empty deployments directory is treated as no format."""
        # Create deployments/mainnet/ but with no .json files
        deployments_dir = tmp_path / "deployments" / "mainnet"
        deployments_dir.mkdir(parents=True)

        # Should return None because no .json files exist
        result = detect_deployment_format(tmp_path, "mainnet")
        assert result is None

    def test_deployments_directory_with_non_json_files(self, tmp_path: Path):
        """Test that non-.json files in deployments directory are ignored."""
        deployments_dir = tmp_path / "deployments" / "mainnet"
        deployments_dir.mkdir(parents=True)
        (deployments_dir / "README.md").write_text("# Readme")
        (deployments_dir / ".gitkeep").write_text("")

        # Should return None because no .json files exist
        result = detect_deployment_format(tmp_path, "mainnet")
        assert result is None
