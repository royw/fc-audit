"""Module for handling FreeCAD document files."""

from __future__ import annotations

import html
import logging
import re
import zipfile
from pathlib import Path
from re import Match
from typing import Any

from lxml import etree
from lxml.etree import _Element

from .exceptions import (
    ExpressionError,
    InvalidFileError,
    ReferenceError,
    XMLParseError,
)
from .reference import Reference

logger = logging.getLogger(__name__)
""" Logger for this module """


def _extract_property_value(prop_elem: _Element) -> tuple[str, str] | None:
    """Extract property name and value from a Property element.

    Args:
        prop_elem: Property element from XML containing a 'name' attribute

    Returns:
        Tuple of (property_name, property_value) if successful, None if invalid
    """
    try:
        name = str(prop_elem.attrib["name"])
        string_elem = prop_elem.find("String")
        value = str(string_elem.text) if string_elem is not None and string_elem.text is not None else ""
        return name, value
    except (KeyError, AttributeError):
        return None


def _find_parent_object_name(elem: _Element) -> str:
    """Find the name of the parent Object element.

    Args:
        elem: XML element to start searching from

    Returns:
        Object name if found, 'unknown' otherwise
    """
    parent = elem.getparent()
    while parent is not None:
        if parent.tag == "Object":
            return str(parent.attrib.get("name", "unknown"))
        parent = parent.getparent()
    return "unknown"


def _collect_properties_from_xml(root: _Element) -> dict[str, list[tuple[str, str]]]:
    """Collect properties and their contexts from an XML document.

    Args:
        root: Root element of the XML document

    Returns:
        Dictionary mapping property names to lists of (object_name, value) tuples.
        Each property can appear multiple times if it exists in different objects.
    """
    properties: dict[str, list[tuple[str, str]]] = {}

    # Process each Property element
    for prop in root.findall(".//Property[@name]"):
        # Extract property name and value
        prop_info = _extract_property_value(prop)
        if prop_info is None:
            continue

        name, value = prop_info
        obj_name = _find_parent_object_name(prop)

        # Add to results
        if name not in properties:
            properties[name] = []
        properties[name].append((obj_name, value))

    return properties


def get_document_properties_with_context(filepath: Path) -> dict[str, list[tuple[str, str]]]:
    """Extract properties with their object context from a FreeCAD document.

    Args:
        filepath: Path to FCStd file

    Returns:
        Dictionary mapping property names to lists of (object_name, value) tuples.
        Each property can appear multiple times if it exists in different objects.
        Example:
            {
                'Length': [('Box', '10mm'), ('Cylinder', '20mm')],
                'Width': [('Box', '5mm')]
            }

    Raises:
        XMLParseError: If XML parsing fails or document structure is invalid
    """
    try:
        content = _read_xml_content(filepath)
        root = _parse_xml_content(content)
    except XMLParseError:
        raise
    except Exception as err:
        error_msg = f"Failed to read document: {err}"
        logger.error(error_msg)
        raise XMLParseError(error_msg) from err

    return _collect_properties_from_xml(root)


def _extract_cell_alias(cell: _Element) -> str | None:
    """Extract alias from a Cell element if it exists and is non-empty.

    Args:
        cell: Cell element from XML that may have an alias attribute

    Returns:
        The alias if it exists and is non-empty, None otherwise
    """
    try:
        alias = str(cell.attrib["alias"])
        return alias if alias else None
    except KeyError:
        return None


def _collect_cell_aliases(root: _Element) -> set[str]:
    """Collect all non-empty aliases from Cell elements in the document.

    Args:
        root: Root element of the XML document

    Returns:
        Set of unique cell aliases
    """
    aliases: set[str] = set()
    for cell in root.findall(".//Cell[@alias]"):
        alias = _extract_cell_alias(cell)
        if alias:
            aliases.add(alias)
    return aliases


def get_cell_aliases(filepath: Path) -> set[str]:
    """Extract unique cell aliases from a FreeCAD document.

    This function:
    1. Reads the XML content from the FCStd file
    2. Parses the XML into a tree structure
    3. Finds all Cell elements with non-empty aliases
    4. Returns a set of unique aliases

    Args:
        filepath: Path to FCStd file

    Returns:
        Set of unique cell aliases found in the document

    Raises:
        XMLParseError: If XML parsing fails
    """
    try:
        content: str = _read_xml_content(filepath)
        root: _Element = _parse_xml_content(content)
        return _collect_cell_aliases(root)

    except XMLParseError as e:
        logger.error(str(e))
        raise
    except Exception as e:
        error_msg = f"Failed to parse cell aliases: {e}"
        logger.error(error_msg)
        raise XMLParseError(error_msg) from e


