"""Tests for the command line interface."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from loguru import logger

from fc_audit.cli import handle_get_references, main, parse_args, setup_logging

TESTS_DIR = Path(__file__).parent
DATA_DIR = TESTS_DIR / "data"


def test_parse_args_default() -> None:
    """Test that the CLI requires at least one command argument.
    Should raise SystemExit when no arguments are provided."""

    with pytest.raises(SystemExit):
        parse_args([])


def test_parse_args_verbose() -> None:
    """Test that both -v and --verbose flags are recognized but still require a command.
    Should raise SystemExit when only verbose flag is provided."""

    with pytest.raises(SystemExit):
        parse_args(["-v"])

    with pytest.raises(SystemExit):
        parse_args(["--verbose"])


def test_parse_args_log_file() -> None:
    """Test that --log-file argument is recognized but still requires a command.
    Should raise SystemExit when only log file is provided."""

    with pytest.raises(SystemExit):
        parse_args(["--log-file", "test.log"])


def test_setup_logging_default(capsys: pytest.CaptureFixture[str]) -> None:
    """Test that default logging setup outputs INFO level messages to stderr
    but filters out DEBUG level messages."""

    setup_logging()
    logger.info("Test message")
    captured = capsys.readouterr()
    assert "Test message" in captured.err
    assert "DEBUG" not in captured.err


def test_setup_logging_verbose(capsys: pytest.CaptureFixture[str]) -> None:
    """Test that verbose logging setup allows DEBUG level messages
    to be output to stderr."""

    setup_logging(None, True)
    logger.debug("Debug message")
    captured = capsys.readouterr()
    assert "Debug message" in captured.err


def test_parse_args_get_references() -> None:
    """Test parsing of get-references command with various arguments.
    Verifies:
    1. Default format (by-alias) when no format flags are provided
    2. Alias filtering with --aliases option
    3. Different output formats (--by-object, --by-file)
    4. JSON output format (--json)"""

    # Test default format
    args = parse_args(["get-references", str(DATA_DIR / "Test1.FCStd")])
    assert args.command == "get-references"
    assert args.files == [DATA_DIR / "Test1.FCStd"]
    assert args.aliases is None
    assert args.by_alias is True
    assert not args.by_object
    assert not args.by_file
    assert not args.json

    # Test with aliases
    args = parse_args(["get-references", "--aliases", "Length,Height", DATA_DIR / "Test1.FCStd"])
    assert args.aliases == "Length,Height"

    # Test different formats
    args = parse_args(["get-references", "--by-object", DATA_DIR / "Test1.FCStd"])
    assert args.by_object is True

    args = parse_args(["get-references", "--by-file", DATA_DIR / "Test1.FCStd"])
    assert args.by_file is True

    args = parse_args(["get-references", "--json", DATA_DIR / "Test1.FCStd"])
    assert args.json is True


def test_get_references_by_alias(capsys: pytest.CaptureFixture[str]) -> None:
    """Test the default by-alias output format of get-references command.
    Verifies that references are correctly grouped by alias name and that
    the output includes the file, object name, and expression for each reference."""

    main(["get-references", "--by-alias", str(DATA_DIR / "Test1.FCStd")])
    captured = capsys.readouterr()

    # Check output format
    output = captured.out
    assert "Alias references found:" in output
    assert "Alias: Length" in output
    assert "  File: Test1.FCStd" in output
    assert "  Object: Box" in output
    assert "  Expression: <<globals>>#<<params>>.Length + 10" in output
    assert "Alias: Width" in output
    assert "  File: Test1.FCStd" in output
    assert "  Object: Box" in output
    assert "  Expression: <<globals>>#<<params>>.Width + 5" in output
    assert "Alias: Height" in output
    assert "  File: Test1.FCStd" in output
    assert "  Object: Box" in output
    assert "  Expression: <<globals>>#<<params>>.Height" in output


def test_get_references_by_object(capsys: pytest.CaptureFixture[str]) -> None:
    """Test the --by-object output format of get-references command.
    Verifies that references are correctly grouped by object name within each file
    and that all aliases and expressions for each object are displayed."""
    # Test normal case
    args = parse_args(["get-references", "--by-object", DATA_DIR / "Test1.FCStd"])
    assert handle_get_references(args, [Path(DATA_DIR / "Test1.FCStd")]) == 0
    captured = capsys.readouterr()
    assert "Alias references found:" in captured.out
    assert "\nObject: Box" in captured.out
    assert "  File: Test1.FCStd" in captured.out
    assert "  Alias: Height" in captured.out
    assert "  Expression: <<globals>>#<<params>>.Height" in captured.out
    assert "  Alias: Length" in captured.out
    assert "  Expression: <<globals>>#<<params>>.Length + 10" in captured.out

    # Test missing object name
    args = parse_args(["get-references", "--by-object", str(DATA_DIR / "Empty.FCStd")])
    assert handle_get_references(args, [Path(DATA_DIR / "Empty.FCStd")]) == 0
    captured = capsys.readouterr()
    assert "No alias references found" in captured.out


def test_get_references_by_file(capsys: pytest.CaptureFixture[str]) -> None:
    """Test the --by-file output format of get-references command.
    Verifies that references are correctly grouped by file and that all
    aliases and their corresponding objects and expressions are displayed."""
    args = parse_args(["get-references", "--by-file", DATA_DIR / "Test1.FCStd"])
    assert handle_get_references(args, [Path(DATA_DIR / "Test1.FCStd")]) == 0
    captured = capsys.readouterr()
    assert "Alias references found:" in captured.out
    assert "\nFile: Test1.FCStd" in captured.out
    assert "  Alias: Height" in captured.out
    assert "    Object: Box" in captured.out
    assert "    Expression: <<globals>>#<<params>>.Height" in captured.out
    assert "  Alias: Length" in captured.out
    assert "    Object: Box" in captured.out
    assert "    Expression: <<globals>>#<<params>>.Length + 10" in captured.out
    assert "  Alias: Width" in captured.out
    assert "  Expression: <<globals>>#<<params>>.Width + 5" in captured.out

    # Test empty references
    args = parse_args(["get-references", "--by-file", str(DATA_DIR / "Empty.FCStd")])
    assert handle_get_references(args, [Path(DATA_DIR / "Empty.FCStd")]) == 0
    captured = capsys.readouterr()
    assert "No alias references found" in captured.out
    assert "Empty.FCStd" in captured.out


def test_get_references_json(capsys: pytest.CaptureFixture[str]) -> None:
    """Test the --json output format of get-references command.
    Verifies that the output is valid JSON and contains all reference information
    including files, objects, and expressions properly structured."""
    args = parse_args(["get-references", "--json", DATA_DIR / "Test1.FCStd"])
    assert handle_get_references(args, [Path(DATA_DIR / "Test1.FCStd")]) == 0
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    expected = {
        "Length": [
            {
                "object_name": "Box",
                "expression": "<<globals>>#<<params>>.Length + 10",
                "filename": "Test1.FCStd",
                "spreadsheet": "Sheet",
                "alias": "Length",
            }
        ],
        "Width": [
            {
                "object_name": "Box",
                "expression": "<<globals>>#<<params>>.Width + 5",
                "filename": "Test1.FCStd",
                "spreadsheet": "Sheet",
                "alias": "Width",
            }
        ],
        "Height": [
            {
                "object_name": "Box",
                "expression": "<<globals>>#<<params>>.Height",
                "filename": "Test1.FCStd",
                "spreadsheet": "Sheet",
                "alias": "Height",
            },
        ],
    }
    assert result == expected

    # Test empty references
    args = parse_args(["get-references", "--json", DATA_DIR / "Empty.FCStd"])
    assert handle_get_references(args, [Path(DATA_DIR / "Empty.FCStd")]) == 0
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result == {"message": "No alias references found"}

    # Test error handling
    args = parse_args(["get-references", "--json", str(DATA_DIR / "Invalid.FCStd")])
    assert handle_get_references(args, [Path(DATA_DIR / "Invalid.FCStd")]) == 0
    captured = capsys.readouterr()
    assert "No alias references found" in captured.out


def test_get_references_with_aliases(capsys: pytest.CaptureFixture[str]) -> None:
    """Test get-references command with alias filtering."""
    # Test exact match
    main(["get-references", "--aliases", "Length", str(DATA_DIR / "Test1.FCStd")])
    captured = capsys.readouterr()
    assert "Alias: Length" in captured.out
    assert "Alias: Height" not in captured.out
    assert "Alias: Width" not in captured.out

    # Test wildcard
    main(["get-references", "--aliases", "*th", str(DATA_DIR / "Test1.FCStd")])
    captured = capsys.readouterr()
    assert "Alias: Length" in captured.out
    assert "Alias: Height" not in captured.out
    assert "Alias: Width" in captured.out

    # Test empty
    main(["get-references", "--aliases", "", str(DATA_DIR / "Empty.FCStd")])
    captured = capsys.readouterr()
    assert "No alias references found" in captured.out

    # Test invalid
    main(["get-references", "--aliases", "[invalid]", str(DATA_DIR / "Test1.FCStd")])
    captured = capsys.readouterr()
    assert "No alias references found" in captured.out


def test_get_references_multiple_files(capsys: pytest.CaptureFixture[str]) -> None:
    """Test get-references command with multiple files.
    Verifies that:
    1. Multiple files are handled correctly
    2. References are merged correctly
    3. Output format is correct"""
    main(["get-references", str(DATA_DIR / "Empty.FCStd"), str(DATA_DIR / "Test1.FCStd")])
    captured = capsys.readouterr()
    assert "Alias references found:" in captured.out
    assert "is not a valid FCStd file" in captured.err
    assert " Empty.FCStd" in captured.out
    assert " Test1.FCStd" in captured.out


def test_get_references_empty_file(capsys: pytest.CaptureFixture[str]) -> None:
    """Test get-references command with empty file.
    Verifies that:
    1. Empty files are handled correctly
    2. Error message is displayed
    3. JSON output format works"""
    # Test normal output
    args = parse_args(["get-references", DATA_DIR / "Empty.FCStd"])
    assert handle_get_references(args, [Path(DATA_DIR / "Empty.FCStd")]) == 0
    captured = capsys.readouterr()
    assert "No alias references found" in captured.out
    assert "Empty.FCStd" in captured.out

    # Test JSON output
    args = parse_args(["get-references", "--json", DATA_DIR / "Empty.FCStd"])
    assert handle_get_references(args, [Path(DATA_DIR / "Empty.FCStd")]) == 0
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result == {"message": "No alias references found"}


def test_get_references_invalid_file(capsys: pytest.CaptureFixture[str]) -> None:
    """Test get-references command with an invalid file.
    Verifies that:
    1. Invalid files are handled gracefully
    2. Appropriate error message is shown
    3. Command exits successfully"""
    main(["get-references", str(DATA_DIR / "Invalid.FCStd")])
    captured = capsys.readouterr()
    assert "is not a valid FCStd file" in captured.err


def test_get_references_pattern_edge_cases(capsys: pytest.CaptureFixture[str]) -> None:
    """Test get-references command with various pattern matching edge cases.
    Verifies that:
    1. Empty patterns are handled
    2. Invalid patterns are handled
    3. Multiple patterns with mixed validity work
    4. Unicode patterns work"""

    # Test empty pattern
    main(["get-references", "--aliases", "", str(DATA_DIR / "Test1.FCStd")])
    captured = capsys.readouterr()
    assert "Alias references found" in captured.out  # Empty pattern matches all
    assert "Alias: Length" in captured.out
    assert "Alias: Width" in captured.out
    assert "Alias: Height" in captured.out

    # Test invalid pattern
    main(["get-references", "--aliases", "[invalid]", str(DATA_DIR / "Test1.FCStd")])
    captured = capsys.readouterr()
    assert "No alias references found" in captured.out

    # Test mixed patterns
    main(["get-references", "--aliases", "Length,Width", str(DATA_DIR / "Test1.FCStd")])
    captured = capsys.readouterr()
    assert "Alias: Length" in captured.out
    assert "Alias: Width" in captured.out

    # Test Unicode pattern
    main(["get-references", "--aliases", "*\u0041*", str(DATA_DIR / "Test1.FCStd")])  # \u0041 is 'A'
    captured = capsys.readouterr()
    assert "No alias references found" in captured.out

    # Test special characters in filename
    main(["get-references", str(DATA_DIR / "Test1 [v1.2].FCStd")])
    captured = capsys.readouterr()
    assert "No alias references found" in captured.out
    assert "Test1 [v1.2].FCStd" in captured.out

    # Test special characters in alias pattern
    main(["get-references", "--aliases", "*[LW]*", str(DATA_DIR / "Test1.FCStd")])
    captured = capsys.readouterr()
    assert "Alias references found" in captured.out
    assert "Alias: Length" in captured.out  # Should match Length
    assert "Alias: Width" in captured.out  # Should match Width

    # Test Unicode characters in filename
    main(["get-references", str(DATA_DIR / "Test1_éñå.FCStd")])
    captured = capsys.readouterr()
    assert "No alias references found" in captured.out
    assert "Test1_éñå.FCStd" in captured.out

    # Test Unicode characters in alias pattern
    main(["get-references", "--aliases", "*é*", str(DATA_DIR / "Test1.FCStd")])
    captured = capsys.readouterr()
    assert "No alias references found" in captured.out  # Should not find any since no aliases contain é


def test_get_properties(capsys: pytest.CaptureFixture[str]) -> None:
    """Test get-properties command.
    Verifies that:
    1. Properties are correctly extracted
    2. Output format is correct
    3. Multiple files are handled"""
    main(["get-properties", str(DATA_DIR / "Test1.FCStd")])
    captured = capsys.readouterr()
    assert "Properties found:" in captured.out
    assert "Author" in captured.out
    assert "Comment" in captured.out
    assert "Company" in captured.out

    # Test empty file
    main(["get-properties", str(DATA_DIR / "Empty.FCStd")])
    captured = capsys.readouterr()
    assert "No properties found" in captured.out

    # Test invalid file
    main(["get-properties", str(DATA_DIR / "Invalid.FCStd")])
    captured = capsys.readouterr()
    assert "is not a valid FCStd file" in captured.err


def test_get_aliases(capsys: pytest.CaptureFixture[str]) -> None:
    """Test get-aliases command.
    Verifies that:
    1. Aliases are correctly extracted
    2. Output format is correct
    3. Multiple files are handled"""
    main(["get-aliases", str(DATA_DIR / "Test1.FCStd")])
    captured = capsys.readouterr()
    assert "Cell aliases found:" in captured.out
    assert "Length" in captured.out
    assert "Width" in captured.out
    assert "Height" in captured.out

    # Test empty file
    main(["get-aliases", str(DATA_DIR / "Empty.FCStd")])
    captured = capsys.readouterr()
    assert "No cell aliases found" in captured.out

    # Test invalid file
    main(["get-aliases", str(DATA_DIR / "Invalid.FCStd")])
    captured = capsys.readouterr()
    assert "is not a valid FCStd file" in captured.err


def test_setup_logging_error(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    """Test error handling in logging setup.
    Verifies that:
    1. Invalid log file paths are handled gracefully
    2. Appropriate error messages are shown
    3. Default logging still works"""
    # Test invalid log file
    invalid_path = tmp_path / "nonexistent" / "log.txt"
    main(["--log-file", str(invalid_path), "get-references", str(DATA_DIR / "Test1.FCStd")])
    captured = capsys.readouterr()
    assert "Starting fc-audit" in captured.err  # Default logging should still work

    # Test default logging works without log file
    main(["get-references", "--json", str(DATA_DIR / "Test1.FCStd"), str(DATA_DIR / "Empty.FCStd")])
    captured = capsys.readouterr()
    assert "Starting fc-audit" in captured.err
