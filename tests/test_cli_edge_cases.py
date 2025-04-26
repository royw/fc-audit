"""Tests for edge cases in the CLI module."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from pytest_mock import MockerFixture

from fc_audit.cli import (
    _filter_aliases,
    _handle_get_aliases,
    _handle_get_properties,
    _handle_get_references,
)
from fc_audit.exceptions import InvalidFileError


def test_filter_aliases_empty_pattern() -> None:
    """Test that _filter_aliases returns original set when pattern is empty."""
    aliases: set[str] = {"alias1", "alias2", "alias3"}
    assert _filter_aliases(aliases, "") == aliases


def test_filter_aliases_no_matches() -> None:
    """Test that _filter_aliases returns empty set when no aliases match pattern."""
    aliases: set[str] = {"alias1", "alias2", "alias3"}
    assert _filter_aliases(aliases, "nomatch*") == set()


def test__handle_get_properties_all_files_error(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test _handle_get_properties when all files have errors."""

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
    assert _handle_get_properties(args, [bad_file]) == 1


def test__handle_get_aliases_all_files_error(tmp_path: Path) -> None:
    """Test _handle_get_aliases when all files have errors."""

    class MockArgs(Namespace):
        filter: str | None = None
        json: bool = False
        csv: bool = False

    bad_file = tmp_path / "bad.FCStd"
    bad_file.touch()

    args = MockArgs()
    assert _handle_get_aliases(args, [bad_file]) == 1


def test__handle_get_aliases_no_aliases(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test _handle_get_aliases when no aliases are found."""

    class MockArgs(Namespace):
        filter: str | None = None
        json: bool = False
        csv: bool = False

    mock_file = tmp_path / "test.FCStd"
    mock_file.touch()

    # Mock get_cell_aliases to return empty set
    mocker.patch("fc_audit.cli.get_cell_aliases", return_value=set())

    args = MockArgs()
    assert _handle_get_aliases(args, [mock_file]) == 0


def test__handle_get_references_all_files_error(tmp_path: Path) -> None:
    """Test _handle_get_references when all files have errors."""

    class MockArgs(Namespace):
        filter: str | None = None
        by_object: bool = False
        by_file: bool = False
        by_alias: bool = False
        json: bool = False
        csv: bool = False

    bad_file = tmp_path / "bad.FCStd"
    bad_file.touch()

    args = MockArgs()
    assert _handle_get_references(args, [bad_file]) == 1


def test__handle_get_references_general_error(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test _handle_get_references when a general error occurs."""

    class MockArgs(Namespace):
        filter: str | None = None
        by_object: bool = False
        by_file: bool = False
        by_alias: bool = False
        json: bool = False
        csv: bool = False

    mock_file = tmp_path / "test.FCStd"
    mock_file.touch()

    # Mock ReferenceCollector to raise an exception
    mocker.patch("fc_audit.cli.ReferenceCollector", side_effect=Exception("Test error"))

    args = MockArgs()
    assert _handle_get_references(args, [mock_file]) == 1


def test__handle_get_references_invalid_format_combination(mocker: MockerFixture) -> None:
    """Test _handle_get_references with invalid format combination."""

    class MockArgs(Namespace):
        filter: str | None = None
        by_object: bool = True
        by_file: bool = True
        by_alias: bool = False
        json: bool = False
        csv: bool = False

    # Mock ReferenceCollector to return empty dict
    mocker.patch("fc_audit.cli.ReferenceCollector", autospec=True)
    mocker.patch(
        "fc_audit.cli.ReferenceOutputter.output", side_effect=ValueError("Cannot specify multiple output formats")
    )

    args = MockArgs()
    assert _handle_get_references(args, [Path("test.FCStd")]) == 1
