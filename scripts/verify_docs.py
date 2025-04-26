#!/usr/bin/env python3
"""Script to verify that all public and protected functions are documented in mkdocs."""

import argparse
import ast
import fnmatch
import sys
from pathlib import Path
from typing import Optional, Set, Tuple


def get_functions_from_file(file_path: str, include_private: bool = False) -> set[str]:
    """Extract function names from a Python file.

    Args:
        file_path: Path to the Python file
        include_private: Whether to include private functions (starting with _)

    Returns:
        Set of function names
    """
    with open(file_path, 'r') as f:
        tree = ast.parse(f.read())

    functions = set()
    module_name = Path(file_path).stem
    class_methods = set()

    def add_function(name: str, is_method: bool = False) -> None:
        """Add a function to the set if it matches the privacy criteria."""
        if include_private or not name.startswith('_'):
            if is_method:
                class_methods.add(name)
            else:
                functions.add(f"fc_audit.{module_name}.{name}")

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and not node.name.startswith('__'):
            class_name = node.name
            functions.add(f"fc_audit.{module_name}.{class_name}")

            # Add class methods
            for child in node.body:
                if isinstance(child, ast.FunctionDef):
                    method_name = child.name
                    if include_private or not method_name.startswith('_'):
                        functions.add(f"fc_audit.{module_name}.{class_name}.{method_name}")
                        class_methods.add(method_name)

        # Add module-level functions that aren't class methods
        elif isinstance(node, ast.FunctionDef) and node.name not in class_methods:
            add_function(node.name)

    return functions


def get_documented_functions(
    docs_dir: str,
    doc_patterns: list[str] = ['*.md'],
    header_patterns: list[str] = ['##*', '###*']
) -> set[str]:
    """Extract documented function names from documentation files.

    Args:
        docs_dir: Path to the documentation directory
        doc_patterns: List of file patterns to match documentation files
        header_patterns: List of patterns to match documentation headers

    Returns:
        Set of documented function names
    """
    documented = set()

    def process_line(line: str) -> str | None:
        """Process a line and return the function reference if found."""
        line = line.strip()
        if line.startswith('::: fc_audit.'):
            return line.split(':::')[1].strip()
        return None

    def process_file(file_path: Path) -> None:
        """Process a markdown file and add documented functions to the set."""
        with open(file_path, 'r') as f:
            for line in f:
                func = process_line(line)
                if func:
                    documented.add(func)

    # Process all markdown files
    for pattern in doc_patterns:
        for doc_file in Path(docs_dir).rglob(pattern):
            process_file(doc_file)

    return documented


def find_source_files(
    src_dir: str,
    include_patterns: list[str] = ['*.py'],
    exclude_patterns: list[str] | None = None
) -> list[Path]:
    """Find source files to check for documentation.

    Args:
        src_dir: Path to source directory
        include_patterns: List of file patterns to include
        exclude_patterns: List of file patterns to exclude

    Returns:
        List of paths to source files
    """
    exclude_patterns = exclude_patterns or ['__*']
    return [
        file
        for pattern in include_patterns
        for file in Path(src_dir).rglob(pattern)
        if not any(fnmatch.fnmatch(file.name, ex) for ex in exclude_patterns)
    ]


def check_documentation(
    src_dir: str,
    docs_dir: str,
    include_patterns: list[str],
    exclude_patterns: list[str],
    doc_patterns: list[str],
    header_patterns: list[str],
    include_private: bool,
    quiet: bool
) -> tuple[set[str], set[str]]:
    """Check for undocumented functions.

    Args:
        src_dir: Path to source directory
        docs_dir: Path to documentation directory
        include_patterns: List of file patterns to include
        exclude_patterns: List of file patterns to exclude
        doc_patterns: List of file patterns for documentation files
        header_patterns: List of patterns for documentation headers
        include_private: Whether to check private functions
        quiet: Whether to suppress output

    Returns:
        Tuple of (undocumented function names, obsolete function names)
    """
    # Get all functions from source files
    source_files = find_source_files(src_dir, include_patterns, exclude_patterns)
    source_funcs = set()
    for file in source_files:
        source_funcs.update(get_functions_from_file(str(file), include_private))

    # Get all documented functions
    doc_files = find_source_files(docs_dir, doc_patterns)
    doc_funcs = get_documented_functions(str(docs_dir))

    # Find undocumented and obsolete functions
    undocumented = source_funcs - doc_funcs
    obsolete = doc_funcs - source_funcs

    # Report results
    if not quiet:
        if undocumented:
            print("The following functions are not documented:")
            print('\n'.join(f"  - {func}" for func in sorted(undocumented)))
        else:
            print("✓ All functions are documented!")
        if obsolete:
            print("\nObsolete function documentation:")
            for func in sorted(obsolete):
                print(f"  {func}")

    return undocumented, obsolete


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description="Check for undocumented functions in a Python project"
    )
    parser.add_argument(
        "--src", "-s",
        default="src",
        help="Source directory to check (default: src)"
    )
    parser.add_argument(
        "--docs", "-d",
        default="docs",
        help="Documentation directory to check (default: docs)"
    )
    parser.add_argument(
        "--include", "-i",
        nargs="*",
        default=["*.py"],
        help="File patterns to include (default: *.py)"
    )
    parser.add_argument(
        "--exclude", "-e",
        nargs="*",
        default=["__*"],
        help="File patterns to exclude (default: __*)"
    )
    parser.add_argument(
        "--doc-patterns",
        nargs="*",
        default=["*.md"],
        help="Documentation file patterns (default: *.md)"
    )
    parser.add_argument(
        "--header-patterns",
        nargs="*",
        default=["##*", "###*"],
        help="Header patterns in documentation (default: ##* ###*)"
    )
    parser.add_argument(
        "--include-private",
        action="store_true",
        help="Include private functions (starting with _)"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress output"
    )
    parser.add_argument(
        "--update", "-u",
        action="store_true",
        help="Update documentation files with missing functions"
    )
    return parser.parse_args()


