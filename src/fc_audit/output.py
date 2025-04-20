"""Module for formatting and outputting references."""

from __future__ import annotations

import fnmatch
import json
from collections.abc import Sequence

from .reference_collector import Reference


class ReferenceOutputter:
    """Formats and outputs references in different formats."""

    def __init__(self, references: dict[str, list[Reference]], processed_files: set[str]) -> None:
        """Initialize the outputter.

        Args:
            references: Dictionary mapping alias names to lists of references
            processed_files: Set of all processed file names
        """
        self.references: dict[str, list[Reference]] = references
        self.processed_files: set[str] = processed_files

    def filter_by_patterns(self, patterns: Sequence[str]) -> None:
        """Filter references by alias patterns.

        Args:
            patterns: List of glob patterns to match against alias names
        """
        if not patterns or not any(patterns):
            return

        filtered_refs: dict[str, list[Reference]] = {}
        alias: str
        refs: list[Reference]
        for alias, refs in self.references.items():
            pattern: str
            for pattern in patterns:
                if pattern and fnmatch.fnmatch(alias, pattern):
                    filtered_refs[alias] = refs
                    break
        self.references = filtered_refs

    def format_by_object(self) -> dict[str, dict[str, dict[str, list[Reference]]]]:
        """Format references grouped by file and object.

        Returns:
            Dictionary with structure:
            {
                filename: {
                    object_name: {
                        alias: [references]
                    }
                }
            }
        """
        if not self.references:
            return {}

        by_file_obj: dict[str, dict[str, dict[str, list[Reference]]]] = {}
        alias: str
        refs: list[Reference]
        ref: Reference
        for alias, refs in self.references.items():
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

    def format_by_file(self) -> dict[str, dict[str, list[Reference]]]:
        """Format references grouped by file and alias.

        Returns:
            Dictionary with structure:
            {
                filename: {
                    alias: [references]
                }
            }
        """
        if not self.references:
            return {}

        by_file: dict[str, dict[str, list[Reference]]] = {}
        alias: str
        refs: list[Reference]
        ref: Reference
        for alias, refs in self.references.items():
            for ref in refs:
                if ref.filename is not None:
                    if ref.filename not in by_file:
                        by_file[ref.filename] = {}
                    if alias not in by_file[ref.filename]:
                        by_file[ref.filename][alias] = []
                    by_file[ref.filename][alias].append(ref)
        return by_file

    def to_json(self) -> str:
        """Convert references to JSON format.

        Returns:
            JSON string representation of the references
        """
        if not self.references:
            return json.dumps({"message": "No alias references found"})

        # Convert references to serializable format
        json_refs: dict[str, list[dict[str, str | None]]] = {}
        alias: str
        refs: list[Reference]
        ref: Reference
        for alias, refs in self.references.items():
            json_refs[alias] = []
            for ref in refs:
                json_refs[alias].append(
                    {
                        "filename": ref.filename,
                        "object_name": ref.object_name,
                        "expression": ref.expression,
                        "spreadsheet": ref.spreadsheet,
                    }
                )
        return json.dumps(json_refs, indent=2)

    def print_by_object(self) -> None:
        """Print references grouped by object name."""
        if not self.references:
            print("No alias references found")
            return

        by_file_obj = self.format_by_object()
        for filename in sorted(by_file_obj):
            for obj_name in sorted(by_file_obj[filename]):
                print(f"\nObject: {obj_name}")
                print(f"  File: {filename}")
                alias: str
                refs: list[Reference]
                ref: Reference
                for alias in sorted(by_file_obj[filename][obj_name]):
                    refs = by_file_obj[filename][obj_name][alias]
                    for ref in refs:
                        print(f"  Alias: {alias}")
                        print(f"  Expression: {ref.expression}")

    def print_by_file(self) -> None:
        """Print references grouped by file and alias."""
        if not self.references:
            print("No alias references found")
            return

        by_file = self.format_by_file()
        for filename in sorted(by_file):
            print(f"\nFile: {filename}")
            alias: str
            ref: Reference
            for alias in sorted(by_file[filename]):
                print(f"  Alias: {alias}")
                for ref in by_file[filename][alias]:
                    print(f"    Object: {ref.object_name}")
                    print(f"    Expression: {ref.expression}")

    def print_by_alias(self) -> None:
        """Print references grouped by alias name."""
        if not self.references:
            print("No alias references found")
            return

        alias: str
        ref: Reference
        for alias in sorted(self.references):
            print(f"\nAlias: {alias}")
            for ref in sorted(self.references[alias], key=lambda r: (r.filename or "", r.object_name)):
                print(f"  File: {ref.filename}")
                print(f"  Object: {ref.object_name}")
                print(f"  Expression: {ref.expression}")

    def print_empty_files(self) -> None:
        """Print list of files that have no references."""
        # Get set of files that have references
        files_with_refs: set[str] = set()
        for refs in self.references.values():
            for ref in refs:
                if ref.filename:
                    files_with_refs.add(ref.filename)

        # Find files that were processed but have no references
        empty_files: set[str] = self.processed_files - files_with_refs
        if empty_files:
            print("\nFiles with no references:")
            for filename in sorted(empty_files):
                print(f"  {filename}")
