"""Repository ingestion for ethswarm-deployments library."""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict

from .constants import NETWORK_CONFIG
from .exceptions import DefectiveDeploymentError
from .parsers import DeploymentFormat, detect_deployment_format, parse_hardhat_deployment, parse_legacy_deployment
from .versions import filter_stable_tags


def _process_hardhat_contracts(
    hardhat_dir: Path,
    network: str,
    network_config: Dict[str, Any],
    timestamp_lookup: Callable[[int, str], int],
) -> tuple[Dict[str, str], Dict[str, Any]]:
    """
    Process hardhat-deploy format contracts for a network.

    Args:
        hardhat_dir: Path to deployments/{network} directory
        network: Network name
        network_config: Network configuration dict
        timestamp_lookup: Function to get block timestamps

    Returns:
        Tuple of (version_contracts, deployments) where:
        - version_contracts: Maps contract name -> address
        - deployments: Maps address -> deployment data
    """
    version_contracts: Dict[str, str] = {}
    deployments: Dict[str, Any] = {}

    for contract_file in hardhat_dir.glob("*.json"):
        # Contract name from filename
        contract_name = contract_file.stem

        # Parse deployment
        try:
            contract_data = parse_hardhat_deployment(contract_file)
        except DefectiveDeploymentError:
            # Skip defective deployment files (missing block number)
            continue

        address = contract_data["address"]

        # Add to version manifest
        version_contracts[contract_name] = address

        # Store deployment data if not already present
        if address not in deployments:
            # Get timestamp
            timestamp = timestamp_lookup(contract_data["block"], network)

            # Build deployment entry
            deployment_entry: Dict[str, Any] = {
                "address": address,
                "block": contract_data["block"],
                "timestamp": timestamp,
                "abi": contract_data["abi"],
                "url": f"{network_config['block_explorer_url']}/address/{address}",
                "source_format": contract_data["source_format"],
            }

            # Add optional fields
            for optional_field in [
                "transaction_hash",
                "bytecode",
                "deployed_bytecode",
                "constructor_args",
                "solc_input_hash",
                "num_deployments",
            ]:
                if optional_field in contract_data:
                    deployment_entry[optional_field] = contract_data[optional_field]

            deployments[address] = deployment_entry

    return version_contracts, deployments


def _process_legacy_contracts(
    legacy_file: Path,
    network: str,
    network_config: Dict[str, Any],
    timestamp_lookup: Callable[[int, str], int],
) -> tuple[Dict[str, str], Dict[str, Any]]:
    """
    Process legacy format contracts for a network.

    Args:
        legacy_file: Path to {network}_deployed.json file
        network: Network name
        network_config: Network configuration dict
        timestamp_lookup: Function to get block timestamps

    Returns:
        Tuple of (version_contracts, deployments) where:
        - version_contracts: Maps contract name -> address
        - deployments: Maps address -> deployment data
    """
    version_contracts: Dict[str, str] = {}
    deployments: Dict[str, Any] = {}

    # Parse legacy format
    legacy_contracts = parse_legacy_deployment(legacy_file)

    for contract_name, contract_data in legacy_contracts.items():
        address = contract_data["address"]

        # Add to version manifest
        version_contracts[contract_name] = address

        # Store deployment data if not already present
        if address not in deployments:
            # Get timestamp
            timestamp = timestamp_lookup(contract_data["block"], network)

            # Build deployment entry
            deployment_entry: Dict[str, Any] = {
                "address": address,
                "block": contract_data["block"],
                "timestamp": timestamp,
                "abi": contract_data["abi"],
                "source_format": contract_data["source_format"],
            }

            # URL might be in legacy data or we construct it
            if "url" in contract_data:
                deployment_entry["url"] = contract_data["url"]
            else:
                deployment_entry["url"] = (
                    f"{network_config['block_explorer_url']}/address/{address}"
                )

            # Add bytecode if present
            if "bytecode" in contract_data:
                deployment_entry["bytecode"] = contract_data["bytecode"]

            deployments[address] = deployment_entry

    return version_contracts, deployments


def _fill_forward_versions(network_data: Dict[str, Any], stable_tags: list[str]) -> None:
    """
    Fill forward missing contracts in version manifests.

    If a contract exists in one version but is missing in the next version,
    copy the contract reference forward to subsequent versions until it appears
    again or we reach the end.

    This handles cases where deployment files are defective (missing block numbers)
    for contracts that weren't redeployed (e.g., Token, StakeRegistry in early versions).

    Args:
        network_data: Network data dict containing 'versions' and 'deployments'
        stable_tags: Ordered list of version tags to process
    """
    versions = network_data["versions"]

    # Track the last known address for each contract name
    last_known: Dict[str, str] = {}

    # Process versions in order
    for tag in stable_tags:
        # Skip if this version has no manifest (no deployments found)
        if tag not in versions:
            continue

        contracts: Dict[str, str] = versions[tag]["contracts"]

        # Fill forward: add any contracts from last_known that are missing in current version
        contracts |= last_known

        # Update last_known with current version's contracts
        last_known.update(contracts)


