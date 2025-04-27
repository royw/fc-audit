"""Tests for the command line interface."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pytest
from loguru import logger

from fc_audit.cli import (
    _handle_get_references,
    main,
    parse_args,
    setup_logging,
)
from fc_audit.reference_collector import Reference
from fc_audit.reference_outputter import ReferenceOutputter

TESTS_DIR = Path(__file__).parent
DATA_DIR = TESTS_DIR / "data"


def _check_help_output(capsys: pytest.CaptureFixture[str], args: list[str], expected_options: list[str]) -> None:
    """Helper to run help and check options."""
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


def test_main_help_output(capsys: pytest.CaptureFixture[str]) -> None:
    """Test that all top-level options appear in the main help output."""
    top_level_options = [
        "--log-file",
        "--debug",
        "references",
        "properties",
        "aliases",
    ]
    _check_help_output(capsys, ["--help"], top_level_options)


def test_references_help_output(capsys: pytest.CaptureFixture[str]) -> None:
    """Test that all references command options appear in its help output."""
    get_references_options = [
        "--by-alias",
        "--by-object",
        "--by-file",
        "--json",
        "--filter",
    ]
    _check_help_output(capsys, ["references", "--help"], get_references_options)


def test_aliases_help_output(capsys: pytest.CaptureFixture[str]) -> None:
    """Test that all aliases command options appear in its help output."""
    get_aliases_options = [
        "--filter",
    ]
    _check_help_output(capsys, ["aliases", "--help"], get_aliases_options)


def test_properties_help_output(capsys: pytest.CaptureFixture[str]) -> None:
    """Test that properties command help shows the required files argument."""
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


def test_parse_args_debug() -> None:
    """Test that both -d and --debug flags are recognized but still require a command.
    Should raise SystemExit when only debug flag is provided."""

    with pytest.raises(SystemExit):
        parse_args(["-d"])

    with pytest.raises(SystemExit):
        parse_args(["--debug"])


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


def test_setup_logging_debug(capsys: pytest.CaptureFixture[str]) -> None:
    """Test that debug logging setup allows DEBUG level messages
    to be output to stderr."""
    setup_logging(None, True)
    logger.debug("Debug message")
    logger.info("Info message")
    captured = capsys.readouterr()
    assert "Debug message" in captured.err
    assert "Info message" in captured.err


def test_parse_args_references_default() -> None:
    """Test parsing of references command with default arguments."""
    args = parse_args(["references", str(DATA_DIR / "Test1.FCStd")])
    assert args.command == "references"
    assert args.files == [DATA_DIR / "Test1.FCStd"]
    assert args.filter is None
    assert args.by_alias is True
    assert not args.by_object
    assert not args.by_file
    assert not args.json


def test_parse_args_references_filter() -> None:
    """Test parsing of references command with filter argument."""
    args = parse_args(["references", "--filter", "Length,Height", DATA_DIR / "Test1.FCStd"])
    assert args.filter == "Length,Height"


def test_parse_args_references_by_object() -> None:
    """Test parsing of references command with by-object format."""
    args = parse_args(["references", "--by-object", DATA_DIR / "Test1.FCStd"])
    assert args.by_object is True


def test_parse_args_references_by_file() -> None:
    """Test parsing of references command with by-file format."""
    args = parse_args(["references", "--by-file", DATA_DIR / "Test1.FCStd"])
    assert args.by_file is True


def test_parse_args_references_json() -> None:
    """Test parsing of references command with JSON format."""
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

    main(["references", "--filter", "Length,Width", str(DATA_DIR / "Test1.FCStd")])
    captured = capsys.readouterr()

    # Check output format
    output = captured.out
    assert "Alias: Length" in output
    assert "Alias: Width" in output


def test_setup_logging_invalid_path(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    """Test that setup_logging handles invalid log file paths gracefully."""
    # Remove existing handlers
    logger.remove()

    invalid_path = tmp_path / "non\x00existent" / "test.log"
    setup_logging(str(invalid_path))
    captured = capsys.readouterr()
    assert "Failed to set up log file" in captured.err

    # Verify default logging still works
    logger.info("Test message")
    captured = capsys.readouterr()
    assert "Test message" in captured.err


def test_setup_logging_readonly_dir(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    """Test that setup_logging handles read-only directory permissions gracefully."""
    # Remove existing handlers
    logger.remove()

    readonly_dir = tmp_path / "readonly"
    readonly_dir.mkdir()
    readonly_dir.chmod(0o555)  # Read and execute only
    readonly_log = readonly_dir / "test.log"
    setup_logging(str(readonly_log))
    logger.info("Test message")
    captured = capsys.readouterr()
    assert "Failed to set up log file" in captured.err
    assert "Test message" in captured.err


def test_setup_logging_default_fallback(capsys: pytest.CaptureFixture[str]) -> None:
    """Test that setup_logging falls back to default logging when log file is not available."""
    # Remove existing handlers
    logger.remove()

    main(["--debug", "references", "--json", str(DATA_DIR / "Test1.FCStd"), str(DATA_DIR / "Empty.FCStd")])
    captured = capsys.readouterr()
    assert "Starting fc-audit" in captured.err


def test_main_invalid_command(capsys: pytest.CaptureFixture[str]) -> None:
    """Test main function with invalid command."""
    with pytest.raises(SystemExit) as excinfo:
        main(["invalid-command"])
    assert excinfo.value.code == 2
    captured = capsys.readouterr()
    assert "invalid choice" in captured.err.lower()


def test_main_missing_files() -> None:
    """Test main function with missing files argument."""
    with pytest.raises(SystemExit) as excinfo:
        main(["references"])
    assert excinfo.value.code == 2


def test_main_invalid_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test main function with invalid file."""
    invalid_file = tmp_path / "invalid.FCStd"
    invalid_file.write_text("Not a valid FCStd file")
    assert main(["references", str(invalid_file)]) == 1
    captured = capsys.readouterr()
    assert "Error: File 'invalid.FCStd' is not a valid FCStd file" in captured.err
    assert "No valid files provided" in captured.err


