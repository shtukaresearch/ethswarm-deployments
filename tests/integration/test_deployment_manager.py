"""Integration tests for DeploymentManager API."""

from pathlib import Path

import pytest

from ethswarm_deployments import (
    ContractNotFoundError,
    DeploymentManager,
    EventNotFoundError,
    NetworkNotFoundError,
    VersionNotFoundError,
)
from ethswarm_deployments.exceptions import CacheNotFoundError


class TestDeploymentManagerInitialization:
    """Test DeploymentManager initialization."""

    def test_initializes_with_valid_cache(self, temp_deployments_cache: Path):
        """Test that DeploymentManager initializes with valid cache file."""
        mgr = DeploymentManager(str(temp_deployments_cache))
        assert mgr is not None

    def test_initializes_with_default_path(self, temp_deployments_cache: Path, monkeypatch):
        """Test initialization with default cache path."""
        # Mock the default cache path to point to our temp cache
        from ethswarm_deployments import paths

        monkeypatch.setattr(
            paths, "get_default_cache_dir", lambda: temp_deployments_cache.parent
        )

        mgr = DeploymentManager()
        assert mgr is not None

    def test_raises_error_with_missing_cache(self, tmp_path: Path):
        """Test that CacheNotFoundError is raised when cache doesn't exist."""
        non_existent = tmp_path / "does_not_exist.json"

        with pytest.raises(CacheNotFoundError):
            DeploymentManager(str(non_existent))

    def test_cache_not_found_catchable_as_file_not_found(self, tmp_path: Path):
        """Test that CacheNotFoundError can be caught as FileNotFoundError."""
        non_existent = tmp_path / "does_not_exist.json"

        with pytest.raises(FileNotFoundError):
            DeploymentManager(str(non_existent))


class TestVersions:
    """Test the versions() method."""

    def test_returns_list_of_versions_for_mainnet(self, temp_deployments_cache: Path):
        """Test that versions() returns all versions for mainnet."""
        mgr = DeploymentManager(str(temp_deployments_cache))
        versions = mgr.versions("mainnet")

        assert isinstance(versions, list)
        assert "v0.1.0" in versions
        assert "v0.2.0" in versions

    def test_returns_sorted_versions(self, temp_deployments_cache: Path):
        """Test that versions are returned in sorted order."""
        mgr = DeploymentManager(str(temp_deployments_cache))
        versions = mgr.versions("mainnet")

        # Should be sorted chronologically (v0.1.0 before v0.2.0)
        assert versions == sorted(versions)

    def test_versions_for_testnet(self, temp_deployments_cache: Path):
        """Test getting versions for testnet."""
        mgr = DeploymentManager(str(temp_deployments_cache))
        versions = mgr.versions("testnet")

        assert isinstance(versions, list)
        assert "v0.2.0" in versions

    def test_mainnet_is_default_network(self, temp_deployments_cache: Path):
        """Test that mainnet is the default network."""
        mgr = DeploymentManager(str(temp_deployments_cache))
        default_versions = mgr.versions()
        mainnet_versions = mgr.versions("mainnet")

        assert default_versions == mainnet_versions

    def test_raises_error_for_invalid_network(self, temp_deployments_cache: Path):
        """Test that NetworkNotFoundError is raised for invalid network."""
        mgr = DeploymentManager(str(temp_deployments_cache))

        with pytest.raises(NetworkNotFoundError) as exc_info:
            mgr.versions("invalid_network")

        assert "invalid_network" in str(exc_info.value)


