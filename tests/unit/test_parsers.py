"""Unit tests for deployment file parsers."""

import json
from pathlib import Path

import pytest

from ethswarm_deployments.exceptions import DefectiveDeploymentError
from ethswarm_deployments.parsers import parse_hardhat_deployment, parse_legacy_deployment


class TestParseHardhatDeployment:
    """Test the parse_hardhat_deployment function."""

    def test_parses_complete_hardhat_file(self, hardhat_deploy_sample: Path):
        """Test parsing a hardhat-deploy JSON file with all fields."""
        result = parse_hardhat_deployment(hardhat_deploy_sample)

        # Required fields
        assert result["address"] == "0xbbcdefabcdefabcdefabcdefabcdefabcdefabcd"
        assert result["block"] == 27391088
        assert result["abi"] is not None
        assert len(result["abi"]) > 0
        assert result["source_format"] == "hardhat-deploy"

        # Optional fields
        assert result["transaction_hash"] == (
            "0xbcdef1234567890abcdef1234567890abcdef1234567890abcdef12345678901"
        )
        assert result["bytecode"] == "0x608060405234801561001057600080fd5b50604051"
        assert result["deployed_bytecode"] == (
            "0x608060405234801561001057600080fd5b50600436106100"
        )
        assert result["constructor_args"] == []
        assert result["solc_input_hash"] == "def456ghi789"
        assert result["num_deployments"] == 1

    def test_field_mapping_from_hardhat_names(self, tmp_path: Path):
        """Test that hardhat field names are mapped to canonical names."""
        # Create a test file with hardhat naming
        test_file = tmp_path / "test.json"
        data = {
            "address": "0x1234567890123456789012345678901234567890",
            "abi": [{"type": "function", "name": "test"}],
            "receipt": {
                "blockNumber": 12345,
                "transactionHash": "0xabc",
            },
            "transactionHash": "0xabc",
            "bytecode": "0x1234",
            "deployedBytecode": "0x5678",
            "args": ["arg1", "arg2"],
            "solcInputHash": "hash123",
            "numDeployments": 3,
        }
        test_file.write_text(json.dumps(data))

        result = parse_hardhat_deployment(test_file)

        # Check field mappings
        assert result["block"] == 12345  # from receipt.blockNumber
        assert result["transaction_hash"] == "0xabc"  # from transactionHash
        assert result["constructor_args"] == ["arg1", "arg2"]  # from args
        assert result["deployed_bytecode"] == "0x5678"  # from deployedBytecode
        assert result["solc_input_hash"] == "hash123"  # from solcInputHash
        assert result["num_deployments"] == 3  # from numDeployments

    def test_parses_minimal_hardhat_file(self, tmp_path: Path):
        """Test parsing with only required fields."""
        test_file = tmp_path / "minimal.json"
        data = {
            "address": "0x1234567890123456789012345678901234567890",
            "abi": [],
            "receipt": {"blockNumber": 12345},
        }
        test_file.write_text(json.dumps(data))

        result = parse_hardhat_deployment(test_file)

        # Required fields present
        assert result["address"] == "0x1234567890123456789012345678901234567890"
        assert result["block"] == 12345
        assert result["abi"] == []
        assert result["source_format"] == "hardhat-deploy"

        # Optional fields not present (or None)
        assert "transaction_hash" not in result or result["transaction_hash"] is None
        assert "bytecode" not in result or result["bytecode"] is None
        assert "deployed_bytecode" not in result or result["deployed_bytecode"] is None
        assert "constructor_args" not in result or result["constructor_args"] is None

    def test_handles_missing_optional_fields(self, tmp_path: Path):
        """Test that missing optional fields don't cause errors."""
        test_file = tmp_path / "partial.json"
        data = {
            "address": "0x1234567890123456789012345678901234567890",
            "abi": [{"type": "event", "name": "Test"}],
            "receipt": {"blockNumber": 12345},
            # Only some optional fields
            "bytecode": "0x1234",
        }
        test_file.write_text(json.dumps(data))

        result = parse_hardhat_deployment(test_file)

        assert result["address"] == "0x1234567890123456789012345678901234567890"
        assert result["bytecode"] == "0x1234"
        # Other optional fields should not be present or be None
        assert "deployed_bytecode" not in result or result["deployed_bytecode"] is None

    def test_invalid_json_raises_error(self, tmp_path: Path):
        """Test that invalid JSON raises appropriate error."""
        test_file = tmp_path / "invalid.json"
        test_file.write_text("{ invalid json }")

        with pytest.raises((json.JSONDecodeError, ValueError)):
            parse_hardhat_deployment(test_file)

    def test_missing_required_fields_raises_error(self, tmp_path: Path):
        """Test that missing required fields raises KeyError."""
        test_file = tmp_path / "missing.json"
        # Missing required 'abi' field
        data = {
            "address": "0x1234567890123456789012345678901234567890",
            "receipt": {"blockNumber": 12345},
        }
        test_file.write_text(json.dumps(data))

        with pytest.raises(KeyError):
            parse_hardhat_deployment(test_file)

    def test_missing_block_number_raises_defective_error(self, tmp_path: Path):
        """Test that missing block number raises DefectiveDeploymentError."""
        test_file = tmp_path / "defective.json"
        # Missing block number (neither in receipt nor top-level)
        data = {
            "address": "0x1234567890123456789012345678901234567890",
            "abi": [],
        }
        test_file.write_text(json.dumps(data))

        with pytest.raises(DefectiveDeploymentError) as exc_info:
            parse_hardhat_deployment(test_file)

        # Check error message mentions the file path
        assert str(test_file) in str(exc_info.value)


