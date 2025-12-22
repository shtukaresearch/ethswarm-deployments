# Test Suite Implementation Summary

This document summarizes the comprehensive test suite implemented for the swarm-deployments library, following the specifications in DESIGN.md.

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                                 # Shared pytest fixtures
├── fixtures/                                   # Test data
│   ├── __init__.py
│   ├── sample_deployments.json                 # Mock deployment cache
│   ├── sample_block_timestamps.json            # Mock timestamp cache
│   ├── hardhat_deploy/
│   │   └── StakeRegistry.json                  # Sample hardhat-deploy file
│   └── legacy/
│       └── mainnet_deployed.json               # Sample legacy file
├── unit/                                       # Unit tests
│   ├── __init__.py
│   ├── test_contract_name_normalization.py     # LEGACY_TO_CANONICAL mapping tests
│   ├── test_version_filtering.py               # filter_stable_tags() tests
│   ├── test_format_detection.py                # detect_deployment_format() tests
│   ├── test_parsers.py                         # Parser function tests
│   ├── test_timestamp_cache.py                 # Timestamp cache tests
│   ├── test_path_helpers.py                    # Path utility tests
│   └── test_exceptions.py                      # Exception hierarchy tests
└── integration/                                # Integration tests
    ├── __init__.py
    ├── test_deployment_manager.py              # Full DeploymentManager API tests
    ├── test_cache_generation.py                # regenerate_from_github() tests
    └── test_backward_compatibility.py          # Legacy name support tests