def test_main_empty_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test main function with empty file."""
    empty_file = tmp_path / "empty.FCStd"
    empty_file.write_text("")
    assert main(["references", str(empty_file)]) == 1
    captured = capsys.readouterr()
    assert "Error: File 'empty.FCStd' is not a valid FCStd file" in captured.err
    assert "No valid files provided" in captured.err


def test_main_multiple_files(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test main function with multiple files including invalid ones."""
    invalid_file = tmp_path / "invalid.FCStd"
    invalid_file.write_text("Not a valid FCStd file")
    assert main(["references", str(DATA_DIR / "Test1.FCStd"), str(invalid_file)]) == 0
    captured = capsys.readouterr()
    assert "Alias:" in captured.out
    assert "Error: File 'invalid.FCStd' is not a valid FCStd file" in captured.err


def test_main_invalid_filter(capsys: pytest.CaptureFixture[str]) -> None:
    """Test main function with invalid filter pattern."""
    assert main(["references", "--filter", "[", str(DATA_DIR / "Test1.FCStd")]) == 1
    captured = capsys.readouterr()
    assert "No alias references found" in captured.out


def test_main_invalid_log_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test main function with invalid log file."""
    invalid_log = tmp_path / "in\x00valid" / "log.txt"
    assert main(["--log-file", str(invalid_log), "references", str(DATA_DIR / "Test1.FCStd")]) == 0
    captured = capsys.readouterr()
    assert "Failed to set up log file" in captured.err
    assert "Alias:" in captured.out


def test_main_invalid_format_combination(capsys: pytest.CaptureFixture[str]) -> None:
    """Test main function with invalid format combination."""
    with pytest.raises(SystemExit) as excinfo:
        main(["references", "--json", "--csv", str(DATA_DIR / "Test1.FCStd")])
    assert excinfo.value.code == 2
    captured = capsys.readouterr()
    assert "not allowed with argument" in captured.err.lower()


def test_main_none_args(capsys: pytest.CaptureFixture[str]) -> None:
    """Test main function with None args."""
    with pytest.raises(SystemExit):
        main(None)

    # Should use sys.argv[1:] which is empty in test environment
    with pytest.raises(SystemExit):
        main(["--debug"])

    captured = capsys.readouterr()
    assert "error" in captured.err


def test_by_file_sort_order(capsys: pytest.CaptureFixture[str]) -> None:
    """Test that --by-file output is sorted by file, alias, then object."""
    from fc_audit.reference_collector import Reference
    from fc_audit.reference_outputter import ReferenceOutputter

    # Construct unsorted input
    refs = {
        "Beta": [
            Reference(object_name="ObjB", expression="e1", filename="b.FCStd", spreadsheet="s", alias="Beta"),
            Reference(object_name="ObjB", expression="e3", filename="a.FCStd", spreadsheet="s", alias="Beta"),
        ],
        "Alpha": [
            Reference(object_name="ObjA", expression="e2", filename="b.FCStd", spreadsheet="s", alias="Alpha"),
            Reference(object_name="ObjC", expression="e4", filename="a.FCStd", spreadsheet="s", alias="Alpha"),
            Reference(object_name="ObjA", expression="e5", filename="a.FCStd", spreadsheet="s", alias="Alpha"),
        ],
    }
    outputter = ReferenceOutputter(refs, {"a.FCStd", "b.FCStd"})
    outputter.print_by_file()
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
    from fc_audit.reference_collector import Reference
    from fc_audit.reference_outputter import ReferenceOutputter

    # Construct unsorted input
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
    outputter = ReferenceOutputter(refs, {"a.FCStd", "b.FCStd"})
    outputter.print_by_alias()
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


def test_references_csv_format(capsys: pytest.CaptureFixture[str]) -> None:
    """Test the --csv output format of references command."""
    refs = {
        "Length": [
            Reference(
                filename="Test1.FCStd",
                object_name="Box",
                expression="<<globals>>#<<params>>.Length + 10",
            )
        ],
        "Width,Special": [  # Test comma in alias name
            Reference(
                filename="Test1.FCStd",
                object_name='Box"Quote"',  # Test quote in object name
                expression='<<globals>>#<<params>>."Width,Special" * 2',
            )
        ],
    }
    processed_files = {"Test1.FCStd"}
    outputter = ReferenceOutputter(refs, processed_files)
    outputter.to_csv()
    captured = capsys.readouterr()

    # Split output into lines and verify each line
    lines = captured.out.splitlines()
    assert len(lines) == 3  # Header + 2 data lines
    assert lines[0] == '"alias","filename","object_name","expression"'

    # Verify data lines are properly formatted

    def split_csv_string(csv_string: str) -> list[str]:
        """Split a CSV string, handling quoted fields with commas."""
        # Replace commas within quoted fields with a different character
        s = re.sub(r'\"((?:[^"]|\"\")*)\"', lambda m: m.group(0).replace(",", "|"), csv_string)
        # Split the string using commas
        return [item.replace("|", ",") for item in s.split(",")]

    for line in lines[1:]:
        parts = split_csv_string(line)
        assert len(parts) == 4
        assert all(part.startswith('"') and part.endswith('"') for part in parts)


def test_references_csv_empty(capsys: pytest.CaptureFixture[str]) -> None:
    """Test CSV output with empty reference set."""
    refs: dict[str, list[Reference]] = {}
    processed_files: set[str] = set()
    outputter = ReferenceOutputter(refs, processed_files)
    outputter.to_csv()
    captured = capsys.readouterr()

    # Should output 'No alias references found'
    assert captured.out == "No alias references found\n"


def test_references_csv_sort_order(capsys: pytest.CaptureFixture[str]) -> None:
    """Test that CSV output is sorted by alias, then filename, then object name."""
    refs = {
        "B": [
            Reference(filename="2.FCStd", object_name="Box", expression="expr"),
            Reference(filename="1.FCStd", object_name="Box", expression="expr"),
        ],
        "A": [
            Reference(filename="1.FCStd", object_name="Sketch", expression="expr"),
            Reference(filename="1.FCStd", object_name="Box", expression="expr"),
        ],
    }
    processed_files = {"1.FCStd", "2.FCStd"}
    outputter = ReferenceOutputter(refs, processed_files)
    outputter.to_csv()
    captured = capsys.readouterr()

    lines = captured.out.splitlines()[1:]  # Skip header
    assert "A" in lines[0]  # First alias alphabetically
    assert "1.FCStd" in lines[0]  # First file alphabetically
    assert "Box" in lines[0]  # First object alphabetically


def test_references_format_conflict() -> None:
    """Test that incompatible format options raise an error."""
    # Test that --by-object and --by-file can't be used together
    with pytest.raises(SystemExit):
        parse_args(["references", "file.FCStd", "--by-object", "--by-file"])

    # Test that --by-object and --json can't be used together
    with pytest.raises(SystemExit):
        parse_args(["references", "file.FCStd", "--by-object", "--json"])

    # Test that --by-file and --json can't be used together
    with pytest.raises(SystemExit):
        parse_args(["references", "file.FCStd", "--by-file", "--json"])

    # Test that --by-alias and --json can't be used together
    with pytest.raises(SystemExit):
        parse_args(["references", "file.FCStd", "--by-alias", "--json"])


def test_aliases_no_by_options() -> None:
    """Test that aliases command does not support --by-* options."""
    # Test that --by-object is not supported
    with pytest.raises(SystemExit):
        parse_args(["aliases", "file.FCStd", "--by-object"])

    # Test that --by-file is not supported
    with pytest.raises(SystemExit):
        parse_args(["aliases", "file.FCStd", "--by-file"])

    # Test that --by-alias is not supported
    with pytest.raises(SystemExit):
        parse_args(["aliases", "file.FCStd", "--by-alias"])


def test_properties_no_by_alias() -> None:
    """Test that properties command does not support --by-alias option."""
    # Test that --by-alias is not supported
    with pytest.raises(SystemExit):
        parse_args(["properties", "file.FCStd", "--by-alias"])


def test_references_invalid_files(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test handling of invalid file paths."""
    nonexistent = tmp_path / "nonexistent.FCStd"
    invalid = tmp_path / "invalid.txt"
    invalid.touch()

    args = argparse.Namespace(
        files=[nonexistent],
        filter=None,
        json=False,
        csv=True,
        text=True,
        by_object=False,
        by_alias=False,
    )
    # Should exit with error code 1 and print error message
    result = _handle_get_references(args, args.files)
    assert result == 1
    captured = capsys.readouterr()
    assert "No alias references found" in captured.out

    args.files = [invalid]
    # Should exit with error code 1 and print error message
    result = _handle_get_references(args, args.files)
    assert result == 1
    captured = capsys.readouterr()
    assert "No alias references found" in captured.out


def test_main_entry_point(capsys: pytest.CaptureFixture[str]) -> None:
    """Test the main entry point with various arguments."""
    from fc_audit.__main__ import main as main_entry

    # Test help output
    with pytest.raises(SystemExit):
        main_entry(["--help"])
    captured = capsys.readouterr()
    assert "usage:" in captured.out

    # Test invalid command
    with pytest.raises(SystemExit):
        main_entry(["invalid"])
    captured = capsys.readouterr()
    assert "error:" in captured.err
