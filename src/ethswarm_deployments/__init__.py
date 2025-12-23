"""
ethswarm-deployments: Python library for managing Ethswarm smart contract deployments
"""

from importlib.metadata import PackageNotFoundError, version

from .deployments import DeploymentManager, regenerate_from_github
from .exceptions import (
    CacheNotFoundError,
    ContractNotFoundError,
    DefectiveDeploymentError,
    DeploymentError,
    EventNotFoundError,
    NetworkNotFoundError,
    VersionNotFoundError,
)
from .types import ContractDeployment

try:
    __version__ = version("ethswarm-deployments")
except PackageNotFoundError:
    __version__ = None

__all__ = [
    "DeploymentManager",
    "regenerate_from_github",
    "ContractDeployment",
    "DeploymentError",
    "CacheNotFoundError",
    "NetworkNotFoundError",
    "VersionNotFoundError",
    "ContractNotFoundError",
    "EventNotFoundError",
    "DefectiveDeploymentError",
]
