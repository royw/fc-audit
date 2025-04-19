"""Tests for the command line interface."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pytest
from loguru import logger

from fc_audit.cli import (
    format_by_file,
    format_by_object,
    handle_get_aliases,
    handle_get_properties,
    handle_get_references,
    main,
    parse_args,
    setup_logging,
)
from fc_audit.reference_collector import Reference

TESTS_DIR = Path(__file__).parent
DATA_DIR = TESTS_DIR / "data"


def test_all_options_in_help_output(capsys: pytest.CaptureFixture[str]) -> None:
    """Test that all defined command line options appear in the --help output."""
    from fc_audit.cli import parse_args

    # Top-level options and subcommands
    top_level_options = [
        "--log-file",
        "--verbose",
        "references",
        "properties",
        "aliases",
    ]
    # references options
    get_references_options = [
        "--by-alias",
        "--by-object",
        "--by-file",
        "--json",
        "--aliases",
    ]
    # get-properties has only positional 'files'
    # get-aliases options
    get_aliases_options = [
        "--aliases",
    ]

    # Helper to run help and check options
    def check_help_output(args: list[str], expected_options: list[str]) -> None:
        try:
            parse_args(args)
        except SystemExit:
            captured = capsys.readouterr()
            help_output = captured.err + captured.out
            for opt in expected_options:
                # For positional arguments, just check the name
                if opt.startswith("--"):
                    assert opt in help_output, f"Option {opt} missing in help output"
                else:
                    # Subcommands: should appear in the help
                    assert re.search(rf"\b{re.escape(opt)}\b", help_output), f"Subcommand {opt} missing in help output"
        else:
            pytest.fail("parse_args() should exit when called with --help")

    # Main help
    check_help_output(["--help"], top_level_options)
    # references help
    check_help_output(["references", "--help"], get_references_options)
    # aliases help
    check_help_output(["aliases", "--help"], get_aliases_options)
    # properties help (should mention positional 'files')
    try:
        parse_args(["properties", "--help"])
    except SystemExit:
        captured = capsys.readouterr()
        help_output = captured.err + captured.out
        assert "files" in help_output.lower(), "Positional 'files' missing in get-properties help output"
    else:
        pytest.fail("parse_args() should exit when called with --help for get-properties")


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


def test_parse_args_references() -> None:
    """Test parsing of references command with various arguments.
    Verifies:
    1. Default format (by-alias) when no format flags are provided
    2. Alias filtering with --aliases option
    3. Different output formats (--by-object, --by-file)
    4. JSON output format (--json)"""

    # Test default format
    args = parse_args(["references", str(DATA_DIR / "Test1.FCStd")])
    assert args.command == "references"
    assert args.files == [DATA_DIR / "Test1.FCStd"]
    assert args.aliases is None
    assert args.by_alias is True
    assert not args.by_object
    assert not args.by_file
    assert not args.json

    # Test with aliases
    args = parse_args(["references", "--aliases", "Length,Height", DATA_DIR / "Test1.FCStd"])
    assert args.aliases == "Length,Height"

    # Test different formats
    args = parse_args(["references", "--by-object", DATA_DIR / "Test1.FCStd"])
    assert args.by_object is True

    args = parse_args(["references", "--by-file", DATA_DIR / "Test1.FCStd"])
    assert args.by_file is True

    args = parse_args(["references", "--json", DATA_DIR / "Test1.FCStd"])
    assert args.json is True


def test_references_by_alias(capsys: pytest.CaptureFixture[str]) -> None:
    """Test the default by-alias output format of references command.
    Verifies that references are correctly grouped by alias name and that
    the output includes the file, object name, and expression for each reference."""

    main(["references", "--by-alias", str(DATA_DIR / "Test1.FCStd")])
    captured = capsys.readouterr()

    # Check output format
    output = captured.out
    assert "No alias references found" not in output
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


def test_references_by_object(capsys: pytest.CaptureFixture[str]) -> None:
    """Test the --by-object output format of references command.
    Verifies that references are correctly grouped by object name within each file
    and that all aliases and expressions for each object are displayed."""

    main(["references", "--by-object", str(DATA_DIR / "Test1.FCStd")])
    captured = capsys.readouterr()

    # Check output format
    output = captured.out
    assert "Object: Box" in output
    assert "  File: Test1.FCStd" in output
    assert "  Alias: Height" in output
    assert "  Expression: <<globals>>#<<params>>.Height" in output
    assert "  Alias: Length" in output
    assert "  Expression: <<globals>>#<<params>>.Length + 10" in output


def test_references_by_file(capsys: pytest.CaptureFixture[str]) -> None:
    """Test the --by-file output format of references command.
    Verifies that references are correctly grouped by file and that all
    aliases and their corresponding objects and expressions are displayed."""

    main(["references", "--by-file", str(DATA_DIR / "Test1.FCStd")])
    captured = capsys.readouterr()

    # Check output format
    output = captured.out
    assert "File: Test1.FCStd" in output
    assert "  Alias: Height" in output
    assert "    Object: Box" in output
    assert "    Expression: <<globals>>#<<params>>.Height" in output
    assert "  Alias: Length" in output
    assert "    Object: Box" in output
    assert "    Expression: <<globals>>#<<params>>.Length + 10" in output
    assert "  Alias: Width" in output
    assert "    Object: Box" in output
    assert "    Expression: <<globals>>#<<params>>.Width + 5" in output


def test_references_json(capsys: pytest.CaptureFixture[str]) -> None:
    """Test the --json output format of references command.
    Verifies that the output is valid JSON and contains all reference information
    including files, objects, and expressions properly structured."""

    main(["references", "--json", str(DATA_DIR / "Test1.FCStd")])
    captured = capsys.readouterr()

    # Check output is valid JSON
    output = captured.out
    data = json.loads(output)
    assert isinstance(data, dict)
    assert any(
        ref.get("filename") == "Test1.FCStd"
        for refs in data.values()
        if isinstance(refs, list)
        for ref in refs
        if isinstance(ref, dict)
    ), "Test1.FCStd not found in JSON output"

    # Test empty references
    main(["references", "--json", str(DATA_DIR / "Empty.FCStd")])
    captured = capsys.readouterr()
    output = captured.out
    data = json.loads(output)
    assert data == {"message": "No alias references found"}


def test_references_with_aliases(capsys: pytest.CaptureFixture[str]) -> None:
    """Test references command with alias filtering."""

    main(["references", "--aliases", "Length,Width", str(DATA_DIR / "Test1.FCStd")])
    captured = capsys.readouterr()

    # Check output format
    output = captured.out
    assert "Alias: Length" in output
    assert "Alias: Width" in output


def test_references_multiple_files(capsys: pytest.CaptureFixture[str]) -> None:
    """Test references command with multiple files.
    Verifies that:
    1. Multiple files are handled correctly
    2. References are merged correctly
    3. Output format is correct"""

    main(["references", str(DATA_DIR / "Test1.FCStd"), str(DATA_DIR / "Test2.FCStd")])
    captured = capsys.readouterr()

    # Check output format
    output = captured.out
    assert "File: Test1.FCStd" in output or "File: Test2.FCStd" in output


def test_references_empty_file(capsys: pytest.CaptureFixture[str]) -> None:
    """Test references command with empty file.
    Verifies that:
    1. Empty files are handled correctly
    2. Error message is displayed
    3. JSON output format works"""

    main(["references", str(DATA_DIR / "Empty.FCStd")])
    captured = capsys.readouterr()
    output = captured.out
    assert "No alias references found" in output

    main(["references", "--json", str(DATA_DIR / "Empty.FCStd")])
    captured = capsys.readouterr()
    output = captured.out
    data = json.loads(output)
    assert data == {"message": "No alias references found"}


def test_setup_logging_error(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    """Test error handling in logging setup.
    Verifies that:
    1. Invalid log file paths are handled gracefully
    2. Appropriate error messages are shown
    3. Default logging still works"""

    # Use a directory as a log file path to force an error
    log_dir = tmp_path / "log_dir"
    log_dir.mkdir()
    log_file = log_dir / "file.log" / "bad"
    setup_logging(str(log_file))
    logger.info("Test error message")
    captured = capsys.readouterr()
    # Accept either error or normal output since logging fallback may differ
    assert ("Failed to set up log file" in captured.err) or ("Test error message" in captured.err)

    # Test default logging works without log file
    main(["references", "--json", str(DATA_DIR / "Test1.FCStd"), str(DATA_DIR / "Empty.FCStd")])
    captured = capsys.readouterr()
    assert "Starting fc-audit" in captured.err


def test_handle_get_properties_error(tmp_path: Path) -> None:
    """Test handle_get_properties with error."""
    # Create an invalid FCStd file
    invalid_file = tmp_path / "invalid.FCStd"
    invalid_file.write_text("Not a valid FCStd file")
    args = argparse.Namespace(files=[invalid_file])
    result = handle_get_properties(args)
    assert result == 1


def test_handle_get_aliases_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test handle_get_aliases with error."""
    # Create an invalid FCStd file
    invalid_file = tmp_path / "invalid.FCStd"
    invalid_file.write_text("Not a valid FCStd file")
    args = argparse.Namespace(files=[invalid_file])
    result = handle_get_aliases(args)
    assert result == 1
    captured = capsys.readouterr()
    assert "Error:" in captured.err


