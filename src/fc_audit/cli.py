"""Command line interface for fc-audit."""

from __future__ import annotations

import argparse
import fnmatch
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

from loguru import logger

from .alias_outputter import AliasOutputter
from .exceptions import InvalidFileError, XMLParseError
from .fcstd import get_cell_aliases
from .logging import setup_logging
from .parser import parse_args
from .properties_outputter import PropertiesOutputter
from .reference import Reference
from .reference_collector import ReferenceCollector
from .reference_outputter import ReferenceOutputter
from .validation import is_fcstd_file


def _filter_references_by_patterns(
    references: dict[str, list[Reference]], patterns: str
) -> dict[str, list[Reference]]:
    """Filter references by alias patterns using glob-style matching.

    This function filters the references dictionary by matching alias names against
    the provided patterns. Each pattern is treated as a glob pattern (e.g., '*width*'
    would match 'BoxWidth', 'width', etc.).

    Args:
        references: Dictionary mapping alias names to lists of references
        patterns: Comma-separated glob patterns to match against alias names
            (e.g., 'width*,height*,*length')

    Returns:
        A new dictionary containing only the references whose aliases match at least
        one of the patterns. If patterns is empty or None, returns the original
        references dictionary unmodified.

    Example:
        >>> refs = {"Width": [...], "Height": [...], "Length": [...]}
        >>> _filter_references_by_patterns(refs, "W*,L*")
        {'Width': [...], 'Length': [...]}
    """
    if not patterns:
        return references

    filtered_refs: dict[str, list[Reference]] = {}
    for alias, refs in references.items():
        for pattern in patterns.split(","):
            if pattern and fnmatch.fnmatch(alias, pattern):
                filtered_refs[alias] = refs
                break
    return filtered_refs


def _filter_aliases(aliases: set[str], patterns: str) -> set[str]:
    """Filter aliases by glob patterns.

    This function filters a set of aliases by matching them against the provided
    glob patterns. Similar to _filter_references_by_patterns but operates on a
    simple set of strings rather than a dictionary of references.

    Args:
        aliases: Set of alias names to filter
        patterns: Comma-separated glob patterns to match against alias names
            (e.g., 'width*,height*,*length')

    Returns:
        A new set containing only the aliases that match at least one of the
        patterns. If patterns is empty or None, returns the original set of
        aliases unmodified.

    Example:
        >>> aliases = {"Width", "Height", "Length"}
        >>> _filter_aliases(aliases, "W*,L*")
        {'Width', 'Length'}
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


def _handle_get_properties(args: argparse.Namespace, file_paths: list[Path]) -> int:
    """Handle the get-properties command by extracting and outputting FreeCAD document properties.

    For each valid FreeCAD document, this function:
    1. Creates a PropertiesOutputter instance
    2. Applies any requested property filters
    3. Outputs the properties in the specified format (text, JSON, or CSV)

    Args:
        args: Command line arguments containing:
            - filter: Optional glob patterns to filter properties
            - format: Output format (text, json, or csv)
            - output: Optional output file path
        file_paths: List of valid FreeCAD document paths to process

    Returns:
        0 if at least one file was processed successfully
        1 if no files were processed successfully or if errors occurred

    Note:
        Errors during processing of individual files are logged but don't
        immediately stop execution - the function attempts to process all files.
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


