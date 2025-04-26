"""Module for outputting FreeCAD document properties in various formats."""

from __future__ import annotations

import argparse
import csv
import fnmatch
import json
import sys
from pathlib import Path
from typing import Any

from fc_audit.fcstd import get_document_properties_with_context


class PropertiesOutputter:
    """Class for outputting FreeCAD document properties in various formats.

    This class takes a list of FreeCAD files and provides methods to output
    their properties in different formats. Properties can be filtered by name
    patterns to focus on specific properties of interest.

    The primary interface is the output(args) method, which uses command-line
    arguments to determine the output format.

    Supported output formats:
    - Text (default): List of unique property names
    - JSON (--json): Detailed property information per file
    - CSV (--csv): File, object, and property columns

    Example:
        ```python
        files = [Path("part1.FCStd"), Path("part2.FCStd")]
        outputter = PropertiesOutputter(files)
        outputter.output(args)  # Format determined by args
        ```
    """

    def __init__(self, filepaths: list[Path]) -> None:
        """Initialize with list of FreeCAD document files.

        Args:
            filepaths: List of paths to FCStd files
        """
        self.filepaths = filepaths
        self.file_properties: dict[Path, dict[str, list[tuple[str, str]]]] = {}

        for filepath in filepaths:
            try:
                self.file_properties[filepath] = get_document_properties_with_context(filepath)
            except Exception as e:
                print(str(e), file=sys.stderr)

    def filter_properties(self, pattern: str) -> None:
        """Filter properties by pattern.

        Args:
            pattern: Pattern to match against property names
        """
        if not pattern:
            return

        for filepath in list(self.file_properties.keys()):
            filtered_props = {}
            for prop, values in self.file_properties[filepath].items():
                if fnmatch.fnmatch(prop, pattern):
                    filtered_props[prop] = values
            self.file_properties[filepath] = filtered_props

    def _output_text(self) -> None:
        """Print properties in simple list format."""
        properties: set[str] = set()
        for file_props in self.file_properties.values():
            properties.update(file_props.keys())

        for prop in sorted(properties):
            print(prop)

    def _output_json(self) -> None:
        """Print properties in JSON format."""
        data: list[dict[str, Any]] = []
        for filepath, props in self.file_properties.items():
            properties: list[dict[str, str]] = []
            file_data = {"file": str(filepath), "properties": properties}
            for prop, obj_values in props.items():
                for obj_name, _value in obj_values:
                    properties.append({"name": prop, "object": obj_name})
            data.append(file_data)
        print(json.dumps(data, indent=2))

    def _output_csv(self) -> None:
        """Print properties as comma-separated values."""
        writer = csv.writer(sys.stdout, quoting=csv.QUOTE_ALL)
        writer.writerow(["file", "object", "property"])
        rows = []
        for filepath, props in sorted(self.file_properties.items()):
            for prop, obj_values in sorted(props.items()):
                for obj_name, _value in sorted(obj_values):
                    rows.append([str(filepath), obj_name, prop])
        # Sort by file, then object, then property
        rows.sort(key=lambda x: (x[0], x[1], x[2]))
        writer.writerows(rows)

    def output(self, args: argparse.Namespace) -> None:
        """Output properties in the format specified by args.

        Args:
            args: Namespace containing output format flags
        """

        # Get the output format from args
        if getattr(args, "json", False):
            self._output_json()
        elif args.csv:
            self._output_csv()
        else:
            self._output_text()
