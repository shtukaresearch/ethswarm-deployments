"""Version filtering utilities for ethswarm-deployments library."""

from typing import List


def filter_stable_tags(tags: List[str]) -> List[str]:
    """
    Filter git tags to only include stable versions.

    Stable versions:
    - Start with 'v'
    - Do not contain '-rc' (case-insensitive)

    Args:
        tags: List of git tags

    Returns:
        List of stable version tags
    """
    return [
        t
        for t in tags
        if t.startswith("v") and "-rc" not in t.lower()
    ]
