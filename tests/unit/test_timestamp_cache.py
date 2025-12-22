"""Unit tests for block timestamp caching functionality."""

import json
from pathlib import Path
from typing import Dict

import pytest
import responses

from ethswarm_deployments.timestamps import (
    get_block_timestamp,
    load_timestamp_cache,
    save_timestamp_cache,
)


class TestLoadTimestampCache:
    """Test the load_timestamp_cache function."""

    def test_loads_existing_cache_file(self, temp_timestamps_cache: Path):
        """Test loading an existing timestamp cache file."""
        cache = load_timestamp_cache(temp_timestamps_cache)

        assert "mainnet" in cache
        assert "testnet" in cache
        assert cache["mainnet"]["25527075"] == 1671456789
        assert cache["testnet"]["1234567"] == 1650000000

    def test_returns_empty_structure_when_file_missing(self, tmp_path: Path):
        """Test that missing file returns empty dictionary structure."""
        non_existent = tmp_path / "does_not_exist.json"
        cache = load_timestamp_cache(non_existent)

        # Should return empty dict (or empty structure like {"mainnet": {}, "testnet": {}})
        assert isinstance(cache, dict)
        # Either completely empty or with empty network dicts
        assert len(cache) == 0 or all(len(v) == 0 for v in cache.values())

    def test_handles_empty_json_file(self, tmp_path: Path):
        """Test handling of empty JSON file."""
        empty_file = tmp_path / "empty.json"
        empty_file.write_text("{}")

        cache = load_timestamp_cache(empty_file)
        assert isinstance(cache, dict)

    def test_handles_corrupted_json_file(self, tmp_path: Path):
        """Test handling of corrupted JSON file."""
        corrupted = tmp_path / "corrupted.json"
        corrupted.write_text("{ invalid json")

        # Should either return empty dict or raise JSONDecodeError
        try:
            cache = load_timestamp_cache(corrupted)
            assert isinstance(cache, dict)
        except json.JSONDecodeError:
            pass  # This is also acceptable behavior


class TestSaveTimestampCache:
    """Test the save_timestamp_cache function."""

    def test_saves_cache_to_file(self, tmp_path: Path):
        """Test saving cache to disk."""
        cache_file = tmp_path / "test_cache.json"
        cache_data = {
            "mainnet": {
                "12345": 1671456789,
                "67890": 1681228800,
            },
            "testnet": {
                "11111": 1650000000,
            },
        }

        save_timestamp_cache(cache_data, cache_file)

        # Verify file was created and contains correct data
        assert cache_file.exists()
        with open(cache_file) as f:
            loaded = json.load(f)
        assert loaded == cache_data

    def test_creates_parent_directories(self, tmp_path: Path):
        """Test that parent directories are created if they don't exist."""
        nested_path = tmp_path / "level1" / "level2" / "cache.json"
        cache_data = {"mainnet": {"12345": 1671456789}}

        save_timestamp_cache(cache_data, nested_path)

        assert nested_path.exists()
        assert nested_path.parent.exists()

    def test_overwrites_existing_file(self, tmp_path: Path):
        """Test that existing file is overwritten."""
        cache_file = tmp_path / "cache.json"
        cache_file.write_text('{"old": "data"}')

        new_data = {"mainnet": {"12345": 1671456789}}
        save_timestamp_cache(new_data, cache_file)

        with open(cache_file) as f:
            loaded = json.load(f)
        assert loaded == new_data
        assert "old" not in loaded

    def test_saves_empty_cache(self, tmp_path: Path):
        """Test saving an empty cache."""
        cache_file = tmp_path / "empty_cache.json"
        save_timestamp_cache({}, cache_file)

        assert cache_file.exists()
        with open(cache_file) as f:
            loaded = json.load(f)
        assert loaded == {}


