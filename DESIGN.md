# swarm-deployments Design Document

## Overview

This document specifies the design for a Python library that ingests Swarm smart contract deployment data from GitHub and provides a clean Python interface for accessing that data across multiple versions and networks.

## Goals

1. **Multi-network support**: Handle both mainnet (Gnosis Chain) and testnet (Sepolia) deployments
2. **Version tracking**: Access any version of deployed contracts (v0.4.0 through latest)
3. **Efficient caching**: Minimize RPC calls using persistent block timestamp cache
4. **Backward compatibility**: Support both legacy and canonical contract names
5. **Rich metadata**: Include all useful deployment data (bytecode, args, transaction hashes)
6. **Simple API**: Clean, intuitive interface matching existing patterns

## Architecture

### Data Flow

```
GitHub Repo → Clone → Parse Deployments → Fetch Timestamps → Cache JSON
                ↓                              ↑
         hardhat-deploy/          Block Timestamp Cache
         legacy formats           (persistent, reusable)
                ↓
         DeploymentManager
                ↓
         Python Interface
```

### Cache Structure

Two cache files stored in `~/.swarm-deployments/`:

1. **deployments.json** - Main deployment cache (~3-5 MB)
2. **block_timestamps.json** - Block timestamp cache (~5-10 KB)

---

## Cache File Specifications

### 1. Deployment Cache (`deployments.json`)

#### Schema

```json
{
  "metadata": {
    "generated_at": "2025-12-21 12:00:00 UTC",
    "source_repo": "https://github.com/ethersphere/storage-incentives",
    "networks": ["mainnet", "testnet"]
  },
  "networks": {
    "mainnet": {
      "chain_id": 100,
      "chain_name": "Gnosis Chain",
      "block_explorer_url": "https://gnosisscan.io",
      "versions": {
        "v0.4.0": {
          "contracts": {
            "StakeRegistry": {
              "address": "0x...",
              "block": 25527075,
              "timestamp": 1671456789,
              "abi": [...],
              "url": "https://gnosisscan.io/address/0x...",
              "transaction_hash": "0x...",
              "source_format": "legacy",
              "bytecode": "0x...",
              "deployed_bytecode": "0x...",
              "constructor_args": [...],
              "solc_input_hash": "...",
              "num_deployments": 1
            },
            "Token": {...},
            "PostageStamp": {...},
            "PriceOracle": {...},
            "Redistribution": {...}
          }
        },
        "v0.5.0": {...},
        "v0.6.0": {...}
      }
    },
    "testnet": {
      "chain_id": 11155111,
      "chain_name": "Sepolia",
      "block_explorer_url": "https://sepolia.etherscan.io",
      "versions": {...}
    }
  }
}
```

#### Field Descriptions

**Top-level metadata:**
- `generated_at`: ISO timestamp of cache generation
- `source_repo`: GitHub repository URL
- `networks`: List of networks in cache

**Network-level fields:**
- `chain_id`: EVM chain ID (100 for mainnet, 10200 for testnet)
- `chain_name`: Human-readable chain name
- `block_explorer_url`: Base URL for block explorer

**Contract-level fields:**

| Field | Type | Required | Source | Description |
|-------|------|----------|--------|-------------|
| `address` | string | Yes | Both | Contract address (checksummed) |
| `block` | number | Yes | Both | Deployment block number |
| `timestamp` | number | Yes | RPC | Unix timestamp of deployment block |
| `abi` | array | Yes | Both | Full contract ABI |
| `url` | string | Yes | Computed | Block explorer URL for contract |
| `transaction_hash` | string | No | Hardhat | Deployment transaction hash |
| `source_format` | string | Yes | Metadata | "legacy" or "hardhat-deploy" |
| `bytecode` | string | No | Both | **Creation bytecode**: Complete code sent during deployment, includes constructor + initialization + runtime code. Larger than deployed_bytecode. |
| `deployed_bytecode` | string | No | Hardhat | **Runtime bytecode**: Code living on blockchain after deployment, excludes constructor. What actually executes when contract is called. May be null in older deployments. |
| `constructor_args` | array | No | Hardhat | Constructor arguments used during deployment |
| `solc_input_hash` | string | No | Hardhat | Hash of Solidity compiler input (changes when source code changes) |
| `num_deployments` | number | No | Hardhat | Local deployment counter tracked by hardhat-deploy. Increments each time this contract name is deployed in this network directory, regardless of whether bytecode changes. Resets if deployment directory is deleted. |

