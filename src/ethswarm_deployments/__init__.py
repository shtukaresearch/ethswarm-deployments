"""
ethswarm-deployments: Python library for managing Ethswarm smart contract deployments.

This library provides access to Swarm smart contract deployment data from the
ethersphere/storage-incentives GitHub repository across multiple contract versions
(v0.4.0 through v0.9.4+) and networks (mainnet on Gnosis Chain, testnet on Sepolia).

Quick Start
-----------
    from ethswarm_deployments import DeploymentManager

    mgr = DeploymentManager()
    deployment = mgr.deployment("StakeRegistry")
    print(f"StakeRegistry at {deployment.address}")

    # Specific version and network
    deployment = mgr.deployment("Redistribution", version="v0.9.2", network="testnet")

    # List versions and contracts
    versions = mgr.versions()
    contracts = mgr.contracts()

Key Classes
-----------
DeploymentManager
    Main interface for querying contract deployments. Supports multi-network,
    multi-version queries with backward-compatible contract name aliases.

ContractDeployment
    Dataclass containing deployment info: address, abi, bytecode, constructor_args,
    tx_hash, block_number, block_timestamp, version, network.

Cache Management
----------------
Data is cached locally at ~/.ethswarm-deployments/deployments.json. To regenerate:

    from ethswarm_deployments import regenerate_from_github
    regenerate_from_github(
        mainnet_rpc_url="https://rpc.gnosischain.com",
        testnet_rpc_url="https://ethereum-sepolia-rpc.publicnode.com"
    )

Full documentation: https://github.com/shtukaresearch/ethswarm-deployments
"""

from importlib.metadata import PackageNotFoundError, version

from .deployments import DeploymentManager, regenerate_from_github
from .exceptions import (
    CacheNotFoundError,
    ContractNotFoundError,
    DefectiveDeploymentError,
    DeploymentError,
    EventNotFoundError,
    NetworkNotFoundError,
    VersionNotFoundError,
)
from .types import ContractDeployment

try:
    __version__ = version("ethswarm-deployments")
except PackageNotFoundError:
    __version__ = None

__all__ = [
    "DeploymentManager",
    "regenerate_from_github",
    "ContractDeployment",
    "DeploymentError",
    "CacheNotFoundError",
    "NetworkNotFoundError",
    "VersionNotFoundError",
    "ContractNotFoundError",
    "EventNotFoundError",
    "DefectiveDeploymentError",
]
