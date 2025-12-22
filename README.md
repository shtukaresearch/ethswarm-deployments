# ethswarm-deployments

Python library for managing Ethswarm smart contract deployment data across all versions and networks.

## Overview

This library ingests Swarm smart contract deployment data from the [ethersphere/storage-incentives](https://github.com/ethersphere/storage-incentives) GitHub repository and provides a clean Python interface for accessing deployment information across:

- Multiple contract versions (v0.4.0 through v0.9.4+)
- Multiple networks (mainnet, testnet)
- Both legacy and hardhat-deploy format contracts

## Features

- **Multi-network support**: Query deployments on Gnosis Chain mainnet and Sepolia testnet
- **Version tracking**: Access any version of deployed contracts
- **Backward compatible**: Supports both legacy (`staking`) and canonical (`StakeRegistry`) contract names
- **Persistent caching**: Local cache with block timestamp optimization
- **Rich metadata**: Includes ABIs, bytecode, constructor args, and transaction hashes

## Installation

```bash
pip install ethswarm-deployments
```

## Quick Start

```python
from ethswarm_deployments import DeploymentManager

# Initialize (uses cached data at ~/.ethswarm-deployments/deployments.json)
mgr = DeploymentManager()

# Get latest deployment on mainnet (default)
deployment = mgr.deployment("StakeRegistry")
print(f"StakeRegistry at {deployment.address}")

# Get specific version on testnet
deployment = mgr.deployment("Redistribution", version="v0.9.2", network="testnet")

# List all versions
versions = mgr.versions()

# Get all deployments of a contract across versions
all_staking = mgr.all_deployments("StakeRegistry")
```

## Regenerating Cache

The cache can be regenerated from GitHub:

```python
from ethswarm_deployments import regenerate_from_github

# Regenerate cache (requires RPC endpoints)
regenerate_from_github(
    mainnet_rpc_url="https://rpc.gnosischain.com",
    testnet_rpc_url="https://ethereum-sepolia-rpc.publicnode.com"
)
```

## License

MIT
