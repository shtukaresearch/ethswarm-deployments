"""Path management utilities for ethswarm-deployments library."""

from pathlib import Path
from typing import Optional, Union


def get_default_cache_dir() -> Path:
    """
    Get default cache directory (working directory).

    Returns:
        Path to ./.ethswarm-deployments
    """
    return Path.cwd() / ".ethswarm-deployments"


def get_cache_path(cache_root: Optional[Union[Path, str]] = None) -> Path:
    """
    Get deployment cache file path.

    Args:
        cache_root: Custom cache directory (defaults to ./.ethswarm-deployments)

    Returns:
        Path to deployments.json
    """
    if cache_root is None:
        cache_root = get_default_cache_dir()
    else:
        cache_root = Path(cache_root).absolute()

    return cache_root / "deployments.json"
