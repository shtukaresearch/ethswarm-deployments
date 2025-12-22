"""Unit tests for path helper functions."""

from pathlib import Path

import pytest

from ethswarm_deployments.paths import get_cache_paths, get_default_cache_dir


class TestGetDefaultCacheDir:
    """Test the get_default_cache_dir function."""

    def test_returns_path_in_user_home(self):
        """Test that default cache dir is in user's home directory."""
        cache_dir = get_default_cache_dir()

        assert isinstance(cache_dir, Path)
        assert cache_dir.name == ".ethswarm-deployments"

        # Should be in user's home directory
        home = Path.home()
        assert cache_dir.parent == home

    def test_returns_absolute_path(self):
        """Test that returned path is absolute."""
        cache_dir = get_default_cache_dir()
        assert cache_dir.is_absolute()

    def test_consistent_across_calls(self):
        """Test that multiple calls return the same path."""
        dir1 = get_default_cache_dir()
        dir2 = get_default_cache_dir()
        assert dir1 == dir2


class TestGetCachePaths:
    """Test the get_cache_paths function."""

    def test_returns_tuple_of_two_paths(self):
        """Test that function returns a tuple of two Path objects."""
        result = get_cache_paths()

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], Path)
        assert isinstance(result[1], Path)

    def test_default_paths_in_home_directory(self):
        """Test that default paths are in ~/.ethswarm-deployments/."""
        deployments_path, timestamps_path = get_cache_paths()

        home = Path.home()
        expected_dir = home / ".ethswarm-deployments"

        assert deployments_path.parent == expected_dir
        assert timestamps_path.parent == expected_dir

    def test_default_filenames(self):
        """Test that default filenames are correct."""
        deployments_path, timestamps_path = get_cache_paths()

        assert deployments_path.name == "deployments.json"
        assert timestamps_path.name == "block_timestamps.json"

    def test_custom_cache_root(self, tmp_path: Path):
        """Test using a custom cache root directory."""
        custom_root = tmp_path / "custom_cache"
        deployments_path, timestamps_path = get_cache_paths(cache_root=custom_root)

        assert deployments_path.parent == custom_root
        assert timestamps_path.parent == custom_root
        assert deployments_path.name == "deployments.json"
        assert timestamps_path.name == "block_timestamps.json"

    def test_custom_cache_root_as_string(self, tmp_path: Path):
        """Test that custom cache root can be provided as string."""
        custom_root = str(tmp_path / "string_cache")
        deployments_path, timestamps_path = get_cache_paths(cache_root=custom_root)

        assert deployments_path.parent == Path(custom_root)
        assert timestamps_path.parent == Path(custom_root)

    def test_none_cache_root_uses_default(self):
        """Test that None cache_root parameter uses default."""
        default_deployments, default_timestamps = get_cache_paths(cache_root=None)
        no_arg_deployments, no_arg_timestamps = get_cache_paths()

        assert default_deployments == no_arg_deployments
        assert default_timestamps == no_arg_timestamps

    def test_paths_are_absolute(self):
        """Test that returned paths are absolute."""
        deployments_path, timestamps_path = get_cache_paths()

        assert deployments_path.is_absolute()
        assert timestamps_path.is_absolute()

    def test_relative_custom_root_converted_to_absolute(self, tmp_path: Path, monkeypatch):
        """Test that relative custom root is converted to absolute path."""
        # Change to tmp directory
        monkeypatch.chdir(tmp_path)

        # Use relative path
        deployments_path, timestamps_path = get_cache_paths(cache_root="relative_cache")

        # Paths should be absolute
        assert deployments_path.is_absolute()
        assert timestamps_path.is_absolute()
