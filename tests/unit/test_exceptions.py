"""Unit tests for custom exception classes."""

import pytest

from swarm_deployments.exceptions import (
    CacheNotFoundError,
    ContractNotFoundError,
    DeploymentError,
    EventNotFoundError,
    NetworkNotFoundError,
    VersionNotFoundError,
)


class TestExceptionHierarchy:
    """Test the exception class hierarchy and inheritance."""

    def test_deployment_error_is_base_exception(self):
        """Test that DeploymentError is the base exception."""
        exc = DeploymentError("test message")
        assert isinstance(exc, Exception)
        assert str(exc) == "test message"

    def test_cache_not_found_inherits_correctly(self):
        """Test CacheNotFoundError inheritance."""
        exc = CacheNotFoundError("test")

        # Should inherit from both DeploymentError and FileNotFoundError
        assert isinstance(exc, DeploymentError)
        assert isinstance(exc, FileNotFoundError)
        assert isinstance(exc, Exception)

    def test_network_not_found_inherits_correctly(self):
        """Test NetworkNotFoundError inheritance."""
        exc = NetworkNotFoundError("test")

        assert isinstance(exc, DeploymentError)
        assert isinstance(exc, ValueError)
        assert isinstance(exc, Exception)

    def test_version_not_found_inherits_correctly(self):
        """Test VersionNotFoundError inheritance."""
        exc = VersionNotFoundError("test")

        assert isinstance(exc, DeploymentError)
        assert isinstance(exc, ValueError)
        assert isinstance(exc, Exception)

    def test_contract_not_found_inherits_correctly(self):
        """Test ContractNotFoundError inheritance."""
        exc = ContractNotFoundError("test")

        assert isinstance(exc, DeploymentError)
        assert isinstance(exc, ValueError)
        assert isinstance(exc, Exception)

    def test_event_not_found_inherits_correctly(self):
        """Test EventNotFoundError inheritance."""
        exc = EventNotFoundError("test")

        assert isinstance(exc, DeploymentError)
        assert isinstance(exc, ValueError)
        assert isinstance(exc, Exception)


class TestExceptionCatching:
    """Test that exceptions can be caught as their base types."""

    def test_catch_cache_not_found_as_file_not_found_error(self):
        """Test that CacheNotFoundError can be caught as FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            raise CacheNotFoundError("test")

    def test_catch_cache_not_found_as_deployment_error(self):
        """Test that CacheNotFoundError can be caught as DeploymentError."""
        with pytest.raises(DeploymentError):
            raise CacheNotFoundError("test")

    def test_catch_network_not_found_as_value_error(self):
        """Test that NetworkNotFoundError can be caught as ValueError."""
        with pytest.raises(ValueError):
            raise NetworkNotFoundError("test")

    def test_catch_version_not_found_as_value_error(self):
        """Test that VersionNotFoundError can be caught as ValueError."""
        with pytest.raises(ValueError):
            raise VersionNotFoundError("test")

    def test_catch_contract_not_found_as_value_error(self):
        """Test that ContractNotFoundError can be caught as ValueError."""
        with pytest.raises(ValueError):
            raise ContractNotFoundError("test")

    def test_catch_event_not_found_as_value_error(self):
        """Test that EventNotFoundError can be caught as ValueError."""
        with pytest.raises(ValueError):
            raise EventNotFoundError("test")

    def test_catch_all_as_deployment_error(self):
        """Test that all custom exceptions can be caught as DeploymentError."""
        exceptions = [
            CacheNotFoundError("test"),
            NetworkNotFoundError("test"),
            VersionNotFoundError("test"),
            ContractNotFoundError("test"),
            EventNotFoundError("test"),
        ]

        for exc in exceptions:
            with pytest.raises(DeploymentError):
                raise exc


class TestExceptionMessages:
    """Test exception message formatting according to specification."""

    def test_cache_not_found_message_format(self):
        """Test CacheNotFoundError message format."""
        path = "/path/to/cache.json"
        exc = CacheNotFoundError(
            f"Deployment cache not found at {path}. "
            f"Run regenerate_from_github() to create it."
        )

        assert "Deployment cache not found at" in str(exc)
        assert path in str(exc)
        assert "regenerate_from_github()" in str(exc)

    def test_network_not_found_message_format(self):
        """Test NetworkNotFoundError message format."""
        network = "unknown_network"
        exc = NetworkNotFoundError(f"Network '{network}' not found in cache")

        assert network in str(exc)
        assert "not found in cache" in str(exc)

    def test_version_not_found_no_versions_message(self):
        """Test VersionNotFoundError message when no versions exist."""
        network = "mainnet"
        exc = VersionNotFoundError(f"No versions found for network '{network}'")

        assert network in str(exc)
        assert "No versions found" in str(exc)

    def test_version_not_found_specific_version_message(self):
        """Test VersionNotFoundError message for specific version."""
        version = "v999.0.0"
        network = "mainnet"
        exc = VersionNotFoundError(f"Version '{version}' not found in network '{network}'")

        assert version in str(exc)
        assert network in str(exc)
        assert "not found" in str(exc)

    def test_contract_not_found_message_format(self):
        """Test ContractNotFoundError message format."""
        contract = "UnknownContract"
        version = "v0.9.2"
        network = "mainnet"
        exc = ContractNotFoundError(
            f"Contract '{contract}' not found in version '{version}' on network '{network}'"
        )

        assert contract in str(exc)
        assert version in str(exc)
        assert network in str(exc)
        assert "not found" in str(exc)

    def test_event_not_found_message_format(self):
        """Test EventNotFoundError message format."""
        event = "UnknownEvent"
        contract = "StakeRegistry"
        version = "v0.9.2"
        exc = EventNotFoundError(f"Event '{event}' not found in {contract} {version} ABI")

        assert event in str(exc)
        assert contract in str(exc)
        assert version in str(exc)
        assert "not found" in str(exc)
        assert "ABI" in str(exc)


class TestExceptionCreation:
    """Test creating exceptions with various message types."""

    def test_exceptions_accept_string_messages(self):
        """Test that all exceptions accept string messages."""
        exceptions = [
            DeploymentError,
            CacheNotFoundError,
            NetworkNotFoundError,
            VersionNotFoundError,
            ContractNotFoundError,
            EventNotFoundError,
        ]

        for exc_class in exceptions:
            exc = exc_class("test message")
            assert str(exc) == "test message"

    def test_exceptions_accept_empty_messages(self):
        """Test that exceptions can be created with empty messages."""
        exceptions = [
            DeploymentError,
            CacheNotFoundError,
            NetworkNotFoundError,
            VersionNotFoundError,
            ContractNotFoundError,
            EventNotFoundError,
        ]

        for exc_class in exceptions:
            exc = exc_class("")
            assert isinstance(exc, exc_class)
