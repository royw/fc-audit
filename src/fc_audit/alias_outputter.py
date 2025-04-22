"""Module for handling alias output formatting."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from typing import Any


class AliasOutputter:
    """Class for handling alias output formatting."""

    def __init__(self, aliases: set[str]) -> None:
        """Initialize AliasOutputter.

        Args:
            aliases: Set of aliases
        """
        self.aliases = aliases

    def output_json(self) -> None:
        """Output aliases in JSON format."""
        output: dict[str, Any] = {
            "aliases": sorted(self.aliases),
        }
        print(json.dumps(output, indent=2))

    def output_text(self) -> None:
        """Output aliases in text format."""
        print("\nAliases:")
        for alias in sorted(self.aliases):
            print(f"  {alias}")

    def output_csv(self) -> None:
        """Output aliases in CSV format."""
        writer = csv.writer(sys.stdout)
        writer.writerow(["Alias"])
        for alias in sorted(self.aliases):
            writer.writerow([alias])

    def output(self, args: argparse.Namespace) -> None:
        """Output aliases in the specified format based on command line arguments.

        Args:
            args: Command line arguments namespace
        """
        if args.json:
            self.output_json()
        elif args.csv:
            self.output_csv()
        else:
            self.output_text()
