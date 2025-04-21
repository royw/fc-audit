"""Module for collecting references from FreeCAD documents."""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path
from re import Match

from loguru import logger


@dataclass
class Reference:
    """A reference to a spreadsheet cell in a FreeCAD document."""

    object_name: str
    expression: str
    filename: str | None = None
    spreadsheet: str | None = None
    alias: str = ""


class ReferenceCollector:
    """Collects references from FreeCAD documents."""

    def __init__(self, file_paths: list[Path]) -> None:
        """Initialize the collector with a list of files to process.

        Args:
            file_paths: List of paths to FCStd files
        """
        self.file_paths = file_paths
        self.references: dict[str, list[Reference]] = {}
        self.processed_files: set[str] = set()

    def collect(self) -> dict[str, list[Reference]]:
        """Collect references from all files.

        Returns:
            Dictionary mapping alias names to lists of references
        """
        filepath: Path
        for filepath in self.file_paths:
            try:
                self._process_file(filepath)
            except (ValueError, ET.ParseError) as e:
                logger.error(f"Error processing {filepath}: {e}")
                continue

        return self.references

    def _process_file(self, filepath: Path) -> None:
        """Process a single FCStd file.

        Args:
            filepath: Path to FCStd file to process

        Raises:
            ValueError: If file is not a valid FCStd file
        """
        if not self._is_fcstd_file(filepath):
            error_msg = f"{filepath} is not a valid FCStd file"
            raise ValueError(error_msg)

        filename: str = filepath.name
        self.processed_files.add(filename)

        with zipfile.ZipFile(filepath) as zf, zf.open("Document.xml") as f:
            content: str = f.read().decode("utf-8")
            file_refs: dict[str, list[Reference]] = self._parse_document_references(content, filename)
            self._merge_references(file_refs)

    def _is_fcstd_file(self, filepath: Path) -> bool:
        """Check if a file is a valid FCStd file."""
        if not zipfile.is_zipfile(filepath):
            return False

        with zipfile.ZipFile(filepath) as zf:
            return "Document.xml" in zf.namelist()

    def _parse_document_references(self, content: str, filename: str) -> dict[str, list[Reference]]:
        """Parse XML content to extract all alias references from a Document."""
        try:
            root: ET.Element = ET.fromstring(content)
        except ET.ParseError as e:
            logger.error(f"Error parsing XML in {filename}: {e}")
            return {}

        refs: dict[str, list[Reference]] = {}
        obj: ET.Element
        for obj in root.findall(".//Object"):
            alias: str
            ref: Reference
            for alias, ref in self._parse_object_element(obj, filename):
                if alias not in refs:
                    refs[alias] = []
                refs[alias].append(ref)

        return refs

    def _parse_object_element(self, obj: ET.Element, filename: str) -> list[tuple[str, Reference]]:
        """Parse an Object element and extract all references from its expressions."""
        if "name" not in obj.attrib:
            return []

        obj_name: str = obj.attrib["name"]
        refs: list[tuple[str, Reference]] = []

        expr: ET.Element
        for expr in obj.findall(".//Expression[@expression]"):
            result = self._parse_expression_element(expr, obj_name, filename)
            if result:
                refs.append(result)

        return refs

    def _parse_expression_element(
        self, expr_elem: ET.Element, obj_name: str, filename: str
    ) -> tuple[str, Reference] | None:
        """Parse an Expression element and create a Reference if it contains an alias."""
        expr: str = html.unescape(expr_elem.attrib["expression"])
        alias: str | None = self._parse_reference(expr)
        if not alias:
            return None

        ref: Reference = Reference(
            object_name=obj_name,
            expression=expr,
            filename=filename,
            spreadsheet="params",  # TODO: Extract from expression
            alias=alias,
        )
        return (alias, ref)

    def _parse_reference(self, expr: str) -> str | None:
        """Parse a reference from an expression.

        Handles both formats:
        - <<globals>>#<<params>>.ALIAS
        - <<params>>.ALIAS
        """
        patterns: list[str] = [r"<<globals>>#<<params>>\.([^\s+\-*/()]+)", r"<<params>>\.([^\s+\-*/()]+)"]
        for pattern in patterns:
            match: Match[str] | None = re.search(pattern, expr)
            if match:
                return match.group(1)
        return None

    def _merge_references(self, new_refs: dict[str, list[Reference]]) -> None:
        """Merge new references into the existing references."""
        alias: str
        refs: list[Reference]
        for alias, refs in new_refs.items():
            if alias not in self.references:
                self.references[alias] = []
            self.references[alias].extend(refs)
