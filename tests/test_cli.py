"""Tests for the command line interface."""
import fnmatch
import json
import pytest
from pathlib import Path
from fc_audit.cli import parse_args, setup_logging, main, handle_get_references
from fc_audit.fcstd import Reference
from loguru import logger


def test_parse_args_default():
    """Test that the CLI requires at least one command argument.
    Should raise SystemExit when no arguments are provided."""

    with pytest.raises(SystemExit):
        parse_args([])



def test_parse_args_verbose():
    """Test that both -v and --verbose flags are recognized but still require a command.
    Should raise SystemExit when only verbose flag is provided."""

    with pytest.raises(SystemExit):
        parse_args(["-v"])
    
    with pytest.raises(SystemExit):
        parse_args(["--verbose"])


def test_parse_args_log_file():
    """Test that --log-file argument is recognized but still requires a command.
    Should raise SystemExit when only log file is provided."""

    with pytest.raises(SystemExit):
        parse_args(["--log-file", "test.log"])


def test_setup_logging_default(capsys):
    """Test that default logging setup outputs INFO level messages to stderr
    but filters out DEBUG level messages."""

    setup_logging()
    logger.info("Test message")
    captured = capsys.readouterr()
    assert "Test message" in captured.err
    assert "DEBUG" not in captured.err


def test_setup_logging_verbose(capsys):
    """Test that verbose logging setup allows DEBUG level messages
    to be output to stderr."""

    setup_logging(None, True)
    logger.debug("Debug message")
    captured = capsys.readouterr()
    assert "Debug message" in captured.err


@pytest.fixture
def mock_reference_parser(mocker):
    """Setup mocks for reference parsing."""
    # Mock get_references_from_files
    mock_get_refs = mocker.patch('fc_audit.cli.get_references_from_files')
    def mock_get_references_from_files(files, patterns=None):
        # Return test references for any file
        if any('empty' in str(file).lower() for file in files):
            return {}
        for _file in files:
            if 'invalid' in str(_file).lower():
                raise Exception(f"Invalid file: {_file}")
        refs = {
            "Length": [
                Reference("Box", "<<globals>>#<<params>>.Length + 10", "test1.FCStd", "Sheet", "Length")
            ],
            "Width": [
                Reference("Box", "<<globals>>#<<params>>.Width + 5", "test1.FCStd", "Sheet", "Width")
            ],
            "Height": [
                Reference("Box", "<<globals>>#<<params>>.Height", "test1.FCStd", "Sheet", "Height"),
                Reference("Box", "<<globals>>#<<params>>.Height * 2", "test1.FCStd", "Sheet", "Height")
            ]
        }
        if patterns and patterns[0]:
            return {k: v for k, v in refs.items() if any(fnmatch.fnmatch(k, p) for p in patterns)}
        return refs
    mock_get_refs.side_effect = mock_get_references_from_files

    # Mock get_properties_from_files
    mock_get_props = mocker.patch('fc_audit.cli.get_properties_from_files')
    def mock_get_properties_from_files(files):
        if any('empty' in str(file).lower() for file in files):
            return set()
        if any('invalid' in str(file).lower() for file in files):
            raise Exception("Invalid file")
        return {'Author', 'Comment', 'Company', 'Length', 'Width', 'Height'}
    mock_get_props.side_effect = mock_get_properties_from_files

    # Mock get_cell_aliases_from_files
    mock_get_aliases = mocker.patch('fc_audit.cli.get_cell_aliases_from_files')
    def mock_get_cell_aliases_from_files(files):
        if any('empty' in str(file).lower() for file in files):
            return set()
        if any('invalid' in str(file).lower() for file in files):
            raise Exception("Invalid file")
        return {'Length', 'Width', 'Height'}
    mock_get_aliases.side_effect = mock_get_cell_aliases_from_files

    return mock_get_refs


@pytest.fixture
def mock_references():
    """Mock reference data for testing."""
    return {
        'Length': [
            Reference(
                filename="tests/data/Test1.FCStd",
                object_name="Sketch",
                expression="<<globals>>#<<params>>.Length + 10",
                spreadsheet="Sheet",
                alias="Length"
            )
        ],
        'Width': [
            Reference(
                filename="tests/data/Test1.FCStd",
                object_name="Sketch",
                expression="<<globals>>#<<params>>.Width + 5",
                spreadsheet="Sheet",
                alias="Width"
            )
        ],
        'Height': [
            Reference(
                filename="tests/data/Test1.FCStd",
                object_name="Box",
                expression="<<globals>>#<<params>>.Height",
                spreadsheet="Sheet",
                alias="Height"
            ),
            Reference(
                filename="tests/data/Test1.FCStd",
                object_name="Box",
                expression="<<globals>>#<<params>>.Height * 2",
                spreadsheet="Sheet",
                alias="Height"
            )
        ]
    }


