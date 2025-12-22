"""Repository ingestion for ethswarm-deployments library."""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict

from .constants import NETWORK_CONFIG
from .parsers import DeploymentFormat, detect_deployment_format, parse_hardhat_deployment, parse_legacy_deployment
from .versions import filter_stable_tags


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

        # Initialize cache structure
        cache: Dict[str, Any] = {
            "metadata": {
                "generated_at": "",  # Will be set by regenerate_from_github
                "source_repo": repo_url,
                "networks": list(NETWORK_CONFIG.keys()),
            },
            "networks": {},
        }

        # Process each network
        for network, network_config in NETWORK_CONFIG.items():
            network_data: Dict[str, Any] = {
                "chain_id": network_config["chain_id"],
                "chain_name": network_config["chain_name"],
                "block_explorer_url": network_config["block_explorer_url"],
                "deployments": {},  # Normalized: address -> deployment data
                "versions": {},     # Version manifests: name -> address
            }

            # Process each stable tag
            for tag in stable_tags:
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

                if deployment_format is None:
                    # No deployment files for this network/version
                    continue

                # Parse deployments based on format
                # version_contracts maps contract_name -> address for this version
                version_contracts: Dict[str, str] = {}

                if deployment_format == DeploymentFormat.HARDHAT_DEPLOY:
                    # Parse hardhat-deploy format
                    hardhat_dir = repo_dir / "deployments" / network
                    skip_network = False
                    for contract_file in hardhat_dir.glob("*.json"):
                        # Contract name from filename
                        contract_name = contract_file.stem

                        # Parse deployment
                        contract_data = parse_hardhat_deployment(contract_file)

                        # Skip if incomplete (no block number)
                        if contract_data is None:
                            continue

                        address = contract_data["address"]

                        # Add to version manifest
                        version_contracts[contract_name] = address

                        # Store deployment data if not already present
                        if address not in network_data["deployments"]:
                            # Get timestamp
                            try:
                                timestamp = timestamp_lookup(contract_data["block"], network)
                            except ValueError:
                                # No RPC URL for this network, skip entire network
                                skip_network = True
                                break

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

                            network_data["deployments"][address] = deployment_entry

                    # If we need to skip this network, clear version_contracts and break
                    if skip_network:
                        version_contracts = {}
                        break  # Break out of tag loop for this network

                elif deployment_format == DeploymentFormat.LEGACY:
                    # Parse legacy format
                    legacy_file = repo_dir / f"{network}_deployed.json"
                    legacy_contracts = parse_legacy_deployment(legacy_file)

                    skip_network = False
                    for contract_name, contract_data in legacy_contracts.items():
                        address = contract_data["address"]

                        # Add to version manifest
                        version_contracts[contract_name] = address

                        # Store deployment data if not already present
                        if address not in network_data["deployments"]:
                            # Get timestamp
                            try:
                                timestamp = timestamp_lookup(contract_data["block"], network)
                            except ValueError:
                                # No RPC URL for this network, skip entire network
                                skip_network = True
                                break

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

                            network_data["deployments"][address] = deployment_entry

                    # If we need to skip this network, clear version_contracts and break
                    if skip_network:
                        version_contracts = {}
                        break  # Break out of tag loop for this network

                # Add version manifest if we found any contracts
                if version_contracts:
                    network_data["versions"][tag] = {"contracts": version_contracts}

            # Add network to cache if we found any versions
            if network_data["versions"]:
                cache["networks"][network] = network_data

        # Update metadata to reflect which networks were actually processed
        cache["metadata"]["networks"] = list(cache["networks"].keys())

        return cache
