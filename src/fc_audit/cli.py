"""Command line interface for fc-audit."""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

from loguru import logger

from .alias_outputter import AliasOutputter
from .exceptions import InvalidFileError, XMLParseError
from .fcstd import get_cell_aliases, is_fcstd_file
from .logging import setup_logging
from .parser import parse_args
from .properties_outputter import PropertiesOutputter
from .reference_collector import Reference as BaseReference
from .reference_collector import ReferenceCollector
from .reference_outputter import ReferenceOutputter


def _ensure_reference_path_exists(
    by_file_obj: dict[str, dict[str, dict[str, list[BaseReference]]]],
    filename: str,
    object_name: str,
    alias: str,
) -> None:
    """Ensure all necessary dictionary paths exist for a reference.

    Args:
        by_file_obj: The target dictionary to update
        filename: Name of the file containing the reference
        object_name: Name of the object containing the reference
        alias: Name of the alias being referenced
    """
    if filename not in by_file_obj:
        by_file_obj[filename] = {}
    if object_name not in by_file_obj[filename]:
        by_file_obj[filename][object_name] = {}
    if alias not in by_file_obj[filename][object_name]:
        by_file_obj[filename][object_name][alias] = []


def format_by_object(
    references: dict[str, list[BaseReference]],
) -> dict[str, dict[str, dict[str, list[BaseReference]]]]:
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

    by_file_obj: dict[str, dict[str, dict[str, list[BaseReference]]]] = {}

    for alias, refs in references.items():
        for ref in refs:
            if ref.filename is not None:
                _ensure_reference_path_exists(by_file_obj, ref.filename, ref.object_name, alias)
                by_file_obj[ref.filename][ref.object_name][alias].append(ref)

    return by_file_obj


def format_by_file(
    references: dict[str, list[BaseReference]],
) -> dict[str, dict[str, list[BaseReference]]]:
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
    by_file: dict[str, dict[str, list[BaseReference]]] = {}
    alias: str
    refs: list[BaseReference]
    for alias, refs in references.items():
        ref: BaseReference
        for ref in refs:
            if ref.filename is not None:
                if ref.filename not in by_file:
                    by_file[ref.filename] = {}
                if alias not in by_file[ref.filename]:
                    by_file[ref.filename][alias] = []
                by_file[ref.filename][alias].append(ref)
    return by_file


def process_references(
    file_paths: list[Path], aliases: str | None = None
) -> tuple[dict[str, list[BaseReference]], set[str]]:
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


def print_references(
    references: dict[str, list[BaseReference]], output_format: str, processed_files: set[str]
) -> None:
    """Print references in the specified format.

    Args:
        references: Dictionary of references to print
        output_format: One of 'json', 'csv', 'by_object', 'by_file', or 'by_alias'
        processed_files: Set of all processed file names
    """
    outputter: ReferenceOutputter = ReferenceOutputter(references, processed_files)
    if output_format == "json":
        if not references:
            print('{"message": "No alias references found"}')
        else:
            print(outputter.to_json())
    elif output_format == "csv":
        outputter.to_csv()
    elif output_format == "by_file":
        outputter.print_by_file()
    elif output_format == "by_object":
        outputter.print_by_object()
    else:  # by_alias
        outputter.print_by_alias()