class TestLatestVersion:
    """Test the latest_version() method."""

    def test_returns_latest_version_for_mainnet(self, temp_deployments_cache: Path):
        """Test that latest_version() returns the most recent version."""
        mgr = DeploymentManager(str(temp_deployments_cache))
        latest = mgr.latest_version("mainnet")

        assert latest == "v0.2.0"  # v0.2.0 is the latest in our fixture

    def test_returns_latest_version_for_testnet(self, temp_deployments_cache: Path):
        """Test getting latest version for testnet."""
        mgr = DeploymentManager(str(temp_deployments_cache))
        latest = mgr.latest_version("testnet")

        assert latest == "v0.2.0"

    def test_mainnet_is_default(self, temp_deployments_cache: Path):
        """Test that mainnet is the default network for latest_version."""
        mgr = DeploymentManager(str(temp_deployments_cache))
        default_latest = mgr.latest_version()
        mainnet_latest = mgr.latest_version("mainnet")

        assert default_latest == mainnet_latest

    def test_raises_error_when_no_versions(self, temp_deployments_cache: Path, monkeypatch):
        """Test that VersionNotFoundError is raised when no versions exist."""
        mgr = DeploymentManager(str(temp_deployments_cache))

        # Mock the data to have no versions for a network
        def mock_versions(network):
            return []

        monkeypatch.setattr(mgr, "versions", mock_versions)

        with pytest.raises(VersionNotFoundError):
            mgr.latest_version("mainnet")


class TestContractNames:
    """Test the contract_names() method."""

    def test_returns_contract_names_for_version(self, temp_deployments_cache: Path):
        """Test that contract_names() returns list of contracts."""
        mgr = DeploymentManager(str(temp_deployments_cache))
        contracts = mgr.contract_names(version="v0.2.0", network="mainnet")

        assert isinstance(contracts, list)
        assert "Token" in contracts
        assert "StakeRegistry" in contracts

    def test_uses_latest_version_when_not_specified(self, temp_deployments_cache: Path):
        """Test that latest version is used when version not specified."""
        mgr = DeploymentManager(str(temp_deployments_cache))
        contracts = mgr.contract_names(network="mainnet")

        # Should use v0.2.0 (latest)
        assert "Token" in contracts
        assert "StakeRegistry" in contracts

    def test_mainnet_is_default_network(self, temp_deployments_cache: Path):
        """Test that mainnet is the default network."""
        mgr = DeploymentManager(str(temp_deployments_cache))
        default_contracts = mgr.contract_names(version="v0.2.0")
        mainnet_contracts = mgr.contract_names(version="v0.2.0", network="mainnet")

        assert default_contracts == mainnet_contracts

    def test_raises_error_for_invalid_version(self, temp_deployments_cache: Path):
        """Test that VersionNotFoundError is raised for invalid version."""
        mgr = DeploymentManager(str(temp_deployments_cache))

        with pytest.raises(VersionNotFoundError) as exc_info:
            mgr.contract_names(version="v999.0.0", network="mainnet")

        assert "v999.0.0" in str(exc_info.value)


