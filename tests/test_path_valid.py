"""Tests for path validation functions."""

from __future__ import annotations

import errno
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from fc_audit.validation import ERROR_INVALID_NAME, is_pathname_valid


def test_invalid_input_types() -> None:
    """Test invalid input types."""
    assert not is_pathname_valid("")  # Empty string
    assert not is_pathname_valid(None)  # type: ignore[arg-type]
    assert not is_pathname_valid(123)  # type: ignore[arg-type]
    assert not is_pathname_valid([])  # type: ignore[arg-type]


def test_valid_paths() -> None:
    """Test valid path names."""
    assert is_pathname_valid("file.txt")
    assert is_pathname_valid("dir/file.txt")
    assert is_pathname_valid("/absolute/path/file.txt")
    assert is_pathname_valid("./relative/path/file.txt")
    assert is_pathname_valid("../parent/path/file.txt")


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
def test_windows_paths() -> None:
    """Test Windows-specific paths."""
    assert is_pathname_valid("C:\\Windows\\System32")
    assert is_pathname_valid("D:\\Program Files\\App")
    assert is_pathname_valid("file.txt")  # Local file


def test_invalid_characters() -> None:
    """Test paths with invalid characters."""
    # Create a string with a null character
    assert not is_pathname_valid("file" + "\0" + "txt")
    assert not is_pathname_valid("file" + "\x00" + "txt")


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
def test_windows_invalid_paths() -> None:
    """Test invalid Windows paths."""
    with patch("os.lstat") as mock_lstat:
        # Simulate a Windows error for invalid name
        mock_lstat.side_effect = OSError()
        mock_lstat.side_effect.winerror = ERROR_INVALID_NAME  # type: ignore[attr-defined]
        assert not is_pathname_valid("COM1")  # Reserved name in Windows


def test_too_long_path() -> None:
    """Test path that is too long."""
    with patch("os.lstat") as mock_lstat:
        # Simulate a "name too long" error
        error = OSError()
        error.errno = errno.ENAMETOOLONG
        mock_lstat.side_effect = error
        very_long_name = "x" * 1000
        assert not is_pathname_valid(very_long_name)


def test_path_with_range_error() -> None:
    """Test path that causes ERANGE error."""
    with patch("os.lstat") as mock_lstat:
        # Simulate an ERANGE error
        error = OSError()
        error.errno = errno.ERANGE
        mock_lstat.side_effect = error
        assert not is_pathname_valid("some/path")


def test_drive_handling() -> None:
    """Test drive specification handling."""
    if sys.platform == "win32":
        with patch.dict(os.environ, {"HOMEDRIVE": "D:"}):
            assert is_pathname_valid("file.txt")
    else:
        assert is_pathname_valid("/absolute/path")  # Unix absolute path


def test_successful_path_validation() -> None:
    """Test successful path validation."""
    # Mock all potential error sources to ensure we hit the final return True
    with (
        patch("os.path.splitdrive", return_value=("", "test.txt")),
        patch("pathlib.Path.is_dir", return_value=True),
        patch("os.lstat") as mock_lstat,
    ):
        # Mock successful lstat call
        mock_lstat.return_value = None
        # Test with a simple path that should pass all checks
        assert is_pathname_valid("test.txt")


def test_successful_path_validation_with_no_errors() -> None:
    """Test successful path validation with no errors."""
    # Test with a path that definitely exists in the codebase
    test_file = Path(__file__).parent / "test_path_valid.py"
    assert test_file.exists()
    # Patch out all potential error sources to ensure we hit the final return True
    with patch("pathlib.Path") as mock_path:
        # Mock the Path class to avoid any exceptions
        mock_path.return_value = mock_path
        mock_path.exists.return_value = True
        mock_path.is_dir.return_value = False
        mock_path.is_file.return_value = True
        mock_path.__str__ = lambda: str(test_file)  # type: ignore[method-assign]
        # Test with a simple path that should pass all checks
        assert is_pathname_valid(str(test_file))
