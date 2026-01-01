"""Unit tests for path helper functions."""

from pathlib import Path

import pytest

from ethswarm_deployments.paths import get_cache_path, get_default_cache_dir


class TestGetDefaultCacheDir:
    """Test the get_default_cache_dir function."""

    def test_returns_path_in_working_directory(self):
        """Test that default cache dir is in working directory."""
        cache_dir = get_default_cache_dir()

        assert isinstance(cache_dir, Path)
        assert cache_dir.name == ".ethswarm-deployments"

        # Should be in working directory
        assert cache_dir.parent == Path.cwd()

    def test_returns_absolute_path(self):
        """Test that returned path is absolute."""
        cache_dir = get_default_cache_dir()
        assert cache_dir.is_absolute()

    def test_consistent_across_calls(self):
        """Test that multiple calls return the same path."""
        dir1 = get_default_cache_dir()
        dir2 = get_default_cache_dir()
        assert dir1 == dir2


class TestGetCachePath:
    """Test the get_cache_path function."""

    def test_returns_path_object(self):
        """Test that function returns a Path object."""
        result = get_cache_path()

        assert isinstance(result, Path)

    def test_default_path_in_working_directory(self):
        """Test that default path is in ./.ethswarm-deployments/."""
        deployments_path = get_cache_path()

        expected_dir = Path.cwd() / ".ethswarm-deployments"

        assert deployments_path.parent == expected_dir

    def test_default_filename(self):
        """Test that default filename is correct."""
        deployments_path = get_cache_path()

        assert deployments_path.name == "deployments.json"

    def test_custom_cache_root(self, tmp_path: Path):
        """Test using a custom cache root directory."""
        custom_root = tmp_path / "custom_cache"
        deployments_path = get_cache_path(cache_root=custom_root)

        assert deployments_path.parent == custom_root
        assert deployments_path.name == "deployments.json"

    def test_custom_cache_root_as_string(self, tmp_path: Path):
        """Test that custom cache root can be provided as string."""
        custom_root = str(tmp_path / "string_cache")
        deployments_path = get_cache_path(cache_root=custom_root)

        assert deployments_path.parent == Path(custom_root)

    def test_none_cache_root_uses_default(self):
        """Test that None cache_root parameter uses default."""
        default_deployments = get_cache_path(cache_root=None)
        no_arg_deployments = get_cache_path()

        assert default_deployments == no_arg_deployments

    def test_path_is_absolute(self):
        """Test that returned path is absolute."""
        deployments_path = get_cache_path()

        assert deployments_path.is_absolute()

    def test_relative_custom_root_converted_to_absolute(self, tmp_path: Path, monkeypatch):
        """Test that relative custom root is converted to absolute path."""
        # Change to tmp directory
        monkeypatch.chdir(tmp_path)

        # Use relative path
        deployments_path = get_cache_path(cache_root="relative_cache")

        # Path should be absolute
        assert deployments_path.is_absolute()