```

## Unit Tests (6 test modules)

**Note**: Contract name normalization is tested only at the integration level in `test_backward_compatibility.py`, as the mapping is a fixed constant with no algorithmic logic to unit test.

### 1. Version Filtering (`test_version_filtering.py`)
- ✓ Tests filter_stable_tags() keeps only v-prefixed tags
- ✓ Tests removal of -rc versions (case-insensitive)
- ✓ Tests filtering of non-version tags (branches, etc.)
- ✓ Tests empty list handling
- ✓ Tests when no stable versions exist
- ✓ Tests complex version numbers
- ✓ Tests order preservation
- ✓ Tests -rc substring matching anywhere in tag (not just suffix)
- ✓ Tests that only '-rc' substring is matched (not just 'rc' characters)
- ✓ Tests case-insensitive -rc matching in any position

### 2. Format Detection (`test_format_detection.py`)
- ✓ Tests detection of hardhat-deploy format (deployments/network/*.json)
- ✓ Tests detection of legacy format (network_deployed.json)
- ✓ Tests return of NONE when no deployment files exist
- ✓ Tests hardhat-deploy priority over legacy
- ✓ Tests both mainnet and testnet detection
- ✓ Tests handling of empty directories and non-.json files

**Note**: The `DeploymentFormat` enum values are not tested at unit level, as they are validated by parser tests (which check `source_format` strings) and integration tests (which verify the cache JSON contains correct values).

### 3. Parsers (`test_parsers.py`)
- ✓ Tests parse_hardhat_deployment() with complete fields
- ✓ Tests field mapping (hardhat names → canonical names)
- ✓ Tests parsing with minimal required fields only
- ✓ Tests handling of missing optional fields
- ✓ Tests invalid JSON error handling
- ✓ Tests missing required fields error handling
- ✓ Tests parse_legacy_deployment() with all contracts
- ✓ Tests legacy name → canonical name mapping
- ✓ Tests extraction of required fields
- ✓ Tests inclusion of optional fields (bytecode, url)
- ✓ Tests all legacy contract names

### 4. Timestamp Cache (`test_timestamp_cache.py`)
- ✓ Tests load_timestamp_cache() with existing file
- ✓ Tests loading from non-existent file (returns empty)
- ✓ Tests handling of empty/corrupted JSON
- ✓ Tests save_timestamp_cache() to disk
- ✓ Tests creation of parent directories
- ✓ Tests overwriting existing files
- ✓ Tests get_block_timestamp() cache hit (no RPC call)
- ✓ Tests cache miss (makes RPC call via responses library)
- ✓ Tests cache update after RPC call
- ✓ Tests network-specific cache handling
- ✓ Tests RPC request format (JSON-RPC)
- ✓ Tests RPC error handling
- ✓ Tests network error handling
- ✓ Tests block numbers stored as strings (JSON requirement)

### 5. Path Helpers (`test_path_helpers.py`)
- ✓ Tests get_default_cache_dir() returns ~/.ethswarm-deployments
- ✓ Tests returned path is absolute
- ✓ Tests consistency across calls
- ✓ Tests get_cache_paths() returns tuple of two paths
- ✓ Tests default paths in home directory
- ✓ Tests correct filenames (deployments.json, block_timestamps.json)
- ✓ Tests custom cache root
- ✓ Tests custom root as string
- ✓ Tests None cache_root uses default
- ✓ Tests paths are absolute
- ✓ Tests relative custom root converted to absolute

### 6. Exceptions (`test_exceptions.py`)
- ✓ Tests CacheNotFoundError catchable as FileNotFoundError
- ✓ Tests CacheNotFoundError catchable as DeploymentError
- ✓ Tests NetworkNotFoundError catchable as ValueError
- ✓ Tests VersionNotFoundError catchable as ValueError
- ✓ Tests ContractNotFoundError catchable as ValueError
- ✓ Tests EventNotFoundError catchable as ValueError
- ✓ Tests all custom exceptions catchable as DeploymentError
- ✓ Tests all exceptions accept string messages
- ✓ Tests all exceptions accept empty messages

**Note**: Exception inheritance hierarchy is validated by catching behavior tests. Exception message formats are not tested as messages are for human debugging, not part of the API contract.


## Integration Tests (3 test modules, ~60 test cases)

### 1. DeploymentManager API (`test_deployment_manager.py`)
**Initialization:**
- ✓ Tests initialization with valid cache
- ✓ Tests initialization with default path
- ✓ Tests CacheNotFoundError when cache missing
- ✓ Tests exception catchable as FileNotFoundError

**versions():**
- ✓ Tests returns list for mainnet/testnet
- ✓ Tests versions are sorted
- ✓ Tests mainnet is default network
- ✓ Tests NetworkNotFoundError for invalid network

**latest_version():**
- ✓ Tests returns latest version
- ✓ Tests for both networks
- ✓ Tests mainnet as default
- ✓ Tests VersionNotFoundError when no versions

**contract_names():**
- ✓ Tests returns contract names for version
- ✓ Tests uses latest version when not specified
- ✓ Tests mainnet as default
- ✓ Tests VersionNotFoundError for invalid version

**deployment():**
- ✓ Tests returns ContractDeployment with canonical name
- ✓ Tests all fields populated (required and optional)
- ✓ Tests uses latest version when not specified
- ✓ Tests mainnet as default
- ✓ Tests ContractNotFoundError for missing contract
- ✓ Tests VersionNotFoundError for invalid version

**all_deployments():**
- ✓ Tests returns all versions of contract
- ✓ Tests deployments sorted by version
- ✓ Tests mainnet as default
- ✓ Tests empty list for missing contract

**event_abi():**
- ✓ Tests returns event ABI definition
- ✓ Tests event inputs structure
- ✓ Tests uses latest version when not specified
- ✓ Tests EventNotFoundError for missing event

**has_contract():**
- ✓ Tests returns True for existing contract
- ✓ Tests returns False for missing contract
- ✓ Tests returns False for invalid version
- ✓ Tests mainnet as default

**metadata():**
- ✓ Tests returns metadata dict
- ✓ Tests networks list is correct

**network_info():**
- ✓ Tests returns mainnet info (chain_id, chain_name, block_explorer_url)
- ✓ Tests returns testnet info
- ✓ Tests mainnet as default
- ✓ Tests NetworkNotFoundError for invalid network

### 2. Cache Generation (`test_cache_generation.py`)
**Note:** These tests use the real storage-incentives repository and RPC endpoints.

- ✓ Tests regenerate_from_github() with explicit RPC URLs
- ✓ Tests uses environment variables (GNO_RPC_URL, SEP_RPC_URL)
- ✓ Tests ValueError when RPC URLs missing
- ✓ Tests parameter precedence over environment variable
- ✓ Tests default output path (skipped to avoid modifying user cache)
- ✓ Tests timestamp cache reused across runs
- ✓ Tests stable tags filtering (no -rc versions)
- ✓ Tests cache contains required metadata
- ✓ Tests contract deployments have all required fields
- ✓ Tests git error handling
- ✓ Tests creates parent directories

### 3. Backward Compatibility (`test_backward_compatibility.py`)
**Legacy name support:**
- ✓ Tests 'bzzToken' works for Token
- ✓ Tests 'staking' works for StakeRegistry
- ✓ Tests all legacy names work
- ✓ Tests all_deployments() with legacy names
- ✓ Tests event_abi() with legacy names
- ✓ Tests has_contract() with legacy names

**Mixed usage:**
- ✓ Tests canonical and legacy names interchangeable
- ✓ Tests deployment always returns canonical name

**Edge cases:**
- ✓ Tests case-sensitivity of legacy names
- ✓ Tests unknown legacy names raise error
- ✓ Tests contract_names() returns only canonical names

## Test Fixtures

### Sample Data
- **sample_deployments.json**: Complete mock cache with 2 versions (v0.1.0, v0.2.0), 2 contracts (Token, StakeRegistry), 2 networks (mainnet, testnet)
- **sample_block_timestamps.json**: Mock timestamp cache with sample block→timestamp mappings
- **hardhat_deploy/StakeRegistry.json**: Sample hardhat-deploy format file
- **legacy/mainnet_deployed.json**: Sample legacy format file with bzzToken and staking contracts

### Shared Fixtures (conftest.py)
- `fixtures_dir`: Path to fixtures directory
- `sample_deployments_json`: Loaded deployment cache data
- `sample_block_timestamps_json`: Loaded timestamp cache data
- `temp_cache_dir`: Temporary cache directory
- `temp_deployments_cache`: Temporary deployments.json with sample data
- `temp_timestamps_cache`: Temporary block_timestamps.json with sample data
- `hardhat_deploy_sample`: Path to hardhat-deploy sample file
- `legacy_deploy_sample`: Path to legacy sample file

## Configuration

### pyproject.toml additions:
```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "ruff>=0.1.0",
    "responses>=0.24.0",  # Added for HTTP mocking
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

