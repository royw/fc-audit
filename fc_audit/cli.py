"""Command line interface for fc-audit."""
import argparse
import fnmatch
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from loguru import logger

from .fcstd import (
    get_properties_from_files,
    get_cell_aliases_from_files,
    get_references,
    get_references_from_files,
    Reference
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


def parse_args(args=None) -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed command line arguments
    """
    parser = argparse.ArgumentParser(description='FreeCAD document analysis tool')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--log-file',
                       help='Path to log file')
    
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # get-properties command
    get_props = subparsers.add_parser('get-properties', 
                                     help='Extract unique property names from FreeCAD documents')
    get_props.add_argument('files', nargs='+', type=str,
                          help='One or more FCStd files to analyze')
    
    # get-aliases command
    get_aliases = subparsers.add_parser('get-aliases',
                                       help='Extract cell aliases from FreeCAD documents')
    get_aliases.add_argument('files', nargs='+', type=str,
                            help='One or more FCStd files to analyze')
    
    # get-expressions command
    get_exprs = subparsers.add_parser('get-expressions',
                                     help='Extract expressions from FreeCAD documents')
    get_exprs.add_argument('files', nargs='+', type=str,
                          help='One or more FCStd files to analyze')
    
    # get-references command
    get_refs = subparsers.add_parser('get-references',
                                    help='Extract alias references from FreeCAD documents')
    get_refs.add_argument('files', nargs='+', type=str,
                         help='One or more FCStd files to analyze')
    get_refs.add_argument('--aliases', type=str,
                         help='Comma-separated list of aliases to show (default: show all)')
    
    # Output format group
    format_group = get_refs.add_mutually_exclusive_group()
    format_group.add_argument('--by-alias', action='store_true', default=True,
                            help='Group output by alias (default)')
    format_group.add_argument('--by-object', action='store_true',
                            help='Group output by file and object')
    format_group.add_argument('--by-file', action='store_true',
                            help='Group output by file and alias')
    format_group.add_argument('--json', action='store_true',
                            help='Output in JSON format')
    
    return parser.parse_args(args)


def format_by_object(references: Dict[str, List[Reference]]) -> Dict[str, Dict[str, Dict[str, List[Reference]]]]:
    """Format references grouped by object."""
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


def format_by_file(references: Dict[str, List[Reference]]) -> Dict[str, Dict[str, List[Reference]]]:
    """Format references grouped by file."""
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


def filter_references_by_patterns(references: Dict[str, List[Reference]], patterns: List[str]) -> Dict[str, List[Reference]]:
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
        json_data[alias] = [{
            'filename': ref.filename,
            'object_name': ref.object_name,
            'expression': ref.expression,
            'spreadsheet': ref.spreadsheet,
            'alias': ref.alias
        } for ref in refs]
    return json.dumps(json_data, indent=2)


def print_references_by_object(references: Dict[str, List[Reference]]) -> None:
    """Print references grouped by object name.
    
    Args:
        references: Dictionary of references grouped by alias name
    """
    if not references:
        print("No alias references found")
        return

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
    """Print references grouped by file.
    
    Args:
        references: Dictionary of references to print
    """
    if not references:
        print("No alias references found")
        return

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
        references: Dictionary of references grouped by alias name
    """
    if not references:
        print("No alias references found")
        return

    for alias, refs in sorted(references.items()):
        print(f"Alias: {alias}")
        for ref in refs:
            print(f"  File: {ref.filename}")
            print(f"  Object: {ref.object_name}")
            print(f"  Expression: {ref.expression}")
            print()


def handle_get_properties(files: List[Path]) -> None:
    """Handle get-properties command.
    
    Args:
        files: List of files to process
    """
    properties = get_properties_from_files(files)
    if not properties:
        print("\nNo properties found\n")
        return
    print("\nProperties found:\n")
    for prop in sorted(properties):
        print(f"  {prop}")


def handle_get_aliases(files: List[Path]) -> None:
    """Handle get-aliases command.
    
    Args:
        files: List of files to process
    """
    aliases = get_cell_aliases_from_files(files)
    if not aliases:
        print("\nNo cell aliases found\n")
        return
    print("\nCell aliases found:\n")
    for alias in sorted(aliases):
        print(f"  {alias}")


def handle_get_references(args: argparse.Namespace, file_paths: List[Path]) -> int:
    """Handle get-references and get-expressions commands.
    
    Args:
        args: Command line arguments
        file_paths: List of files to process
        
    Returns:
        Exit code (0 for success)
    """
    try:
        references = get_references_from_files(file_paths)

        if args.aliases:
            patterns = [p.strip() for p in args.aliases.split(',')]
            references = filter_references_by_patterns(references, patterns)

        if not references:
            if args.json:
                print(convert_references_to_json({}))
            else:
                print("No alias references found")
            return 0

        if args.json:
            print(convert_references_to_json(references))
            return 0

        print("\nAlias references found:\n")
        if args.by_object:
            print_references_by_object(references)
        elif args.by_file:
            print_references_by_file(references)
        else:  # by_alias is default
            print_references_by_alias(references)

        return 0
    except Exception as e:
        logger.error(f"Error in handle_get_references: {e}")
        return 1


def main(args=None) -> int:
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
        
        if parsed_args.command == 'get-properties':
            handle_get_properties(file_paths)
        elif parsed_args.command == 'get-aliases':
            handle_get_aliases(file_paths)
        elif parsed_args.command in ['get-references', 'get-expressions']:
            return handle_get_references(parsed_args, file_paths)
        
        return 0
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