class TestDeployment:
    """Test the deployment() method."""

    def test_returns_contract_deployment_with_canonical_name(self, temp_deployments_cache: Path):
        """Test getting deployment with canonical contract name."""
        mgr = DeploymentManager(str(temp_deployments_cache))
        deployment = mgr.deployment("Token", version="v0.2.0", network="mainnet")

        assert deployment.name == "Token"
        assert deployment.version == "v0.2.0"
        assert deployment.network == "mainnet"
        assert deployment.address == "0x2234567890123456789012345678901234567890"
        assert deployment.block == 27391083
        assert deployment.timestamp == 1681228800

    def test_returns_deployment_with_all_fields(self, temp_deployments_cache: Path):
        """Test that all fields are populated in ContractDeployment."""
        mgr = DeploymentManager(str(temp_deployments_cache))
        deployment = mgr.deployment("StakeRegistry", version="v0.2.0", network="mainnet")

        # Required fields
        assert deployment.name is not None
        assert deployment.version is not None
        assert deployment.address is not None
        assert deployment.block > 0
        assert deployment.timestamp > 0
        assert deployment.abi is not None
        assert deployment.network is not None
        assert deployment.url is not None

        # Optional fields (from hardhat-deploy in v0.2.0)
        assert deployment.transaction_hash is not None
        assert deployment.bytecode is not None
        assert deployment.deployed_bytecode is not None
        assert deployment.source_format == "hardhat-deploy"

    def test_uses_latest_version_when_not_specified(self, temp_deployments_cache: Path):
        """Test that latest version is used when version not specified."""
        mgr = DeploymentManager(str(temp_deployments_cache))
        deployment = mgr.deployment("Token", network="mainnet")

        # Should use v0.2.0 (latest)
        assert deployment.version == "v0.2.0"

    def test_mainnet_is_default_network(self, temp_deployments_cache: Path):
        """Test that mainnet is the default network."""
        mgr = DeploymentManager(str(temp_deployments_cache))
        default_dep = mgr.deployment("Token", version="v0.2.0")
        mainnet_dep = mgr.deployment("Token", version="v0.2.0", network="mainnet")

        assert default_dep.address == mainnet_dep.address
        assert default_dep.network == "mainnet"

    def test_raises_error_for_missing_contract(self, temp_deployments_cache: Path):
        """Test that ContractNotFoundError is raised for missing contract."""
        mgr = DeploymentManager(str(temp_deployments_cache))

        with pytest.raises(ContractNotFoundError) as exc_info:
            mgr.deployment("NonExistentContract", version="v0.2.0", network="mainnet")

        assert "NonExistentContract" in str(exc_info.value)
        assert "v0.2.0" in str(exc_info.value)
        assert "mainnet" in str(exc_info.value)

    def test_raises_error_for_invalid_version(self, temp_deployments_cache: Path):
        """Test that VersionNotFoundError is raised for invalid version."""
        mgr = DeploymentManager(str(temp_deployments_cache))

        with pytest.raises(VersionNotFoundError):
            mgr.deployment("Token", version="v999.0.0", network="mainnet")


class TestAllDeployments:
    """Test the all_deployments() method."""

    def test_returns_all_versions_of_contract(self, temp_deployments_cache: Path):
        """Test that all_deployments() returns all versions."""
        mgr = DeploymentManager(str(temp_deployments_cache))
        all_deps = mgr.all_deployments("Token", network="mainnet")

        assert isinstance(all_deps, list)
        assert len(all_deps) == 2  # v0.1.0 and v0.2.0

        versions = [dep.version for dep in all_deps]
        assert "v0.1.0" in versions
        assert "v0.2.0" in versions

    def test_deployments_sorted_by_version(self, temp_deployments_cache: Path):
        """Test that deployments are sorted by version."""
        mgr = DeploymentManager(str(temp_deployments_cache))
        all_deps = mgr.all_deployments("Token", network="mainnet")

        versions = [dep.version for dep in all_deps]
        assert versions == sorted(versions)

    def test_mainnet_is_default_network(self, temp_deployments_cache: Path):
        """Test that mainnet is the default network."""
        mgr = DeploymentManager(str(temp_deployments_cache))
        default_deps = mgr.all_deployments("Token")
        mainnet_deps = mgr.all_deployments("Token", network="mainnet")

        assert len(default_deps) == len(mainnet_deps)
        assert all(dep.network == "mainnet" for dep in default_deps)

    def test_returns_empty_list_for_missing_contract(self, temp_deployments_cache: Path):
        """Test behavior when contract doesn't exist in any version."""
        mgr = DeploymentManager(str(temp_deployments_cache))

        # This might return empty list or raise ContractNotFoundError
        # depending on implementation choice
        result = mgr.all_deployments("NonExistent", network="mainnet")
        assert isinstance(result, list)
        assert len(result) == 0


