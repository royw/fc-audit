"""Tests for error paths in the CLI module."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from fc_audit.cli import (
    _filter_aliases,
    _filter_references_by_patterns,
    handle_get_aliases,
    handle_get_properties,
    handle_get_references,
    main,
    valid_files,
)
from fc_audit.exceptions import InvalidFileError


def test_filter_references_empty_pattern() -> None:
    """Test that _filter_references_by_patterns returns original dict when pattern is empty."""
    references: dict[str, list] = {"alias1": [], "alias2": []}
    assert _filter_references_by_patterns(references, "") == references


def test_filter_references_no_matches() -> None:
    """Test that _filter_references_by_patterns returns empty dict when no aliases match pattern."""
    references: dict[str, list] = {"alias1": [], "alias2": []}
    assert _filter_references_by_patterns(references, "nomatch*") == {}


def test_filter_references_multiple_patterns() -> None:
    """Test that _filter_references_by_patterns handles multiple patterns."""
    references: dict[str, list] = {"alias1": [], "alias2": [], "test3": []}
    assert _filter_references_by_patterns(references, "alias*,test*") == references


def test_filter_references_empty_pattern_in_list() -> None:
    """Test that _filter_references_by_patterns handles empty patterns in list."""
    references: dict[str, list] = {"alias1": [], "alias2": []}
    assert _filter_references_by_patterns(references, ",alias*,") == {"alias1": [], "alias2": []}


def test_filter_aliases_empty_pattern() -> None:
    """Test that _filter_aliases returns original set when pattern is empty."""
    aliases: set[str] = {"alias1", "alias2"}
    assert _filter_aliases(aliases, "") == aliases


def test_filter_aliases_no_matches() -> None:
    """Test that _filter_aliases returns empty set when no aliases match pattern."""
    aliases: set[str] = {"alias1", "alias2"}
    assert _filter_aliases(aliases, "nomatch*") == set()


def test_valid_files_nonexistent() -> None:
    """Test that valid_files filters out non-existent files."""
    files: list[Path] = [Path("nonexistent.FCStd")]
    assert list(valid_files(files)) == []


def test_valid_files_invalid_extension() -> None:
    """Test that valid_files filters out files with wrong extension."""
    files: list[Path] = [Path(__file__)]  # Use this test file as an example
    assert list(valid_files(files)) == []


def test_valid_files_invalid_fcstd(mocker: MockerFixture) -> None:
    """Test that valid_files filters out invalid FCStd files."""
    mocker.patch("fc_audit.validation.is_fcstd_file", return_value=False)
    files: list[Path] = [Path("test.FCStd")]
    assert list(valid_files(files)) == []


def test_valid_files_error(mocker: MockerFixture) -> None:
    """Test that valid_files handles errors when checking files."""
    mocker.patch("fc_audit.validation.is_fcstd_file", side_effect=Exception("Test error"))
    files: list[Path] = [Path("test.FCStd")]
    assert list(valid_files(files)) == []


def test_handle_get_properties_error(mocker: MockerFixture, tmp_path: Path) -> None:
    """Test handle_get_properties error path."""

    class MockArgs(Namespace):
        filter: str | None = None
        json: bool = False
        csv: bool = False
        text: bool = True

    bad_file = tmp_path / "bad.FCStd"
    bad_file.touch()

    # Mock PropertiesOutputter to raise an exception
    mock_outputter = mocker.patch("fc_audit.cli.PropertiesOutputter")
    mock_outputter.side_effect = InvalidFileError("Test error")

    args = MockArgs()
    assert handle_get_properties(args, [bad_file]) == 1


def test_handle_get_properties_filter_error(mocker: MockerFixture, tmp_path: Path) -> None:
    """Test handle_get_properties error path when filtering properties."""

    class MockArgs(Namespace):
        filter: str = "test*"
        by_object: bool = False
        by_file: bool = False
        json: bool = False
        csv: bool = False

    bad_file = tmp_path / "bad.FCStd"
    bad_file.touch()

    # Mock PropertiesOutputter
    mock_outputter = mocker.MagicMock()
    mock_outputter.filter_properties.side_effect = InvalidFileError("Test error")
    mocker.patch("fc_audit.cli.PropertiesOutputter", return_value=mock_outputter)

    args = MockArgs()
    assert handle_get_properties(args, [bad_file]) == 1


def test_handle_get_properties_output_error(mocker: MockerFixture, tmp_path: Path) -> None:
    """Test handle_get_properties error path when outputting properties."""

    class MockArgs(Namespace):
        filter: str | None = None
        json: bool = False
        csv: bool = False
        text: bool = True

    bad_file = tmp_path / "bad.FCStd"
    bad_file.touch()

    # Mock PropertiesOutputter
    mock_outputter = mocker.MagicMock()
    mock_outputter.output.side_effect = InvalidFileError("Test error")
    mocker.patch("fc_audit.cli.PropertiesOutputter", return_value=mock_outputter)

    args = MockArgs()
    assert handle_get_properties(args, [bad_file]) == 1


def test_handle_get_aliases_error(mocker: MockerFixture, tmp_path: Path) -> None:
    """Test handle_get_aliases error path."""

    class MockArgs(Namespace):
        filter: str | None = None
        json: bool = False
        csv: bool = False
        text: bool = True

    bad_file = tmp_path / "bad.FCStd"
    bad_file.touch()

    # Mock AliasOutputter to raise an exception
    mock_outputter = mocker.patch("fc_audit.cli.AliasOutputter")
    mock_outputter.side_effect = InvalidFileError("Test error")

    args = MockArgs()
    assert handle_get_aliases(args, [bad_file]) == 1


def test_handle_get_aliases_output_error(mocker: MockerFixture, tmp_path: Path) -> None:
    """Test handle_get_aliases error path when outputting aliases."""

    class MockArgs(Namespace):
        filter: str | None = None
        json: bool = False
        csv: bool = False
        text: bool = True

    bad_file = tmp_path / "bad.FCStd"
    bad_file.touch()

    # Mock AliasOutputter
    mock_outputter = mocker.MagicMock()
    mock_outputter.output.side_effect = InvalidFileError("Test error")
    mocker.patch("fc_audit.cli.AliasOutputter", return_value=mock_outputter)

    args = MockArgs()
    assert handle_get_aliases(args, [bad_file]) == 1


def test_handle_get_references_error(mocker: MockerFixture, tmp_path: Path) -> None:
    """Test handle_get_references error path."""

    class MockArgs(Namespace):
        filter: str | None = None
        json: bool = False
        csv: bool = False
        text: bool = True

    bad_file = tmp_path / "bad.FCStd"
    bad_file.touch()

    # Mock ReferenceCollector to raise an exception
    mock_collector = mocker.patch("fc_audit.cli.ReferenceCollector")
    mock_collector.side_effect = InvalidFileError("Test error")

    args = MockArgs()
    assert handle_get_references(args, [bad_file]) == 1


def test_main_no_args() -> None:
    """Test that main exits with error when no args provided."""
    with pytest.raises(SystemExit):
        main([])


def test_main_invalid_command() -> None:
    """Test that main exits with error for invalid command."""
    with pytest.raises(SystemExit):
        main(["invalid"])


def test_main_missing_files() -> None:
    """Test that main exits with error when files argument is missing."""
    with pytest.raises(SystemExit):
        main(["properties"])


def test_main_invalid_file() -> None:
    """Test that main handles invalid file paths."""
    assert main(["properties", "nonexistent.FCStd"]) == 1


def test_main_error_handling(mocker: MockerFixture) -> None:
    """Test main error handling path."""
    # Mock setup_logging to raise an exception
    mocker.patch("fc_audit.cli.setup_logging", side_effect=Exception("Test error"))
    assert main(["properties", "test.FCStd"]) == 1


def test_main_error_handling_with_args(mocker: MockerFixture) -> None:
    """Test main error handling path with args."""
    # Mock parse_args to raise a SystemExit
    mocker.patch("fc_audit.cli.parse_args", side_effect=SystemExit(1))
    with pytest.raises(SystemExit):
        main(["--invalid-arg"])
