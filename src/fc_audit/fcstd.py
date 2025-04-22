"""Module for handling FreeCAD document files."""

from __future__ import annotations

import html
import logging
import re
import zipfile
from dataclasses import dataclass
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
from .reference_collector import Reference as BaseReference

logger = logging.getLogger(__name__)


def is_fcstd_file(filepath: Path) -> bool:
    """Check if a file is a valid FCStd file.

    Args:
        filepath: Path to file to check

    Returns:
        True if file is a valid FCStd file, False otherwise
    """
    try:
        if not filepath.is_file():
            logger.debug("%s is not a file", filepath)
            return False

        logger.debug("Checking if %s is a valid FCStd file", filepath)
        if not zipfile.is_zipfile(filepath):
            logger.debug("%s is not a valid zip file", filepath)
            return False

        with zipfile.ZipFile(filepath) as zf:
            files: list[str] = zf.namelist()
            debug_msg = f"Files in {filepath}: {files}"
            logger.debug(debug_msg)
            return "Document.xml" in files
    except Exception as e:
        debug_msg = f"Error checking {filepath}: {e}"
        logger.debug(debug_msg)
        return False


def get_document_properties_with_context(filepath: Path) -> dict[str, list[tuple[str, str]]]:
    """Extract properties with their object context from a FreeCAD document.

    Args:
        filepath: Path to FCStd file

    Returns:
        Dictionary mapping property names to lists of (object_name, value) tuples

    Raises:
        InvalidFileError: If file is not a valid FCStd file
        XMLParseError: If XML parsing fails
    """
    if not is_fcstd_file(filepath):
        error_msg = f"{filepath} is not a valid FCStd file"
        raise InvalidFileError(error_msg)

    try:
        content: str = _read_xml_content(filepath)
        root: _Element = _parse_xml_content(content)

        # Find all Property elements with their object context
        properties: dict[str, list[tuple[str, str]]] = {}
        for prop in root.findall(".//Property[@name]"):
            try:
                name = str(prop.attrib["name"])
                obj_elem, _ = _find_parent_with_identifier(prop, root)
                obj_name = str(obj_elem.attrib.get("name", "unknown")) if obj_elem is not None else "unknown"
                string_elem = prop.find("String")
                value = str(string_elem.text) if string_elem is not None and string_elem.text is not None else ""
                if name not in properties:
                    properties[name] = []
                properties[name].append((str(obj_name), value))
            except (KeyError, AttributeError):
                continue

        return properties

    except (InvalidFileError, XMLParseError) as e:
        logger.error(str(e))
        raise
    except Exception as e:
        error_msg = f"Failed to parse properties: {e}"
        logger.error(error_msg)
        raise XMLParseError(error_msg) from e


def get_document_properties(filepath: Path) -> set[str]:
    """Extract unique property names from a FreeCAD document.

    Args:
        filepath: Path to FCStd file

    Returns:
        Set of unique property names found in the document

    Raises:
        InvalidFileError: If file is not a valid FCStd file
        XMLParseError: If XML parsing fails
    """
    if not is_fcstd_file(filepath):
        error_msg = f"{filepath} is not a valid FCStd file"
        raise InvalidFileError(error_msg)

    try:
        content: str = _read_xml_content(filepath)
        root: _Element = _parse_xml_content(content)

        # Find all Property elements
        properties: set[str] = set()
        for prop in root.findall(".//Property[@name]"):
            try:
                properties.add(str(prop.attrib["name"]))
            except KeyError:
                continue

        return properties

    except (InvalidFileError, XMLParseError) as e:
        logger.error(str(e))
        raise
    except Exception as e:
        error_msg = f"Failed to parse properties: {e}"
        logger.error(error_msg)
        raise XMLParseError(error_msg) from e


