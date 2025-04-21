"""Command line interface for fc-audit."""

from __future__ import annotations

import argparse
import sys
from argparse import _SubParsersAction
from collections.abc import Sequence
from pathlib import Path

from loguru import logger

from .exceptions import InvalidFileError, XMLParseError
from .fcstd import (
    get_cell_aliases,
    get_document_properties,
)
from .output import ReferenceOutputter
from .reference_collector import Reference, ReferenceCollector


def setup_logging(log_file: str | None = None, verbose: bool = False) -> None:
    """Configure logging settings.

    Args:
        log_file: Optional path to log file
        verbose: If True, set log level to DEBUG
    """
    # Remove default handler
    logger.remove()

    # Add stderr handler with appropriate level
    level: str = "DEBUG" if verbose else "INFO"
    logger.add(sys.stderr, level=level)

    # Add file handler if specified
    if log_file:
        try:
            # Create parent directory if it doesn't exist
            log_path: Path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            logger.add(log_file, rotation="10 MB")
        except Exception as e:
            logger.error(f"Failed to set up log file: {e}")

    # Log startup message
    logger.info("Starting fc-audit")


def parse_args(argv: Sequence[str | Path] | None = None) -> argparse.Namespace:
    """Parse command line arguments.

    Args:
        argv: Command line arguments

    Returns:
        Parsed arguments
    """
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="fc-audit",
        description="Analyze FreeCAD documents for cell references",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        help="Path to log file",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    subparsers: _SubParsersAction[argparse.ArgumentParser] = parser.add_subparsers(
        dest="command", required=True, description="Commands"
    )

    # references command
    references_parser: argparse.ArgumentParser = subparsers.add_parser(
        "references", help="Show cell references from FreeCAD documents"
    )
    references_parser.add_argument("files", nargs="+", type=Path, help="FreeCAD document files to analyze")

    # Format options
    format_group: argparse._MutuallyExclusiveGroup = references_parser.add_mutually_exclusive_group()
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
        "--aliases",
        help="Filter aliases by pattern (e.g. 'Length*' or '*Width')",
    )

    # properties command
    properties_parser: argparse.ArgumentParser = subparsers.add_parser(
        "properties", help="Show document properties from FreeCAD documents"
    )
    properties_parser.add_argument("files", nargs="+", type=Path, help="FreeCAD document files to analyze")

    # aliases command
    aliases_parser: argparse.ArgumentParser = subparsers.add_parser(
        "aliases", help="Show cell aliases from FreeCAD documents"
    )
    aliases_parser.add_argument("files", nargs="+", type=Path, help="FreeCAD document files to analyze")
    aliases_parser.add_argument(
        "--aliases",
        type=str,
        help="Comma-separated list of aliases to show (default: show all)",
    )

    args: argparse.Namespace = parser.parse_args([str(a) for a in (argv or [])])

    # Set by-alias as default if no format option is specified
    if args.command == "references" and not any(
        [
            getattr(args, "by_alias", False),
            getattr(args, "by_object", False),
            getattr(args, "by_file", False),
            getattr(args, "json", False),
        ]
    ):
        args.by_alias = True
    return args


def format_by_object(
    references: dict[str, list[Reference]],
) -> dict[str, dict[str, dict[str, list[Reference]]]]:
    """Format references grouped by file and object.

    Args:
        references: Dictionary mapping alias names to lists of references

    Returns:
        Dictionary with structure:
        {
            filename: {
                object_name: {
                    alias: [references]
                }
            }
        }
        Returns empty dict if references is empty.
    """
    if not references:
        return {}
    by_file_obj: dict[str, dict[str, dict[str, list[Reference]]]] = {}
    alias: str
    refs: list[Reference]
    for alias, refs in references.items():
        ref: Reference
        for ref in refs:
            if ref.filename is not None:
                if ref.filename not in by_file_obj:
                    by_file_obj[ref.filename] = {}
                if ref.object_name not in by_file_obj[ref.filename]:
                    by_file_obj[ref.filename][ref.object_name] = {}
                if alias not in by_file_obj[ref.filename][ref.object_name]:
                    by_file_obj[ref.filename][ref.object_name][alias] = []
                by_file_obj[ref.filename][ref.object_name][alias].append(ref)
    return by_file_obj


def format_by_file(
    references: dict[str, list[Reference]],
) -> dict[str, dict[str, list[Reference]]]:
    """Format references grouped by file and alias.

    Args:
        references: Dictionary mapping alias names to lists of references

    Returns:
        Dictionary with structure:
        {
            filename: {
                alias: [references]
            }
        }
        Returns empty dict if references is empty.
    """
    if not references:
        return {}
    by_file: dict[str, dict[str, list[Reference]]] = {}
    alias: str
    refs: list[Reference]
    for alias, refs in references.items():
        ref: Reference
        for ref in refs:
            if ref.filename is not None:
                if ref.filename not in by_file:
                    by_file[ref.filename] = {}
                if alias not in by_file[ref.filename]:
                    by_file[ref.filename][alias] = []
                by_file[ref.filename][alias].append(ref)
    return by_file