class TestEventAbi:
    """Test the event_abi() method."""

    def test_returns_event_abi(self, temp_deployments_cache: Path):
        """Test that event_abi() returns correct event definition."""
        mgr = DeploymentManager(str(temp_deployments_cache))
        event_abi = mgr.event_abi("Token", "Transfer", version="v0.2.0", network="mainnet")

        assert isinstance(event_abi, dict)
        assert event_abi["type"] == "event"
        assert event_abi["name"] == "Transfer"
        assert "inputs" in event_abi

    def test_event_inputs_structure(self, temp_deployments_cache: Path):
        """Test the structure of event inputs."""
        mgr = DeploymentManager(str(temp_deployments_cache))
        event_abi = mgr.event_abi("Token", "Transfer", version="v0.2.0", network="mainnet")

        inputs = event_abi["inputs"]
        assert isinstance(inputs, list)
        assert len(inputs) == 3  # from, to, value

        # Check input structure
        for input_def in inputs:
            assert "name" in input_def
            assert "type" in input_def
            assert "indexed" in input_def

    def test_uses_latest_version_when_not_specified(self, temp_deployments_cache: Path):
        """Test that latest version is used when version not specified."""
        mgr = DeploymentManager(str(temp_deployments_cache))
        event_abi = mgr.event_abi("StakeRegistry", "StakeUpdated", network="mainnet")

        assert event_abi["name"] == "StakeUpdated"

    def test_raises_error_for_missing_event(self, temp_deployments_cache: Path):
        """Test that EventNotFoundError is raised for missing event."""
        mgr = DeploymentManager(str(temp_deployments_cache))

        with pytest.raises(EventNotFoundError) as exc_info:
            mgr.event_abi("Token", "NonExistentEvent", version="v0.2.0", network="mainnet")

        assert "NonExistentEvent" in str(exc_info.value)
        assert "Token" in str(exc_info.value)


class TestHasContract:
    """Test the has_contract() method."""

    def test_returns_true_for_existing_contract(self, temp_deployments_cache: Path):
        """Test that has_contract() returns True for existing contract."""
        mgr = DeploymentManager(str(temp_deployments_cache))
        assert mgr.has_contract("Token", "v0.2.0", "mainnet") is True
        assert mgr.has_contract("StakeRegistry", "v0.2.0", "mainnet") is True

    def test_returns_false_for_missing_contract(self, temp_deployments_cache: Path):
        """Test that has_contract() returns False for missing contract."""
        mgr = DeploymentManager(str(temp_deployments_cache))
        assert mgr.has_contract("NonExistent", "v0.2.0", "mainnet") is False

    def test_returns_false_for_invalid_version(self, temp_deployments_cache: Path):
        """Test that has_contract() returns False for invalid version."""
        mgr = DeploymentManager(str(temp_deployments_cache))
        assert mgr.has_contract("Token", "v999.0.0", "mainnet") is False

    def test_mainnet_is_default_network(self, temp_deployments_cache: Path):
        """Test that mainnet is the default network."""
        mgr = DeploymentManager(str(temp_deployments_cache))
        default_result = mgr.has_contract("Token", "v0.2.0")
        mainnet_result = mgr.has_contract("Token", "v0.2.0", "mainnet")

        assert default_result == mainnet_result


class TestMetadata:
    """Test the metadata() method."""

    def test_returns_metadata_dict(self, temp_deployments_cache: Path):
        """Test that metadata() returns cache metadata."""
        mgr = DeploymentManager(str(temp_deployments_cache))
        metadata = mgr.metadata()

        assert isinstance(metadata, dict)
        assert "generated_at" in metadata
        assert "source_repo" in metadata
        assert "networks" in metadata

    def test_metadata_networks_list(self, temp_deployments_cache: Path):
        """Test that networks list is correct in metadata."""
        mgr = DeploymentManager(str(temp_deployments_cache))
        metadata = mgr.metadata()

        networks = metadata["networks"]
        assert isinstance(networks, list)
        assert "mainnet" in networks
        assert "testnet" in networks


