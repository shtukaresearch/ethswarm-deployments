# ethswarm-deployments Design Document

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

Two cache files stored in `~/.ethswarm-deployments/`:

1. **deployments.json** - Main deployment cache (~2-3 MB)
2. **block_timestamps.json** - Block timestamp cache (~5-10 KB)

---

## Cache File Specifications

### 1. Deployment Cache (`deployments.json`)

#### Schema

The cache uses a **normalized structure** to avoid data duplication:
- **`deployments`**: Stores each unique contract deployment instance (by address)
- **`versions`**: Maps version numbers to contract addresses, forming a version manifest

```json
{
  "metadata": {
    "generated_at": "2025-12-22 12:00:00 UTC",
    "source_repo": "https://github.com/ethersphere/storage-incentives",
    "networks": ["mainnet", "testnet"]
  },
  "networks": {
    "mainnet": {
      "chain_id": 100,
      "chain_name": "Gnosis Chain",
      "block_explorer_url": "https://gnosisscan.io",

      "deployments": {
        "0xdBF3Ea6F5beE45c02255B2c26a16F300502F68da": {
          "address": "0xdBF3Ea6F5beE45c02255B2c26a16F300502F68da",
          "block": 16514506,
          "timestamp": 1623417600,
          "abi": [...],
          "url": "https://gnosisscan.io/address/0xdBF3Ea6F5beE45c02255B2c26a16F300502F68da",
          "bytecode": "0x...",
          "source_format": "bridged"
        },
        "0xda2a16EE889E7F04980A8d597b48c8D51B9518F4": {
          "address": "0xda2a16EE889E7F04980A8d597b48c8D51B9518F4",
          "block": 25527075,
          "timestamp": 1671456789,
          "abi": [...],
          "url": "https://gnosisscan.io/address/0xda2a16EE889E7F04980A8d597b48c8D51B9518F4",
          "transaction_hash": "0x...",
          "bytecode": "0x...",
          "deployed_bytecode": "0x...",
          "constructor_args": [...],
          "solc_input_hash": "...",
          "num_deployments": 1,
          "source_format": "hardhat-deploy"
        },
        "0x45a1502382541Cd610CC9068e88727426b696293": {
          "address": "0x45a1502382541Cd610CC9068e88727426b696293",
          "block": 35961749,
          "timestamp": 1725984000,
          "abi": [...],
          "url": "https://gnosisscan.io/address/0x45a1502382541Cd610CC9068e88727426b696293",
          "transaction_hash": "0x...",
          "bytecode": "0x...",
          "deployed_bytecode": "0x...",
          "constructor_args": [...],
          "solc_input_hash": "...",
          "num_deployments": 2,
          "source_format": "hardhat-deploy"
        }
      },

      "versions": {
        "v0.4.0": {
          "contracts": {
            "Token": "0xdBF3Ea6F5beE45c02255B2c26a16F300502F68da",
            "StakeRegistry": "0xda2a16EE889E7F04980A8d597b48c8D51B9518F4",
            "PostageStamp": "0x...",
            "PriceOracle": "0x...",
            "Redistribution": "0x..."
          }
        },
        "v0.5.0": {
          "contracts": {
            "Token": "0xdBF3Ea6F5beE45c02255B2c26a16F300502F68da",
            "StakeRegistry": "0xda2a16EE889E7F04980A8d597b48c8D51B9518F4",
            "PostageStamp": "0x...",
            "PriceOracle": "0x...",
            "Redistribution": "0xNEW..."
          }
        },
        "v0.9.1": {
          "contracts": {
            "Token": "0xdBF3Ea6F5beE45c02255B2c26a16F300502F68da",
            "StakeRegistry": "0x45a1502382541Cd610CC9068e88727426b696293",
            "PostageStamp": "0x...",
            "PriceOracle": "0x...",
            "Redistribution": "0xNEWER..."
          }
        }
      }
    },
    "testnet": {
      "chain_id": 11155111,
      "chain_name": "Sepolia",
      "block_explorer_url": "https://sepolia.etherscan.io",
      "deployments": {...},
      "versions": {...}
    }
  }
}
```