**Field Inclusion Rules:**
- **Always include**: address, block, timestamp, abi, url, source_format
- **Include if available**: All optional fields when source data provides them
- **Exclude**: Compiler metadata (63% bloat), devdoc, userdoc, storageLayout

### 2. Block Timestamp Cache (`block_timestamps.json`)

#### Schema

```json
{
  "mainnet": {
    "25527075": 1671456789,
    "25527076": 1671456794,
    "27391083": 1681228800
  },
  "testnet": {
    "1234567": 1650000000
  }
}
```

#### Purpose

- Cache block timestamps to avoid redundant RPC calls
- Network-keyed for multi-chain support
- Block number (as string) → Unix timestamp mapping
  - **Note**: JSON specification requires object keys to be strings, so block numbers are stored as string keys
- Persistent across cache regenerations
- Can be safely deleted (will be regenerated)

---

## Python Interface Specification

### Core Classes

#### 1. ContractDeployment (dataclass)

```python
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

@dataclass
class ContractDeployment:
    """Information about a deployed contract"""

    # Required fields
    version: str                    # e.g., "v0.9.2"
    name: str                       # Canonical name, e.g., "StakeRegistry"
    address: str                    # Checksummed address
    block: int                      # Deployment block number
    timestamp: int                  # Unix timestamp
    abi: List[Dict[str, Any]]      # Full contract ABI
    network: str                    # "mainnet" or "testnet"
    url: str                        # Block explorer URL

    # Optional fields (from hardhat-deploy)
    transaction_hash: Optional[str] = None
    bytecode: Optional[str] = None
    deployed_bytecode: Optional[str] = None
    constructor_args: Optional[List[Any]] = None
    solc_input_hash: Optional[str] = None
    num_deployments: Optional[int] = None
    source_format: Optional[str] = None  # "legacy" or "hardhat-deploy"
```

#### 2. DeploymentManager (class)

