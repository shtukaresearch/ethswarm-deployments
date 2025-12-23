"""Deployment file parsers for ethswarm-deployments library."""

import json
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from .constants import LEGACY_TO_CANONICAL
from .exceptions import DefectiveDeploymentError


class DeploymentFormat(Enum):
    """
    Deployment file format types.

    Value strings define de/serialization law.

    All enum values appear as source_format in cache:
    - HARDHAT_DEPLOY: Contracts deployed via hardhat-deploy
    - LEGACY: Contracts from legacy deployment format
    - BRIDGED: Token contract (bridged via Omnibridge, not deployed)
    """

    HARDHAT_DEPLOY = "hardhat-deploy"
    LEGACY = "legacy"
    BRIDGED = "bridged"


def detect_deployment_format(tag_dir: Path, network: str) -> Optional[DeploymentFormat]:
    """
    Detect which deployment format is available in a git tag checkout.

    Assumption: any files
    * with json extension found in child directories of ./deployments, or
    * matching the pattern /{network}_deployed.json in repo root
    are deployment files.

    Args:
        tag_dir: Root directory of checked-out tag
        network: Network name ("mainnet" or "testnet")

    Returns:
        DeploymentFormat.HARDHAT_DEPLOY if deployments/{network}/*.json files exist
        DeploymentFormat.LEGACY if HARDHAT_DEPLOY check fails but {network}_deployed.json exists
        None if no deployment files found

    Note:
        DeploymentFormat.BRIDGED is never returned by this function - it's assigned
        programmatically for the Token contract during cache generation.
    """
    # Check hardhat-deploy format first (preferred)
    hardhat_dir = tag_dir / "deployments" / network
    if hardhat_dir.exists() and list(hardhat_dir.glob("*.json")):
        return DeploymentFormat.HARDHAT_DEPLOY

    # Check legacy format
    legacy_file = tag_dir / f"{network}_deployed.json"
    if legacy_file.exists():
        return DeploymentFormat.LEGACY

    # Neither found
    return None


def parse_hardhat_deployment(file_path: Path) -> Dict[str, Any]:
    """
    Parse a hardhat-deploy JSON file.

    Args:
        file_path: Path to contract deployment JSON file

    Returns:
        Dictionary with canonical field names:
        - Required: address, block, abi, source_format
        - Optional: transaction_hash, bytecode, deployed_bytecode,
          constructor_args, solc_input_hash, num_deployments

    Raises:
        DefectiveDeploymentError: If block number is missing from deployment file
    """
    with open(file_path) as f:
        data = json.load(f)

    # Extract required fields
    # Try to get block number from receipt first, fall back to top-level
    block_number = None
    if "receipt" in data and "blockNumber" in data["receipt"]:
        block_number = data["receipt"]["blockNumber"]
    elif "blockNumber" in data:
        block_number = data["blockNumber"]

    # If no block number, raise error to indicate defective deployment file
    if block_number is None:
        raise DefectiveDeploymentError(
            f"Missing block number in hardhat deployment file: {file_path}"
        )

    result: Dict[str, Any] = {
        "address": data["address"],
        "block": block_number,
        "abi": data["abi"],
        "source_format": "hardhat-deploy",
    }

    # Extract optional fields if present
    if "transactionHash" in data:
        result["transaction_hash"] = data["transactionHash"]
    if "bytecode" in data:
        result["bytecode"] = data["bytecode"]
    if "deployedBytecode" in data:
        result["deployed_bytecode"] = data["deployedBytecode"]
    if "args" in data:
        result["constructor_args"] = data["args"]
    if "solcInputHash" in data:
        result["solc_input_hash"] = data["solcInputHash"]
    if "numDeployments" in data:
        result["num_deployments"] = data["numDeployments"]

    return result


def parse_legacy_deployment(file_path: Path) -> Dict[str, Dict[str, Any]]:
    """
    Parse legacy deployment JSON format.

    Args:
        file_path: Path to {network}_deployed.json file

    Returns:
        Dictionary mapping canonical contract names to contract data
        Each contract has: address, block, abi, source_format, optional bytecode/url
    """
    with open(file_path) as f:
        data = json.load(f)

    result: Dict[str, Dict[str, Any]] = {}

    # Iterate over contracts dict
    for legacy_name, contract_data in data["contracts"].items():
        # Convert legacy name to canonical
        canonical_name = normalize_contract_name(legacy_name)

        # Extract required fields
        contract_result: Dict[str, Any] = {
            "address": contract_data["address"],
            "block": contract_data["block"],
            "abi": contract_data["abi"],
            "source_format": "legacy",
        }

        # Extract optional fields if present
        if "bytecode" in contract_data:
            contract_result["bytecode"] = contract_data["bytecode"]
        if "url" in contract_data:
            contract_result["url"] = contract_data["url"]

        result[canonical_name] = contract_result

    return result


def normalize_contract_name(name: str) -> str:
    """
    Convert contract name to canonical form.

    Args:
        name: Contract name (canonical or legacy)

    Returns:
        Canonical contract name
    """
    # If it's a legacy name, convert to canonical
    if name in LEGACY_TO_CANONICAL:
        return LEGACY_TO_CANONICAL[name]

    # Otherwise return as-is (might be canonical or unknown)
    return name