def validate_paths(src_dir: Path, docs_dir: Path) -> None:
    """Validate that the source and documentation directories exist.

    Args:
        src_dir: Source directory path
        docs_dir: Documentation directory path

    Raises:
        SystemExit: If either directory does not exist
    """
    if not src_dir.is_dir():
        print(f"Error: Source directory '{src_dir}' does not exist", file=sys.stderr)
        sys.exit(1)
    if not docs_dir.is_dir():
        print(f"Error: Documentation directory '{docs_dir}' does not exist", file=sys.stderr)
        sys.exit(1)


def update_documentation(src_dir: Path, docs_dir: Path, undocumented: set[str], obsolete: set[str]) -> None:
    """Update documentation files with missing functions and remove obsolete ones.

    Args:
        src_dir: Source directory path
        docs_dir: Documentation directory path
        undocumented: Set of undocumented function names
        obsolete: Set of obsolete function names that should be removed
    """
    # Group functions by module
    module_funcs: dict[str, set[str]] = {}
    for func in undocumented:
        module = func.split('.')[1]  # fc_audit.module.function -> module
        if module not in module_funcs:
            module_funcs[module] = set()
        module_funcs[module].add(func)

    # Group obsolete functions by module
    module_obsolete: dict[str, set[str]] = {}
    for func in obsolete:
        module = func.split('.')[1]  # fc_audit.module.function -> module
        if module not in module_obsolete:
            module_obsolete[module] = set()
        module_obsolete[module].add(func)

    # Update documentation files
    all_modules = set(module_funcs.keys()) | set(module_obsolete.keys())
    for module in all_modules:
        doc_file = docs_dir / 'reference' / f'{module}.md'
        doc_file.parent.mkdir(parents=True, exist_ok=True)

        # Read existing content or create new file
        if doc_file.exists():
            content = doc_file.read_text()
            if not content.strip():
                content = f'---\ntitle: {module.replace("_", " ").title()}\n---\n'
        else:
            content = f'---\ntitle: {module.replace("_", " ").title()}\n---\n'

        # Remove obsolete functions
        if module in module_obsolete:
            lines = content.splitlines()
            new_lines = []
            skip_until_blank = False
            for line in lines:
                if any(f'::: {func}' in line for func in module_obsolete[module]):
                    skip_until_blank = True
                    continue
                if skip_until_blank and not line.strip():
                    skip_until_blank = False
                    continue
                if not skip_until_blank:
                    new_lines.append(line)
            content = '\n'.join(new_lines)

        # Add missing functions
        if module in module_funcs:
            for func in sorted(module_funcs[module]):
                if f'::: {func}' not in content:
                    content += f'\n::: {func}\n    options:\n        show_root_heading: true\n        show_source: true\n'

        # Write updated content only if there's actual content beyond the header
        if len(content.splitlines()) > 3:
            doc_file.write_text(content)
        else:
            # Remove empty documentation files
            doc_file.unlink(missing_ok=True)


def main() -> None:
    """Main entry point for the script."""
    args = parse_args()

    # Convert relative paths to absolute and validate
    src_dir = Path(args.src).resolve()
    docs_dir = Path(args.docs).resolve()
    validate_paths(src_dir, docs_dir)

    # Check documentation
    undocumented, obsolete = check_documentation(
        str(src_dir),
        str(docs_dir),
        args.include,
        args.exclude,
        args.doc_patterns,
        args.header_patterns,
        args.include_private,
        args.quiet
    )

    # Update documentation if requested
    if args.update and (undocumented or obsolete):
        if not args.quiet:
            print("\nUpdating documentation files...")
        update_documentation(src_dir, docs_dir, undocumented, obsolete)
        if not args.quiet:
            print("✓ Documentation updated!")

    sys.exit(1 if (undocumented or obsolete) and not args.update else 0)


if __name__ == '__main__':
    main()