def _validate_xml_content(content: str, filepath: Path) -> None:
    """Validate that the content is a valid XML document.

    Args:
        content: String content to validate
        filepath: Path to the source file (for error messages)

    Raises:
        XMLParseError: If content is not valid XML
    """
    error_msg = f"Invalid XML content in {filepath}"
    if not content.strip().startswith("<?xml"):
        raise XMLParseError(error_msg)


def _read_xml_content(filepath: Path) -> str:
    """Read XML content from a FCStd file.

    This function:
    1. Opens the FCStd file as a zip archive
    2. Extracts the Document.xml file
    3. Decodes the content as UTF-8
    4. Validates that it's a valid XML document

    Args:
        filepath: Path to FCStd file

    Returns:
        XML content as string

    Raises:
        InvalidFileError: If the file cannot be read or is not a valid FCStd file
        XMLParseError: If the content is not valid XML
    """
    # Try to open the file as a zip archive
    try:
        with zipfile.ZipFile(filepath) as zf:
            # Try to read Document.xml from the archive
            try:
                content = zf.read("Document.xml").decode("utf-8")
            except KeyError as err:
                error_msg = f"Document.xml not found in {filepath}"
                raise InvalidFileError(error_msg) from err
            except UnicodeDecodeError as err:
                error_msg = f"Document.xml in {filepath} is not valid UTF-8"
                raise InvalidFileError(error_msg) from err

    except zipfile.BadZipFile as err:
        error_msg = f"Failed to read {filepath}: not a zip file"
        raise InvalidFileError(error_msg) from err
    except OSError as err:
        error_msg = f"Failed to read {filepath}: {err}"
        raise InvalidFileError(error_msg) from err

    # Validate the XML content
    _validate_xml_content(content, filepath)
    return content


def _parse_xml_content(content: str) -> _Element:
    """Parse XML content into an ElementTree.

    Args:
        content: XML content as string

    Returns:
        Root element of parsed XML tree

    Raises:
        XMLParseError: If XML parsing fails
    """
    try:
        # Remove XML declaration to avoid encoding issues with lxml
        content = re.sub(r"<\?xml[^>]+\?>", "", content)
        return etree.fromstring(content.encode("utf-8"))
    except etree.ParseError as e:
        error_msg = f"Failed to parse XML content: {e}"
        logger.error(error_msg)
        raise XMLParseError(error_msg) from e


def _extract_expression_string(expr: Any) -> str:
    """Extract expression string from various input types.

    Args:
        expr: Input expression (XML Element or string)

    Returns:
        Expression string

    Raises:
        XMLParseError: If expr is None, has invalid type, or missing required attributes
    """
    if expr is None:
        error_msg = "Expression cannot be None"
        raise XMLParseError(error_msg)

    if isinstance(expr, etree._Element):
        if "ExpressionEngine" not in expr.attrib:
            error_msg = "XML Element must have an ExpressionEngine attribute"
            raise XMLParseError(error_msg)
        return str(expr.attrib.get("ExpressionEngine", ""))
    if isinstance(expr, str):
        return expr
    error_msg = f"Invalid expression type: {type(expr)}"
    raise XMLParseError(error_msg)


def _extract_alias_from_expression(expr_str: str) -> str | None:
    """Extract alias from an expression string.

    The expression format is: [<<filename>>]#[<<spreadsheet>>].alias
    where the alias part is what we want to extract.

    Args:
        expr_str: Expression string to parse

    Returns:
        Alias if found, None otherwise
    """
    if not expr_str.strip():
        return None

    # Pattern for optional <<n>> or name followed by # then optional <<n>> or name then . then name
    pattern: str = r"<<globals>>#<<params>>\.(\s*[^\s+\-*/()]+)\s*"
    match_obj: Match[str] | None = re.search(pattern, expr_str)
    return match_obj.group(1).strip() if match_obj else None


def _parse_reference(expr: Any) -> str | None:
    """Parse a reference from an expression.

    Format: [<<filename>>]#[<<spreadsheet>>].alias

    This function:
    1. Extracts a string from the input expression (XML Element or string)
    2. Parses the string to find an alias reference
    3. Returns the alias if found

    Args:
        expr: Expression to parse, can be a string or an XML Element

    Returns:
        Alias name if found, None otherwise

    Raises:
        XMLParseError: If expr is None or not a string/XML Element
    """
    expr_str = _extract_expression_string(expr)
    return _extract_alias_from_expression(expr_str)


def _parse_expression_element(expr_elem: _Element, obj_name: str, filename: str) -> tuple[str, Reference] | None:
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
        expr_value = str(expr_elem.attrib["expression"])
        value = html.unescape(expr_value)
        alias: str | None = _parse_reference(value)
        if alias:
            ref: Reference = Reference(object_name=obj_name, expression=value, filename=filename, alias=alias)
            return alias, ref
    except KeyError:
        error_msg = f"Expression element missing 'expression' attribute in {filename}"
        logger.warning(error_msg)
    except Exception as e:
        error_msg = f"Error parsing expression in {filename}: {e}"
        logger.warning(error_msg)
    return None