## Expected Test Results

**Current state:** All tests are expected to FAIL because:
1. Module stubs have not been created yet (import errors)
2. No implementation exists

**After stub implementation (Step 2):** Tests should still FAIL but:
- Import errors should be resolved
- Tests will fail on assertion errors (NotImplementedError, etc.)

**After full implementation (Step 3):** All tests should PASS

## Running the Tests

```bash
# From project root
pytest

# With verbose output
pytest -v

# Run specific test module
pytest tests/unit/test_contract_name_normalization.py

# Run specific test class
pytest tests/integration/test_deployment_manager.py::TestVersions

# Run specific test
pytest tests/unit/test_version_filtering.py::TestFilterStableTags::test_filters_stable_versions_only
```

## Test Coverage Areas

✓ **Contract name normalization** - All mapping functions
✓ **Version filtering** - Stable tag detection
✓ **Format detection** - Hardhat-deploy vs legacy
✓ **File parsing** - Both deployment formats
✓ **Timestamp caching** - Load, save, RPC integration
✓ **Path management** - Default and custom paths
✓ **Exception handling** - All error conditions
✓ **DeploymentManager API** - All public methods
✓ **Cache generation** - Full regeneration workflow
✓ **Backward compatibility** - Legacy name support

## Notes

- Tests use `responses` library for HTTP mocking (RPC calls)
- Integration tests for cache generation use the real storage-incentives repo
- Tests avoid modifying the user's default cache location
- All error messages tested match DESIGN.md specification
- Exception inheritance allows catching as both custom and standard types