class TestNetworkInfo:
    """Test the network_info() method."""

    def test_returns_mainnet_info(self, temp_deployments_cache: Path):
        """Test getting mainnet network information."""
        mgr = DeploymentManager(str(temp_deployments_cache))
        info = mgr.network_info("mainnet")

        assert isinstance(info, dict)
        assert info["chain_id"] == 100
        assert info["chain_name"] == "Gnosis Chain"
        assert info["block_explorer_url"] == "https://gnosisscan.io"

    def test_returns_testnet_info(self, temp_deployments_cache: Path):
        """Test getting testnet network information."""
        mgr = DeploymentManager(str(temp_deployments_cache))
        info = mgr.network_info("testnet")

        assert isinstance(info, dict)
        assert info["chain_id"] == 11155111
        assert info["chain_name"] == "Sepolia"
        assert info["block_explorer_url"] == "https://sepolia.etherscan.io"

    def test_mainnet_is_default(self, temp_deployments_cache: Path):
        """Test that mainnet is the default network."""
        mgr = DeploymentManager(str(temp_deployments_cache))
        default_info = mgr.network_info()
        mainnet_info = mgr.network_info("mainnet")

        assert default_info == mainnet_info

    def test_raises_error_for_invalid_network(self, temp_deployments_cache: Path):
        """Test that NetworkNotFoundError is raised for invalid network."""
        mgr = DeploymentManager(str(temp_deployments_cache))

        with pytest.raises(NetworkNotFoundError) as exc_info:
            mgr.network_info("invalid_network")

        assert "invalid_network" in str(exc_info.value)


class TestPartialCache:
    """Test behavior with partial caches (missing networks)."""

    def test_has_network_returns_true_for_existing(self, temp_deployments_cache: Path):
        """Test that has_network() returns True for networks in cache."""
        mgr = DeploymentManager(str(temp_deployments_cache))

        assert mgr.has_network("mainnet") is True
        assert mgr.has_network("testnet") is True

    def test_has_network_returns_false_for_missing(self, temp_deployments_cache: Path):
        """Test that has_network() returns False for networks not in cache."""
        mgr = DeploymentManager(str(temp_deployments_cache))

        assert mgr.has_network("invalid_network") is False
        assert mgr.has_network("arbitrum") is False

    def test_partial_cache_mainnet_only(self, tmp_path: Path):
        """Test DeploymentManager with cache containing only mainnet."""
        # Create a partial cache with only mainnet (normalized schema)
        partial_cache = {
            "metadata": {
                "generated_at": "2025-12-22 10:00:00 UTC",
                "source_repo": "https://github.com/ethersphere/storage-incentives",
                "networks": ["mainnet"]
            },
            "networks": {
                "mainnet": {
                    "chain_id": 100,
                    "chain_name": "Gnosis Chain",
                    "block_explorer_url": "https://gnosisscan.io",
                    "deployments": {
                        "0x1234567890123456789012345678901234567890": {
                            "address": "0x1234567890123456789012345678901234567890",
                            "block": 25527075,
                            "timestamp": 1671456789,
                            "abi": [],
                            "url": "https://gnosisscan.io/address/0x1234567890123456789012345678901234567890",
                            "source_format": "legacy"
                        }
                    },
                    "versions": {
                        "v0.1.0": {
                            "contracts": {
                                "Token": "0x1234567890123456789012345678901234567890"
                            }
                        }
                    }
                }
            }
        }

        cache_path = tmp_path / "partial_deployments.json"
        import json
        with open(cache_path, "w") as f:
            json.dump(partial_cache, f)

        mgr = DeploymentManager(str(cache_path))

        # Mainnet queries should work
        assert mgr.has_network("mainnet") is True
        assert len(mgr.versions("mainnet")) > 0

        # Testnet queries should fail
        assert mgr.has_network("testnet") is False
        with pytest.raises(NetworkNotFoundError):
            mgr.versions("testnet")
        with pytest.raises(NetworkNotFoundError):
            mgr.deployment("Token", network="testnet")
        with pytest.raises(NetworkNotFoundError):
            mgr.network_info("testnet")
