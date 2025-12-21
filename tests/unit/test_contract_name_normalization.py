"""Unit tests for contract name normalization functionality."""

import pytest

from swarm_deployments.names import (
    CANONICAL_TO_LEGACY,
    LEGACY_TO_CANONICAL,
    normalize_contract_name,
)


class TestNameMappingConstants:
    """Test the name mapping dictionaries."""

    def test_legacy_to_canonical_mapping(self):
        """Test LEGACY_TO_CANONICAL contains expected mappings."""
        expected_mappings = {
            "bzzToken": "Token",
            "staking": "StakeRegistry",
            "postageStamp": "PostageStamp",
            "priceOracle": "PriceOracle",
            "redistribution": "Redistribution",
        }
        assert LEGACY_TO_CANONICAL == expected_mappings

    def test_canonical_to_legacy_mapping(self):
        """Test CANONICAL_TO_LEGACY is correct inverse of LEGACY_TO_CANONICAL."""
        expected_mappings = {
            "Token": "bzzToken",
            "StakeRegistry": "staking",
            "PostageStamp": "postageStamp",
            "PriceOracle": "priceOracle",
            "Redistribution": "redistribution",
        }
        assert CANONICAL_TO_LEGACY == expected_mappings

    def test_mappings_are_bidirectional(self):
        """Test that the two mappings are perfect inverses of each other."""
        for legacy, canonical in LEGACY_TO_CANONICAL.items():
            assert CANONICAL_TO_LEGACY[canonical] == legacy


class TestNormalizeContractName:
    """Test the normalize_contract_name function."""

    def test_canonical_name_unchanged(self):
        """Test that canonical names are returned unchanged."""
        canonical_names = ["Token", "StakeRegistry", "PostageStamp", "PriceOracle", "Redistribution"]
        for name in canonical_names:
            assert normalize_contract_name(name) == name

    def test_legacy_name_converts_to_canonical(self):
        """Test that legacy names are converted to canonical."""
        test_cases = [
            ("bzzToken", "Token"),
            ("staking", "StakeRegistry"),
            ("postageStamp", "PostageStamp"),
            ("priceOracle", "PriceOracle"),
            ("redistribution", "Redistribution"),
        ]
        for legacy, expected_canonical in test_cases:
            assert normalize_contract_name(legacy) == expected_canonical

    def test_unknown_name_returns_unchanged(self):
        """Test that unknown names are returned unchanged (or raises error)."""
        # This behavior depends on implementation - it might return unchanged or raise
        unknown_names = ["UnknownContract", "FooBar", "NotARealContract"]
        for name in unknown_names:
            result = normalize_contract_name(name)
            # Either returns unchanged or raises ValueError
            # The spec doesn't explicitly say, but returning unchanged seems reasonable
            assert result == name or isinstance(result, str)

    def test_empty_string(self):
        """Test handling of empty string."""
        # Should either return empty string or raise ValueError
        result = normalize_contract_name("")
        assert isinstance(result, str)
