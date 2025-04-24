"""Command line argument parser for fc-audit."""

from __future__ import annotations

import argparse
from argparse import _SubParsersAction
from collections.abc import Sequence
from pathlib import Path


def _add_format_options(parser: argparse.ArgumentParser, text_help: str | None = None) -> None:
    """Add common format options to a parser.

    Args:
        parser: The parser to add format options to
        text_help: Help text for the --text option. If None, the option is not added.
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

    Args:
        parser: The parser to add options to
    """
    parser.add_argument(
        "--log-file",
        type=str,
        help="Path to log file",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )


def _add_references_parser(subparsers: _SubParsersAction[argparse.ArgumentParser]) -> None:
    """Add the references command parser.

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

    # Filter options
    references_parser.add_argument(
        "--filter",
        help="Filter aliases by pattern (e.g. 'Length*' or '*Width')",
    )


def _add_properties_parser(subparsers: _SubParsersAction[argparse.ArgumentParser]) -> None:
    """Add the properties command parser.

    Args:
        subparsers: The subparsers to add the properties parser to
    """
    properties_parser = subparsers.add_parser("properties", help="Show document properties from FreeCAD documents")
    properties_parser.add_argument("files", nargs="+", type=Path, help="FreeCAD document files to analyze")

    # Filter options
    properties_parser.add_argument(
        "--filter",
        help="Filter properties by pattern (e.g. 'Length*' or '*Width')",
    )

    _add_format_options(properties_parser, text_help="Output as simple list of properties (default)")


def _add_aliases_parser(subparsers: _SubParsersAction[argparse.ArgumentParser]) -> None:
    """Add the aliases command parser.

    Args:
        subparsers: The subparsers to add the aliases parser to
    """
    aliases_parser = subparsers.add_parser("aliases", help="Show cell aliases from FreeCAD documents")
    aliases_parser.add_argument("files", nargs="+", type=Path, help="FreeCAD document files to analyze")

    _add_format_options(aliases_parser, text_help="Output in text format (default)")

    # Filter options
    aliases_parser.add_argument(
        "--filter",
        help="Comma-separated list of patterns to filter by (default: show all)",
    )


def parse_args(argv: Sequence[str | Path] | None = None) -> argparse.Namespace:
    """Parse command line arguments.

    Args:
        argv: Command line arguments

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        prog="fc-audit",
        description="Analyze FreeCAD documents for cell references",
    )

    _add_common_options(parser)

    # Add subcommands
    subparsers = parser.add_subparsers(dest="command", required=True, description="Commands")

    _add_references_parser(subparsers)
    _add_properties_parser(subparsers)
    _add_aliases_parser(subparsers)

    args = parser.parse_args([str(a) for a in (argv or [])])

    # Set default format options
    if args.command == "references" and not any(
        [
            getattr(args, "by_alias", False),
            getattr(args, "by_object", False),
            getattr(args, "by_file", False),
            getattr(args, "json", False),
            getattr(args, "csv", False),
        ]
    ):
        args.by_alias = True
    elif (
        args.command == "aliases"
        and not any(
            [
                getattr(args, "text", False),
                getattr(args, "json", False),
                getattr(args, "csv", False),
            ]
        )
    ) or (
        args.command == "properties"
        and not any(
            [
                getattr(args, "text", False),
                getattr(args, "json", False),
                getattr(args, "csv", False),
            ]
        )
    ):
        args.text = True

    return args