def _process_tag_for_network(
    tag: str,
    repo_dir: Path,
    network: str,
    network_config: Dict[str, Any],
    timestamp_lookup: Callable[[int, str], int],
) -> tuple[Dict[str, str], Dict[str, Any]]:
    """
    Process a single git tag for a specific network.

    Args:
        tag: Git tag to process
        repo_dir: Repository directory
        network: Network name
        network_config: Network configuration dict
        timestamp_lookup: Function to get block timestamps

    Returns:
        Tuple of (version_contracts, new_deployments) where:
        - version_contracts: Maps contract name -> address for this version
        - new_deployments: Maps address -> deployment data for new deployments
        Returns ({}, {}) if no deployment files found for this tag/network
    """
    # Checkout tag
    try:
        subprocess.run(
            ["git", "-C", str(repo_dir), "checkout", "--quiet", tag],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to checkout tag {tag}: {e.stderr.decode()}") from e

    # Detect deployment format
    deployment_format = detect_deployment_format(repo_dir, network)

    # Process based on format
    match deployment_format:
        case DeploymentFormat.HARDHAT_DEPLOY:
            return _process_hardhat_contracts(
                repo_dir / "deployments" / network,
                network,
                network_config,
                timestamp_lookup,
            )
        case DeploymentFormat.LEGACY:
            return _process_legacy_contracts(
                repo_dir / f"{network}_deployed.json",
                network,
                network_config,
                timestamp_lookup,
            )
        case None:
            # No deployment files for this network/version
            return {}, {}
        case _:
            # Unreachable but exhaustive
            return {}, {}


def parse_deployments_from_repo(
    repo_url: str,
    timestamp_lookup: Callable[[int, str], int],
) -> Dict[str, Any]:
    """
    Parse deployment data from repository (low-level function for testing).

    This function is primarily intended for testing. Use regenerate_from_github()
    for normal cache generation.

    Args:
        repo_url: GitHub repository URL to clone and parse
        timestamp_lookup: Function to get block timestamp
                         Signature: (block_number: int, network: str) -> timestamp: int
                         Called for each deployment to resolve block timestamp

    Returns:
        Deployment cache dictionary (not yet written to disk)
        Structure matches deployments.json schema

    Raises:
        RuntimeError: If git operations or parsing fails
        ValueError: If no RPC URLs available for any network
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_dir = Path(tmp_dir) / "repo"

        # Clone repository
        try:
            # Set GIT_TERMINAL_PROMPT=0 to prevent git from prompting for credentials
            # This ensures failures happen immediately instead of hanging
            env = os.environ.copy()
            env["GIT_TERMINAL_PROMPT"] = "0"
            subprocess.run(
                ["git", "clone", "--quiet", repo_url, str(repo_dir)],
                check=True,
                capture_output=True,
                env=env,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to clone repository: {e.stderr.decode()}") from e

        # Get all tags
        try:
            result = subprocess.run(
                ["git", "-C", str(repo_dir), "tag"],
                check=True,
                capture_output=True,
                text=True,
            )
            all_tags = result.stdout.strip().split("\n") if result.stdout.strip() else []
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get git tags: {e.stderr.decode()}") from e

        # Filter to stable tags only
        stable_tags = filter_stable_tags(all_tags)

        # Determine which networks have RPC availability
        # Test by attempting a dummy timestamp lookup for block 0
        available_networks = []
        for network in NETWORK_CONFIG.keys():
            try:
                _ = timestamp_lookup(0, network)
                available_networks.append(network)
            except ValueError:
                # No RPC for this network, skip it
                pass

        if not available_networks:
            raise ValueError("No RPC URLs available for any network")

        # Initialize cache structure
        cache: Dict[str, Any] = {
            "metadata": {
                "generated_at": "",  # Will be set by regenerate_from_github
                "source_repo": repo_url,
                "networks": available_networks,
            },
            "networks": {},
        }

        # Process only available networks
        for network in available_networks:
            network_config = NETWORK_CONFIG[network]
            network_data: Dict[str, Any] = {
                "chain_id": network_config["chain_id"],
                "chain_name": network_config["chain_name"],
                "block_explorer_url": network_config["block_explorer_url"],
                "deployments": {},  # Normalized: address -> deployment data
                "versions": {},     # Version manifests: name -> address
            }

            # Process each stable tag
            for tag in stable_tags:
                # Process this tag for the current network
                version_contracts, new_deployments = _process_tag_for_network(
                    tag, repo_dir, network, network_config, timestamp_lookup
                )

                # Merge new deployments into network data
                network_data["deployments"].update(new_deployments)

                # Add version manifest if we found any contracts
                if version_contracts:
                    network_data["versions"][tag] = {"contracts": version_contracts}

            # Fill forward missing contracts across versions
            # This handles defective deployment files where contracts exist but
            # weren't properly recorded in some versions
            if network_data["versions"]:
                _fill_forward_versions(network_data, stable_tags)

            # Add network to cache if we found any versions
            if network_data["versions"]:
                cache["networks"][network] = network_data

        return cache