#### Design Rationale

**Normalized Structure Benefits**:
1. **No data duplication**: Each deployment instance stored once, referenced by address
2. **Efficient storage**: ~40% size reduction (Token data not duplicated across 17+ versions)
3. **Natural token handling**: Token isn't special-cased; it simply has the same address across all versions
4. **Clean queries**:
   - `deployment(name, version)` → lookup version → get address → lookup deployment data
   - `all_deployments(name)` → filter deployments by name (already deduplicated)
5. **Version manifest clarity**: Each version's `contracts` section shows the active deployment addresses

**Key Design Decisions**:
- **Plain address keys**: Use `"0xdBF..."` not `"mainnet:0xdBF..."` (deployments already scoped by network)
- **No stored first_version**: Compute dynamically by scanning versions when needed
- **Referential integrity**: Version manifests reference deployments that must exist in `deployments` dict

#### Field Descriptions

**Top-level metadata:**
- `generated_at`: ISO timestamp of cache generation
- `source_repo`: GitHub repository URL
- `networks`: List of networks in cache

**Network-level fields:**
- `chain_id`: EVM chain ID (100 for mainnet, 11155111 for testnet)
- `chain_name`: Human-readable chain name
- `block_explorer_url`: Base URL for block explorer
- `deployments`: Dictionary mapping contract addresses to deployment data (unique instances)
- `versions`: Dictionary mapping version tags to contract manifests (address references)

**Deployment object fields** (stored in `deployments[address]`)

| Field | Type | Required | Source | Description |
|-------|------|----------|--------|-------------|
| `address` | string | Yes | Both | Contract address (checksummed, same as dict key) |
| `block` | number | Yes | Both | Deployment block number |
| `timestamp` | number | Yes | RPC | Unix timestamp of deployment block |
| `abi` | array | Yes | Both | Full contract ABI |
| `url` | string | Yes | Computed | Block explorer URL for contract |
| `transaction_hash` | string | No | Hardhat | Deployment transaction hash (or bridge transaction for Token) |
| `source_format` | string | Yes | Metadata | **Source format**: `"hardhat-deploy"` if sourced from `deployments/{network}/*.json`, `"legacy"` if sourced from `{network}_deployed.json`, `"bridged"` for Token contract (bridged via Omnibridge, not deployed) |
| `bytecode` | string | No | Both | **Creation bytecode**: Complete code sent during deployment, includes constructor + initialization + runtime code. Larger than deployed_bytecode. |
| `deployed_bytecode` | string | No | Hardhat | **Runtime bytecode**: Code living on blockchain after deployment, excludes constructor. What actually executes when contract is called. Not available for legacy/bridged contracts. |
| `constructor_args` | array | No | Hardhat | Constructor arguments used during deployment. Not available for legacy/bridged contracts. |
| `solc_input_hash` | string | No | Hardhat | Hash of Solidity compiler input (changes when source code changes). Not available for legacy/bridged contracts. |
| `num_deployments` | number | No | Hardhat | Local deployment counter tracked by hardhat-deploy. Increments each time this contract name is deployed in this network directory, regardless of whether bytecode changes. Resets if deployment directory is deleted. Not available for legacy/bridged contracts. |

**Version manifest fields** (stored in `versions[version_tag].contracts`)
- Maps canonical contract names to addresses
- Example: `"Token": "0xdBF3Ea6F5beE45c02255B2c26a16F300502F68da"`
- Addresses must reference existing entries in the `deployments` dictionary

**Field Inclusion Rules:**
- **Always include**: address, block, timestamp, abi, url, source_format
- **Include if available**: All optional fields when source data provides them
- **Exclude**: Compiler metadata (63% bloat), devdoc, userdoc, storageLayout
- **Contract name**: Not stored in deployment object; obtained from version manifest lookup

**Special Case: Token Contract**