```python
class DeploymentManager:
    """Manages contract deployment information across networks and versions"""

    def __init__(self, deployment_json_path: Optional[str] = None):
        """
        Initialize the deployment manager

        Args:
            deployment_json_path: Path to deployments.json
                                 If None, uses ~/.swarm-deployments/deployments.json

        Raises:
            FileNotFoundError: If deployment cache not found
        """

    def versions(self, network: str = "mainnet") -> List[str]:
        """
        Get list of all available versions for a network, sorted chronologically

        Args:
            network: Network name ("mainnet" or "testnet")

        Returns:
            List of version strings (e.g., ["v0.4.0", "v0.5.0", ...])
        """

    def latest_version(self, network: str = "mainnet") -> str:
        """
        Get the most recent version for a network

        Args:
            network: Network name ("mainnet" or "testnet")

        Returns:
            Version string (e.g., "v0.9.4")

        Raises:
            ValueError: If no versions found
        """

    def contract_names(
        self,
        version: Optional[str] = None,
        network: str = "mainnet"
    ) -> List[str]:
        """
        Get list of contract names for a given version

        Args:
            version: Contract version (defaults to latest)
            network: Network name ("mainnet" or "testnet")

        Returns:
            List of canonical contract names (e.g., ["StakeRegistry", "Token", ...])

        Raises:
            ValueError: If version not found
        """

    def deployment(
        self,
        contract_name: str,
        version: Optional[str] = None,
        network: str = "mainnet"
    ) -> ContractDeployment:
        """
        Get deployment information for a specific contract

        Accepts both canonical and legacy contract names:
        - "StakeRegistry" or "staking"
        - "Token" or "bzzToken"
        - "PostageStamp" or "postageStamp"
        - etc.

        Args:
            contract_name: Name of contract (canonical or legacy)
            version: Contract version (defaults to latest)
            network: Network name ("mainnet" or "testnet")

        Returns:
            ContractDeployment object

        Raises:
            ValueError: If version or contract not found
        """

    def all_deployments(
        self,
        contract_name: str,
        network: str = "mainnet"
    ) -> List[ContractDeployment]:
        """
        Get all deployments of a contract across all versions

        Args:
            contract_name: Name of contract (canonical or legacy)
            network: Network name ("mainnet" or "testnet")

        Returns:
            List of ContractDeployment objects, sorted by version
        """

    def event_abi(
        self,
        contract_name: str,
        event_name: str,
        version: Optional[str] = None,
        network: str = "mainnet"
    ) -> Dict[str, Any]:
        """
        Get ABI definition for a specific event

        Args:
            contract_name: Name of contract (canonical or legacy)
            event_name: Name of event
            version: Contract version (defaults to latest)
            network: Network name ("mainnet" or "testnet")

        Returns:
            Event ABI definition

        Raises:
            ValueError: If event not found in contract ABI
        """

    def has_contract(
        self,
        contract_name: str,
        version: str,
        network: str = "mainnet"
    ) -> bool:
        """
        Check if a contract exists in a given version/network

        Args:
            contract_name: Name of contract (canonical or legacy)
            version: Contract version
            network: Network name ("mainnet" or "testnet")

        Returns:
            True if contract exists, False otherwise
        """

    def metadata(self) -> Dict[str, Any]:
        """
        Get cache metadata (generation time, source repo, networks)

        Returns:
            Metadata dictionary
        """

    def network_info(self, network: str = "mainnet") -> Dict[str, Any]:
        """
        Get network information (chain ID, name, explorer URL)

        Args:
            network: Network name ("mainnet" or "testnet")

        Returns:
            Dictionary with chain_id, chain_name, block_explorer_url

        Raises:
            ValueError: If network not found
        """
```

### Module-level Functions

```python
def regenerate_from_github(
    output_path: Optional[str] = None,
    repo_url: str = "https://github.com/ethersphere/storage-incentives.git",
    mainnet_rpc_url: Optional[str] = None,
    testnet_rpc_url: Optional[str] = None,
) -> str:
    """
    Regenerate deployment cache by fetching latest data from GitHub

    Processes all stable versions (tags starting with 'v' without '-rc').
    Uses persistent timestamp cache to minimize RPC calls.

    Args:
        output_path: Where to save deployments.json
                    (defaults to ~/.swarm-deployments/deployments.json)
        repo_url: GitHub repository URL
        mainnet_rpc_url: Mainnet RPC URL (defaults to $GNO_RPC_URL)
        testnet_rpc_url: Testnet RPC URL (defaults to $SEP_RPC_URL)

    Returns:
        Path where deployment cache was saved

    Raises:
        ValueError: If RPC URLs not provided and environment variables not set
        RuntimeError: If regeneration fails
    """

def filter_stable_tags(tags: List[str]) -> List[str]:
    """
    Filter git tags to only include stable versions

    Stable versions:
    - Start with 'v'
    - Do not contain '-rc' (case-insensitive)

    Args:
        tags: List of git tags

    Returns:
        List of stable version tags
    """
```

### Contract Name Mapping

```python
# Bidirectional mapping for backward compatibility
LEGACY_TO_CANONICAL = {
    "bzzToken": "Token",
    "staking": "StakeRegistry",
    "postageStamp": "PostageStamp",
    "priceOracle": "PriceOracle",
    "redistribution": "Redistribution",
}

CANONICAL_TO_LEGACY = {v: k for k, v in LEGACY_TO_CANONICAL.items()}

def normalize_contract_name(name: str) -> str:
    """
    Convert contract name to canonical form

    Args:
        name: Contract name (canonical or legacy)

    Returns:
        Canonical contract name
    """
```

