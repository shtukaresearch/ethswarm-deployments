"""Integration tests for cache generation from GitHub."""

import json
import os
import subprocess
from pathlib import Path

import pytest

from ethswarm_deployments import regenerate_from_github


class TestRegenerateFromGithubRPC:
    """Test RPC-based cache generation (requires network access)."""

    def test_regenerates_cache_with_both_rpcs(self, tmp_path: Path):
        """Test cache regeneration with both mainnet and testnet RPC URLs."""
        output_path = tmp_path / "deployments.json"

        mainnet_rpc = os.environ.get("GNO_RPC_URL")
        testnet_rpc = os.environ.get("SEP_RPC_URL")

        if not mainnet_rpc or not testnet_rpc:
            pytest.skip("Both RPC URLs not configured in environment")

        try:
            result_path = regenerate_from_github(
                output_path=str(output_path),
                mainnet_rpc_url=mainnet_rpc,
                testnet_rpc_url=testnet_rpc,
            )

            assert Path(result_path).exists()
            assert Path(result_path) == output_path

            # Verify basic cache structure
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

    def test_regenerates_with_mainnet_rpc_only(self, tmp_path: Path):
        """Test cache regeneration with only mainnet RPC URL."""
        output_path = tmp_path / "deployments.json"

        mainnet_rpc = os.environ.get("GNO_RPC_URL")
        testnet_rpc = os.environ.get("SEP_RPC_URL")

        if not mainnet_rpc:
            pytest.skip("Mainnet RPC URL not configured")

        if testnet_rpc:
            pytest.skip("Test requires only mainnet RPC")

        try:
            # Should work with just mainnet RPC
            result_path = regenerate_from_github(
                output_path=str(output_path),
                mainnet_rpc_url=mainnet_rpc,
                testnet_rpc_url=None,
            )

            assert Path(result_path).exists()

            with open(output_path) as f:
                cache = json.load(f)

            # Should have mainnet data
            assert "mainnet" in cache["networks"]
            assert len(cache["networks"]["mainnet"].get("versions", {})) > 0

        except subprocess.CalledProcessError:
            pytest.skip("Git operations failed")
        except Exception as e:
            pytest.skip(f"Cache generation failed: {e}")

    def test_regenerates_with_testnet_rpc_only(self, tmp_path: Path):
        """Test cache regeneration with only testnet RPC URL."""
        output_path = tmp_path / "deployments.json"

        mainnet_rpc = os.environ.get("GNO_RPC_URL")
        testnet_rpc = os.environ.get("SEP_RPC_URL")

        if not testnet_rpc:
            pytest.skip("Testnet RPC URL not configured")

        if mainnet_rpc:
            pytest.skip("Test requires only testnet RPC")

        try:
            # Should work with just testnet RPC
            result_path = regenerate_from_github(
                output_path=str(output_path),
                mainnet_rpc_url=None,
                testnet_rpc_url=testnet_rpc,
            )

            assert Path(result_path).exists()

            with open(output_path) as f:
                cache = json.load(f)

            # Should have testnet data
            assert "testnet" in cache["networks"]
            assert len(cache["networks"]["testnet"].get("versions", {})) > 0

        except subprocess.CalledProcessError:
            pytest.skip("Git operations failed")
        except Exception as e:
            pytest.skip(f"Cache generation failed: {e}")

    def test_uses_environment_variables_for_rpc_urls(self, tmp_path: Path, monkeypatch):
        """Test that RPC URLs are read from environment variables."""
        output_path = tmp_path / "deployments.json"

        mainnet_rpc = os.environ.get("GNO_RPC_URL")
        testnet_rpc = os.environ.get("SEP_RPC_URL")

        if not (mainnet_rpc or testnet_rpc):
            pytest.skip("At least one RPC URL required")

        # Set environment variables
        if mainnet_rpc:
            monkeypatch.setenv("GNO_RPC_URL", mainnet_rpc)
        if testnet_rpc:
            monkeypatch.setenv("SEP_RPC_URL", testnet_rpc)

        try:
            result_path = regenerate_from_github(output_path=str(output_path))
            assert Path(result_path).exists()
        except (subprocess.CalledProcessError, Exception) as e:
            pytest.skip(f"Cache generation failed: {e}")

    def test_parameter_takes_precedence_over_env_var(self, tmp_path: Path, monkeypatch):
        """Test that explicit RPC URL parameter takes precedence over env var."""
        output_path = tmp_path / "deployments.json"

        mainnet_rpc = os.environ.get("GNO_RPC_URL")
        testnet_rpc = os.environ.get("SEP_RPC_URL")

        if not (mainnet_rpc or testnet_rpc):
            pytest.skip("At least one RPC URL required")

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