def handle_get_properties(args: argparse.Namespace, file_paths: list[Path]) -> int:
    """Handle get-properties command.

    Args:
        args: Command line arguments
        file_paths: List of valid file paths to process

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    success = False

    for path in file_paths:
        try:
            outputter = PropertiesOutputter([path])
            if args.filter:
                outputter.filter_properties(args.filter)
            outputter.output(args)
            success = True
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)

    return 0 if success else 1


def handle_get_aliases(args: argparse.Namespace, files: list[Path]) -> int:
    """Handle get-aliases command.

    Args:
        args: Command line arguments
        files: List of valid files to process

    Returns:
        Exit code
    """
    try:
        file_aliases: set[str]
        all_aliases: set[str] = set()
        success = False

        for path in files:
            try:
                file_aliases = get_cell_aliases(path)
                file_aliases = _filter_aliases(file_aliases, args.filter)
                all_aliases.update(file_aliases)
                success = True
            except (InvalidFileError, XMLParseError) as e:
                logger.error("%s: %s", path, e)

        if not all_aliases:
            logger.warning("No aliases found")

        outputter = AliasOutputter(all_aliases)
        outputter.output(args)

        return 0 if success else 1
    except Exception as e:
        logger.error("Error: %s", e)
        return 1


def _filter_references_by_patterns(
    references: dict[str, list[BaseReference]], patterns: str
) -> dict[str, list[BaseReference]]:
    """Filter references by alias patterns.

    Args:
        references: Dictionary of references to filter
        patterns: Comma-separated patterns to match against

    Returns:
        Filtered dictionary of references
    """
    filtered_refs: dict[str, list[BaseReference]] = {}
    for alias, refs in references.items():
        for pattern in patterns.split(","):
            if pattern and fnmatch.fnmatch(alias, pattern):
                filtered_refs[alias] = refs
                break
    return filtered_refs


def _filter_aliases(aliases: set[str], patterns: str) -> set[str]:
    """Filter aliases by patterns.

    Args:
        aliases: Set of aliases to filter
        patterns: Comma-separated patterns to match against

    Returns:
        Filtered set of aliases
    """
    if not patterns:
        return aliases
    filtered_aliases: set[str] = set()
    for alias in aliases:
        for pattern in patterns.split(","):
            if pattern and fnmatch.fnmatch(alias, pattern):
                filtered_aliases.add(alias)
                break
    return filtered_aliases


def _determine_output_format(args: argparse.Namespace) -> str:
    """Determine the output format from command line arguments.

    Args:
        args: Command line arguments

    Returns:
        Output format string
    """
    if getattr(args, "json", False):
        return "json"
    if getattr(args, "csv", False):
        return "csv"
    if getattr(args, "by_object", False):
        return "by_object"
    if getattr(args, "by_file", False):
        return "by_file"
    return "by_alias"


def _print_no_references(output_format: str) -> None:
    """Print message when no references are found.

    Args:
        output_format: Output format to use
    """
    if output_format == "json":
        print(json.dumps({"message": "No alias references found"}))
    else:
        print("No alias references found")


def _output_references(outputter: ReferenceOutputter, output_format: str) -> None:
    """Output references in the specified format.

    Args:
        outputter: ReferenceOutputter instance
        output_format: Output format to use
    """
    # Create a mock args object with the appropriate format flag set
    mock_args = argparse.Namespace(
        json=output_format == "json",
        csv=output_format == "csv",
        by_object=output_format == "by_object",
        by_file=output_format == "by_file",
        by_alias=output_format == "by_alias",
    )
    outputter.output(mock_args)


def handle_get_references(args: argparse.Namespace, file_paths: list[Path]) -> int:
    """Handle get-references command.

    Args:
        args: Command line arguments
        file_paths: List of valid file paths to process.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        collector = ReferenceCollector(file_paths)
        references = collector.collect()
        if args.filter:
            references = _filter_references_by_patterns(references, args.filter)

        output_format = _determine_output_format(args)
        if not references:
            _print_no_references(output_format)
            return 1

        outputter = ReferenceOutputter(references, collector.processed_files)
        _output_references(outputter, output_format)
        return 0

    except (InvalidFileError, XMLParseError) as e:
        print(f"{file_paths[0]} is not a valid FCStd file: {e}", file=sys.stderr)
        _print_no_references(_determine_output_format(args))
        return 1
    except Exception as e:
        print(f"Error processing files: {e}", file=sys.stderr)
        _print_no_references(_determine_output_format(args))
        return 1


def valid_files(files: list[Path]) -> Iterable[Path]:
    """Filter out non-existent files and invalid FCStd files from the list.

    Args:
        files: List of file paths to validate

    Returns:
        Iterator of valid FCStd file paths
    """
    for path in files:
        if not path.exists():
            print(f"Error: File '{path.name}' not found", file=sys.stderr)
            continue
        if not path.is_file():
            print(f"Error: '{path.name}' is not a file", file=sys.stderr)
            continue
        try:
            if not is_fcstd_file(path):
                print(f"Error: File '{path.name}' is not a valid FCStd file", file=sys.stderr)
                continue
        except Exception as e:
            logger.error("%s: Error checking file: %s", path, e)
            continue
        yield path


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

        valid_paths = list(valid_files(args.files))
        if not valid_paths:
            print("No valid files provided", file=sys.stderr)
            return 1

        if args.command == "references":
            return handle_get_references(args, valid_paths)
        if args.command == "properties":
            return handle_get_properties(args, valid_paths)
        if args.command == "aliases":
            return handle_get_aliases(args, valid_paths)
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 1

    except Exception as e:
        logger.error("Error: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