def get_cell_aliases(filepath: Path) -> set[str]:
    """Extract unique cell aliases from a FreeCAD document.

    Args:
        filepath: Path to FCStd file

    Returns:
        Set of unique cell aliases found in the document

    Raises:
        InvalidFileError: If file is not a valid FCStd file
        XMLParseError: If XML parsing fails
    """
    if not is_fcstd_file(filepath):
        error_msg = f"{filepath} is not a valid FCStd file"
        raise InvalidFileError(error_msg)

    try:
        content: str = _read_xml_content(filepath)
        root: _Element = _parse_xml_content(content)

        # Find all Cell elements with non-empty aliases
        aliases: set[str] = set()
        for cell in root.findall(".//Cell[@alias]"):
            try:
                alias = str(cell.attrib["alias"])
                if alias:  # Skip empty aliases
                    aliases.add(alias)
            except KeyError:
                continue

        return aliases

    except (InvalidFileError, XMLParseError) as e:
        logger.error(str(e))
        raise
    except Exception as e:
        error_msg = f"Failed to parse cell aliases: {e}"
        logger.error(error_msg)
        raise XMLParseError(error_msg) from e


def _find_parent_with_identifier(element: _Element, _root: _Element) -> tuple[_Element | None, str]:
    """Find the nearest ancestor with an identifying attribute and its context string.

    Args:
        element: Element to find parent for
        root: Root element of the XML tree

    Returns:
        Tuple of (parent element, context string) or (None, "unknown")
        The context string is the name of the parent Object element
    """
    # Find the Properties element containing this property
    parent = element.getparent()
    while parent is not None:
        if parent.tag == "Properties":
            # Get the Object element that contains these Properties
            obj = parent.getparent()
            if obj is not None and obj.tag == "Object":
                return obj, obj.attrib.get("name", "unknown")
            break
        parent = parent.getparent()
    return None, "unknown"


def _read_xml_content(filepath: Path) -> str:
    """Read XML content from a FCStd file.

    Args:
        filepath: Path to FCStd file

    Returns:
        XML content as string

    Raises:
        InvalidFileError: If file cannot be read
    """
    try:
        with zipfile.ZipFile(filepath) as zf:
            try:
                with zf.open("Document.xml") as f:
                    content: str = f.read().decode("utf-8")
                    if not content.strip().startswith("<?xml"):
                        error_msg = f"Invalid XML content in {filepath}"
                        raise InvalidFileError(error_msg)
                    return content
            except (KeyError, UnicodeDecodeError) as e:
                error_msg = f"No Document.xml found in {filepath}: {e}"
                raise InvalidFileError(error_msg) from e
    except (zipfile.BadZipFile, OSError) as e:
        error_msg = f"Failed to read {filepath}: {e}"
        raise InvalidFileError(error_msg) from e


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


def _extract_expression(element: _Element | None, root: _Element) -> tuple[str, str]:
    """Extract expression from an XML element.

        Args:
            element: Element to extract expression from
            root: Root element of the XML tree
    {{ ... }}

        Returns:
            Tuple of (parent context string, expression value)

        Raises:
            ExpressionError: If element is None or has no expression attribute
    """
    if element is None:
        return "unknown", ""

    # Get the expression value
    if "ExpressionEngine" not in element.attrib:
        error_msg = "Element must have an ExpressionEngine attribute"
        raise ExpressionError(error_msg)
    value = str(element.attrib["ExpressionEngine"])

    # Find parent with identifier
    parent, context = _find_parent_with_identifier(element, root)
    if parent is None:
        error_msg = "No parent with identifier found"
        raise ExpressionError(error_msg)

    return context, value


def _make_unique_key(base_key: str, existing_keys: set[str]) -> str:
    """Create a unique key by appending a counter if needed.

    Args:
        base_key: Base key to make unique
        existing_keys: Set of existing keys

    Returns:
        Unique key
    """
    if base_key not in existing_keys:
        return base_key

    counter = 1
    while True:
        key = f"{base_key} ({counter})"
        if key not in existing_keys:
            return key
        counter += 1