def _handle_get_aliases(args: argparse.Namespace, files: list[Path]) -> int:
    """Handle the get-aliases command by extracting and outputting spreadsheet cell aliases.

    For each valid FreeCAD document, this function:
    1. Extracts all spreadsheet cell aliases
    2. Optionally filters aliases using glob patterns
    3. Outputs the aliases in the specified format (text, JSON, or CSV)

    Args:
        args: Command line arguments containing:
            - filter: Optional glob patterns to filter aliases
            - format: Output format (text, json, or csv)
            - output: Optional output file path
        files: List of valid FreeCAD document paths to process

    Returns:
        0 if at least one file was processed successfully
        1 if no files were processed successfully or if errors occurred

    Note:
        Errors during processing of individual files are logged but don't
        immediately stop execution - the function attempts to process all files.

    Example output formats:
        text: One alias per line
        json: ["alias1", "alias2", ...]
        csv: alias,\nalias1,\nalias2,\n...
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


def _handle_get_references(args: argparse.Namespace, file_paths: list[Path]) -> int:
    """Handle the get-references command by extracting and outputting spreadsheet references.

    This function analyzes FreeCAD documents to find references between spreadsheets,
    including cross-document references. For each valid document, it:
    1. Collects all spreadsheet cell references
    2. Optionally filters references by alias patterns
    3. Formats references by file and object or by file only
    4. Outputs the references in the specified format

    Args:
        args: Command line arguments containing:
            - filter: Optional glob patterns to filter references by alias
            - format: Output format (text, json, or csv)
            - output: Optional output file path
            - by_file: Group references by file only
            - by_object: Group references by file and object
        file_paths: List of valid FreeCAD document paths to process

    Returns:
        0 if at least one file was processed successfully
        1 if no files were processed successfully or if errors occurred

    Note:
        - If both by_file and by_object are False, references are grouped by alias
        - Cross-document references are included and show the source document
        - Errors during processing are logged but don't stop execution
    """
    try:
        collector = ReferenceCollector(file_paths)
        references = collector.collect()
        if args.filter:
            references = _filter_references_by_patterns(references, args.filter)

        outputter = ReferenceOutputter(references, collector.processed_files)
        if not references:
            outputter.no_references_message(args)
            return 1

        outputter.output(args)
        return 0

    except Exception as e:
        print(f"Error processing files: {e}", file=sys.stderr)
        outputter = ReferenceOutputter({}, set())
        outputter.no_references_message(args)
        return 1


def _valid_files(files: list[Path]) -> Iterable[Path]:
    """Filter out non-existent files and invalid FCStd files from the list.

    This function validates each file path by checking:
    1. The file exists on the filesystem
    2. The file is a valid FreeCAD document (.FCStd)

    Invalid files are logged with appropriate error messages but don't cause
    the function to raise exceptions.

    Args:
        files: List of file paths to validate. Each path should be a Path object
            pointing to a potential FreeCAD document.

    Returns:
        An iterator yielding only the valid FreeCAD document paths. The order
        of the input list is preserved for valid files.

    Example:
        >>> paths = [Path("valid.FCStd"), Path("missing.FCStd"), Path("not_fcstd.txt")]
        >>> list(_valid_files(paths))
        [Path('valid.FCStd')]
    """
    for path in files:
        if not path.exists():
            print(f"Error: File '{path.name}' not found", file=sys.stderr)
            continue
        if not path.is_file():
            print(f"Error: '{path.name}' is not a file", file=sys.stderr)
            continue
        if not is_fcstd_file(path):
            print(f"Error: File '{path.name}' is not a valid FCStd file", file=sys.stderr)
            continue
        yield path


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point for the command line interface.

    This function:
    1. Parses command line arguments
    2. Sets up logging based on verbosity and log file options
    3. Validates input files
    4. Dispatches to the appropriate command handler

    Supported commands:
    - get-properties: Extract and output document properties
    - get-aliases: Extract and output spreadsheet cell aliases
    - get-references: Extract and output spreadsheet references

    Args:
        argv: Command line arguments as a sequence of strings. If None,
            sys.argv[1:] is used.

    Returns:
        0 on successful execution of the requested command
        1 on error (invalid arguments, no valid files, command failure)
        2 on invalid command

    Example:
        >>> main(["get-aliases", "doc.FCStd", "--format", "json"])
        0  # Success
    """
    try:
        # parse command line arguments
        argv = argv or sys.argv[1:]
        args: argparse.Namespace = parse_args(argv)

        # configure logging
        setup_logging(getattr(args, "log_file", None), getattr(args, "debug", False))

        # reduce the list of files to process (arg.files) to a list of valid FCStd files
        valid_paths = list(_valid_files(args.files))
        if not valid_paths:
            print("No valid files provided", file=sys.stderr)
            return 1

        # dispatch to the appropriate handler based on the command
        dispatch_table = {
            "references": _handle_get_references,
            "properties": _handle_get_properties,
            "aliases": _handle_get_aliases,
        }
        handler = dispatch_table.get(args.command)
        if handler is None:
            print(f"Unknown command: {args.command}", file=sys.stderr)
            return 1
        return handler(args, valid_paths)
    except Exception as e:
        logger.error("Error: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