def _parse_object_element(obj: _Element, filename: str) -> list[tuple[str, Reference]]:
    """Parse an Object element and extract all references from its expressions.

    Args:
        obj: Object element from XML that may contain Expression elements
        filename: Name of the FCStd file being parsed

    Returns:
        List of (alias, Reference) tuples for each valid alias reference found
        in any Expression elements within this Object. Returns an empty list
        if no valid references are found or if the Object has no name attribute.
    """
    refs: list[tuple[str, Reference]] = []
    try:
        obj_name: str = str(obj.attrib["name"])
        expr_elem: _Element
        for expr_elem in obj.findall(".//Expression[@expression]"):
            result: tuple[str, Reference] | None = _parse_expression_element(expr_elem, obj_name, filename)
            if result:
                refs.append(result)
    except KeyError:
        error_msg = f"Object element missing 'name' attribute in {filename}"
        logger.warning(error_msg)
    except Exception as e:
        error_msg = f"Error parsing object in {filename}: {e}"
        logger.warning(error_msg)
        raise ReferenceError(error_msg) from e
    return refs


def _group_references_by_alias(obj_refs: list[tuple[str, Reference]]) -> dict[str, list[Reference]]:
    """Group references by their alias names.

    Args:
        obj_refs: List of (alias, Reference) tuples

    Returns:
        Dictionary mapping alias names to lists of Reference objects
    """
    references: dict[str, list[Reference]] = {}
    alias: str
    ref: Reference
    for alias, ref in obj_refs:
        if alias not in references:
            references[alias] = []
        references[alias].append(ref)
    return references


def _parse_expression_and_create_reference(
    expr: _Element, obj_name: str, filename: str
) -> tuple[str, Reference] | None:
    """Parse an Expression element and create a Reference if it contains an alias.

    Args:
        expr: Expression element from XML
        obj_name: Name of the parent Object
        filename: Name of the file being processed

    Returns:
        Tuple of (alias, Reference) if a valid alias is found, None otherwise
    """
    try:
        expr_str = expr.attrib["expression"]
        expr_value = expr_str.decode("utf-8") if isinstance(expr_str, bytes) else str(expr_str)
        alias: str | None = _parse_reference(expr_value)
        if alias:
            ref: Reference = Reference(obj_name, expr_value, filename)
            return alias, ref
    except (KeyError, ExpressionError) as e:
        error_msg = f"Error parsing expression in {filename}: {e}"
        logger.warning(error_msg)
    return None


def _collect_object_references(root: _Element, filename: str) -> list[tuple[str, Reference]]:
    """Collect all references from Object elements in the document.

    Args:
        root: Root element of the XML document
        filename: Name of the file being processed

    Returns:
        List of (alias, Reference) tuples for all valid references
    """
    obj_refs: list[tuple[str, Reference]] = []
    for obj in root.findall(".//Object[@name]"):
        try:
            obj_name: str = str(obj.attrib["name"])
            for expr in obj.findall(".//Expression"):
                result = _parse_expression_and_create_reference(expr, obj_name, filename)
                if result:
                    obj_refs.append(result)
        except KeyError:
            error_msg = f"Object element missing 'name' attribute in {filename}"
            logger.warning(error_msg)
            continue
    return obj_refs


def _parse_document_references(content: str, filename: str) -> dict[str, list[Reference]]:
    """Parse XML content to extract all alias references from a Document.

    Args:
        content: XML content as string
        filename: Name of the file being processed

    Returns:
        Dictionary mapping alias names to lists of Reference objects

    Raises:
        XMLParseError: If XML parsing fails
    """
    try:
        root: _Element = _parse_xml_content(content)
        obj_refs = _collect_object_references(root, filename)
        return _group_references_by_alias(obj_refs)
    except XMLParseError:
        error_msg = f"Failed to parse XML content from {filename}"
        logger.error(error_msg)
        raise
    except Exception as e:
        error_msg = f"Unexpected error parsing {filename}: {e}"
        logger.error(error_msg)
        raise XMLParseError(error_msg) from e


def _merge_references(all_references: dict[str, list[Reference]], new_references: dict[str, list[Reference]]) -> None:
    """Merge new references into the existing set of references.

    Args:
        all_references: Existing dictionary of references
        new_references: New dictionary of references to merge
    """
    alias: str
    refs: list[Reference]
    for alias, refs in new_references.items():
        if alias not in all_references:
            all_references[alias] = []
        all_references[alias].extend(refs)