---

## Implementation Details

### Ingestion Logic

1. **Clone repository** into temporary directory
2. **Get stable tags**: Filter tags starting with 'v' without '-rc'
3. **For each tag**:
   - Checkout tag
   - **Try hardhat-deploy format first**:
     - Check `deployments/mainnet/` directory
     - Parse each `.json` file (contract name from filename)
     - Extract: address, abi, receipt.blockNumber, transactionHash, bytecode, deployedBytecode, args, solcInputHash, numDeployments
   - **Fall back to legacy format**:
     - Check `mainnet_deployed.json`
     - Apply name mapping (legacy → canonical)
     - Extract: address, abi, block, bytecode, url
   - **Repeat for testnet**
4. **Load timestamp cache** from `~/.swarm-deployments/block_timestamps.json`
5. **Fetch missing timestamps** via RPC for new blocks
6. **Update timestamp cache** with new entries
7. **Save deployment cache** to `~/.swarm-deployments/deployments.json`

### Timestamp Cache Management

**Loading:**
```python
def load_timestamp_cache(cache_path: Path) -> Dict[str, Dict[str, int]]:
    """Load existing timestamp cache or return empty dict"""
    if cache_path.exists():
        with open(cache_path) as f:
            return json.load(f)
    return {"mainnet": {}, "testnet": {}}
```

**Saving:**
```python
def save_timestamp_cache(cache: Dict[str, Dict[str, int]], cache_path: Path):
    """Save updated timestamp cache"""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, 'w') as f:
        json.dump(cache, f, indent=2)
```

**Fetching:**
```python
def get_block_timestamp(
    block_number: int,
    network: str,
    rpc_url: str,
    cache: Dict[str, Dict[str, int]]
) -> int:
    """Get block timestamp, using cache or fetching via RPC"""
    block_str = str(block_number)

    # Check cache first
    if block_str in cache.get(network, {}):
        return cache[network][block_str]

    # Fetch via RPC
    response = requests.post(
        rpc_url,
        json={
            "jsonrpc": "2.0",
            "method": "eth_getBlockByNumber",
            "params": [hex(block_number), False],
            "id": 1,
        },
        timeout=30,
    )
    response.raise_for_status()
    block_data = response.json().get("result", {})
    timestamp = int(block_data.get("timestamp", "0x0"), 16)

    # Update cache
    if network not in cache:
        cache[network] = {}
    cache[network][block_str] = timestamp

    return timestamp
```

### Format Detection

```python
def detect_deployment_format(tag_dir: Path, network: str) -> str:
    """
    Detect which deployment format is available

    Returns: "hardhat-deploy", "legacy", or "none"
    """
    hardhat_dir = tag_dir / "deployments" / network
    legacy_file = tag_dir / f"{network}_deployed.json"

    if hardhat_dir.exists() and any(hardhat_dir.glob("*.json")):
        return "hardhat-deploy"
    elif legacy_file.exists():
        return "legacy"
    else:
        return "none"
```

### Hardhat-Deploy Parser

```python
def parse_hardhat_deployment(file_path: Path) -> Dict[str, Any]:
    """
    Parse a hardhat-deploy JSON file

    Returns dict with canonical field names
    """
    with open(file_path) as f:
        data = json.load(f)

    contract = {
        "address": data["address"],
        "block": data["receipt"]["blockNumber"],
        "abi": data["abi"],
        "source_format": "hardhat-deploy",
    }

    # Optional fields
    if "transactionHash" in data:
        contract["transaction_hash"] = data["transactionHash"]
    if "bytecode" in data:
        contract["bytecode"] = data["bytecode"]
    if "deployedBytecode" in data:
        contract["deployed_bytecode"] = data["deployedBytecode"]
    if "args" in data:
        contract["constructor_args"] = data["args"]
    if "solcInputHash" in data:
        contract["solc_input_hash"] = data["solcInputHash"]
    if "numDeployments" in data:
        contract["num_deployments"] = data["numDeployments"]

    return contract
```

