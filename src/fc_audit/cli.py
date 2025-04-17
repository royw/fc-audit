"""Command line interface for fc-audit."""

import argparse
import fnmatch
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from loguru import logger  # type: ignore

from .fcstd import (
    get_properties_from_files,
    get_cell_aliases_from_files,
    get_references_from_files,
    Reference,
)


def setup_logging(log_file: Optional[str] = None, verbose: bool = False) -> None:
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
        logger.add(log_file, rotation="10 MB")


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed command line arguments
    """
    parser = argparse.ArgumentParser(description="FreeCAD document analysis tool")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument("--log-file", help="Path to log file")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # get-properties command
    get_props = subparsers.add_parser(
        "get-properties", help="Extract unique property names from FreeCAD documents"
    )
    get_props.add_argument(
        "files", nargs="+", type=str, help="One or more FCStd files to analyze"
    )

    # get-aliases command
    get_aliases = subparsers.add_parser(
        "get-aliases", help="Extract cell aliases from FreeCAD documents"
    )
    get_aliases.add_argument(
        "files", nargs="+", type=str, help="One or more FCStd files to analyze"
    )

    # get-expressions command
    get_exprs = subparsers.add_parser(
        "get-expressions", help="Extract expressions from FreeCAD documents"
    )
    get_exprs.add_argument(
        "files", nargs="+", type=str, help="One or more FCStd files to analyze"
    )

    # get-references command
    get_refs = subparsers.add_parser(
        "get-references", help="Extract alias references from FreeCAD documents"
    )
    get_refs.add_argument(
        "files", nargs="+", type=str, help="One or more FCStd files to analyze"
    )
    get_refs.add_argument(
        "--aliases",
        type=str,
        help="Comma-separated list of aliases to show (default: show all)",
    )

    # Output format group
    format_group = get_refs.add_mutually_exclusive_group()
    format_group.add_argument(
        "--by-alias",
        action="store_true",
        default=True,
        help="Group output by alias (default)",
    )
    format_group.add_argument(
        "--by-object", action="store_true", help="Group output by file and object"
    )
    format_group.add_argument(
        "--by-file", action="store_true", help="Group output by file and alias"
    )
    format_group.add_argument(
        "--json", action="store_true", help="Output in JSON format"
    )

    return parser.parse_args(args)


def format_by_object(
    references: Dict[str, List[Reference]],
) -> Dict[str, Dict[str, Dict[str, List[Reference]]]]:
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
    by_file_obj: Dict[str, Dict[str, Dict[str, List[Reference]]]] = {}
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
    references: Dict[str, List[Reference]],
) -> Dict[str, Dict[str, List[Reference]]]:
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
    by_file: Dict[str, Dict[str, List[Reference]]] = {}
    for alias, refs in references.items():
        for ref in refs:
            if ref.filename is not None:
                if ref.filename not in by_file:
                    by_file[ref.filename] = {}
                if alias not in by_file[ref.filename]:
                    by_file[ref.filename][alias] = []
                by_file[ref.filename][alias].append(ref)
    return by_file


def filter_references_by_patterns(
    references: Dict[str, List[Reference]], patterns: List[str]
) -> Dict[str, List[Reference]]:
    """Filter references by alias patterns.

    Args:
        references: Dictionary of references to filter
        patterns: List of glob patterns to match against alias names

    Returns:
        Filtered dictionary of references
    """
    # If no patterns or empty pattern, return all references
    if not patterns or not any(patterns):
        return references

    filtered_refs = {}
    for alias in references.keys():
        for pattern in patterns:
            if pattern and fnmatch.fnmatch(alias, pattern):
                filtered_refs[alias] = references[alias]
                break
    return filtered_refs


def convert_references_to_json(references: Dict[str, List[Reference]]) -> str:
    """Convert references to JSON format.

    Args:
        references: Dictionary of references to convert

    Returns:
        JSON string representation of references
    """
    if not references:
        return json.dumps({"message": "No alias references found"}, indent=2)

    json_data = {}
    for alias, refs in references.items():
        json_data[alias] = [
            {
                "filename": ref.filename,
                "object_name": ref.object_name,
                "expression": ref.expression,
                "spreadsheet": ref.spreadsheet,
                "alias": ref.alias,
            }
            for ref in refs
        ]
    return json.dumps(json_data, indent=2)


def print_references_by_object(references: Dict[str, List[Reference]]) -> None:
    """Print references grouped by object name.

    Args:
        references: Dictionary mapping alias names to lists of references

    Output format:
        Object: <object_name>
          File: <filename>
          Alias: <alias_name>
          Expression: <expression>

    If references is empty, prints "No alias references found".
    """
    if not references:
        print("No alias references found")
        return

    print("Alias references found:")

    # Reorganize references by object name
    by_object: Dict[str, List[Reference]] = {}
    for refs in references.values():
        for ref in refs:
            if ref.object_name not in by_object:
                by_object[ref.object_name] = []
            by_object[ref.object_name].append(ref)

    # Print references grouped by object
    for obj_name, refs in sorted(by_object.items()):
        print(f"Object: {obj_name}")
        for ref in refs:
            print(f"  File: {ref.filename}")
            print(f"  Alias: {ref.alias}")
            print(f"  Expression: {ref.expression}")
            print()


def print_references_by_file(references: Dict[str, List[Reference]]) -> None:
    """Print references grouped by file and alias.

    Args:
        references: Dictionary mapping alias names to lists of references

    Output format:
        File: <filename>
          Alias: <alias_name>
            Object: <object_name>
            Expression: <expression>

    If references is empty, prints "No alias references found".
    """
    if not references:
        print("No alias references found")
        return

    print("Alias references found:")

    by_file = format_by_file(references)

    for filename in sorted(by_file.keys()):
        print(f"File: {filename}")
        for alias in sorted(by_file[filename].keys()):
            print(f"  Alias: {alias}")
            for ref in by_file[filename][alias]:
                print(f"    Object: {ref.object_name}")
                print(f"      Expression: {ref.expression}")


def print_references_by_alias(references: Dict[str, List[Reference]]) -> None:
    """Print references grouped by alias name.

    Args:
        references: Dictionary mapping alias names to lists of references

    Output format:
        Alias: <alias_name>
          File: <filename>
          Object: <object_name>
          Expression: <expression>

    If references is empty, prints "No alias references found".
    """
    if not references:
        print("No alias references found")
        return

    print("Alias references found:")

    for alias, refs in sorted(references.items()):
        print(f"Alias: {alias}")
        for ref in refs:
            print(f"  File: {ref.filename}")
            print(f"  Object: {ref.object_name}")
            print(f"  Expression: {ref.expression}")
            print()


def handle_get_properties(files: List[Path]) -> int:
    """Handle get-properties command.

    Args:
        files: List of FCStd files to process

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        properties = get_properties_from_files(files)
        if not properties:
            print("\nNo properties found\n")
            return 1
        print("\nProperties found:\n")
        for prop in sorted(properties):
            print(f"  {prop}")
        return 0
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"Error: {e}")
        return 1


