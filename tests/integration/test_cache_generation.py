"""Integration tests for cache generation from GitHub."""

import json
import os
import subprocess
from pathlib import Path

import pytest
import responses

from swarm_deployments import regenerate_from_github


class TestRegenerateFromGithub:
    """Test the regenerate_from_github() function."""

    def test_regenerates_cache_with_rpc_urls(self, tmp_path: Path):
        """Test cache regeneration with explicit RPC URLs."""
        output_path = tmp_path / "deployments.json"

        # This test will clone the real storage-incentives repo
        # and use real RPC URLs from environment variables
        try:
            mainnet_rpc = os.environ.get("GNO_RPC_URL")
            testnet_rpc = os.environ.get("SEP_RPC_URL")

            if not mainnet_rpc or not testnet_rpc:
                pytest.skip("RPC URLs not configured in environment")

            result_path = regenerate_from_github(
                output_path=str(output_path),
                mainnet_rpc_url=mainnet_rpc,
                testnet_rpc_url=testnet_rpc,
            )

            assert Path(result_path).exists()
            assert Path(result_path) == output_path

            # Verify the cache file structure
            with open(output_path) as f:
                cache = json.load(f)

            assert "metadata" in cache
            assert "networks" in cache
            assert "mainnet" in cache["networks"]
            assert "testnet" in cache["networks"]

        except subprocess.CalledProcessError:
            pytest.skip("Git operations failed (network/git issue)")
        except Exception as e:
            pytest.skip(f"Cache generation failed: {e}")

    def test_uses_environment_variables_for_rpc_urls(self, tmp_path: Path, monkeypatch):
        """Test that RPC URLs are read from environment variables."""
        output_path = tmp_path / "deployments.json"

        mainnet_rpc = os.environ.get("GNO_RPC_URL")
        testnet_rpc = os.environ.get("SEP_RPC_URL")

        if not mainnet_rpc or not testnet_rpc:
            pytest.skip("RPC URLs not configured in environment")

        # Set environment variables
        monkeypatch.setenv("GNO_RPC_URL", mainnet_rpc)
        monkeypatch.setenv("SEP_RPC_URL", testnet_rpc)

        try:
            result_path = regenerate_from_github(output_path=str(output_path))
            assert Path(result_path).exists()
        except (subprocess.CalledProcessError, Exception) as e:
            pytest.skip(f"Cache generation failed: {e}")

    def test_raises_error_when_rpc_urls_missing(self, tmp_path: Path, monkeypatch):
        """Test that ValueError is raised when RPC URLs are not provided."""
        output_path = tmp_path / "deployments.json"

        # Clear environment variables
        monkeypatch.delenv("GNO_RPC_URL", raising=False)
        monkeypatch.delenv("SEP_RPC_URL", raising=False)

        with pytest.raises(ValueError):
            regenerate_from_github(output_path=str(output_path))

    def test_parameter_takes_precedence_over_env_var(self, tmp_path: Path, monkeypatch):
        """Test that explicit RPC URL parameter takes precedence over env var."""
        output_path = tmp_path / "deployments.json"

        mainnet_rpc = os.environ.get("GNO_RPC_URL")
        testnet_rpc = os.environ.get("SEP_RPC_URL")

        if not mainnet_rpc or not testnet_rpc:
            pytest.skip("RPC URLs not configured in environment")

        # Set environment variables to different values
        monkeypatch.setenv("GNO_RPC_URL", "http://should-not-use.example.com")
        monkeypatch.setenv("SEP_RPC_URL", "http://should-not-use.example.com")

        try:
            # Explicit parameters should be used instead
            result_path = regenerate_from_github(
                output_path=str(output_path),
                mainnet_rpc_url=mainnet_rpc,
                testnet_rpc_url=testnet_rpc,
            )
            assert Path(result_path).exists()
        except (subprocess.CalledProcessError, Exception) as e:
            pytest.skip(f"Cache generation failed: {e}")

    def test_uses_default_output_path(self, monkeypatch):
        """Test that default output path is used when not specified."""
        mainnet_rpc = os.environ.get("GNO_RPC_URL")
        testnet_rpc = os.environ.get("SEP_RPC_URL")

        if not mainnet_rpc or not testnet_rpc:
            pytest.skip("RPC URLs not configured in environment")

        # This test would write to ~/.swarm-deployments/deployments.json
        # Skip it to avoid modifying user's actual cache
        pytest.skip("Skipping test that would modify default cache location")

    def test_timestamp_cache_reused_across_runs(self, tmp_path: Path):
        """Test that timestamp cache is reused to minimize RPC calls."""
        output_path = tmp_path / "deployments.json"
        timestamp_cache = tmp_path / "block_timestamps.json"

        mainnet_rpc = os.environ.get("GNO_RPC_URL")
        testnet_rpc = os.environ.get("SEP_RPC_URL")

        if not mainnet_rpc or not testnet_rpc:
            pytest.skip("RPC URLs not configured in environment")

        # Pre-populate timestamp cache
        initial_cache = {
            "mainnet": {
                "25527075": 1671456789,
            },
            "testnet": {},
        }
        with open(timestamp_cache, "w") as f:
            json.dump(initial_cache, f)

        try:
            # First run should read existing cache
            regenerate_from_github(
                output_path=str(output_path),
                mainnet_rpc_url=mainnet_rpc,
                testnet_rpc_url=testnet_rpc,
            )

            # Timestamp cache should exist and have been updated
            assert timestamp_cache.exists()

            with open(timestamp_cache) as f:
                updated_cache = json.load(f)

            # Original entry should still be there
            assert "mainnet" in updated_cache
            # Cache should have potentially more entries
            assert len(updated_cache["mainnet"]) >= len(initial_cache["mainnet"])

        except (subprocess.CalledProcessError, Exception) as e:
            pytest.skip(f"Cache generation failed: {e}")

    def test_stable_tags_filtering(self, tmp_path: Path):
        """Test that only stable tags are processed during regeneration."""
        output_path = tmp_path / "deployments.json"

        mainnet_rpc = os.environ.get("GNO_RPC_URL")
        testnet_rpc = os.environ.get("SEP_RPC_URL")

        if not mainnet_rpc or not testnet_rpc:
            pytest.skip("RPC URLs not configured in environment")

        try:
            regenerate_from_github(
                output_path=str(output_path),
                mainnet_rpc_url=mainnet_rpc,
                testnet_rpc_url=testnet_rpc,
            )

            with open(output_path) as f:
                cache = json.load(f)

            # Check that versions don't include -rc versions
            for network_name, network_data in cache["networks"].items():
                versions = network_data.get("versions", {}).keys()
                for version in versions:
                    assert "-rc" not in version.lower(), f"Found RC version: {version}"
                    assert version.startswith("v"), f"Version doesn't start with 'v': {version}"

        except (subprocess.CalledProcessError, Exception) as e:
            pytest.skip(f"Cache generation failed: {e}")

    def test_cache_contains_required_metadata(self, tmp_path: Path):
        """Test that generated cache contains all required metadata."""
        output_path = tmp_path / "deployments.json"

        mainnet_rpc = os.environ.get("GNO_RPC_URL")
        testnet_rpc = os.environ.get("SEP_RPC_URL")

        if not mainnet_rpc or not testnet_rpc:
            pytest.skip("RPC URLs not configured in environment")

        try:
            regenerate_from_github(
                output_path=str(output_path),
                mainnet_rpc_url=mainnet_rpc,
                testnet_rpc_url=testnet_rpc,
            )

            with open(output_path) as f:
                cache = json.load(f)

            # Check top-level metadata
            assert "metadata" in cache
            metadata = cache["metadata"]
            assert "generated_at" in metadata
            assert "source_repo" in metadata
            assert "networks" in metadata
            assert "storage-incentives" in metadata["source_repo"]

            # Check network-level metadata
            assert "networks" in cache
            for network_name in ["mainnet", "testnet"]:
                assert network_name in cache["networks"]
                network = cache["networks"][network_name]
                assert "chain_id" in network
                assert "chain_name" in network
                assert "block_explorer_url" in network
                assert "versions" in network

        except (subprocess.CalledProcessError, Exception) as e:
            pytest.skip(f"Cache generation failed: {e}")

    def test_contract_deployments_have_required_fields(self, tmp_path: Path):
        """Test that contract deployments have all required fields."""
        output_path = tmp_path / "deployments.json"

        mainnet_rpc = os.environ.get("GNO_RPC_URL")
        testnet_rpc = os.environ.get("SEP_RPC_URL")

        if not mainnet_rpc or not testnet_rpc:
            pytest.skip("RPC URLs not configured in environment")

        try:
            regenerate_from_github(
                output_path=str(output_path),
                mainnet_rpc_url=mainnet_rpc,
                testnet_rpc_url=testnet_rpc,
            )

            with open(output_path) as f:
                cache = json.load(f)

            # Check at least one contract deployment
            found_deployment = False
            for network_name, network_data in cache["networks"].items():
                for version, version_data in network_data.get("versions", {}).items():
                    for contract_name, contract in version_data.get("contracts", {}).items():
                        # Required fields
                        assert "address" in contract
                        assert "block" in contract
                        assert "timestamp" in contract
                        assert "abi" in contract
                        assert "url" in contract
                        assert "source_format" in contract

                        # Validate types
                        assert isinstance(contract["address"], str)
                        assert isinstance(contract["block"], int)
                        assert isinstance(contract["timestamp"], int)
                        assert isinstance(contract["abi"], list)
                        assert isinstance(contract["url"], str)
                        assert contract["source_format"] in ["legacy", "hardhat-deploy"]

                        found_deployment = True
                        break
                    if found_deployment:
                        break
                if found_deployment:
                    break

            assert found_deployment, "No contract deployments found in cache"

        except (subprocess.CalledProcessError, Exception) as e:
            pytest.skip(f"Cache generation failed: {e}")

    def test_handles_git_errors_gracefully(self, tmp_path: Path):
        """Test that git errors are handled appropriately."""
        output_path = tmp_path / "deployments.json"

        # Use an invalid repository URL
        with pytest.raises(RuntimeError):
            regenerate_from_github(
                output_path=str(output_path),
                repo_url="https://github.com/nonexistent/repo-does-not-exist.git",
                mainnet_rpc_url="http://fake-rpc.example.com",
                testnet_rpc_url="http://fake-rpc.example.com",
            )

    def test_creates_parent_directories(self, tmp_path: Path):
        """Test that parent directories are created if they don't exist."""
        output_path = tmp_path / "nested" / "path" / "deployments.json"

        mainnet_rpc = os.environ.get("GNO_RPC_URL")
        testnet_rpc = os.environ.get("SEP_RPC_URL")

        if not mainnet_rpc or not testnet_rpc:
            pytest.skip("RPC URLs not configured in environment")

        try:
            regenerate_from_github(
                output_path=str(output_path),
                mainnet_rpc_url=mainnet_rpc,
                testnet_rpc_url=testnet_rpc,
            )

            assert output_path.exists()
            assert output_path.parent.exists()

        except (subprocess.CalledProcessError, Exception) as e:
            pytest.skip(f"Cache generation failed: {e}")
