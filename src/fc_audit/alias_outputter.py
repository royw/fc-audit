"""Module for handling alias output formatting in various formats.

This module provides functionality to output FreeCAD spreadsheet cell aliases
in different formats:

- Text: Simple line-by-line output (default)
- JSON: Structured output for programmatic use
- CSV: Tabular output for spreadsheet analysis

The output format is determined by command-line arguments and handles sorting
and proper formatting of alias names.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from typing import Any


class AliasOutputter:
    """Class for handling alias output formatting.

    This class takes a set of aliases from FreeCAD spreadsheets and provides
    methods to output them in different formats. All output methods sort the
    aliases alphabetically for consistent presentation.

    The primary interface is the output(args) method, which uses command-line
    arguments to determine the output format.

    Supported output formats:
    - Text (default): One alias per line
    - JSON (--json): Array of aliases in a JSON object
    - CSV (--csv): Single column with header

    Example:
        ```python
        aliases = {"Width", "Height", "Length"}
        outputter = AliasOutputter(aliases)
        outputter.output(args)  # Format determined by args
        ```
    """

    def __init__(self, aliases: set[str]) -> None:
        """Initialize AliasOutputter.

        Args:
            aliases: Set of unique alias names from FreeCAD spreadsheets.
                    These names are case-sensitive and typically represent
                    named cells that can be referenced in expressions.
        """
        self.aliases = aliases

    def _output_json(self) -> None:
        """Output aliases in JSON format.

        Produces a JSON object with an 'aliases' key containing a sorted array
        of all alias names. The output is pretty-printed with 2-space indentation
        for readability.

        Example output:
            {
              "aliases": [
                "Height",
                "Length",
                "Width"
              ]
            }
        """
        output: dict[str, Any] = {
            "aliases": sorted(self.aliases),
        }
        print(json.dumps(output, indent=2))

    def _output_text(self) -> None:
        """Output aliases in text format.

        Outputs each alias on a separate line in alphabetical order.
        This is the simplest and most readable format for humans.

        Example output:
            Height
            Length
            Width
        """
        for alias in sorted(self.aliases):
            print(alias)

    def _output_csv(self) -> None:
        """Output aliases in CSV format.

        Outputs aliases in a single-column CSV format with a header row.
        Useful for importing into spreadsheet applications or data analysis tools.

        Example output:
            Alias
            Height
            Length
            Width
        """
        writer = csv.writer(sys.stdout)
        writer.writerow(["Alias"])
        for alias in sorted(self.aliases):
            writer.writerow([alias])

    def output(self, args: argparse.Namespace) -> None:
        """Output aliases in the specified format based on command line arguments.

        Selects the appropriate output format based on the command line arguments.
        If no specific format is specified, defaults to text output.

        Args:
            args: Command line arguments namespace containing format flags:
                 - args.json: Output in JSON format
                 - args.csv: Output in CSV format
                 - (default): Output in text format
        """
        if args.json:
            self._output_json()
        elif args.csv:
            self._output_csv()
        else:
            self._output_text()