def handle_get_properties(args: argparse.Namespace) -> int:
    """Handle get-properties command.

    Args:
        args: Command line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    error_occurred: bool = False
    properties: set[str] = set()
    for file_path in args.files:
        try:
            file_properties: set[str] = get_document_properties(Path(file_path))
            properties.update(file_properties)
        except Exception as e:
            error_msg = f"{file_path} is not a valid FCStd file: {e}"
            logger.error(error_msg)
            error_occurred = True

    if properties:
        print("Properties found:")
        for prop in sorted(properties):
            print(f"  {prop}")
    else:
        print("No properties found")

    return 1 if error_occurred else 0


def handle_get_aliases(args: argparse.Namespace) -> int:
    """Handle get-aliases command.

    Args:
        args: Command line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    error_occurred: bool = False
    aliases: set[str] = set()
    for file_path in args.files:
        try:
            file_aliases: set[str] = get_cell_aliases(file_path)
            aliases.update(file_aliases)
        except InvalidFileError as e:
            error_msg = f"{file_path} is not a valid FCStd file: {e}"
            logger.error(error_msg)
            error_occurred = True
        except Exception as e:
            error_msg = f"Error processing {file_path}: {e}"
            logger.error(error_msg)
            error_occurred = True

    if aliases:
        print("Cell aliases found:")
        alias: str
        for alias in sorted(aliases):
            print(f"  {alias}")
    else:
        print("No cell aliases found")

    return 1 if error_occurred else 0


def process_references(
    file_paths: list[Path], aliases: str | None = None
) -> tuple[dict[str, list[Reference]], set[str]]:
    """Process files and get references.

    Args:
        file_paths: List of files to process
        aliases: Optional comma-separated list of alias patterns

    Returns:
        Tuple of (references dict, set of processed file names)
    """
    # Collect references from all files
    collector = ReferenceCollector(file_paths)
    references = collector.collect()

    # Create outputter and filter by alias patterns if provided
    outputter = ReferenceOutputter(references, collector.processed_files)
    if aliases:
        patterns = [p.strip() for p in aliases.split(",") if p.strip()]
        outputter.filter_by_patterns(patterns)

    return outputter.references, collector.processed_files


def print_empty_files(processed_files: set[str], references: dict[str, list[Reference]]) -> None:
    """Print list of files that have no references.

    Args:
        processed_files: Set of all processed file names
        references: Dictionary mapping alias names to lists of references

    Output format:
        Files with no references:
          <filename>
          <filename>
          ...
    """
    referenced_files: set[str] = {
        ref.filename for refs in references.values() for ref in refs if ref.filename is not None
    }
    empty_files: set[str] = processed_files - referenced_files
    if empty_files:
        filename: str
        for filename in sorted(empty_files):
            logger.info(f"Note: {filename} contains no spreadsheet references")


def print_references(references: dict[str, list[Reference]], output_format: str, processed_files: set[str]) -> None:
    """Print references in the specified format.

    Args:
        references: Dictionary of references to print
        output_format: One of 'json', 'csv', 'by_object', 'by_file', or 'by_alias'
        processed_files: Set of all processed file names
    """
    outputter: ReferenceOutputter = ReferenceOutputter(references, processed_files)
    if output_format == "json":
        print(outputter.to_json())
    elif output_format == "csv":
        outputter.to_csv()
    elif output_format == "by_file":
        outputter.print_by_file()
    elif output_format == "by_object":
        outputter.print_by_object()
    else:  # by_alias
        outputter.print_by_alias()


def handle_get_references(args: argparse.Namespace, file_paths: list[Path] | None = None) -> int:
    """Handle get-references command.

    Args:
        args: Command line arguments
        file_paths: Optional list of file paths to process. If not provided,
            uses args.files.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        paths: list[Path] = file_paths if file_paths is not None else args.files
        references: dict[str, list[Reference]]
        processed_files: set[str]
        references, processed_files = process_references(paths, args.aliases)

        # Handle output formats
        output_format = (
            "json"
            if getattr(args, "json", False)
            else "csv"
            if getattr(args, "csv", False)
            else "by_object"
            if getattr(args, "by_object", False)
            else "by_file"
            if getattr(args, "by_file", False)
            else "by_alias"
        )
        print_references(references, output_format, processed_files)

        # Return 1 if no references found
        if not references:
            return 1
        return 0
    except InvalidFileError as e:
        logger.error(str(e))
        return 1
    except XMLParseError as e:
        logger.error(str(e))
        return 1
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        return 1


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point for the command line interface.

    Args:
        argv: Command line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        argv = argv or sys.argv[1:]
        args: argparse.Namespace = parse_args(argv)

        # Configure logging
        setup_logging(getattr(args, "log_file", None), getattr(args, "verbose", False))

        if args.command == "properties":
            return handle_get_properties(args)
        if args.command == "aliases":
            return handle_get_aliases(args)
        if args.command == "references":
            return handle_get_references(args)
        logger.error(f"Unknown command: {args.command}")
        return 1
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