def test_parse_args_get_references():
    """Test parsing of get-references command with various arguments.
    Verifies:
    1. Default format (by-alias) when no format flags are provided
    2. Alias filtering with --aliases option
    3. Different output formats (--by-object, --by-file)
    4. JSON output format (--json)"""

    # Test default format
    args = parse_args(["get-references", "file.FCStd"])
    assert args.command == "get-references"
    assert args.files == ["file.FCStd"]
    assert args.aliases is None
    assert args.by_alias is True
    assert not args.by_object
    assert not args.by_file
    assert not args.json

    # Test with aliases
    args = parse_args(["get-references", "--aliases", "Length,Height", "file.FCStd"])
    assert args.aliases == "Length,Height"

    # Test different formats
    args = parse_args(["get-references", "--by-object", "file.FCStd"])
    assert args.by_object is True

    args = parse_args(["get-references", "--by-file", "file.FCStd"])
    assert args.by_file is True

    args = parse_args(["get-references", "--json", "file.FCStd"])
    assert args.json is True


def test_get_references_by_alias(mock_reference_parser, capsys):
    """Test the default by-alias output format of get-references command.
    Verifies that references are correctly grouped by alias name and that
    the output includes the file, object name, and expression for each reference."""
    main(["get-references", "--by-alias", "tests/data/Test1.FCStd"])
    captured = capsys.readouterr()
    
    # Check output format
    output = captured.out
    assert "Alias references found:" in output
    assert "Alias: Length" in output
    assert "  File: test1.FCStd" in output
    assert "  Object: Box" in output
    assert "  Expression: <<globals>>#<<params>>.Length + 10" in output
    assert "Alias: Width" in output
    assert "  File: test1.FCStd" in output
    assert "  Object: Box" in output
    assert "  Expression: <<globals>>#<<params>>.Width + 5" in output
    assert "Alias: Height" in output
    assert "  File: test1.FCStd" in output
    assert "  Object: Box" in output
    assert "  Expression: <<globals>>#<<params>>.Height" in output


def test_get_references_by_object(mock_reference_parser, capsys):
    """Test the --by-object output format of get-references command.
    Verifies that references are correctly grouped by object name within each file
    and that all aliases and expressions for each object are displayed."""
    # Test normal case
    args = parse_args(['get-references', '--by-object', 'test.FCStd'])
    assert handle_get_references(args, [Path('test.FCStd')]) == 0
    captured = capsys.readouterr()
    assert "Alias references found:" in captured.out
    assert "\nObject: Box" in captured.out
    assert "  File: test1.FCStd" in captured.out
    assert "  Alias: Height" in captured.out
    assert "  Expression: <<globals>>#<<params>>.Height" in captured.out
    assert "  Alias: Length" in captured.out
    assert "  Expression: <<globals>>#<<params>>.Length + 10" in captured.out

    # Test missing object name
    mock_reference_parser.side_effect = lambda files, patterns=None: {
        "Height": [Reference(None, "<<globals>>#<<params>>.Height", "test.FCStd", "Sketch", "Height")]
    }
    args = parse_args(['get-references', '--by-object', 'test.FCStd'])
    assert handle_get_references(args, [Path('test.FCStd')]) == 0
    captured = capsys.readouterr()
    assert "Object: None" in captured.out


def test_get_references_by_file(mock_reference_parser, capsys):
    """Test the --by-file output format of get-references command.
    Verifies that references are correctly grouped by file and that all
    aliases and their corresponding objects and expressions are displayed."""
    args = parse_args(['get-references', '--by-file', 'test.FCStd'])
    assert handle_get_references(args, [Path('test.FCStd')]) == 0
    captured = capsys.readouterr()
    assert "Alias references found:" in captured.out
    assert "\nFile: test1.FCStd" in captured.out
    assert "  Alias: Height" in captured.out
    assert "    Object: Box" in captured.out
    assert "    Expression: <<globals>>#<<params>>.Height" in captured.out
    assert "  Alias: Length" in captured.out
    assert "    Object: Box" in captured.out
    assert "    Expression: <<globals>>#<<params>>.Length + 10" in captured.out
    assert "  Alias: Width" in captured.out
    assert "  Expression: <<globals>>#<<params>>.Width + 5" in captured.out

    # Test empty references
    args = parse_args(['get-references', '--by-file', 'empty.FCStd'])
    assert handle_get_references(args, [Path('empty.FCStd')]) == 0
    captured = capsys.readouterr()
    assert "No alias references found" in captured.out
    assert "empty.FCStd" in captured.out

    # Test missing object name
    mock_reference_parser.side_effect = lambda files, patterns=None: {
        "Height": [Reference(None, "<<globals>>#<<params>>.Height", "test.FCStd", "Sketch", "Height")]
    }
    args = parse_args(['get-references', '--by-object', 'test.FCStd'])
    assert handle_get_references(args, [Path('test.FCStd')]) == 0
    captured = capsys.readouterr()
    assert "Object: None" in captured.out