class TestParseLegacyDeployment:
    """Test the parse_legacy_deployment function."""

    def test_parses_legacy_deployment_file(self, legacy_deploy_sample: Path):
        """Test parsing a legacy deployment JSON file."""
        result = parse_legacy_deployment(legacy_deploy_sample)

        # Should have canonical contract names
        assert "Token" in result
        assert "StakeRegistry" in result

        # Should not have legacy names as keys
        assert "bzzToken" not in result
        assert "staking" not in result

    def test_legacy_name_to_canonical_mapping(self, legacy_deploy_sample: Path):
        """Test that legacy names are converted to canonical."""
        result = parse_legacy_deployment(legacy_deploy_sample)

        # Check Token (was bzzToken)
        token = result["Token"]
        assert token["address"] == "0x1234567890123456789012345678901234567890"
        assert token["block"] == 25527075
        assert token["source_format"] == "legacy"

        # Check StakeRegistry (was staking)
        stake = result["StakeRegistry"]
        assert stake["address"] == "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
        assert stake["block"] == 25527080
        assert stake["source_format"] == "legacy"

    def test_extracts_required_fields(self, tmp_path: Path):
        """Test that required fields are extracted from legacy format."""
        test_file = tmp_path / "legacy_test.json"
        data = {
            "contracts": {
                "bzzToken": {
                    "address": "0x1234567890123456789012345678901234567890",
                    "block": 12345,
                    "abi": [{"type": "function"}],
                }
            }
        }
        test_file.write_text(json.dumps(data))

        result = parse_legacy_deployment(test_file)

        token = result["Token"]
        assert token["address"] == "0x1234567890123456789012345678901234567890"
        assert token["block"] == 12345
        assert token["abi"] == [{"type": "function"}]
        assert token["source_format"] == "legacy"

    def test_includes_optional_fields_when_present(self, legacy_deploy_sample: Path):
        """Test that optional fields (bytecode, url) are included if present."""
        result = parse_legacy_deployment(legacy_deploy_sample)

        token = result["Token"]
        # bytecode is present in fixture
        assert "bytecode" in token
        assert token["bytecode"] == "0x60806040"

        # url is present in fixture
        assert "url" in token
        assert "gnosisscan.io" in token["url"]

    def test_handles_missing_optional_fields(self, tmp_path: Path):
        """Test that missing optional fields don't cause errors."""
        test_file = tmp_path / "legacy_minimal.json"
        data = {
            "contracts": {
                "staking": {
                    "address": "0x1234567890123456789012345678901234567890",
                    "block": 12345,
                    "abi": [],
                    # No bytecode or url
                }
            }
        }
        test_file.write_text(json.dumps(data))

        result = parse_legacy_deployment(test_file)

        stake = result["StakeRegistry"]
        assert "bytecode" not in stake or stake["bytecode"] is None
        assert "url" not in stake or stake["url"] is None

    def test_invalid_json_raises_error(self, tmp_path: Path):
        """Test that invalid JSON raises appropriate error."""
        test_file = tmp_path / "invalid.json"
        test_file.write_text("{ invalid }")

        with pytest.raises((json.JSONDecodeError, ValueError)):
            parse_legacy_deployment(test_file)

    def test_missing_contracts_key_raises_error(self, tmp_path: Path):
        """Test that missing 'contracts' key raises KeyError."""
        test_file = tmp_path / "no_contracts.json"
        data = {"other_key": "value"}
        test_file.write_text(json.dumps(data))

        with pytest.raises(KeyError):
            parse_legacy_deployment(test_file)

    def test_all_legacy_names_mapped(self, tmp_path: Path):
        """Test that all legacy contract names are properly mapped."""
        test_file = tmp_path / "all_contracts.json"
        data = {
            "contracts": {
                "bzzToken": {"address": "0x01", "block": 1, "abi": []},
                "staking": {"address": "0x02", "block": 2, "abi": []},
                "postageStamp": {"address": "0x03", "block": 3, "abi": []},
                "priceOracle": {"address": "0x04", "block": 4, "abi": []},
                "redistribution": {"address": "0x05", "block": 5, "abi": []},
            }
        }
        test_file.write_text(json.dumps(data))

        result = parse_legacy_deployment(test_file)

        # All canonical names should be present
        assert "Token" in result
        assert "StakeRegistry" in result
        assert "PostageStamp" in result
        assert "PriceOracle" in result
        assert "Redistribution" in result

        # No legacy names should be keys
        assert "bzzToken" not in result
        assert "staking" not in result
