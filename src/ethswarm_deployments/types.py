"""Data types and dataclasses for ethswarm-deployments library."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ContractDeployment:
    """Information about a deployed contract."""

    # Required fields
    version: str  # e.g., "v0.9.2"
    name: str  # Canonical name, e.g., "StakeRegistry"
    address: str  # Checksummed address
    block: int  # Deployment block number
    timestamp: int  # Unix timestamp
    abi: List[Dict[str, Any]]  # Full contract ABI
    network: str  # "mainnet" or "testnet"
    url: str  # Block explorer URL

    # Optional fields (from hardhat-deploy)
    transaction_hash: Optional[str] = None
    bytecode: Optional[str] = None
    deployed_bytecode: Optional[str] = None
    constructor_args: Optional[List[Any]] = None
    solc_input_hash: Optional[str] = None
    num_deployments: Optional[int] = None
    source_format: Optional[str] = None  # "legacy" or "hardhat-deploy"