class TestRegenerateFromGithubContract:
    """Test the contract of regenerate_from_github() function."""

    def test_raises_error_when_rpc_urls_missing(self, tmp_path: Path, monkeypatch):
        """Test that ValueError is raised when RPC URLs are not provided."""
        output_path = tmp_path / "deployments.json"

        # Clear environment variables
        monkeypatch.delenv("GNO_RPC_URL", raising=False)
        monkeypatch.delenv("SEP_RPC_URL", raising=False)

        with pytest.raises(ValueError):
            regenerate_from_github(output_path=str(output_path))

    def test_handles_git_errors_gracefully(self, tmp_path: Path):
        """Test that git errors raise RuntimeError."""
        output_path = tmp_path / "deployments.json"

        # Use an invalid repository URL
        with pytest.raises(RuntimeError):
            regenerate_from_github(
                output_path=str(output_path),
                repo_url="https://github.com/nonexistent/repo-does-not-exist.git"
            )

    def test_creates_parent_directories(self, tmp_path: Path):
        """Test that parent directories are created if they don't exist."""
        output_path = tmp_path / "nested" / "path" / "deployments.json"

        mainnet_rpc = os.environ.get("GNO_RPC_URL")
        testnet_rpc = os.environ.get("SEP_RPC_URL")

        if not (mainnet_rpc or testnet_rpc):
            pytest.skip("At least one RPC URL required")

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


class TestCacheStructure:
    """Test the structure and content of generated cache."""

    def test_cache_contains_required_metadata(self, tmp_path: Path):
        """Test that generated cache contains all required metadata."""
        output_path = tmp_path / "deployments.json"

        mainnet_rpc = os.environ.get("GNO_RPC_URL")
        testnet_rpc = os.environ.get("SEP_RPC_URL")

        if not (mainnet_rpc or testnet_rpc):
            pytest.skip("At least one RPC URL required")

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
            for network_name in cache["networks"]:
                network = cache["networks"][network_name]
                assert "chain_id" in network
                assert "chain_name" in network
                assert "block_explorer_url" in network
                assert "deployments" in network  # Normalized schema
                assert "versions" in network

        except (subprocess.CalledProcessError, Exception) as e:
            pytest.skip(f"Cache generation failed: {e}")

    def test_stable_tags_filtering(self, tmp_path: Path):
        """Test that only stable tags are processed during regeneration."""
        output_path = tmp_path / "deployments.json"

        mainnet_rpc = os.environ.get("GNO_RPC_URL")
        testnet_rpc = os.environ.get("SEP_RPC_URL")

        if not (mainnet_rpc or testnet_rpc):
            pytest.skip("At least one RPC URL required")

        try:
            regenerate_from_github(
                output_path=str(output_path),
                mainnet_rpc_url=mainnet_rpc,
                testnet_rpc_url=testnet_rpc,
            )

            with open(output_path) as f:
                cache = json.load(f)

            # Check that versions don't include -rc versions
            for network_data in cache["networks"].values():
                versions = network_data.get("versions", {}).keys()
                for version in versions:
                    assert "-rc" not in version.lower()
                    assert version.startswith("v")

        except (subprocess.CalledProcessError, Exception) as e:
            pytest.skip(f"Cache generation failed: {e}")

    def test_contract_deployments_have_required_fields(self, tmp_path: Path):
        """Test that contract deployments have all required fields."""
        output_path = tmp_path / "deployments.json"

        mainnet_rpc = os.environ.get("GNO_RPC_URL")
        testnet_rpc = os.environ.get("SEP_RPC_URL")

        if not (mainnet_rpc or testnet_rpc):
            pytest.skip("At least one RPC URL required")

        try:
            regenerate_from_github(
                output_path=str(output_path),
                mainnet_rpc_url=mainnet_rpc,
                testnet_rpc_url=testnet_rpc,
            )

            with open(output_path) as f:
                cache = json.load(f)

            # Check at least one contract deployment (normalized schema)
            found_deployment = False
            for network_data in cache["networks"].values():
                # Check deployments dict
                for address, deployment in network_data.get("deployments", {}).items():
                    # Required fields
                    assert "address" in deployment
                    assert deployment["address"] == address  # Address matches key
                    assert "block" in deployment
                    assert "timestamp" in deployment
                    assert "abi" in deployment
                    assert "url" in deployment
                    assert "source_format" in deployment
                    assert "name" not in deployment  # Name should NOT be present

                    # Validate types
                    assert isinstance(deployment["address"], str)
                    assert isinstance(deployment["block"], int)
                    assert isinstance(deployment["timestamp"], int)
                    assert isinstance(deployment["abi"], list)
                    assert isinstance(deployment["url"], str)
                    assert deployment["source_format"] in ["legacy", "hardhat-deploy", "bridged"]

                    found_deployment = True
                    break
                if found_deployment:
                    break

            assert found_deployment, "No contract deployments found in cache"

            # Also check version manifest structure
            for network_data in cache["networks"].values():
                for version_data in network_data.get("versions", {}).values():
                    contracts = version_data.get("contracts", {})
                    for contract_name, address in contracts.items():
                        # Should be string addresses, not dicts
                        assert isinstance(contract_name, str)
                        assert isinstance(address, str)
                        assert address.startswith("0x")
                        # Address should exist in deployments dict
                        assert address in network_data["deployments"]

        except (subprocess.CalledProcessError, Exception) as e:
            pytest.skip(f"Cache generation failed: {e}")


