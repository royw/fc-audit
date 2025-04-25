"""Module for formatting and outputting references."""

from __future__ import annotations

import argparse
import csv
import json
import sys

from .reference import Reference


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

    def no_references_message(self, args: argparse.Namespace) -> None:
        """Print message when no references are found.

        Args:
            args: Command line arguments containing output format flags
        """
        if args.json:
            print(json.dumps({"message": "No alias references found"}))
        else:
            print("No alias references found")

    def to_json(self) -> str:
        """Convert references to JSON format.

        Returns:
            JSON string representation of the references
        """
        if not self.references:
            return json.dumps({"message": "No alias references found"})

        # Convert references to serializable format
        result: dict[str, list[dict[str, str | None]]] = {}
        alias: str
        refs: list[Reference]
        for alias, refs in self.references.items():
            result[alias] = [
                {
                    "object_name": ref.object_name,
                    "expression": ref.expression,
                    "filename": ref.filename,
                    "spreadsheet": ref.spreadsheet if ref.spreadsheet else None,
                }
                for ref in refs
            ]
        return json.dumps(result, indent=2)

    def to_csv(self) -> None:
        """Print references as comma-separated values.
        Format: alias,filename,object_name,expression
        """
        if not self.references:
            self.no_references_message(argparse.Namespace(json=False))
            return

        writer = csv.writer(sys.stdout, quoting=csv.QUOTE_ALL)
        writer.writerow(["alias", "filename", "object_name", "expression"])

        # Write data rows
        for alias in sorted(self.references):
            for ref in sorted(self.references[alias], key=lambda r: (r.filename or "", r.object_name)):
                writer.writerow([alias, ref.filename or "", ref.object_name, ref.expression])

    def print_by_object(self) -> None:
        """Print references grouped by object name."""
        if not self.references:
            self.no_references_message(argparse.Namespace(json=False))
            return

        by_file_obj = self.format_by_object()
        filename: str
        obj_name: str
        for filename in sorted(by_file_obj):
            for obj_name in sorted(by_file_obj[filename]):
                print(f"Object: {obj_name}")
                print(f"  File: {filename}")
                # Group by alias and expression
                by_alias: dict[str, set[str]] = {}
                for alias in by_file_obj[filename][obj_name]:
                    by_alias[alias] = set()
                    for ref in by_file_obj[filename][obj_name][alias]:
                        by_alias[alias].add(ref.expression)

                # Print grouped references
                for alias in sorted(by_alias):
                    print(f"    Alias: {alias}")
                    for expr in sorted(by_alias[alias]):
                        print(f"      Expression: {expr}")

    def print_by_file(self) -> None:
        """Print references grouped by file and alias."""
        if not self.references:
            self.no_references_message(argparse.Namespace(json=False))
            return

        by_file = self.format_by_file()
        for filename in sorted(by_file):
            print(f"File: {filename}")
            # Group by alias, then object, then expression
            by_alias: dict[str, dict[str, set[str]]] = {}
            for alias in by_file[filename]:
                for ref in by_file[filename][alias]:
                    if alias not in by_alias:
                        by_alias[alias] = {}
                    if ref.object_name not in by_alias[alias]:
                        by_alias[alias][ref.object_name] = set()
                    by_alias[alias][ref.object_name].add(ref.expression)

            # Print grouped references
            for alias in sorted(by_alias):
                print(f"  Alias: {alias}")
                for obj_name in sorted(by_alias[alias]):
                    print(f"    Object: {obj_name}")
                    for expr in sorted(by_alias[alias][obj_name]):
                        print(f"      Expression: {expr}")

    def print_by_alias(self) -> None:
        """Print references grouped by alias name."""
        if not self.references:
            self.no_references_message(argparse.Namespace(json=False))
            return

        alias: str
        ref: Reference
        for alias in sorted(self.references):
            print(f"Alias: {alias}")
            # Group by file, then object, then expression
            by_file: dict[str, dict[str, set[str]]] = {}
            for ref in self.references[alias]:
                filename = ref.filename or ""
                if filename not in by_file:
                    by_file[filename] = {}
                if ref.object_name not in by_file[filename]:
                    by_file[filename][ref.object_name] = set()
                by_file[filename][ref.object_name].add(ref.expression)

            # Print grouped references
            for filename in sorted(by_file):
                print(f"  File: {filename}")
                for obj_name in sorted(by_file[filename]):
                    print(f"    Object: {obj_name}")
                    for expr in sorted(by_file[filename][obj_name]):
                        print(f"      Expression: {expr}")

    def output(self, args: argparse.Namespace) -> None:
        """Output references in the specified format based on command line arguments.

        Args:
            args: Command line arguments namespace
        """
        if getattr(args, "json", False):
            print(self.to_json())
        elif getattr(args, "csv", False):
            self.to_csv()
        elif getattr(args, "by_object", False):
            self.print_by_object()
        elif getattr(args, "by_file", False):
            self.print_by_file()
        else:
            self.print_by_alias()