class TestGetBlockTimestamp:
    """Test the get_block_timestamp function."""

    def test_cache_hit_no_rpc_call(self):
        """Test that cached timestamp is returned without RPC call."""
        cache: Dict[str, Dict[str, int]] = {
            "mainnet": {
                "12345": 1671456789,
            }
        }

        # No responses registered - should not make any HTTP calls
        timestamp = get_block_timestamp(12345, "mainnet", "http://fake-rpc.example.com", cache)

        assert timestamp == 1671456789
        # Cache should be unchanged
        assert cache["mainnet"]["12345"] == 1671456789

    @responses.activate
    def test_cache_miss_makes_rpc_call(self):
        """Test that cache miss triggers RPC call."""
        # Mock RPC response
        responses.add(
            responses.POST,
            "http://test-rpc.example.com",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "timestamp": "0x63a12345",  # Hex timestamp
                },
            },
            status=200,
        )

        cache: Dict[str, Dict[str, int]] = {"mainnet": {}}
        timestamp = get_block_timestamp(12345, "mainnet", "http://test-rpc.example.com", cache)

        # Should have made RPC call and parsed hex timestamp
        expected_timestamp = int("0x63a12345", 16)
        assert timestamp == expected_timestamp

        # Cache should be updated
        assert cache["mainnet"]["12345"] == expected_timestamp

    @responses.activate
    def test_updates_cache_after_rpc_call(self):
        """Test that cache is updated with new timestamp."""
        responses.add(
            responses.POST,
            "http://test-rpc.example.com",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "timestamp": "0x63a12345",
                },
            },
            status=200,
        )

        cache: Dict[str, Dict[str, int]] = {"mainnet": {}}
        initial_size = len(cache["mainnet"])

        get_block_timestamp(12345, "mainnet", "http://test-rpc.example.com", cache)

        # Cache should have one more entry
        assert len(cache["mainnet"]) == initial_size + 1
        assert "12345" in cache["mainnet"]

    @responses.activate
    def test_testnet_network_handling(self):
        """Test that different networks maintain separate caches."""
        responses.add(
            responses.POST,
            "http://testnet-rpc.example.com",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "timestamp": "0x63b00000",
                },
            },
            status=200,
        )

        cache: Dict[str, Dict[str, int]] = {"mainnet": {}, "testnet": {}}
        timestamp = get_block_timestamp(99999, "testnet", "http://testnet-rpc.example.com", cache)

        # Should update testnet cache, not mainnet
        assert "99999" in cache["testnet"]
        assert "99999" not in cache["mainnet"]

    @responses.activate
    def test_rpc_request_format(self):
        """Test that RPC request has correct format."""

        def request_callback(request):
            # Verify request format
            body = json.loads(request.body)
            assert body["jsonrpc"] == "2.0"
            assert body["method"] == "eth_getBlockByNumber"
            assert body["params"][0] == hex(12345)  # Block number as hex
            assert body["params"][1] is False  # Don't need full transactions

            return (
                200,
                {},
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": body["id"],
                        "result": {"timestamp": "0x63a12345"},
                    }
                ),
            )

        responses.add_callback(
            responses.POST,
            "http://test-rpc.example.com",
            callback=request_callback,
            content_type="application/json",
        )

        cache: Dict[str, Dict[str, int]] = {"mainnet": {}}
        get_block_timestamp(12345, "mainnet", "http://test-rpc.example.com", cache)

    @responses.activate
    def test_handles_rpc_errors(self):
        """Test handling of RPC errors."""
        responses.add(
            responses.POST,
            "http://test-rpc.example.com",
            json={"jsonrpc": "2.0", "id": 1, "error": {"code": -32000, "message": "Block not found"}},
            status=200,
        )

        cache: Dict[str, Dict[str, int]] = {"mainnet": {}}

        # Should raise an appropriate error
        with pytest.raises((KeyError, ValueError, RuntimeError)):
            get_block_timestamp(99999999, "mainnet", "http://test-rpc.example.com", cache)

    @responses.activate
    def test_network_error_handling(self):
        """Test handling of network errors."""
        responses.add(
            responses.POST,
            "http://test-rpc.example.com",
            body="Network error",
            status=500,
        )

        cache: Dict[str, Dict[str, int]] = {"mainnet": {}}

        # Should raise an appropriate error
        with pytest.raises((ConnectionError, RuntimeError, Exception)):
            get_block_timestamp(12345, "mainnet", "http://test-rpc.example.com", cache)

    def test_block_number_as_string_key_in_cache(self):
        """Test that block numbers are stored as strings in cache (JSON requirement)."""
        cache: Dict[str, Dict[str, int]] = {
            "mainnet": {
                "12345": 1671456789,  # String key, not int
            }
        }

        # Should work with int block number parameter
        timestamp = get_block_timestamp(12345, "mainnet", "http://fake-rpc.example.com", cache)
        assert timestamp == 1671456789
