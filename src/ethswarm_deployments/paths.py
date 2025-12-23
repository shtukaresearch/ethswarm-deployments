"""Path management utilities for ethswarm-deployments library."""

from pathlib import Path
from typing import Optional, Union


def get_default_cache_dir() -> Path:
    """
    Get default cache directory (user home).

    Returns:
        Path to ./.ethswarm-deployments
    """
    return Path.cwd() / ".ethswarm-deployments"


def get_cache_paths(cache_root: Optional[Union[Path, str]] = None) -> tuple[Path, Path]:
    """
    Get cache file paths.

    Args:
        cache_root: Custom cache directory (defaults to ./.ethswarm-deployments)

    Returns:
        Tuple of (deployments_path, timestamps_path)
    """
    if cache_root is None:
        cache_root = get_default_cache_dir()
    else:
        cache_root = Path(cache_root).absolute()

    deployments_path = cache_root / "deployments.json"
    timestamps_path = cache_root / "block_timestamps.json"

    return (deployments_path, timestamps_path)
