"""Unit tests for version filtering functionality."""

import pytest

from ethswarm_deployments.versions import filter_stable_tags


class TestFilterStableTags:
    """Test the filter_stable_tags function."""

    def test_filters_stable_versions_only(self):
        """Test that only stable v-prefixed tags without -rc are kept."""
        tags = [
            "v0.1.0",
            "v0.2.0",
            "v0.3.0-rc",
            "v0.4.0-RC",
            "v0.5.0",
            "feature-branch",
            "main",
            "v0.6.0-rc1",
            "v0.7.0",
        ]
        expected = ["v0.1.0", "v0.2.0", "v0.5.0", "v0.7.0"]
        result = filter_stable_tags(tags)
        assert result == expected

    def test_removes_rc_versions_case_insensitive(self):
        """Test that -rc is detected case-insensitively."""
        tags = [
            "v1.0.0-rc",
            "v1.0.1-RC",
            "v1.0.2-Rc",
            "v1.0.3-rC",
            "v1.1.0",
        ]
        expected = ["v1.1.0"]
        result = filter_stable_tags(tags)
        assert result == expected

    def test_keeps_only_v_prefixed_tags(self):
        """Test that only tags starting with 'v' are included."""
        tags = [
            "v1.0.0",
            "1.0.0",
            "release-1.0.0",
            "v2.0.0",
            "version-2.0.0",
        ]
        expected = ["v1.0.0", "v2.0.0", "version-2.0.0"]
        result = filter_stable_tags(tags)
        assert result == expected

    def test_empty_list_handling(self):
        """Test that empty list returns empty list."""
        assert filter_stable_tags([]) == []

    def test_no_stable_versions(self):
        """Test when no tags match stable criteria."""
        tags = [
            "v0.1.0-rc",
            "feature-x",
            "main",
            "develop",
        ]
        expected = []
        result = filter_stable_tags(tags)
        assert result == expected

    def test_all_stable_versions(self):
        """Test when all tags are stable."""
        tags = ["v0.1.0", "v0.2.0", "v0.3.0", "v1.0.0"]
        expected = ["v0.1.0", "v0.2.0", "v0.3.0", "v1.0.0"]
        result = filter_stable_tags(tags)
        assert result == expected

    def test_complex_version_numbers(self):
        """Test with complex version numbers."""
        tags = [
            "v0.1.0",
            "v0.10.0",
            "v0.2.15",
            "v1.0.0-rc",
            "v10.11.12",
        ]
        expected = ["v0.1.0", "v0.10.0", "v0.2.15", "v10.11.12"]
        result = filter_stable_tags(tags)
        assert result == expected

    def test_preserves_order(self):
        """Test that the order of tags is preserved."""
        tags = ["v0.5.0", "v0.1.0", "v0.3.0", "v0.2.0"]
        expected = ["v0.5.0", "v0.1.0", "v0.3.0", "v0.2.0"]
        result = filter_stable_tags(tags)
        assert result == expected

    def test_rc_substring_matching(self):
        """Test that -rc is matched as substring anywhere in tag (per spec: 'do not contain')."""
        tags = [
            "v1.0.0",           # No -rc → include
            "v1.0.0-rc",        # -rc at end → exclude
            "v1.0.0-rc1",       # -rc in middle → exclude
            "v1.0.0-rc-hotfix", # -rc not at end → exclude (substring match)
            "v1.0.0-hotfix",    # No -rc → include
        ]
        expected = ["v1.0.0", "v1.0.0-hotfix"]
        result = filter_stable_tags(tags)
        assert result == expected

    def test_rc_substring_not_suffix_of_rc(self):
        """Test that 'rc' without dash is not matched (spec requires '-rc')."""
        tags = [
            "v1.0.0-src",       # ends with 'rc' but not '-rc' → include
            "v1.0.0-archive",   # contains 'rc' but not '-rc' → include
            "v1.0.0-mercury",   # contains 'rc' but not '-rc' → include
            "v1.0.0-rc",        # actual '-rc' → exclude
        ]
        expected = ["v1.0.0-src", "v1.0.0-archive", "v1.0.0-mercury"]
        result = filter_stable_tags(tags)
        assert result == expected

    def test_rc_substring_case_insensitive_anywhere(self):
        """Test case-insensitive -rc matching as substring."""
        tags = [
            "v1.0.0-RC-final",  # -RC in middle (uppercase) → exclude
            "v1.0.0-hotfix-rc", # -rc at end (lowercase) → exclude
            "v1.0.0-Rc-patch",  # -Rc in middle (mixed case) → exclude
            "v1.0.0-final",     # No -rc → include
        ]
        expected = ["v1.0.0-final"]
        result = filter_stable_tags(tags)
        assert result == expected