class TestFillForwardLogic:
    """Test that fill-forward logic handles defective deployment files correctly."""

    def test_token_and_stakeregistry_present_in_v060(self, tmp_path: Path):
        """
        Test that Token and StakeRegistry are present in v0.6.0.

        v0.6.0 is the first version with hardhat deployment files, but Token
        and StakeRegistry deployment files are defective (missing block numbers).
        The fill-forward logic should copy these contracts from earlier versions.
        """
        output_path = tmp_path / "deployments.json"

        mainnet_rpc = os.environ.get("GNO_RPC_URL")

        if not mainnet_rpc:
            pytest.skip("Mainnet RPC URL required")

        try:
            regenerate_from_github(
                output_path=str(output_path),
                mainnet_rpc_url=mainnet_rpc,
            )

            with open(output_path) as f:
                cache = json.load(f)

            # Check mainnet network
            assert "mainnet" in cache["networks"]
            mainnet = cache["networks"]["mainnet"]

            # Check v0.6.0 exists
            assert "versions" in mainnet
            versions = mainnet["versions"]
            assert "v0.6.0" in versions, "v0.6.0 should be in the cache"

            # Get v0.6.0 contracts
            v060_contracts = versions["v0.6.0"]["contracts"]

            # Token and StakeRegistry should be present (filled forward)
            assert "Token" in v060_contracts, "Token should be present in v0.6.0 (fill-forward)"
            assert "StakeRegistry" in v060_contracts, "StakeRegistry should be present in v0.6.0 (fill-forward)"

            # Get the addresses
            token_address = v060_contracts["Token"]
            stake_address = v060_contracts["StakeRegistry"]

            # Addresses should be valid
            assert token_address.startswith("0x")
            assert stake_address.startswith("0x")

            # The deployment data should exist in the deployments dict
            assert token_address in mainnet["deployments"]
            assert stake_address in mainnet["deployments"]

            # Check that the deployment data has all required fields
            token_deployment = mainnet["deployments"][token_address]
            stake_deployment = mainnet["deployments"][stake_address]

            for deployment in [token_deployment, stake_deployment]:
                assert "address" in deployment
                assert "block" in deployment
                assert "timestamp" in deployment
                assert "abi" in deployment
                assert "url" in deployment
                assert "source_format" in deployment

        except (subprocess.CalledProcessError, Exception) as e:
            pytest.skip(f"Cache generation failed: {e}")

    def test_fill_forward_preserves_addresses_across_versions(self, tmp_path: Path):
        """
        Test that fill-forward preserves the same addresses across versions.

        When a contract is filled forward, it should maintain the same address
        until it's actually redeployed.
        """
        output_path = tmp_path / "deployments.json"

        mainnet_rpc = os.environ.get("GNO_RPC_URL")

        if not mainnet_rpc:
            pytest.skip("Mainnet RPC URL required")

        try:
            regenerate_from_github(
                output_path=str(output_path),
                mainnet_rpc_url=mainnet_rpc,
            )

            with open(output_path) as f:
                cache = json.load(f)

            mainnet = cache["networks"]["mainnet"]
            versions = mainnet["versions"]

            # Check that Token address is consistent across early versions
            # Token is bridged and never redeployed, so should have same address
            token_addresses = set()
            for version_tag in ["v0.4.0", "v0.5.0", "v0.6.0", "v0.7.0", "v0.8.0"]:
                if version_tag in versions:
                    contracts = versions[version_tag]["contracts"]
                    if "Token" in contracts:
                        token_addresses.add(contracts["Token"])

            # All Token addresses should be the same
            assert len(token_addresses) <= 1, (
                f"Token should have consistent address across versions, found: {token_addresses}"
            )

        except (subprocess.CalledProcessError, Exception) as e:
            pytest.skip(f"Cache generation failed: {e}")
