"""Unit tests for custom exception classes."""

import pytest

from ethswarm_deployments.exceptions import (
    CacheNotFoundError,
    ContractNotFoundError,
    DeploymentError,
    EventNotFoundError,
    NetworkNotFoundError,
    VersionNotFoundError,
)


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
