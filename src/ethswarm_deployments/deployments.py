"""Main API for ethswarm-deployments library."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .exceptions import (
    CacheNotFoundError,
    ContractNotFoundError,
    EventNotFoundError,
    NetworkNotFoundError,
    VersionNotFoundError,
)
from .ingestion import parse_deployments_from_repo
from .parsers import normalize_contract_name
from .paths import get_cache_paths, get_default_cache_dir
from .timestamps import get_block_timestamp, load_timestamp_cache, save_timestamp_cache
from .types import ContractDeployment


class DeploymentManager:
    """Manages contract deployment information across networks and versions."""

    def __init__(self, deployment_json_path: Optional[str] = None):
        """
        Initialize the deployment manager.

        Args:
            deployment_json_path: Path to deployments.json
                                 If None, uses ~/.ethswarm-deployments/deployments.json

        Raises:
            CacheNotFoundError: If deployment cache not found
        """
        if deployment_json_path is None:
            deployment_json_path = str(get_cache_paths()[0])

        cache_path = Path(deployment_json_path)
        if not cache_path.exists():
            raise CacheNotFoundError(
                f"Deployment cache not found at {cache_path}. "
                "Run regenerate_from_github() to create it."
            )

        with open(cache_path) as f:
            self._cache = json.load(f)

    def has_network(self, network: str) -> bool:
        """
        Check if a network is available in the cache.

        Args:
            network: Network name to check

        Returns:
            True if network exists in cache, False otherwise
        """
        return network in self._cache.get("networks", {})

    def versions(self, network: str = "mainnet") -> List[str]:
        """
        Get list of all available versions for a network, sorted chronologically.

        Args:
            network: Network name ("mainnet" or "testnet")

        Returns:
            List of version strings (e.g., ["v0.4.0", "v0.5.0", ...])

        Raises:
            NetworkNotFoundError: If network not in cache
        """
        if not self.has_network(network):
            raise NetworkNotFoundError(f"Network '{network}' not found in cache")

        versions_dict = self._cache["networks"][network].get("versions", {})
        return sorted(versions_dict.keys())

    def latest_version(self, network: str = "mainnet") -> str:
        """
        Get the most recent version for a network.

        Args:
            network: Network name ("mainnet" or "testnet")

        Returns:
            Version string (e.g., "v0.9.4")

        Raises:
            NetworkNotFoundError: If network not in cache
            VersionNotFoundError: If no versions found
        """
        versions = self.versions(network)
        if not versions:
            raise VersionNotFoundError(f"No versions found for network '{network}'")
        return versions[-1]

    def contract_names(
        self, version: Optional[str] = None, network: str = "mainnet"
    ) -> List[str]:
        """
        Get list of contract names for a given version.

        Args:
            version: Contract version (defaults to latest)
            network: Network name ("mainnet" or "testnet")

        Returns:
            List of canonical contract names (e.g., ["StakeRegistry", "Token", ...])

        Raises:
            NetworkNotFoundError: If network not in cache
            VersionNotFoundError: If version not found
        """
        if not self.has_network(network):
            raise NetworkNotFoundError(f"Network '{network}' not found in cache")

        if version is None:
            version = self.latest_version(network)

        versions_dict = self._cache["networks"][network].get("versions", {})
        if version not in versions_dict:
            raise VersionNotFoundError(
                f"Version '{version}' not found in network '{network}'"
            )

        contracts = versions_dict[version].get("contracts", {})
        return list(contracts.keys())

    def deployment(
        self,
        contract_name: str,
        version: Optional[str] = None,
        network: str = "mainnet",
    ) -> ContractDeployment:
        """
        Get deployment information for a specific contract.

        Accepts both canonical and legacy contract names.

        Args:
            contract_name: Name of contract (canonical or legacy)
            version: Contract version (defaults to latest)
            network: Network name ("mainnet" or "testnet")

        Returns:
            ContractDeployment object

        Raises:
            NetworkNotFoundError: If network not in cache
            VersionNotFoundError: If version not found
            ContractNotFoundError: If contract not found in version
        """
        if not self.has_network(network):
            raise NetworkNotFoundError(f"Network '{network}' not found in cache")

        # Normalize contract name (legacy → canonical)
        canonical_name = normalize_contract_name(contract_name)

        if version is None:
            version = self.latest_version(network)

        versions_dict = self._cache["networks"][network].get("versions", {})
        if version not in versions_dict:
            raise VersionNotFoundError(
                f"Version '{version}' not found in network '{network}'"
            )

        contracts = versions_dict[version].get("contracts", {})
        if canonical_name not in contracts:
            raise ContractNotFoundError(
                f"Contract '{contract_name}' not found in version '{version}' "
                f"on network '{network}'"
            )

        # Get address reference from version manifest
        address = contracts[canonical_name]

        # Lookup deployment data
        deployment_data = self._cache["networks"][network]["deployments"][address]

        # Build ContractDeployment object
        return ContractDeployment(
            version=version,
            name=canonical_name,
            address=deployment_data["address"],
            block=deployment_data["block"],
            timestamp=deployment_data["timestamp"],
            abi=deployment_data["abi"],
            network=network,
            url=deployment_data["url"],
            transaction_hash=deployment_data.get("transaction_hash"),
            bytecode=deployment_data.get("bytecode"),
            deployed_bytecode=deployment_data.get("deployed_bytecode"),
            constructor_args=deployment_data.get("constructor_args"),
            solc_input_hash=deployment_data.get("solc_input_hash"),
            num_deployments=deployment_data.get("num_deployments"),
            source_format=deployment_data.get("source_format"),
        )

    def all_deployments(
        self, contract_name: str, network: str = "mainnet"
    ) -> List[ContractDeployment]:
        """
        Get all distinct deployments of a contract across all versions.

        Returns only unique deployments (by address). If the same contract address
        appears in multiple versions (e.g., Token contract), only one entry is
        returned with the earliest version where it appeared.

        Args:
            contract_name: Name of contract (canonical or legacy)
            network: Network name ("mainnet" or "testnet")

        Returns:
            List of ContractDeployment objects with distinct addresses,
            sorted chronologically by first appearance (earliest version first)
        """
        canonical_name = normalize_contract_name(contract_name)

        # Collect {version: address} mappings
        version_addresses: Dict[str, str] = {}
        for version in self.versions(network):
            contracts = self._cache["networks"][network]["versions"][version].get("contracts", {})
            if canonical_name in contracts:
                version_addresses[version] = contracts[canonical_name]

        # Deduplicate by address, keeping earliest version
        seen_addresses: Dict[str, str] = {}
        for version in sorted(version_addresses.keys()):
            address = version_addresses[version]
            if address not in seen_addresses:
                seen_addresses[address] = version

        # Build result list
        result = []
        deployments_dict = self._cache["networks"][network]["deployments"]
        for address, first_version in seen_addresses.items():
            deployment_data = deployments_dict[address]
            result.append(
                ContractDeployment(
                    version=first_version,
                    name=canonical_name,
                    address=address,
                    block=deployment_data["block"],
                    timestamp=deployment_data["timestamp"],
                    abi=deployment_data["abi"],
                    network=network,
                    url=deployment_data["url"],
                    transaction_hash=deployment_data.get("transaction_hash"),
                    bytecode=deployment_data.get("bytecode"),
                    deployed_bytecode=deployment_data.get("deployed_bytecode"),
                    constructor_args=deployment_data.get("constructor_args"),
                    solc_input_hash=deployment_data.get("solc_input_hash"),
                    num_deployments=deployment_data.get("num_deployments"),
                    source_format=deployment_data.get("source_format"),
                )
            )

        # Sort by block number (chronological order)
        result.sort(key=lambda d: d.block)
        return result

    def event_abi(
        self,
        contract_name: str,
        event_name: str,
        version: Optional[str] = None,
        network: str = "mainnet",
    ) -> Dict[str, Any]:
        """
        Get ABI definition for a specific event.

        Args:
            contract_name: Name of contract (canonical or legacy)
            event_name: Name of event
            version: Contract version (defaults to latest)
            network: Network name ("mainnet" or "testnet")

        Returns:
            Event ABI definition

        Raises:
            EventNotFoundError: If event not found in contract ABI
        """
        deployment = self.deployment(contract_name, version, network)

        # Linear search through ABI for event
        for item in deployment.abi:
            if item.get("type") == "event" and item.get("name") == event_name:
                return item

        raise EventNotFoundError(
            f"Event '{event_name}' not found in {contract_name} {version} ABI"
        )

    def has_contract(
        self, contract_name: str, version: str, network: str = "mainnet"
    ) -> bool:
        """
        Check if a contract exists in a given version/network.

        Args:
            contract_name: Name of contract (canonical or legacy)
            version: Contract version
            network: Network name ("mainnet" or "testnet")

        Returns:
            True if contract exists, False otherwise
        """
        if not self.has_network(network):
            return False

        canonical_name = normalize_contract_name(contract_name)

        versions_dict = self._cache["networks"][network].get("versions", {})
        if version not in versions_dict:
            return False

        contracts = versions_dict[version].get("contracts", {})
        return canonical_name in contracts

    def metadata(self) -> Dict[str, Any]:
        """
        Get cache metadata (generation time, source repo, networks).

        Returns:
            Metadata dictionary
        """
        return self._cache.get("metadata", {})

    def network_info(self, network: str = "mainnet") -> Dict[str, Any]:
        """
        Get network information (chain ID, name, explorer URL).

        Args:
            network: Network name ("mainnet" or "testnet")

        Returns:
            Dictionary with chain_id, chain_name, block_explorer_url

        Raises:
            NetworkNotFoundError: If network not in cache
        """
        if not self.has_network(network):
            raise NetworkNotFoundError(f"Network '{network}' not found in cache")

        network_data = self._cache["networks"][network]
        return {
            "chain_id": network_data["chain_id"],
            "chain_name": network_data["chain_name"],
            "block_explorer_url": network_data["block_explorer_url"],
        }


def regenerate_from_github(
    output_path: Optional[str] = None,
    repo_url: str = "https://github.com/ethersphere/storage-incentives.git",
    mainnet_rpc_url: Optional[str] = None,
    testnet_rpc_url: Optional[str] = None,
) -> str:
    """
    Regenerate deployment cache by fetching latest data from GitHub.

    Processes all stable versions (tags starting with 'v' without '-rc').
    Uses persistent timestamp cache to minimize RPC calls.

    Args:
        output_path: Where to save deployments.json
                    (defaults to ~/.ethswarm-deployments/deployments.json)
        repo_url: GitHub repository URL
        mainnet_rpc_url: Mainnet RPC URL (defaults to $GNO_RPC_URL)
        testnet_rpc_url: Testnet RPC URL (defaults to $SEP_RPC_URL)

    Returns:
        Path where deployment cache was saved

    Raises:
        ValueError: If both RPC URLs missing (need at least one)
        RuntimeError: If regeneration fails
    """
    # Get RPC URLs from environment if not provided
    if mainnet_rpc_url is None:
        mainnet_rpc_url = os.environ.get("GNO_RPC_URL")
    if testnet_rpc_url is None:
        testnet_rpc_url = os.environ.get("SEP_RPC_URL")

    # Need at least one RPC URL
    if mainnet_rpc_url is None and testnet_rpc_url is None:
        raise ValueError(
            "RPC URL required: set $GNO_RPC_URL or $SEP_RPC_URL environment variable, "
            "or pass mainnet_rpc_url or testnet_rpc_url parameter"
        )

    # Determine output path
    if output_path is None:
        output_path = str(get_cache_paths()[0])

    output_path_obj = Path(output_path)
    timestamp_cache_path = output_path_obj.parent / "block_timestamps.json"

    # Load existing timestamp cache
    timestamp_cache = load_timestamp_cache(timestamp_cache_path)

    # Create timestamp lookup function
    def timestamp_lookup(block_number: int, network: str) -> int:
        # Determine which RPC URL to use
        if network == "mainnet":
            rpc_url = mainnet_rpc_url
        elif network == "testnet":
            rpc_url = testnet_rpc_url
        else:
            raise ValueError(f"Unknown network: {network}")

        # Skip if no RPC URL for this network
        if rpc_url is None:
            raise ValueError(f"No RPC URL configured for network '{network}'")

        return get_block_timestamp(block_number, network, rpc_url, timestamp_cache)

    # Parse deployments from repo
    cache_data = parse_deployments_from_repo(repo_url, timestamp_lookup)

    # Set generation timestamp
    cache_data["metadata"]["generated_at"] = datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )

    # Save deployment cache
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path_obj, "w") as f:
        json.dump(cache_data, f, indent=2)

    # Save updated timestamp cache
    save_timestamp_cache(timestamp_cache, timestamp_cache_path)

    return str(output_path_obj)