The Token contract has `source_format: "bridged"` and is missing optional Hardhat fields because:
- **Not deployed via Hardhat**: The Token was bridged from Ethereum mainnet ([0x19062190b1925b5b6689d7073fdfc8c2976ef8cb](https://etherscan.io/token/0x19062190b1925b5b6689d7073fdfc8c2976ef8cb)) to Gnosis Chain via [Gnosis Omnibridge](https://docs.gnosischain.com/bridges/About%20Token%20Bridges/omnibridge) on June 11, 2021
- **Transaction is bridge call**: The `transaction_hash` field references the Omnibridge `executeAffirmation()` call, not a contract deployment
- **Same address across versions**: The Token deployment appears with the same address in all versions (v0.4.0+), demonstrating the normalized schema's efficiency

**Partial Cache Support:**

Caches may contain a subset of networks (e.g., only "mainnet" or only "testnet")
if regenerated with partial RPC configuration. This is intentional and supports:

- **Testing**: Generate cache with single test network
- **Production**: Use mainnet-only caches in production environments
- **Development**: Set up one network at a time

When a network is missing from the cache:
- All DeploymentManager methods raise `NetworkNotFoundError` for that network
- Use `has_network(network)` to check availability before querying
- Timestamps are guaranteed present for all cached networks (never None)

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
                                 If None, uses ~/.ethswarm-deployments/deployments.json

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
        Get all distinct deployments of a contract across all versions

        Returns only unique deployments (by address). If the same contract address
        appears in multiple versions (e.g., Token contract), only one entry is
        returned with the earliest version where it appeared.

        Args:
            contract_name: Name of contract (canonical or legacy)
            network: Network name ("mainnet" or "testnet")

        Returns:
            List of ContractDeployment objects with distinct addresses,
            sorted chronologically by first appearance (earliest version first)

        Example:
            If StakeRegistry was deployed at 0xAAA in v0.4.0, then redeployed
            at 0xBBB in v0.9.1, this returns two deployments:
            - StakeRegistry at 0xAAA (version="v0.4.0")
            - StakeRegistry at 0xBBB (version="v0.9.1")

            If Token remains at 0xdBF... across all versions, this returns
            one deployment:
            - Token at 0xdBF... (version="v0.4.0")
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

    def has_network(self, network: str) -> bool:
        """
        Check if a network is available in the cache

        Args:
            network: Network name to check

        Returns:
            True if network exists in cache, False otherwise

        Notes:
            Caches may contain only a subset of networks if regenerated
            with partial RPC configuration
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
            NetworkNotFoundError: If network not in cache
        """
```

### Module-level Functions

```python
def parse_deployments_from_repo(
    repo_url: str,
    timestamp_lookup: Callable[[int, str], int],
) -> Dict[str, Any]:
    """
    Parse deployment data from repository (low-level function for testing)

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

    Notes:
        - Processes all stable versions (tags starting with 'v' without '-rc')
        - timestamp_lookup is called once per unique (block_number, network) pair
        - For testing, provide a mock function: lambda block, net: 1600000000 + block
    """

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
                    (defaults to ~/.ethswarm-deployments/deployments.json)
        repo_url: GitHub repository URL
        mainnet_rpc_url: Mainnet RPC URL (defaults to $GNO_RPC_URL)
        testnet_rpc_url: Testnet RPC URL (defaults to $SEP_RPC_URL)

    Returns:
        Path where deployment cache was saved

    Raises:
        ValueError: If both RPC URLs missing (need at least one)
        RuntimeError: If regeneration fails

    Notes:
        Partial cache support: Only networks with valid RPC URLs will be
        included in the generated cache. This allows:
        - Testing with single network
        - Production use of mainnet-only or testnet-only caches
        - Gradual RPC setup

        If a network is not in the cache, DeploymentManager methods will
        raise NetworkNotFoundError when querying that network.

    Implementation notes:
        - Uses parse_deployments_from_repo() internally
        - Creates timestamp_lookup from RPC URLs and timestamp cache
        - Processes only networks with available RPC URLs
        - Saves result to disk and updates timestamp cache
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

The library supports two naming conventions for contracts:

1. **Canonical names** (from hardhat-deploy): `Token`, `StakeRegistry`, `PostageStamp`, `PriceOracle`, `Redistribution`
   - Source: JSON filenames in `deployments/mainnet/*.json` (e.g., `StakeRegistry.json`)
   - Specified in `deploy()` calls in deployment scripts

2. **Legacy names** (from Swarm's custom format): `bzzToken`, `staking`, `postageStamp`, `priceOracle`, `redistribution`
   - Source: Object keys in `mainnet_deployed.json` under `contracts`
   - Manually curated for the Swarm node API

**Rationale for Hardcoded Mapping**:

The correspondence between legacy and canonical names must be maintained as a **hardcoded constant** because:

1. **Names are manually curated**: Legacy names were hand-picked for the Swarm node API and don't follow a consistent derivation rule:
   - `bzzToken` is manually chosen (not `testToken` from the deploy tag)
   - `priceOracle` uses the full name (not `oracle` from the deploy tag)
   - Other names happen to match their deploy tags (`staking`, `postageStamp`, `redistribution`)

2. **No algorithmic relationship**: The mapping cannot be derived from:
   - Contract addresses (addresses change across versions)
   - Source filenames (`TestToken.sol` → `Token` vs `bzzToken`)
   - Deployment script tags (`oracle` → `PriceOracle` vs `priceOracle`)
   - Any naming convention or transformation rule

3. **Stable across versions**: Analysis of tags v0.4.0 through v0.9.2 confirms:
   - Legacy names are identical across all versions
   - Canonical names are identical across all versions (since v0.6.0)
   - The 1:1 correspondence is consistent and stable

**Implementation**:

```python
# Hardcoded bidirectional mapping for backward compatibility
LEGACY_TO_CANONICAL = {
    "bzzToken": "Token",
    "staking": "StakeRegistry",
    "postageStamp": "PostageStamp",
    "priceOracle": "PriceOracle",
    "redistribution": "Redistribution",
}

def normalize_contract_name(name: str) -> str:
    """
    Convert contract name to canonical form

    Args:
        name: Contract name (canonical or legacy)

    Returns:
        Canonical contract name

    Implementation notes:
    - Returns canonical names unchanged
    - Converts legacy names to canonical using LEGACY_TO_CANONICAL
    - Unknown names may return unchanged or raise ValueError (implementation choice)
    """
```

**Note**: Only these two naming conventions appear in deployment JSON files. Hardhat deployment tags and Solidity source filenames are internal to the storage-incentives repository and are not exposed by this library.

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
4. **Load timestamp cache** from `~/.ethswarm-deployments/block_timestamps.json`
5. **Fetch missing timestamps** via RPC for new blocks
6. **Update timestamp cache** with new entries
7. **Save deployment cache** to `~/.ethswarm-deployments/deployments.json`

### Timestamp Cache Management

**Loading:**
```python
def load_timestamp_cache(cache_path: Path) -> Dict[str, Dict[str, int]]:
    """
    Load existing timestamp cache or return empty dict

    Args:
        cache_path: Path to block_timestamps.json file

    Returns:
        Dictionary mapping network -> block_number_str -> timestamp
        Empty structure if file doesn't exist
    """
```

**Saving:**
```python
def save_timestamp_cache(cache: Dict[str, Dict[str, int]], cache_path: Path):
    """
    Save updated timestamp cache to disk

    Args:
        cache: Timestamp cache dictionary
        cache_path: Path to block_timestamps.json file

    Creates parent directories if they don't exist
    """
```

**Fetching:**
```python
def get_block_timestamp(
    block_number: int,
    network: str,
    rpc_url: str,
    cache: Dict[str, Dict[str, int]]
) -> int:
    """
    Get block timestamp, using cache or fetching via RPC

    Args:
        block_number: Block number to get timestamp for
        network: Network name ("mainnet" or "testnet")
        rpc_url: RPC endpoint URL
        cache: Timestamp cache (will be updated if RPC call is made)

    Returns:
        Unix timestamp of the block

    Implementation notes:
    - Check cache first (network -> str(block_number) lookup)
    - If not cached, make RPC call via eth_getBlockByNumber
    - Parse hex timestamp from response
    - Update cache with new value
    - Return timestamp
    """
```

### Format Detection

```python
from enum import Enum

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
        DeploymentFormat.LEGACY if HARDHAT_DEPLOY check fails but {network}_deployed.json file exists
        None if no deployment files found

    Note:
        DeploymentFormat.BRIDGED is never returned by this function - it's assigned
        programmatically for the Token contract during cache generation.
    """
```

### Hardhat-Deploy Parser

```python
def parse_hardhat_deployment(file_path: Path) -> Dict[str, Any]:
    """
    Parse a hardhat-deploy JSON file

    Args:
        file_path: Path to contract deployment JSON file

    Returns:
        Dictionary with canonical field names:
        - Required: address, block, abi, source_format
        - Optional: transaction_hash, bytecode, deployed_bytecode,
          constructor_args, solc_input_hash, num_deployments
    """
```

#### Hardhat-Deploy → Canonical Transformation

**Input Format**: JSON file from `deployments/{network}/{ContractName}.json`

**Field Mapping**:

| Hardhat Field | JSON Path | Canonical Field | Type | Required | Transformation |
|---------------|-----------|-----------------|------|----------|----------------|
| `address` | `.address` | `address` | string | Yes | Identity |
| `blockNumber` | `.receipt.blockNumber` | `block` | int | Yes | Identity |
| `abi` | `.abi` | `abi` | array | Yes | Identity |
| `transactionHash` | `.transactionHash` | `transaction_hash` | string | No | Identity |
| `bytecode` | `.bytecode` | `bytecode` | string | No | Identity |
| `deployedBytecode` | `.deployedBytecode` | `deployed_bytecode` | string | No | Identity |
| `args` | `.args` | `constructor_args` | array | No | Identity |
| `solcInputHash` | `.solcInputHash` | `solc_input_hash` | string | No | Identity |
| `numDeployments` | `.numDeployments` | `num_deployments` | int | No | Identity |
| — | — | `source_format` | string | Yes | Constant: `"hardhat-deploy"` |

**Notes**:
- All transformations except `source_format` are identity (copy value as-is)
- Field renames follow snake_case convention
- Optional fields are omitted from output if not present in input
- `receipt.blockNumber` is the only nested field extraction

### Legacy Parser

```python
def parse_legacy_deployment(file_path: Path) -> Dict[str, Dict[str, Any]]:
    """
    Parse legacy deployment JSON format

    Args:
        file_path: Path to {network}_deployed.json file

    Returns:
        Dictionary mapping canonical contract names to contract data
        Each contract has: address, block, abi, source_format, optional bytecode/url
    """
```

#### Legacy → Canonical Transformation

**Input Format**: JSON file `{network}_deployed.json` with structure:
```json
{
  "contracts": {
    "bzzToken": { ... },
    "staking": { ... },
    ...
  }
}
```

**Field Mapping** (per contract):

| Legacy Field | JSON Path | Canonical Field | Type | Required | Transformation |
|--------------|-----------|-----------------|------|----------|----------------|
| `address` | `.contracts.{legacy_name}.address` | `address` | string | Yes | Identity |
| `block` | `.contracts.{legacy_name}.block` | `block` | int | Yes | Identity |
| `abi` | `.contracts.{legacy_name}.abi` | `abi` | array | Yes | Identity |
| `bytecode` | `.contracts.{legacy_name}.bytecode` | `bytecode` | string | No | Identity |
| `url` | `.contracts.{legacy_name}.url` | `url` | string | No | Identity |
| — | — | `source_format` | string | Yes | Constant: `"legacy"` |

**Contract Name Mapping**:

| Legacy Name (dict key) | Canonical Name (output key) |
|------------------------|------------------------------|
| `bzzToken` | `Token` |
| `staking` | `StakeRegistry` |
| `postageStamp` | `PostageStamp` |
| `priceOracle` | `PriceOracle` |
| `redistribution` | `Redistribution` |

**Notes**:
- Output dict uses canonical names as keys, not legacy names
- All field transformations are identity (copy value as-is)
- Optional fields (`bytecode`, `url`) are omitted from output if not present in input
- Contract name mapping uses `LEGACY_TO_CANONICAL` constant

---

## Configuration

### Environment Variables

Based on [EIP-3770 chain short names](https://eips.ethereum.org/EIPS/eip-3770):

- `GNO_RPC_URL`: Default RPC URL for Gnosis Chain mainnet (chain ID 100, short name "gno")
- `SEP_RPC_URL`: Default RPC URL for Sepolia testnet (chain ID 11155111, short name "sep")

**Rationale**: EIP-3770 defines standard short names for EVM chains in the [ethereum-lists/chains](https://github.com/ethereum-lists/chains) repository, used by Gnosis Safe and other multi-chain applications.

### Default Paths

Default cache root: `./.ethswarm-deployments/`

- Deployment cache: `./.ethswarm-deployments/deployments.json`
- Timestamp cache: `./.ethswarm-deployments/block_timestamps.json`

**Path Configuration**: Future-proofed path management supporting different cache locations:

```python
from pathlib import Path
from typing import Optional

def get_default_cache_dir() -> Path:
    """
    Get default cache directory (user home)

    Returns:
        Path to ./.ethswarm-deployments
    """

def get_cache_paths(cache_root: Optional[Path] = None) -> tuple[Path, Path]:
    """
    Get cache file paths

    Args:
        cache_root: Custom cache directory (defaults to ./.ethswarm-deployments)

    Returns:
        Tuple of (deployments_path, timestamps_path)

    Implementation notes:
    - If cache_root is None, use get_default_cache_dir()
    - Return tuple of cache_root/deployments.json and cache_root/block_timestamps.json
    """
```

**Usage patterns**:
```python
# User-local (default)
mgr = DeploymentManager()  # Uses ~/.ethswarm-deployments/

# Working directory local
mgr = DeploymentManager(".ethswarm-deployments/deployments.json")

# System-wide (requires permissions)
mgr = DeploymentManager("/var/cache/swarm-deployments/deployments.json")

# Custom location
mgr = DeploymentManager("/path/to/custom/deployments.json")
```

### Network Configuration

Implementation note: hardcoded dict based on data retrieved from https://github.com/ethereum-lists/chains.

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
from ethswarm_deployments import DeploymentManager

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
from ethswarm_deployments import regenerate_from_github

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
from ethswarm_deployments import (
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
from ethswarm_deployments import ContractNotFoundError

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
from ethswarm_deployments import VersionNotFoundError

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
from ethswarm_deployments import NetworkNotFoundError

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
from ethswarm_deployments import EventNotFoundError

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
| 1.4 | 2025-12-21 | Removed implementations from code snippets (timestamp cache management, format detection, parsers, path configuration), added DeploymentFormat enum for type-safe format detection, converted all code examples to specification-style with signatures and docstrings only |
| 1.5 | 2025-12-22 | Added transformation tables for parser specifications: hardhat-deploy → canonical and legacy → canonical field mappings with JSON paths, types, and contract name mapping |
| 1.6 | 2025-12-22 | Added parse_deployments_from_repo() function specification to enable testing without RPC dependency through timestamp_lookup callback parameter, maintaining timestamps as required field |
| 1.7 | 2025-12-22 | Added partial cache support: caches may contain subset of networks based on RPC availability, added has_network() method, updated regenerate_from_github() to require at least one RPC URL and skip networks without RPC, timestamps remain required (int, not Optional) for all cached networks |
| 1.8 | 2025-12-22 | **Major schema change**: Normalized cache structure with separate `deployments` (keyed by address) and `versions` (address references) to eliminate duplication. Token contract documented as `source_format: "bridged"` (Omnibridge from Ethereum mainnet). Clarified `all_deployments()` returns distinct deployments only with earliest version. Added `DeploymentFormat.BRIDGED` enum value for Token contract, clarified `NONE` is detection-only. Cache size reduced ~40%. |
| 1.9 | 2025-12-22 | Removed `name` field from deployment objects (redundant, obtained from version manifest). Removed `DeploymentFormat.NONE`, replaced with `Optional[DeploymentFormat]` return type for `detect_deployment_format()`. Enum now only contains values that appear in cache. |
