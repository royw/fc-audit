"""Command line interface for fc-audit."""

from __future__ import annotations

import argparse
import json
import sys
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
    level = "DEBUG" if verbose else "INFO"
    logger.add(sys.stderr, level=level)

    # Add file handler if specified
    if log_file:
        try:
            # Create parent directory if it doesn't exist
            log_path = Path(log_file)
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
    parser = argparse.ArgumentParser(description="Analyze FreeCAD documents for cell references")
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

    subparsers = parser.add_subparsers(dest="command", required=True)

    # get-references command
    get_refs = subparsers.add_parser("get-references", help="Get cell references from FreeCAD documents")
    get_refs.add_argument("files", nargs="+", type=Path, help="FreeCAD document files to analyze")

    # Format options
    format_group = get_refs.add_mutually_exclusive_group()
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

    # Filter options
    get_refs.add_argument(
        "--aliases",
        help="Filter aliases by pattern (e.g. 'Length*' or '*Width')",
    )

    # get-properties command
    get_props = subparsers.add_parser("get-properties", help="Get document properties from FreeCAD documents")
    get_props.add_argument("files", nargs="+", type=Path, help="FreeCAD document files to analyze")

    # get-aliases command
    get_aliases = subparsers.add_parser("get-aliases", help="Get cell aliases from FreeCAD documents")
    get_aliases.add_argument("files", nargs="+", type=Path, help="FreeCAD document files to analyze")
    get_aliases.add_argument(
        "--aliases",
        type=str,
        help="Comma-separated list of aliases to show (default: show all)",
    )

    args = parser.parse_args([str(a) for a in (argv or [])])

    # Set by-alias as default if no format option is specified
    if args.command == "get-references" and not any(
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
    for alias, refs in references.items():
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
    for alias, refs in references.items():
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
    error_occurred = False
    properties = set()
    for file_path in args.files:
        try:
            file_properties = get_document_properties(Path(file_path))
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
    error_occurred = False
    aliases = set()
    for file_path in args.files:
        try:
            file_aliases = get_cell_aliases(file_path)
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
    referenced_files = {ref.filename for refs in references.values() for ref in refs}
    empty_files = processed_files - referenced_files
    if empty_files:
        for filename in sorted(empty_files):
            logger.error(f"{filename} has no references")


def print_references(references: dict[str, list[Reference]], output_format: str, processed_files: set[str]) -> None:
    """Print references in the specified format.

    Args:
        references: Dictionary of references to print
        output_format: One of 'json', 'by_object', 'by_file', or 'by_alias'
        processed_files: Set of all processed file names
    """
    outputter = ReferenceOutputter(references, processed_files)
    if output_format == "json":
        print(outputter.to_json())
    elif output_format == "by_file":
        outputter.print_by_file()
    else:  # by_alias
        outputter.print_by_alias()


def _format_json_output(references: dict[str, list[Reference]]) -> None:
    """Format and print references in JSON format.

    Args:
        references: Dictionary mapping alias names to lists of references
    """
    if not references:
        print(json.dumps({"message": "No alias references found"}))
        return

    result = {}
    for alias, refs in references.items():
        result[alias] = [
            {
                "object_name": ref.object_name,
                "expression": ref.expression,
                "filename": ref.filename,
                "spreadsheet": ref.spreadsheet if ref.spreadsheet else None,
            }
            for ref in refs
        ]
    print(json.dumps(result), end="")


def _print_by_object_format(by_object: dict[str, dict[str, dict[str, list[Reference]]]]) -> None:
    """Print references grouped by object.

    Args:
        by_object: References formatted by object
    """
    for filename, objects in by_object.items():
        for obj_name, aliases in objects.items():
            print(f"\nObject: {obj_name}")
            print(f"  File: {filename}")
            for alias, refs in aliases.items():
                print(f"  Alias: {alias}")
                for ref in refs:
                    print(f"  Expression: {ref.expression}")


def _print_by_file_format(by_file: dict[str, dict[str, list[Reference]]]) -> None:
    """Print references grouped by file.

    Args:
        by_file: References formatted by file
    """
    for filename, aliases in by_file.items():
        print(f"\nFile: {filename}")
        for alias, refs in aliases.items():
            print(f"  Alias: {alias}")
            for ref in refs:
                print(f"    Object: {ref.object_name}")
                print(f"    Expression: {ref.expression}")


def _print_by_alias_format(references: dict[str, list[Reference]]) -> None:
    """Print references grouped by alias.

    Args:
        references: Dictionary mapping alias names to lists of references
    """
    for alias, refs in references.items():
        print(f"\nAlias: {alias}")
        for ref in refs:
            print(f"  File: {ref.filename}")
            print(f"  Object: {ref.object_name}")
            print(f"  Expression: {ref.expression}")


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
        paths = file_paths if file_paths is not None else args.files
        references, processed_files = process_references(paths, args.aliases)

        # Handle different output formats
        if getattr(args, "json", False):
            _format_json_output(references)
            return 0
        if getattr(args, "by_object", False):
            _print_by_object_format(format_by_object(references))
        elif getattr(args, "by_file", False):
            _print_by_file_format(format_by_file(references))
        else:  # by-alias (default)
            _print_by_alias_format(references)

        # Print summary if no references found
        if not references:
            print("\nNo alias references found")
        # Always print empty files list
        print_empty_files(processed_files, references)

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
        args = parse_args(argv or [])
        setup_logging(log_file=args.log_file, verbose=args.verbose)

        logger.info("Starting fc-audit")

        if args.command == "get-properties":
            return handle_get_properties(args)
        if args.command == "get-aliases":
            return handle_get_aliases(args)
        if args.command == "get-references":
            return handle_get_references(args)
        logger.error(f"Unknown command: {args.command}")
        return 1
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
