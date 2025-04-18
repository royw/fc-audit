"""Module for handling FreeCAD document files."""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path

from loguru import logger


def is_fcstd_file(filepath: Path) -> bool:
    """Check if a file is a valid FCStd file.

    Args:
        filepath: Path to file to check

    Returns:
        True if file is a valid FCStd file, False otherwise
    """
    logger.debug(f"Checking if {filepath} is a valid FCStd file")
    if not zipfile.is_zipfile(filepath):
        logger.debug(f"{filepath} is not a valid zip file")
        return False

    with zipfile.ZipFile(filepath) as zf:
        files = zf.namelist()
        logger.debug(f"Files in {filepath}: {files}")
        return "Document.xml" in files


def get_document_properties(filepath: Path) -> set[str]:
    """Extract unique property names from a FreeCAD document.

    Args:
        filepath: Path to FCStd file

    Returns:
        Set of unique property names found in the document

    Raises:
        ValueError: If file is not a valid FCStd file
    """
    if not is_fcstd_file(filepath):
        error_msg = f"{filepath} is not a valid FCStd file"
        raise ValueError(error_msg)

    properties = set()
    with zipfile.ZipFile(filepath) as zf, zf.open("Document.xml") as f:
        tree = ET.parse(f)
        root = tree.getroot()

        # Find all Property elements
        for prop in root.findall(".//Property"):
            if "name" in prop.attrib:
                properties.add(prop.attrib["name"])

    return properties


def get_cell_aliases(filepath: Path) -> set[str]:
    """Extract unique cell aliases from a FreeCAD document.

    Args:
        filepath: Path to FCStd file

    Returns:
        Set of unique cell aliases found in the document

    Raises:
        ValueError: If file is not a valid FCStd file
    """
    if not is_fcstd_file(filepath):
        error_msg = f"{filepath} is not a valid FCStd file"
        raise ValueError(error_msg)

    aliases = set()
    with zipfile.ZipFile(filepath) as zf, zf.open("Document.xml") as f:
        tree = ET.parse(f)
        root = tree.getroot()

        # Find all Cell elements with alias attributes
        for cell in root.findall(".//Cell[@alias]"):
            aliases.add(cell.attrib["alias"])

    return aliases


def _find_parent_with_identifier(element: ET.Element, root: ET.Element) -> tuple[ET.Element | None, str]:
    """Find the nearest ancestor with an identifying attribute and its context string.

    An identifying attribute is one of:
    - name: The name of the object or element
    - type: The type of the object or element
    - label: A human-readable label for the object

    Args:
        element: Element to find parent for
        root: Root element of the XML tree

    Returns:
        Tuple of (parent element or None, context string)
        The context string is formatted as 'Tag[identifier]' where identifier
        is the value of the first identifying attribute found (name, type, or label)
    """
    for ancestor in root.findall(".//*"):
        for child in ancestor.findall(".//*"):
            if child == element:
                # Build context string from the ancestor's attributes
                if "name" in ancestor.attrib:
                    return ancestor, f"{ancestor.tag}[{ancestor.attrib['name']}]"
                if "type" in ancestor.attrib:
                    return ancestor, f"{ancestor.tag}[{ancestor.attrib['type']}]"
                if "label" in ancestor.attrib:
                    return ancestor, f"{ancestor.tag}[{ancestor.attrib['label']}]"
                return ancestor, ancestor.tag
    return None, "unknown"


def get_expressions(filepath: Path) -> dict[str, str]:
    """Extract expressions from a FreeCAD document.

    Args:
        filepath: Path to FCStd file

    Returns:
        Dictionary mapping expression elements to their unescaped expressions

    Raises:
        ValueError: If file is not a valid FCStd file
    """
    if not is_fcstd_file(filepath):
        error_msg = f"{filepath} is not a valid FCStd file"
        raise ValueError(error_msg)

    expressions = {}
    with zipfile.ZipFile(filepath) as zf, zf.open("Document.xml") as f:
        content = f.read().decode("utf-8")
        tree = ET.fromstring(content)
        root = tree

        # Find all Expression elements with expression attributes
        for expr in root.findall(".//Expression[@expression]"):
            # Find parent context
            _, context = _find_parent_with_identifier(expr, root)

            # Unescape the expression value
            value = html.unescape(expr.attrib["expression"])

            # Create a unique key by combining context with expression count
            key = context
            base_key = key
            counter = 1
            while key in expressions:
                counter += 1
                key = f"{base_key} ({counter})"

            expressions[key] = value

    return expressions


@dataclass
class Reference:
    """A reference to a spreadsheet cell in a FreeCAD document.

    Attributes:
        object_name: Name of the object containing the reference
        expression: The full expression string containing the reference
        filename: Optional name of the file containing the reference
        spreadsheet: Optional name of the spreadsheet containing the referenced cell
        alias: The alias name of the referenced cell (empty if not found)
    """

    object_name: str
    expression: str
    filename: str | None = None
    spreadsheet: str | None = None
    alias: str = ""


def parse_reference(expr: str) -> str | None:
    """Parse a reference from an expression.

    Format: [<<filename>>]#[<<spreadsheet>>].alias

    Args:
        expr: Expression to parse

    Returns:
        Alias name if found, None otherwise
    """
    # Pattern for optional <<n>> or name followed by # then optional <<n>> or name then . then name
    pattern = r"<<globals>>#<<params>>\.([^\s+\-*/()]+)"
    match = re.search(pattern, expr)
    if match:
        # The alias is always the first group
        return match.group(1)
    return None


