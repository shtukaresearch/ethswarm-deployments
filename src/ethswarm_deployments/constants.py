"""Configuration constants for ethswarm-deployments library."""

# Hardcoded bidirectional mapping for backward compatibility
# Maps legacy contract names (from mainnet_deployed.json) to canonical names (from hardhat-deploy)
LEGACY_TO_CANONICAL = {
    "bzzToken": "Token",
    "staking": "StakeRegistry",
    "postageStamp": "PostageStamp",
    "priceOracle": "PriceOracle",
    "redistribution": "Redistribution",
}

# Network configuration based on ethereum-lists/chains
# EIP-3770 chain short names for environment variables
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
