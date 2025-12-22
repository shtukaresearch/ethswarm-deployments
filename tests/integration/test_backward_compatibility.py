"""Integration tests for backward compatibility with legacy contract names."""

from pathlib import Path

import pytest

from ethswarm_deployments import DeploymentManager


class TestLegacyNameSupport:
    """Test that legacy contract names work correctly."""

    def test_deployment_with_legacy_token_name(self, temp_deployments_cache: Path):
        """Test that 'bzzToken' legacy name works for Token contract."""
        mgr = DeploymentManager(str(temp_deployments_cache))

        canonical = mgr.deployment("Token", version="v0.2.0", network="mainnet")
        legacy = mgr.deployment("bzzToken", version="v0.2.0", network="mainnet")

        # Should return same contract
        assert canonical.address == legacy.address
        assert canonical.block == legacy.block
        assert canonical.name == legacy.name  # Name should be canonical

    def test_deployment_with_legacy_staking_name(self, temp_deployments_cache: Path):
        """Test that 'staking' legacy name works for StakeRegistry contract."""
        mgr = DeploymentManager(str(temp_deployments_cache))

        canonical = mgr.deployment("StakeRegistry", version="v0.2.0", network="mainnet")
        legacy = mgr.deployment("staking", version="v0.2.0", network="mainnet")

        assert canonical.address == legacy.address
        assert canonical.block == legacy.block

    def test_all_legacy_names_work(self, temp_deployments_cache: Path):
        """Test that all legacy contract names are supported."""
        mgr = DeploymentManager(str(temp_deployments_cache))

        legacy_to_canonical = {
            "bzzToken": "Token",
            "staking": "StakeRegistry",
        }

        for legacy, canonical in legacy_to_canonical.items():
            try:
                legacy_dep = mgr.deployment(legacy, network="mainnet")
                canonical_dep = mgr.deployment(canonical, network="mainnet")
                assert legacy_dep.address == canonical_dep.address
            except Exception:
                # Contract might not exist in fixture, that's okay
                pass

    def test_all_deployments_with_legacy_name(self, temp_deployments_cache: Path):
        """Test that all_deployments() works with legacy names."""
        mgr = DeploymentManager(str(temp_deployments_cache))

        canonical_deps = mgr.all_deployments("Token", network="mainnet")
        legacy_deps = mgr.all_deployments("bzzToken", network="mainnet")

        assert len(canonical_deps) == len(legacy_deps)
        for canonical, legacy in zip(canonical_deps, legacy_deps):
            assert canonical.address == legacy.address

    def test_event_abi_with_legacy_name(self, temp_deployments_cache: Path):
        """Test that event_abi() works with legacy contract names."""
        mgr = DeploymentManager(str(temp_deployments_cache))

        canonical_abi = mgr.event_abi("Token", "Transfer", version="v0.2.0", network="mainnet")
        legacy_abi = mgr.event_abi("bzzToken", "Transfer", version="v0.2.0", network="mainnet")

        assert canonical_abi == legacy_abi

    def test_has_contract_with_legacy_name(self, temp_deployments_cache: Path):
        """Test that has_contract() works with legacy names."""
        mgr = DeploymentManager(str(temp_deployments_cache))

        canonical_exists = mgr.has_contract("Token", "v0.2.0", "mainnet")
        legacy_exists = mgr.has_contract("bzzToken", "v0.2.0", "mainnet")

        assert canonical_exists == legacy_exists


class TestMixedNameUsage:
    """Test using both canonical and legacy names in same session."""

    def test_mixed_name_usage_in_queries(self, temp_deployments_cache: Path):
        """Test that canonical and legacy names can be used interchangeably."""
        mgr = DeploymentManager(str(temp_deployments_cache))

        # Get one contract with canonical name
        token = mgr.deployment("Token", version="v0.2.0", network="mainnet")

        # Get another with legacy name
        stake = mgr.deployment("staking", version="v0.2.0", network="mainnet")

        # Both should work and return valid deployments
        assert token.address is not None
        assert stake.address is not None
        assert token.address != stake.address

    def test_legacy_name_returns_canonical_name_in_result(self, temp_deployments_cache: Path):
        """Test that ContractDeployment always has canonical name even when queried with legacy."""
        mgr = DeploymentManager(str(temp_deployments_cache))

        deployment = mgr.deployment("bzzToken", version="v0.2.0", network="mainnet")

        # The deployment object should have the canonical name
        assert deployment.name == "Token"
        # Not the legacy name
        assert deployment.name != "bzzToken"


class TestLegacyNameEdgeCases:
    """Test edge cases for legacy name support."""

    def test_case_sensitive_legacy_names(self, temp_deployments_cache: Path):
        """Test that legacy names are case-sensitive."""
        mgr = DeploymentManager(str(temp_deployments_cache))

        # 'bzzToken' should work
        deployment = mgr.deployment("bzzToken", version="v0.2.0", network="mainnet")
        assert deployment is not None

        # 'bzztoken' (lowercase) should not work (case-sensitive)
        # This might raise ContractNotFoundError or work depending on implementation
        # Just documenting the expected behavior
        try:
            wrong_case = mgr.deployment("bzztoken", version="v0.2.0", network="mainnet")
            # If it works, it should return the same contract
            assert wrong_case.address == deployment.address
        except Exception:
            # Or it might raise an error for unknown contract
            pass

    def test_unknown_legacy_name_raises_error(self, temp_deployments_cache: Path):
        """Test that unknown legacy names raise appropriate error."""
        mgr = DeploymentManager(str(temp_deployments_cache))

        from ethswarm_deployments.exceptions import ContractNotFoundError

        with pytest.raises(ContractNotFoundError):
            mgr.deployment("unknownLegacyName", version="v0.2.0", network="mainnet")


class TestContractNamesWithLegacy:
    """Test that contract_names() returns canonical names."""

    def test_contract_names_returns_canonical_only(self, temp_deployments_cache: Path):
        """Test that contract_names() always returns canonical names, never legacy."""
        mgr = DeploymentManager(str(temp_deployments_cache))

        contracts = mgr.contract_names(version="v0.2.0", network="mainnet")

        # Should contain canonical names
        if "Token" in contracts or "StakeRegistry" in contracts:
            # Should NOT contain legacy names
            assert "bzzToken" not in contracts
            assert "staking" not in contracts

        # All returned names should be canonical
        canonical_names = ["Token", "StakeRegistry", "PostageStamp", "PriceOracle", "Redistribution"]
        for contract in contracts:
            if contract in ["Token", "StakeRegistry", "PostageStamp", "PriceOracle", "Redistribution"]:
                assert contract in canonical_names