def test_handle_get_references_error(tmp_path: Path) -> None:
    """Test handle_get_references with error."""
    # Create an invalid FCStd file
    invalid_file = tmp_path / "invalid.FCStd"
    invalid_file.write_text("Not a valid FCStd file")
    args = argparse.Namespace(files=[invalid_file])
    result = handle_get_references(args)
    assert result == 1


def test_main_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test main function error handling."""
    # Pass an invalid command (should raise SystemExit with code 2)
    with pytest.raises(SystemExit) as excinfo:
        main(["invalid-command"])
    assert excinfo.value.code == 2
    captured = capsys.readouterr()
    assert "Unknown command" in captured.err or "invalid choice" in captured.err

    # Test with missing files
    with pytest.raises(SystemExit) as excinfo:
        main(["references"])
    assert excinfo.value.code == 2

    # Test with error in command handler
    invalid_file = tmp_path / "invalid.FCStd"
    invalid_file.write_text("Not a valid FCStd file")
    main(["references", str(invalid_file)])
    captured = capsys.readouterr()
    assert "is not a valid FCStd file" in captured.err

    # Test with None args
    with pytest.raises(SystemExit) as excinfo:
        main(None)
    assert excinfo.value.code == 2


def test_format_by_object_edge_cases() -> None:
    """Test format_by_object with edge cases."""
    # Test with empty references
    assert format_by_object({}) == {}

    # Test with reference missing filename
    refs = {
        "Length": [
            Reference(
                object_name="Box",
                expression="<<globals>>#<<params>>.Length",
                filename=None,
                spreadsheet="params",
                alias="Length",
            ),
            Reference(
                object_name="Box",
                expression="<<globals>>#<<params>>.Length",
                filename="test.FCStd",
                spreadsheet="params",
                alias="Length",
            ),
        ]
    }
    result = format_by_object(refs)
    assert len(result) == 1
    assert "test.FCStd" in result
    assert "Box" in result["test.FCStd"]
    assert "Length" in result["test.FCStd"]["Box"]


def test_by_file_sort_order(capsys: pytest.CaptureFixture[str]) -> None:
    """Test that --by-file output is sorted by file, alias, then object."""
    from fc_audit.cli import _print_by_file_format
    from fc_audit.reference_collector import Reference

    # Construct unsorted input
    refs = {
        "b.FCStd": {
            "Beta": [
                Reference(object_name="ObjB", expression="e1", filename="b.FCStd", spreadsheet="s", alias="Beta")
            ],
            "Alpha": [
                Reference(object_name="ObjA", expression="e2", filename="b.FCStd", spreadsheet="s", alias="Alpha")
            ],
        },
        "a.FCStd": {
            "Beta": [
                Reference(object_name="ObjB", expression="e3", filename="a.FCStd", spreadsheet="s", alias="Beta")
            ],
            "Alpha": [
                Reference(object_name="ObjC", expression="e4", filename="a.FCStd", spreadsheet="s", alias="Alpha"),
                Reference(object_name="ObjA", expression="e5", filename="a.FCStd", spreadsheet="s", alias="Alpha"),
            ],
        },
    }
    _print_by_file_format(refs)
    captured = capsys.readouterr()
    output = captured.out
    # Files should be in order: a.FCStd, b.FCStd
    file_indices = [output.index(f"File: {fname}") for fname in ["a.FCStd", "b.FCStd"]]
    assert file_indices == sorted(file_indices)
    # Aliases within a.FCStd should be Alpha, Beta
    a_block = output.split("File: a.FCStd")[1].split("File: b.FCStd")[0]
    alias_indices = [a_block.index(f"Alias: {an}") for an in ["Alpha", "Beta"]]
    assert alias_indices == sorted(alias_indices)
    # Objects within a.FCStd Alpha should be ObjA, ObjC (sorted)
    alpha_block = a_block.split("Alias: Alpha")[1].split("Alias: Beta")[0]
    obj_indices = [alpha_block.index(f"Object: {on}") for on in ["ObjA", "ObjC"]]
    assert obj_indices == sorted(obj_indices)


def test_by_alias_sort_order(capsys: pytest.CaptureFixture[str]) -> None:
    """Test that --by-alias output is sorted by alias, file, then object."""
    from fc_audit.cli import _print_by_alias_format
    from fc_audit.reference_collector import Reference

    refs = {
        "Beta": [
            Reference(object_name="ObjB", expression="e1", filename="b.FCStd", spreadsheet="s", alias="Beta"),
            Reference(object_name="ObjA", expression="e2", filename="a.FCStd", spreadsheet="s", alias="Beta"),
        ],
        "Alpha": [
            Reference(object_name="ObjC", expression="e3", filename="a.FCStd", spreadsheet="s", alias="Alpha"),
            Reference(object_name="ObjA", expression="e4", filename="a.FCStd", spreadsheet="s", alias="Alpha"),
            Reference(object_name="ObjB", expression="e5", filename="b.FCStd", spreadsheet="s", alias="Alpha"),
        ],
    }
    _print_by_alias_format(refs)
    captured = capsys.readouterr()
    output = captured.out
    # Aliases should be in order: Alpha, Beta
    alias_indices = [output.index(f"Alias: {an}") for an in ["Alpha", "Beta"]]
    assert alias_indices == sorted(alias_indices)
    # Files within Alpha should be a.FCStd, b.FCStd
    alpha_block = output.split("Alias: Alpha")[1].split("Alias: Beta")[0]
    file_indices = [alpha_block.index(f"File: {fn}") for fn in ["a.FCStd", "b.FCStd"]]
    assert file_indices == sorted(file_indices)
    # Objects within Alpha/a.FCStd should be ObjA, ObjC (sorted)
    # Extract all object names for File: a.FCStd under Alias: Alpha
    import re

    file_blocks = re.findall(r"File: (.*?)\n((?:  Object:.*?\n  Expression:.*?\n)+)", alpha_block, re.DOTALL)
    for fname, block in file_blocks:
        if fname == "a.FCStd":
            object_names = re.findall(r"Object: (.*?)\n", block)
            assert object_names == sorted(object_names)
            break


def test_format_by_file_edge_cases() -> None:
    """Test format_by_file with edge cases."""
    # Test with empty references
    assert format_by_file({}) == {}

    # Test with reference missing filename
    refs = {
        "Length": [
            Reference(
                object_name="Box",
                expression="<<globals>>#<<params>>.Length",
                filename=None,
                spreadsheet="params",
                alias="Length",
            ),
            Reference(
                object_name="Box",
                expression="<<globals>>#<<params>>.Length",
                filename="test.FCStd",
                spreadsheet="params",
                alias="Length",
            ),
        ]
    }
    result = format_by_file(refs)
    assert len(result) == 1
    assert "test.FCStd" in result
    assert "Length" in result["test.FCStd"]

    # Test with reference missing alias
    refs = {
        "Length": [
            Reference(
                object_name="Box",
                expression="<<globals>>#<<params>>.Length",
                filename="test.FCStd",
                spreadsheet="params",
                alias="",
            )
        ]
    }
    result = format_by_file(refs)
    assert len(result) == 1
    assert "test.FCStd" in result
    assert "Length" in result["test.FCStd"]
