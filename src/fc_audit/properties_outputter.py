"""Module for outputting FreeCAD document properties in various formats."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

from fc_audit.fcstd import get_document_properties_with_context


class PropertiesOutputter:
    """Class for outputting FreeCAD document properties in various formats."""

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

    def output_text(self) -> None:
        """Print properties in simple list format."""
        properties: set[str] = set()
        for file_props in self.file_properties.values():
            properties.update(file_props.keys())

        for prop in sorted(properties):
            print(prop)

    def output_by_file(self) -> None:
        """Print properties grouped by file."""
        for filepath in sorted(self.file_properties.keys()):
            print(f"\nFile: {filepath}")
            for prop in sorted(self.file_properties[filepath].keys()):
                print(f"  {prop}")
                for _obj_name, value in sorted(self.file_properties[filepath][prop]):
                    if value:
                        print(f"    Value: {value}")

    def output_by_object(self) -> None:
        """Print properties grouped by file and object."""
        for filepath in sorted(self.file_properties.keys()):
            print(f"\nFile: {filepath}")
            # Group properties by object
            obj_props: dict[str, dict[str, str]] = {}
            for prop, obj_values in self.file_properties[filepath].items():
                for obj_name, value in obj_values:
                    if obj_name not in obj_props:
                        obj_props[obj_name] = {}
                    obj_props[obj_name][prop] = value

            for obj_name in sorted(obj_props.keys()):
                print(f"  Object: {obj_name}")
                for prop in sorted(obj_props[obj_name].keys()):
                    value = obj_props[obj_name][prop]
                    if value:
                        print(f"    {prop}: {value}")
                    else:
                        print(f"    {prop}")

    def output_json(self) -> None:
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

    def output_csv(self) -> None:
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
        if args.json:
            self.output_json()
        elif args.csv:
            self.output_csv()
        elif args.by_file:
            self.output_by_file()
        elif args.by_object:
            self.output_by_object()
        else:
            self.output_text()