def handle_get_aliases(files: List[Path]) -> int:
    """Handle get-aliases command.

    Args:
        files: List of FCStd files to process

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        aliases = get_cell_aliases_from_files(files)
        if not aliases:
            print("\nNo cell aliases found\n")
            return 1
        print("\nCell aliases found:\n")
        for alias in sorted(aliases):
            print(f"  {alias}")
        return 0
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"Error: {e}")
        return 1


def process_references(
    file_paths: List[Path], aliases: Optional[str] = None
) -> Tuple[Dict[str, List[Reference]], Set[str]]:
    """Process files and get references.

    Args:
        file_paths: List of files to process
        aliases: Optional comma-separated list of alias patterns

    Returns:
        Tuple of (references dict, set of processed file names)
    """
    # Get references
    references: Dict[str, List[Reference]] = {}
    processed_files: Set[str] = set()

    try:
        references = get_references_from_files(file_paths)
        if aliases:
            patterns = [p.strip() for p in aliases.split(",")]
            references = filter_references_by_patterns(references, patterns)

        # Add all files that have references
        for refs in references.values():
            for ref in refs:
                if ref.filename:
                    processed_files.add(str(ref.filename))
    except Exception as e:
        logger.error(f"Error processing files: {e}")
        raise

    # Add empty files
    for file_path in file_paths:
        processed_files.add(str(file_path.name))
    return references, processed_files


def print_empty_files(
    processed_files: Set[str], references: Dict[str, List[Reference]]
) -> None:
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
    # Get files that have references
    files_with_refs = {
        ref.filename
        for refs in references.values()
        for ref in refs
        if ref.filename is not None
    }
    empty_files = [f for f in processed_files if f not in files_with_refs]
    if empty_files:
        print("\nEmpty files:")
        for file in sorted(empty_files):
            print(f"  {file}")


def print_references(
    references: Dict[str, List[Reference]], output_format: str
) -> None:
    """Print references in the specified format.

    Args:
        references: Dictionary of references to print
        output_format: One of 'json', 'by_object', 'by_file', or 'by_alias'
    """
    if output_format == "json":
        print(convert_references_to_json(references))
        return

    print("\nAlias references found:\n")
    if output_format == "by_object":
        print_references_by_object(references)
    elif output_format == "by_file":
        print_references_by_file(references)
    else:  # by_alias is default
        print_references_by_alias(references)


def handle_get_references(args: argparse.Namespace, file_paths: List[Path]) -> int:
    """Handle get-references and get-expressions commands.

    Args:
        args: Command line arguments
        file_paths: List of files to process

    Returns:
        Exit code (0 for success)
    """
    try:
        references, processed_files = process_references(file_paths, args.aliases)

        if not references:
            if args.json:
                print(json.dumps({"message": "No alias references found"}))
            else:
                print("No alias references found")
                print("\nProcessed files:")
                for file in sorted(processed_files):
                    print(f"  {file}")
            return 0

        # Determine output format
        output_format = (
            "json"
            if args.json
            else (
                "by_object"
                if args.by_object
                else ("by_file" if args.by_file else "by_alias")
            )
        )
        print_references(references, output_format)

        if not args.json:
            print_empty_files(processed_files, references)

        return 0
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"Error: {e}")
        return 1


def main(args: list[str] | None = None) -> int:
    """Main entry point for the application.

    Args:
        args: Optional list of command line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        parsed_args = parse_args(args)
        setup_logging(parsed_args.log_file, parsed_args.verbose)

        logger.info("Starting fc-audit")

        # Convert file paths to Path objects
        file_paths = [Path(f) for f in parsed_args.files]

        if parsed_args.command == "get-properties":
            handle_get_properties(file_paths)
        elif parsed_args.command == "get-aliases":
            handle_get_aliases(file_paths)
        elif parsed_args.command in ["get-references", "get-expressions"]:
            return handle_get_references(parsed_args, file_paths)
        else:
            logger.error(f"Unknown command: {parsed_args.command}")
            return 1
        return 0
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
