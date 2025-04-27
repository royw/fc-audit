"""Command line argument parser for fc-audit.

This module provides the command-line interface for fc-audit, handling argument parsing
for all supported commands (properties, references, aliases). It defines the structure
and options for each command, including:

- Format options (text, JSON, CSV)
- Filtering options
- Output grouping options
- Common options (logging, verbosity)

The parser is designed to be user-friendly and follows standard CLI conventions.
"""

from __future__ import annotations

import argparse
from argparse import _SubParsersAction
from collections.abc import Sequence
from pathlib import Path

from .version import __version__


def _add_format_options(parser: argparse.ArgumentParser, text_help: str | None = None) -> None:
    """Add common format options to a parser.

    Adds mutually exclusive output format options to the given parser. These options
    control how the command's output is formatted. Available formats are:

        - text (optional, controlled by text_help)
        - JSON (for programmatic use)
        - CSV (for spreadsheet analysis)

    Args:
        parser: The parser to add format options to
        text_help: Help text for the --text option. If None, the option is not added.

    Example:
        If text_help is provided, these options are added to the parser:

            --text: Output in text format
            --json: Output in JSON format
            --csv:  Output as comma-separated values
    """
    format_group = parser.add_mutually_exclusive_group()
    if text_help:
        format_group.add_argument(
            "--text",
            action="store_true",
            help=text_help,
        )
    format_group.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )
    format_group.add_argument(
        "--csv",
        action="store_true",
        help="Output as comma-separated values",
    )


def _add_common_options(parser: argparse.ArgumentParser) -> None:
    """Add common options to the parser.

    Adds options that are common to all commands:

        - Logging options (--log-file to specify log output)
        - Verbosity control (-v/--verbose for detailed output)

    These options help with debugging and monitoring the tool's operation.

    Args:
        parser: The parser to add options to
    """
    parser.add_argument(
        "--log-file",
        type=str,
        help="Path to log file",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Enable debug output",
    )


def _add_references_parser(subparsers: _SubParsersAction[argparse.ArgumentParser]) -> None:
    """Add the references command parser.

    Configures the 'references' command which analyzes cell references in FreeCAD documents.
    The command supports multiple output formats and grouping options:

    Format Options (mutually exclusive):

    - --by-alias: Group by alias name (default)
    - --by-object: Group by object name
    - --by-file: Group by filename
    - --json: JSON output
    - --csv: CSV output

    Filter Options:

    - --filter: Pattern to filter aliases (e.g., 'Length*')

    Args:
        subparsers: The subparsers to add the references parser to
    """
    references_parser = subparsers.add_parser("references", help="Show cell references from FreeCAD documents")
    references_parser.add_argument("files", nargs="+", type=Path, help="FreeCAD document files to analyze")

    # Format options
    format_group = references_parser.add_mutually_exclusive_group()
    format_group.add_argument(
        "--by-alias",
        action="store_true",
        help="Group references by alias (default)",
    )
    format_group.add_argument(
        "--by-object",
        action="store_true",
        help="Group references by object",
    )
    format_group.add_argument(
        "--by-file",
        action="store_true",
        help="Group references by file",
    )
    format_group.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )
    format_group.add_argument(
        "--csv",
        action="store_true",
        help="Output as comma-separated values",
    )

    references_parser.set_defaults(by_alias=True)

    # Filter options
    references_parser.add_argument(
        "--filter",
        help="Filter aliases by pattern (e.g. 'Length*' or '*Width')",
    )


def _add_properties_parser(subparsers: _SubParsersAction[argparse.ArgumentParser]) -> None:
    """Add the properties command parser.

    Configures the 'properties' command which extracts and displays document properties
    from FreeCAD files. The command supports multiple output formats:

    Format Options (mutually exclusive):

        - --text: Simple list output (default)
        - --json: JSON output
        - --csv: CSV output

    Filter Options:
    - --filter: Pattern to filter properties (e.g., 'Shape*')

    Args:
        subparsers: The subparsers to add the properties parser to
    """
    properties_parser = subparsers.add_parser("properties", help="Show document properties from FreeCAD documents")
    properties_parser.add_argument("files", nargs="+", type=Path, help="FreeCAD document files to analyze")

    _add_format_options(properties_parser, text_help="Output as simple list of properties (default)")

    # Set all defaults, including those not used but expected by the outputter
    properties_parser.set_defaults(
        text=True,
    )

    # Filter options
    properties_parser.add_argument(
        "--filter",
        help="Filter properties by pattern (e.g. 'Length*' or '*Width')",
    )


def _add_aliases_parser(subparsers: _SubParsersAction[argparse.ArgumentParser]) -> None:
    """Add the aliases command parser.

    Configures the 'aliases' command which extracts cell aliases from FreeCAD spreadsheets.
    The command supports multiple output formats:

    Format Options (mutually exclusive):

        - --text: Text output (default)
        - --json: JSON output
        - --csv: CSV output

    Filter Options:

        - --filter: Comma-separated patterns to filter aliases

    Args:
        subparsers: The subparsers to add the aliases parser to
    """
    aliases_parser = subparsers.add_parser("aliases", help="Show cell aliases from FreeCAD documents")
    aliases_parser.add_argument("files", nargs="+", type=Path, help="FreeCAD document files to analyze")

    _add_format_options(aliases_parser, text_help="Output in text format (default)")

    aliases_parser.set_defaults(text=True)

    # Filter options
    aliases_parser.add_argument(
        "--filter",
        help="Comma-separated list of patterns to filter by (default: show all)",
    )


def parse_args(argv: Sequence[str | Path] | None = None) -> argparse.Namespace:
    """Parse command line arguments.

    Main entry point for parsing command line arguments. Configures and runs the argument
    parser with all available commands and their options. Supports three main commands:

    1. properties: Extract document properties
    2. references: Analyze cell references
    3. aliases: Extract spreadsheet cell aliases

    Each command has its own set of format and filter options.

    Args:
        argv: Command line arguments to parse. If None, sys.argv[1:] is used.

    Returns:
        Parsed arguments as a Namespace object containing all specified options
        and their values.
    """
    parser = argparse.ArgumentParser(prog="fc-audit", description="Analyze FreeCAD documents for cell references")
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show program version and exit",
    )

    _add_common_options(parser)

    # Add subcommands
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Create subparsers with their own defaults
    _add_properties_parser(subparsers)
    _add_references_parser(subparsers)
    _add_aliases_parser(subparsers)

    # Parse arguments
    return parser.parse_args([str(a) for a in (argv or [])])