def _parse_expression_element(expr_elem: ET.Element, obj_name: str, filename: str) -> tuple[str, Reference] | None:
    """Parse an Expression element and create a Reference if it contains an alias.

    Args:
        expr_elem: Expression element from XML containing an 'expression' attribute
        obj_name: Name of the parent Object containing this expression
        filename: Name of the FCStd file being parsed

    Returns:
        If the expression contains a valid alias reference:
            A tuple of (alias_name, Reference)
            where Reference contains the full context of the reference
        If no valid alias reference is found:
            None
    """
    try:
        expr = html.unescape(expr_elem.attrib["expression"])
        alias = parse_reference(expr)
        if alias:
            ref = Reference(object_name=obj_name, expression=expr, filename=filename, alias=alias)
            return alias, ref
    except KeyError:
        error_msg = f"Expression element missing 'expression' attribute in {filename}"
        logger.warning(error_msg)
    except Exception as e:
        error_msg = f"Error parsing expression in {filename}: {e}"
        logger.warning(error_msg)
    return None


def _parse_object_element(obj: ET.Element, filename: str) -> list[tuple[str, Reference]]:
    """Parse an Object element and extract all references from its expressions.

    Args:
        obj: Object element from XML that may contain Expression elements
        filename: Name of the FCStd file being parsed

    Returns:
        List of (alias, Reference) tuples for each valid alias reference found
        in any Expression elements within this Object. Returns an empty list
        if no valid references are found or if the Object has no name attribute.
    """
    refs = []
    try:
        obj_name = obj.attrib["name"]
        for expr_elem in obj.findall(".//Expression[@expression]"):
            result = _parse_expression_element(expr_elem, obj_name, filename)
            if result:
                refs.append(result)
    except KeyError:
        error_msg = f"Object element missing 'name' attribute in {filename}"
        logger.warning(error_msg)
    except Exception as e:
        error_msg = f"Error parsing object in {filename}: {e}"
        logger.warning(error_msg)
    return refs


def _parse_document_references(content: str, filename: str) -> dict[str, list[Reference]]:
    """Parse XML content to extract all alias references from a Document.

    Args:
        content: XML content from Document.xml as a string
        filename: Name of the FCStd file being parsed

    Returns:
        Dictionary mapping alias names to lists of Reference objects.
        Each Reference object contains the full context of where and how
        the alias is referenced. Returns an empty dict if the content
        is not valid XML or contains no valid references.
    """
    references: dict[str, list[Reference]] = {}
    try:
        root = ET.fromstring(content)

        # Find all Cell elements with aliases in ObjectData section
        for sheet in root.findall(".//ObjectData/Object[@name='Sheet']/Cells/Cell[@alias]"):
            alias = sheet.attrib["alias"]
            if alias not in references:
                references[alias] = []

        # Find all Expression elements with expression attributes
        for obj in root.findall(".//Object[@name]"):
            for alias, ref in _parse_object_element(obj, filename):
                if alias not in references:
                    references[alias] = []
                ref.spreadsheet = "Sheet"
                references[alias].append(ref)

        if not references:
            info_msg = f"No alias references found in {filename}"
            logger.info(info_msg)
    except ET.ParseError as e:
        error_msg = f"Failed to parse XML content from {filename}: {e}"
        logger.error(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error parsing {filename}: {e}"
        logger.error(error_msg)

    return references


def get_references(filepath: Path) -> dict[str, list[Reference]]:
    """Extract alias references from a FreeCAD document.

    Args:
        filepath: Path to FCStd file

    Returns:
        Dictionary mapping alias names to list of references

    Raises:
        ValueError: If file is not a valid FCStd file
    """
    if not is_fcstd_file(filepath):
        error_msg = f"{filepath} is not a valid FCStd file"
        raise ValueError(error_msg)

    with zipfile.ZipFile(filepath) as zf, zf.open("Document.xml") as f:
        content = f.read().decode("utf-8")
        return _parse_document_references(content, str(filepath))


def get_references_from_files(filepaths: list[Path]) -> dict[str, list[Reference]]:
    """Extract alias references from multiple FreeCAD documents.

    Args:
        filepaths: List of paths to FCStd files

    Returns:
        Dictionary mapping alias names to list of references
    """
    all_references: dict[str, list[Reference]] = {}
    for filepath in filepaths:
        try:
            file_refs = get_references(filepath)
            for alias, refs in file_refs.items():
                if alias not in all_references:
                    all_references[alias] = []
                # Add filename to each reference
                for ref in refs:
                    ref.filename = filepath.name
                all_references[alias].extend(refs)
        except ValueError as e:
            error_msg = f"Error processing {filepath}: {e}"
            logger.warning(error_msg)
            continue

    return all_references


def get_cell_aliases_from_files(filepaths: list[Path]) -> set[str]:
    """Extract unique cell aliases from multiple FreeCAD documents.

    Args:
        filepaths: List of paths to FCStd files

    Returns:
        Set of unique cell aliases found across all documents
    """
    all_aliases = set()
    for filepath in filepaths:
        try:
            aliases = get_cell_aliases(filepath)
            all_aliases.update(aliases)
        except (ValueError, ET.ParseError) as e:
            logger.warning(str(e))
            continue

    return all_aliases


def get_properties_from_files(filepaths: list[Path]) -> set[str]:
    """Extract unique property names from multiple FreeCAD documents.

    Args:
        filepaths: List of paths to FCStd files

    Returns:
        Set of unique property names found across all documents
    """
    all_properties = set()
    for filepath in filepaths:
        try:
            props = get_document_properties(filepath)
            all_properties.update(props)
        except ValueError as e:
            logger.warning(str(e))
            continue

    return all_properties