### Legacy Parser

```python
def parse_legacy_deployment(file_path: Path) -> Dict[str, Dict[str, Any]]:
    """
    Parse legacy deployment JSON

    Returns dict mapping canonical names to contract data
    """
    with open(file_path) as f:
        data = json.load(f)

    contracts = {}
    for legacy_name, contract_data in data.get("contracts", {}).items():
        # Convert to canonical name
        canonical_name = LEGACY_TO_CANONICAL.get(legacy_name, legacy_name)

        contract = {
            "address": contract_data["address"],
            "block": contract_data.get("block", 0),
            "abi": contract_data["abi"],
            "source_format": "legacy",
        }

        # Optional fields
        if "bytecode" in contract_data:
            contract["bytecode"] = contract_data["bytecode"]
        if "url" in contract_data:
            # Keep legacy URL if present, will be overwritten later
            contract["url"] = contract_data["url"]

        contracts[canonical_name] = contract

    return contracts
```

---

## Configuration

### Environment Variables

Based on [EIP-3770 chain short names](https://eips.ethereum.org/EIPS/eip-3770):

- `GNO_RPC_URL`: Default RPC URL for Gnosis Chain mainnet (chain ID 100, short name "gno")
- `SEP_RPC_URL`: Default RPC URL for Sepolia testnet (chain ID 11155111, short name "sep")

**Rationale**: EIP-3770 defines standard short names for EVM chains in the [ethereum-lists/chains](https://github.com/ethereum-lists/chains) repository, used by Gnosis Safe and other multi-chain applications.

### Default Paths

Default cache root: `~/.swarm-deployments/`

- Deployment cache: `~/.swarm-deployments/deployments.json`
- Timestamp cache: `~/.swarm-deployments/block_timestamps.json`

**Path Configuration**: Future-proofed path management supporting different cache locations:

```python
from pathlib import Path
from typing import Optional

def get_default_cache_dir() -> Path:
    """Get default cache directory (user home)"""
    return Path.home() / ".swarm-deployments"

def get_cache_paths(cache_root: Optional[Path] = None) -> tuple[Path, Path]:
    """
    Get cache file paths

    Args:
        cache_root: Custom cache directory (defaults to ~/.swarm-deployments)

    Returns:
        Tuple of (deployments_path, timestamps_path)
    """
    if cache_root is None:
        cache_root = get_default_cache_dir()

    return (
        cache_root / "deployments.json",
        cache_root / "block_timestamps.json",
    )
```

**Usage patterns**:
```python
# User-local (default)
mgr = DeploymentManager()  # Uses ~/.swarm-deployments/

# Working directory local
mgr = DeploymentManager(".swarm-deployments/deployments.json")

# System-wide (requires permissions)
mgr = DeploymentManager("/var/cache/swarm-deployments/deployments.json")

# Custom location
mgr = DeploymentManager("/path/to/custom/deployments.json")
```

### Network Configuration

```python
NETWORK_CONFIG = {
    "mainnet": {
        "chain_id": 100,
        "chain_name": "Gnosis Chain",
        "short_name": "gno",  # EIP-3770
        "block_explorer_url": "https://gnosisscan.io",
        "default_rpc_env": "GNO_RPC_URL",
    },
    "testnet": {
        "chain_id": 11155111,
        "chain_name": "Sepolia",
        "short_name": "sep",  # EIP-3770
        "block_explorer_url": "https://sepolia.etherscan.io",
        "default_rpc_env": "SEP_RPC_URL",
    },
}
```

---

## API Usage Examples

### Basic Usage

```python
from swarm_deployments import DeploymentManager

mgr = DeploymentManager()

# Get latest StakeRegistry on mainnet
stake = mgr.deployment("StakeRegistry")
print(f"Address: {stake.address}")
print(f"Block: {stake.block}")
print(f"Version: {stake.version}")

# Legacy name works too
stake = mgr.deployment("staking")  # Same result

# Get specific version on testnet
redistribution = mgr.deployment(
    "Redistribution",
    version="v0.9.2",
    network="testnet"
)
```

### Version Queries

```python
# List all versions
versions = mgr.versions()  # mainnet by default
testnet_versions = mgr.versions(network="testnet")

# Get latest version
latest = mgr.latest_version()

# List contracts in a version
contracts = mgr.contract_names(version="v0.9.2")
```

### Historical Analysis

```python
# Get all deployments of Redistribution contract
all_redist = mgr.all_deployments("Redistribution")

for deployment in all_redist:
    print(f"{deployment.version}: {deployment.address} (block {deployment.block})")
```

### Event ABI Extraction

```python
# Get event ABI
event_abi = mgr.event_abi("StakeRegistry", "StakeUpdated")

# Use with web3
from web3 import Web3
w3 = Web3(...)
contract = w3.eth.contract(address=stake.address, abi=stake.abi)
event = contract.events.StakeUpdated()
```

### Contract Existence Checks

```python
# Check if contract exists before accessing
if mgr.has_contract("NewContract", "v0.9.4"):
    deployment = mgr.deployment("NewContract", version="v0.9.4")
else:
    print("NewContract not deployed in v0.9.4")
```

### Metadata Access

```python
# Get cache metadata
metadata = mgr.metadata()
print(f"Generated: {metadata['generated_at']}")
print(f"Networks: {metadata['networks']}")

# Get network info
mainnet_info = mgr.network_info("mainnet")
print(f"Chain ID: {mainnet_info['chain_id']}")
print(f"Explorer: {mainnet_info['block_explorer_url']}")
```

### Cache Regeneration

```python
from swarm_deployments import regenerate_from_github

# Full regeneration with custom RPC endpoints
regenerate_from_github(
    mainnet_rpc_url="https://rpc.gnosischain.com",
    testnet_rpc_url="https://ethereum-sepolia-rpc.publicnode.com"
)

# Using environment variables
import os
os.environ["GNO_RPC_URL"] = "https://rpc.gnosischain.com"
os.environ["SEP_RPC_URL"] = "https://sepolia.gateway.tenderly.co"
regenerate_from_github()
```

---

## Error Handling

### Exception Hierarchy

The library raises standard Python exceptions that callers should handle:

```python
# Custom exceptions (if needed for future extension)
class DeploymentError(Exception):
    """Base exception for deployment-related errors"""
    pass

class CacheNotFoundError(DeploymentError, FileNotFoundError):
    """Raised when deployment cache file is not found"""
    pass

class NetworkNotFoundError(DeploymentError, ValueError):
    """Raised when requested network is not in cache"""
    pass

class VersionNotFoundError(DeploymentError, ValueError):
    """Raised when requested version is not found"""
    pass

class ContractNotFoundError(DeploymentError, ValueError):
    """Raised when requested contract is not found in version"""
    pass

class EventNotFoundError(DeploymentError, ValueError):
    """Raised when requested event is not found in contract ABI"""
    pass
```

### Exception Reference

| Exception | Raised By | Condition | Message Format |
|-----------|-----------|-----------|----------------|
| `CacheNotFoundError` | `DeploymentManager.__init__()` | Cache file doesn't exist | "Deployment cache not found at {path}. Run regenerate_from_github() to create it." |
| `NetworkNotFoundError` | `versions()`, `latest_version()`, `network_info()` | Network not found in cache | "Network '{network}' not found in cache" |
| `VersionNotFoundError` | `latest_version()` | No versions in network | "No versions found for network '{network}'" |
| `VersionNotFoundError` | `deployment()`, `contract_names()` | Version not found | "Version '{version}' not found in network '{network}'" |
| `ContractNotFoundError` | `deployment()` | Contract not found | "Contract '{contract}' not found in version '{version}' on network '{network}'" |
| `EventNotFoundError` | `event_abi()` | Event not found in ABI | "Event '{event}' not found in {contract} {version} ABI" |
| `ValueError` | `regenerate_from_github()` | Missing RPC URLs | "RPC URL required: set ${ENV_VAR} or pass {param_name} parameter" |
| `RuntimeError` | `regenerate_from_github()` | Git/network/RPC failures | Specific error message from underlying failure |

**Note**: All custom exceptions inherit from their standard counterparts (e.g., `CacheNotFoundError` inherits from `FileNotFoundError`), so existing code catching standard exceptions will continue to work.

### Usage Examples

**Handling cache not found:**
```python
from swarm_deployments import (
    DeploymentManager,
    regenerate_from_github,
    CacheNotFoundError
)

try:
    mgr = DeploymentManager()
except CacheNotFoundError as e:
    # Cache doesn't exist, regenerate it
    regenerate_from_github()
    mgr = DeploymentManager()

# Also works with standard FileNotFoundError for backward compatibility
try:
    mgr = DeploymentManager()
except FileNotFoundError as e:
    # CacheNotFoundError inherits from FileNotFoundError
    regenerate_from_github()
    mgr = DeploymentManager()
```

**Handling missing contracts:**
```python
from swarm_deployments import ContractNotFoundError

# Using custom exception
try:
    deployment = mgr.deployment("NewContract", version="v0.9.4")
except ContractNotFoundError as e:
    # Contract doesn't exist in this version
    logging.warning(f"Contract not found: {e}")
    deployment = None

# Or using standard ValueError (also works due to inheritance)
try:
    deployment = mgr.deployment("NewContract", version="v0.9.4")
except ValueError as e:
    logging.warning(f"Contract not found: {e}")
    deployment = None

# Or check first to avoid exception
if mgr.has_contract("NewContract", "v0.9.4"):
    deployment = mgr.deployment("NewContract", version="v0.9.4")
```

**Handling invalid versions:**
```python
from swarm_deployments import VersionNotFoundError

try:
    deployment = mgr.deployment("StakeRegistry", version="v999.0.0")
except VersionNotFoundError as e:
    # Version doesn't exist
    available = mgr.versions()
    latest = mgr.latest_version()
    print(f"Invalid version. Available: {available}, Latest: {latest}")
```

**Handling network errors:**
```python
from swarm_deployments import NetworkNotFoundError

try:
    deployment = mgr.deployment("StakeRegistry", network="unknown")
except NetworkNotFoundError as e:
    # Network not in cache
    metadata = mgr.metadata()
    available_networks = metadata['networks']
    print(f"Available networks: {available_networks}")
```

**Handling event lookup failures:**
```python
from swarm_deployments import EventNotFoundError

try:
    event_abi = mgr.event_abi("StakeRegistry", "NonExistentEvent")
except EventNotFoundError as e:
    # Event not in contract ABI
    logging.error(f"Event not found: {e}")
    event_abi = None
```

**Handling regeneration failures:**
```python
import os

try:
    os.environ["GNO_RPC_URL"] = "https://rpc.gnosischain.com"
    os.environ["SEP_RPC_URL"] = "https://sepolia.gateway.tenderly.co"
    regenerate_from_github()
except ValueError as e:
    # Missing RPC configuration
    print(f"Configuration error: {e}")
except RuntimeError as e:
    # Network, git, or RPC failure
    print(f"Regeneration failed: {e}")
```

### Best Practices

1. **Use custom exceptions for specific error handling**: Catch `CacheNotFoundError`, `ContractNotFoundError`, etc. when you need to handle specific cases differently
2. **Use base exceptions for broad error handling**: Catch `FileNotFoundError` or `ValueError` when you want to handle all related errors uniformly (works due to inheritance)
3. **Always handle `CacheNotFoundError`** when initializing `DeploymentManager` in production code
4. **Use `has_contract()`** before calling `deployment()` to avoid exceptions in known uncertain cases
5. **Let exceptions propagate** in library code unless you have specific recovery logic
6. **Log exceptions** at appropriate levels (ERROR for failures, WARNING for missing optional data)
7. **Import only the exceptions you use**: Keeps code clean and signals intent to readers

---

## Testing Strategy

### Unit Tests

- Contract name normalization (legacy ↔ canonical)
- Version filtering (stable tags only)
- Format detection (hardhat-deploy vs legacy)
- Timestamp cache hit/miss
- Parser edge cases (missing optional fields)

### Integration Tests

- Full ingestion from test repository
- Multi-network cache generation
- API queries against generated cache
- Backward compatibility with legacy names
- Error handling (missing versions, contracts)

### Test Data

Create minimal test fixture repository with:
- 2 versions (v0.1.0, v0.2.0)
- 2 contracts (Token, StakeRegistry)
- Both formats (hardhat-deploy in v0.2.0, legacy in v0.1.0)
- Both networks (mainnet, testnet)

---

## Performance Considerations

### Cache Size

- **Deployment cache**: ~3-5 MB (all versions, both networks)
- **Timestamp cache**: ~5-10 KB
- **Total**: ~5 MB (trivial for modern systems)

### Load Time

- Initial load: ~50-100 ms (JSON parse + dictionary construction)
- Subsequent queries: <1 ms (in-memory dictionary lookup)

### Regeneration Time

With timestamp cache:
- First run: ~2-3 minutes (clone + parse + RPC calls)
- Subsequent runs: ~30-60 seconds (most timestamps cached)

Without timestamp cache:
- Every run: ~2-3 minutes (full RPC calls)

### Optimization Strategies

1. **Lazy loading**: Only parse requested network data
2. **Timestamp batching**: Batch RPC requests for multiple blocks
3. **Parallel processing**: Process versions concurrently
4. **Incremental updates**: Only process new tags (future enhancement)

---

## Future Enhancements

### Possible Additions

1. **Incremental updates**: Only fetch new versions
2. **ABI diffing**: Compare ABI changes across versions
3. **Bytecode verification**: Verify deployed bytecode matches source
4. **Multi-chain support**: Support other EVM chains
5. **Event indexing**: Pre-compute event signatures
6. **CLI tool**: Command-line interface for cache management
7. **Auto-update**: Automatic cache refresh on library import
8. **Version semantics**: Parse semver for smart version queries

### Not Planned

- Custom deployment tracking (out of scope)
- Live blockchain queries (use web3.py)
- Contract interaction (use web3.py)
- Deployment scripts (use hardhat-deploy)

---

## Appendix

### File Size Breakdown

| Component | Size | Percentage |
|-----------|------|------------|
| ABIs | ~2.5 MB | 50% |
| Bytecode | ~1.5 MB | 30% |
| Constructor args | ~0.5 MB | 10% |
| Metadata | ~0.5 MB | 10% |
| **Total** | **~5 MB** | **100%** |

### Version Coverage

Expected coverage (as of 2025-12-21):
- Total tags: 20 (v0.1.0 through v0.9.4)
- Tags with deployments: 17 (v0.4.0 onwards)
- Cached versions: 17
- Networks: 2 (mainnet, testnet)
- Contracts per version: 5 (Token, StakeRegistry, PostageStamp, PriceOracle, Redistribution)

### Dependencies

**Runtime:**
- `requests>=2.31.0` (HTTP requests for RPC calls)

**Development:**
- `pytest>=7.4.0` (testing)
- `ruff>=0.1.0` (linting/formatting)

**No dependencies on:**
- web3.py (not needed for cache generation)
- eth-utils (not needed for basic operations)
- Complex parsing libraries (stdlib JSON sufficient)

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-21 | Initial design document |
| 1.1 | 2025-12-21 | Updated testnet from Chiado to Sepolia (chain ID 11155111), added EIP-3770 chain codes, added path configuration methods, added JSON key format rationale, removed migration section |
| 1.2 | 2025-12-21 | Enhanced field descriptions for bytecode/deployed_bytecode/num_deployments, rewrote error handling for library usage with proper exception hierarchy and handling examples |
| 1.3 | 2025-12-21 | Updated exception reference table and usage examples to use custom exception types, added note about backward compatibility through inheritance, updated __init__.py to export custom exceptions |
