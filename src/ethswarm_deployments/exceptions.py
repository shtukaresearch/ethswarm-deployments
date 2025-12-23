"""Custom exception classes for ethswarm-deployments library."""


class DeploymentError(Exception):
    """Base exception for deployment-related errors."""

    pass


class CacheNotFoundError(DeploymentError, FileNotFoundError):
    """Raised when deployment cache file is not found."""

    pass


class NetworkNotFoundError(DeploymentError, ValueError):
    """Raised when requested network is not in cache."""

    pass


class VersionNotFoundError(DeploymentError, ValueError):
    """Raised when requested version is not found."""

    pass


class ContractNotFoundError(DeploymentError, ValueError):
    """Raised when requested contract is not found in version."""

    pass


class EventNotFoundError(DeploymentError, ValueError):
    """Raised when requested event is not found in contract ABI."""

    pass


class DefectiveDeploymentError(DeploymentError, ValueError):
    """Raised when a hardhat deployment file is missing required block number."""

    pass