def get_expressions(filepath: Path) -> dict[str, list[str]]:
    """Extract expressions from a FreeCAD document.

    Args:
        filepath: Path to FCStd file

    Returns:
        Dictionary mapping expression elements to their unescaped expressions

    Raises:
        InvalidFileError: If file is not a valid FCStd file
        XMLParseError: If XML parsing fails or nesting depth exceeds limit
    """
    if not is_fcstd_file(filepath):
        error_msg = f"{filepath} is not a valid FCStd file"
        raise InvalidFileError(error_msg)

    expressions: dict[str, list[str]] = {}
    try:
        content: str = _read_xml_content(filepath)
        root: _Element = _parse_xml_content(content)

        # Find all Property elements with ExpressionEngine attributes
        expr: _Element
        for expr in root.findall(".//Property[@ExpressionEngine]"):
            try:
                context: str
                value: str
                context, value = _extract_expression(expr, root)
                # Only include expressions that look like references
                if context != "unknown" and "<<globals>>#<<params>>" in value:
                    if context not in expressions:
                        expressions[context] = []
                    expressions[context].append(value)
            except ExpressionError as e:
                error_msg = f"Error parsing expression in {filepath}: {e}"
                logger.warning(error_msg)
                continue
    except InvalidFileError:
        raise
    except (etree.ParseError, XMLParseError) as e:
        error_msg = f"Failed to parse XML content from {filepath}: {e}"
        logger.error(error_msg)
        error_msg = f"Failed to parse XML content: {e}"
        raise XMLParseError(error_msg) from e
    except Exception as e:
        error_msg = f"Failed to parse expressions: {e}"
        logger.error(error_msg)
        return {}

    return expressions


@dataclass
class Reference(BaseReference):
    """A reference to a spreadsheet cell in a FreeCAD document.

    Attributes:
        object_name: Name of the object containing the reference
        expression: The full expression string containing the reference
        filename: Optional name of the file containing the reference
        spreadsheet: Optional name of the spreadsheet containing the referenced cell
        alias: The alias name of the referenced cell (empty if not found)
    """


def parse_reference(expr: Any) -> str | None:
    """Parse a reference from an expression.

    Format: [<<filename>>]#[<<spreadsheet>>].alias

    Args:
        expr: Expression to parse, can be a string or an XML Element

    Returns:
        Alias name if found, None otherwise

    Raises:
        XMLParseError: If expr is None or not a string/XML Element
    """
    if expr is None:
        error_msg = "Expression cannot be None"
        raise XMLParseError(error_msg)

    if isinstance(expr, etree._Element):
        # For XML Elements, we expect an ExpressionEngine attribute
        if "ExpressionEngine" not in expr.attrib:
            error_msg = "XML Element must have an ExpressionEngine attribute"
            raise XMLParseError(error_msg)
        expr_str = str(expr.attrib.get("ExpressionEngine", ""))
    elif isinstance(expr, str):
        expr_str = expr
    else:
        error_msg = f"Invalid expression type: {type(expr)}"
        raise XMLParseError(error_msg)

    # Return None for empty strings or expressions that don't match the pattern
    if not expr_str.strip():
        return None

    # Pattern for optional <<n>> or name followed by # then optional <<n>> or name then . then name
    pattern: str = r"<<globals>>#<<params>>\.([^\s+\-*/()]+)"
    match_obj: Match[str] | None = re.search(pattern, expr_str)
    if match_obj:
        # The alias is always the first group
        return match_obj.group(1)
    return None


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
        alias: str | None = parse_reference(value)
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

        # Find all Object elements with expressions
        obj_refs: list[tuple[str, Reference]] = []
        obj: _Element
        for obj in root.findall(".//Object[@name]"):
            obj_name: str = str(obj.attrib["name"])
            expr: _Element
            for expr in obj.findall(".//Expression"):
                try:
                    expr_str = expr.attrib["expression"]
                    expr_value = expr_str.decode("utf-8") if isinstance(expr_str, bytes) else str(expr_str)
                    alias: str | None = parse_reference(expr_value)
                    if alias:
                        ref: Reference = Reference(obj_name, expr_value, filename)
                        obj_refs.append((alias, ref))
                except (KeyError, ExpressionError) as e:
                    error_msg = f"Error parsing expression in {filename}: {e}"
                    logger.warning(error_msg)
                    continue

        return _group_references_by_alias(obj_refs)
    except XMLParseError:
        error_msg = f"Failed to parse XML content from {filename}"
        logger.error(error_msg)
        return {}
    except Exception as e:
        error_msg = f"Unexpected error parsing {filename}: {e}"
        logger.error(error_msg)
        return {}