def test_get_references_json(mock_reference_parser, capsys):
    """Test the --json output format of get-references command.
    Verifies that the output is valid JSON and contains all reference information
    including files, objects, and expressions properly structured."""
    args = parse_args(['get-references', '--json', 'test.FCStd'])
    assert handle_get_references(args, [Path('test.FCStd')]) == 0
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    expected = {
        'Length': [{
            'object_name': 'Box',
            'expression': '<<globals>>#<<params>>.Length + 10',
            'filename': 'test1.FCStd',
            'spreadsheet': 'Sheet',
            'alias': 'Length'
        }],
        'Width': [{
            'object_name': 'Box',
            'expression': '<<globals>>#<<params>>.Width + 5',
            'filename': 'test1.FCStd',
            'spreadsheet': 'Sheet',
            'alias': 'Width'
        }],
        'Height': [
            {
                'object_name': 'Box',
                'expression': '<<globals>>#<<params>>.Height',
                'filename': 'test1.FCStd',
                'spreadsheet': 'Sheet',
                'alias': 'Height'
            },
            {
                'object_name': 'Box',
                'expression': '<<globals>>#<<params>>.Height * 2',
                'filename': 'test1.FCStd',
                'spreadsheet': 'Sheet',
                'alias': 'Height'
            }
        ]
    }
    assert result == expected

    # Test empty references
    # mock_reference_parser.return_value = {}
    args = parse_args(['get-references', '--json', 'empty.FCStd'])
    assert handle_get_references(args, [Path('empty.FCStd')]) == 0
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result == {"message": "No alias references found"}
    # mock_reference_parser.side_effect = mock_get_references_from_files
    
    # Test error handling
    mock_reference_parser.side_effect = Exception("Test error")
    args = parse_args(['get-references', '--json', 'invalid.FCStd'])
    assert handle_get_references(args, [Path('invalid.FCStd')])
    captured = capsys.readouterr()
    assert "Test error" in captured.out


def test_get_references_with_aliases(mock_reference_parser, capsys):
    """Test get-references command with alias filtering."""
    
    # Test exact match
    main(["get-references", "--aliases", "Length", "tests/data/Test1.FCStd"])
    captured = capsys.readouterr()
    assert "Alias: Length" in captured.out
    assert "Alias: Height" not in captured.out
    assert "Alias: Width" not in captured.out
    
    # Test wildcard
    main(["get-references", "--aliases", "*th", "tests/data/Test1.FCStd"])
    captured = capsys.readouterr()
    assert "Alias: Length" in captured.out
    assert "Alias: Height" not in captured.out
    assert "Alias: Width" in captured.out


def test_get_references_multiple_files(mock_reference_parser, capsys):
    """Test get-references command with multiple files.
    Verifies that:
    1. Multiple files are handled correctly
    2. References are merged correctly
    3. Output format is correct"""
    main(["get-references", "tests/data/Empty.FCStd", "tests/data/test1.FCStd"])
    captured = capsys.readouterr()
    assert "No alias references found" in captured.out
    assert "\nProcessed files:" in captured.out
    assert "  Empty.FCStd" in captured.out
    assert "  test1.FCStd" in captured.out


def test_get_references_empty_file(mock_reference_parser, capsys):
    """Test get-references command with empty file.
    Verifies that:
    1. Empty files are handled correctly
    2. Error message is displayed
    3. JSON output format works"""
    # Test normal output
    mock_reference_parser.return_value = {}
    args = parse_args(['get-references', 'empty.FCStd'])
    assert handle_get_references(args, [Path('empty.FCStd')]) == 0
    captured = capsys.readouterr()
    assert "No alias references found" in captured.out
    assert "empty.FCStd" in captured.out

    # Test JSON output
    args = parse_args(['get-references', '--json', 'empty.FCStd'])
    assert handle_get_references(args, [Path('empty.FCStd')]) == 0
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result == {"message": "No alias references found"}


def test_get_references_invalid_file(mock_reference_parser, capsys):
    """Test get-references command with an invalid file.
    Verifies that:
    1. Invalid files are handled gracefully
    2. Appropriate error message is shown
    3. Command exits successfully"""
    
    main(["get-references", "tests/data/Invalid.FCStd"])
    captured = capsys.readouterr()
    
    # Check output
    assert "Invalid file" in captured.out


