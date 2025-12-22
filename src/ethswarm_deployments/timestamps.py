"""Block timestamp cache management for ethswarm-deployments library."""

import json
from pathlib import Path
from typing import Dict

import requests


def load_timestamp_cache(cache_path: Path) -> Dict[str, Dict[str, int]]:
    """
    Load existing timestamp cache or return empty dict.

    Args:
        cache_path: Path to block_timestamps.json file

    Returns:
        Dictionary mapping network -> block_number_str -> timestamp
        Empty dict if file doesn't exist or is corrupted
    """
    try:
        with open(cache_path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_timestamp_cache(cache: Dict[str, Dict[str, int]], cache_path: Path) -> None:
    """
    Save updated timestamp cache to disk.

    Args:
        cache: Timestamp cache dictionary
        cache_path: Path to block_timestamps.json file

    Creates parent directories if they don't exist.
    """
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(cache, f, indent=2)


def get_block_timestamp(
    block_number: int, network: str, rpc_url: str, cache: Dict[str, Dict[str, int]]
) -> int:
    """
    Get block timestamp, using cache or fetching via RPC.

    Args:
        block_number: Block number to get timestamp for
        network: Network name ("mainnet" or "testnet")
        rpc_url: RPC endpoint URL
        cache: Timestamp cache (will be updated if RPC call is made)

    Returns:
        Unix timestamp of the block

    Raises:
        KeyError: If RPC response is missing required fields
        ValueError: If RPC returns an error
        RuntimeError: If network error occurs
    """
    # Convert block number to string for cache key (JSON requirement)
    block_key = str(block_number)

    # Check cache first
    if network in cache and block_key in cache[network]:
        return cache[network][block_key]

    # Cache miss - make RPC call
    try:
        response = requests.post(
            rpc_url,
            json={
                "jsonrpc": "2.0",
                "method": "eth_getBlockByNumber",
                "params": [hex(block_number), False],  # Block number as hex, no full txs
                "id": 1,
            },
            timeout=30,
        )

        # Check for HTTP errors
        if response.status_code != 200:
            raise RuntimeError(f"RPC request failed with status {response.status_code}")

        result = response.json()

        # Check for RPC errors
        if "error" in result:
            raise ValueError(f"RPC error: {result['error']}")

        # Extract and parse timestamp
        timestamp_hex = result["result"]["timestamp"]
        timestamp = int(timestamp_hex, 16)

        # Update cache
        if network not in cache:
            cache[network] = {}
        cache[network][block_key] = timestamp

        return timestamp

    except requests.RequestException as e:
        raise RuntimeError(f"Network error during RPC call: {e}") from e