def get_references(filepath: Path) -> dict[str, list[Reference]]:
    """Extract alias references from a FreeCAD document.

    Args:
        filepath: Path to FCStd file

    Returns:
        Dictionary mapping alias names to list of references

    Raises:
        InvalidFileError: If file is not a valid FCStd file
        XMLParseError: If XML parsing fails or nesting depth exceeds limit
    """
    if not is_fcstd_file(filepath):
        error_msg = f"{filepath} is not a valid FCStd file"
        raise InvalidFileError(error_msg)

    try:
        content: str = _read_xml_content(filepath)
        return _parse_document_references(content, filepath.name)
    except InvalidFileError:
        raise
    except (etree.ParseError, XMLParseError) as e:
        error_msg = f"Error parsing {filepath}: {e}"
        logger.error(error_msg)
        error_msg2 = f"Failed to parse XML content: {e}"
        raise XMLParseError(error_msg2) from e
    except Exception as e:
        error_msg = f"Unexpected error parsing {filepath}: {e}"
        logger.error(error_msg)
        return {}


def get_references_from_files(filepaths: list[Path]) -> dict[str, list[Reference]]:
    """Extract alias references from multiple FreeCAD documents.

    Args:
        filepaths: List of paths to FCStd files

    Returns:
        Dictionary mapping alias names to list of references

    Note:
        This function will attempt to process all files even if some fail.
        Errors for individual files will be logged but not propagated.
    """
    all_references: dict[str, list[Reference]] = {}

    for filepath in filepaths:
        try:
            if not is_fcstd_file(filepath):
                warning_msg = f"Skipping {filepath}: not a valid FCStd file"
                logger.warning(warning_msg)
                continue

            references: dict[str, list[Reference]] = get_references(filepath)
            _merge_references(all_references, references)

        except InvalidFileError as e:
            logger.warning(str(e))
        except (XMLParseError, ReferenceError) as e:
            error_msg = f"Error processing {filepath}: {e}"
            logger.error(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error processing {filepath}: {e}"
            logger.error(error_msg)

    return all_references


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


def get_cell_aliases_from_files(filepaths: list[Path]) -> set[str]:
    """Extract unique cell aliases from multiple FreeCAD documents.

    Args:
        filepaths: List of paths to FCStd files

    Returns:
        Set of unique cell aliases found across all documents

    Note:
        This function will attempt to process all files even if some fail.
        Errors for individual files will be logged but not propagated.
    """
    all_aliases: set[str] = set()

    for filepath in filepaths:
        try:
            if not is_fcstd_file(filepath):
                warning_msg = f"Skipping {filepath}: not a valid FCStd file"
                logger.warning(warning_msg)
                continue

            aliases: set[str] = get_cell_aliases(filepath)
            all_aliases.update(aliases)

        except InvalidFileError as e:
            logger.warning(str(e))
        except XMLParseError as e:
            error_msg = f"Failed to parse XML content from {filepath}: {e}"
            logger.error(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error processing {filepath}: {e}"
            logger.error(error_msg)

    return all_aliases


def get_properties_from_files(filepaths: list[Path]) -> set[str]:
    """Extract unique property names from multiple FreeCAD documents.

    Args:
        filepaths: List of paths to FCStd files

    Returns:
        Set of unique property names found across all documents

    Note:
        This function will attempt to process all files even if some fail.
        Errors for individual files will be logged but not propagated.
    """
    all_properties = set()

    for filepath in filepaths:
        try:
            if not is_fcstd_file(filepath):
                warning_msg = f"Skipping {filepath}: not a valid FCStd file"
                logger.warning(warning_msg)
                continue

            properties: set[str] = get_document_properties(filepath)
            all_properties.update(properties)

        except InvalidFileError as e:
            logger.warning(str(e))
        except XMLParseError as e:
            error_msg = f"Failed to parse XML content from {filepath}: {e}"
            logger.error(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error processing {filepath}: {e}"
            logger.error(error_msg)

    return all_properties