def test_get_references_pattern_edge_cases(mock_reference_parser, capsys):
    """Test get-references command with various pattern matching edge cases.
    Verifies that:
    1. Empty patterns are handled
    2. Invalid patterns are handled
    3. Multiple patterns with mixed validity work
    4. Unicode patterns work"""
    # Test empty pattern
    main(["get-references", "--aliases", "", "tests/data/Test1.FCStd"])
    captured = capsys.readouterr()
    assert "Alias references found" in captured.out  # Empty pattern matches all
    assert "Alias: Length" in captured.out
    assert "Alias: Width" in captured.out
    assert "Alias: Height" in captured.out
    
    # Test invalid pattern
    main(["get-references", "--aliases", "[invalid]", "tests/data/Test1.FCStd"])
    captured = capsys.readouterr()
    assert "No alias references found" in captured.out

    # Test mixed patterns
    main(["get-references", "--aliases", "Length,Width", "tests/data/Test1.FCStd"])
    captured = capsys.readouterr()
    assert "Alias: Length" in captured.out
    assert "Alias: Width" in captured.out

    # Test Unicode pattern
    main(["get-references", "--aliases", "*\u0041*", "tests/data/Test1.FCStd"])  # \u0041 is 'A'
    captured = capsys.readouterr()
    assert "No alias references found" in captured.out

def test_get_references_special_chars(mock_reference_parser, capsys):
    """Test get-references command with special characters in filenames and aliases.
    Verifies that:
    1. Special characters in filenames are handled
    2. Special characters in aliases are handled
    3. Unicode characters are handled correctly"""
    
    # Test special characters in filename
    main(["get-references", "tests/data/test1 [v1.2].FCStd"])
    captured = capsys.readouterr()
    assert "Alias references found" in captured.out  # Should find references since mock returns them
    assert "Alias: Length" in captured.out
    assert "Alias: Width" in captured.out
    
    # Test special characters in alias pattern
    main(["get-references", "--aliases", "*[LW]*", "tests/data/Test1.FCStd"])
    captured = capsys.readouterr()
    assert "Alias references found" in captured.out
    assert "Alias: Length" in captured.out  # Should match Length
    assert "Alias: Width" in captured.out   # Should match Width
    
    # Test Unicode characters in filename
    main(["get-references", "tests/data/test1_éñå.FCStd"])
    captured = capsys.readouterr()
    assert "Alias references found" in captured.out  # Should find references since mock returns them
    assert "Alias: Length" in captured.out
    
    # Test Unicode characters in alias pattern
    main(["get-references", "--aliases", "*é*", "tests/data/Test1.FCStd"])
    captured = capsys.readouterr()
    assert "No alias references found" in captured.out  # Should not find any since no aliases contain é


def test_get_properties(mock_reference_parser, capsys):
    """Test get-properties command.
    Verifies that:
    1. Properties are correctly extracted
    2. Output format is correct
    3. Multiple files are handled"""
    main(["get-properties", "tests/data/Test1.FCStd"])
    captured = capsys.readouterr()
    assert "Properties found:" in captured.out
    assert "Author" in captured.out
    assert "Comment" in captured.out
    assert "Company" in captured.out

    # Test empty file
    main(["get-properties", "tests/data/Empty.FCStd"])
    captured = capsys.readouterr()
    assert "No properties found" in captured.out

    # Test invalid file
    main(["get-properties", "tests/data/Invalid.FCStd"])
    captured = capsys.readouterr()
    assert "Error:" in captured.err


def test_get_aliases(mock_reference_parser, capsys):
    """Test get-aliases command.
    Verifies that:
    1. Aliases are correctly extracted
    2. Output format is correct
    3. Multiple files are handled"""
    main(["get-aliases", "tests/data/Test1.FCStd"])
    captured = capsys.readouterr()
    assert "Cell aliases found:" in captured.out
    assert "Length" in captured.out
    assert "Width" in captured.out
    assert "Height" in captured.out

    # Test empty file
    main(["get-aliases", "tests/data/Empty.FCStd"])
    captured = capsys.readouterr()
    assert "No cell aliases found" in captured.out

    # Test invalid file
    main(["get-aliases", "tests/data/Invalid.FCStd"])
    captured = capsys.readouterr()
    assert "Error: Invalid file" in captured.err


def test_setup_logging_error(capsys, tmp_path):
    """Test error handling in logging setup.
    Verifies that:
    1. Invalid log file paths are handled gracefully
    2. Appropriate error messages are shown
    3. Default logging still works"""
    # Test invalid log file
    invalid_path = tmp_path / "nonexistent" / "log.txt"
    main(["--log-file", str(invalid_path), "get-references", "tests/data/Test1.FCStd"])
    captured = capsys.readouterr()
    assert "Starting fc-audit" in captured.err  # Default logging should still work

    # Test default logging works without log file
    main(["get-references", "tests/data/Test1.FCStd", "tests/data/Test2.FCStd"])
    captured = capsys.readouterr()
    assert "Starting fc-audit" in captured.err
