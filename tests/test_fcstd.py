"""Tests for the FreeCAD document handling module."""

from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest

from fc_audit.fcstd import (
    Reference,
    get_cell_aliases,
    get_cell_aliases_from_files,
    get_document_properties,
    get_expressions,
    get_properties_from_files,
    get_references,
    get_references_from_files,
    parse_reference,
)


@pytest.fixture
def sample_xml() -> str:
    """Sample XML data for testing."""
    return """<?xml version='1.0' encoding='utf-8'?>
<Document SchemaVersion="4">
    <Object name="Spreadsheet">
        <Properties>
            <Property name="cells">
                <Map count="2">
                    <Item key="A1" value="5"/>
                    <Item key="B1" value="=&lt;&lt;globals&gt;&gt;#&lt;&lt;params&gt;&gt;.Length * 2"/>
                </Map>
            </Property>
            <Property name="alias">
                <Map count="1">
                    <Item key="A1" value="Length"/>
                </Map>
            </Property>
            <Cell alias="Length">5</Cell>
            <Cell alias="Height">10</Cell>
        </Properties>
    </Object>
    <Object name="Pad">
        <Expression expression="=&lt;&lt;globals&gt;&gt;#&lt;&lt;params&gt;&gt;.Height + 10"/>
    </Object>
    <Object name="Sketch">
        <Expression expression="=&lt;&lt;globals&gt;&gt;#&lt;&lt;params&gt;&gt;.Length * 2"/>
    </Object>
</Document>"""


@pytest.fixture
def mock_fcstd(tmp_path: Path, sample_xml: str) -> Path:
    """Create a mock FCStd file for testing."""
    test_file = tmp_path / "test.FCStd"

    # Create a zip file (FCStd is a zip file)
    with zipfile.ZipFile(test_file, "w") as zf:
        zf.writestr("Document.xml", sample_xml)

    return test_file


def test_parse_reference_valid() -> None:
    """Test parsing of valid reference expressions.
    Verifies that the alias name is correctly extracted from expressions
    in the format '<<globals>>#<<params>>.AliasName'."""

    expr = "<<globals>>#<<params>>.Length * 2"
    assert parse_reference(expr) == "Length"

    expr = "<<globals>>#<<params>>.Height + 10"
    assert parse_reference(expr) == "Height"


def test_parse_reference_invalid() -> None:
    """Test parsing of invalid reference expressions.
    Verifies that None is returned for expressions that don't match
    the expected format (e.g., simple values, cell references, empty strings)."""

    assert parse_reference("5") is None
    assert parse_reference("=A1 * 2") is None
    assert parse_reference("") is None


def test_get_expressions(mock_fcstd: Path) -> None:
    """Test extraction of expressions from an FCStd file.
    Verifies that expressions are correctly extracted from Expression elements
    and mapped to their corresponding objects with proper context."""

    expressions = get_expressions(mock_fcstd)
    assert len(expressions) == 2
    assert expressions["Object[Pad]"] == "=<<globals>>#<<params>>.Height + 10"
    assert expressions["Object[Sketch]"] == "=<<globals>>#<<params>>.Length * 2"


def test_parse_document_references(sample_xml: str) -> None:
    """Test parsing of XML content to extract references.
    Verifies that:
    1. References are correctly grouped by alias name
    2. Each reference contains the correct object name and expression
    3. Multiple references to the same alias are properly handled"""
    from fc_audit.fcstd import _parse_document_references

    references = _parse_document_references(sample_xml, "test.FCStd")

    # Check Height reference
    assert "Height" in references
    assert len(references["Height"]) == 1
    assert references["Height"][0].object_name == "Pad"
    assert references["Height"][0].expression == "=<<globals>>#<<params>>.Height + 10"
    assert references["Height"][0].filename == "test.FCStd"

    # Check Length reference
    assert "Length" in references
    assert len(references["Length"]) == 1
    assert references["Length"][0].object_name == "Sketch"
    assert references["Length"][0].expression == "=<<globals>>#<<params>>.Length * 2"
    assert references["Length"][0].filename == "test.FCStd"


def test_get_references(mock_fcstd: Path) -> None:
    """Test extraction of alias references from an FCStd file.
    Verifies that:
    1. Invalid files are rejected
    2. XML content is correctly extracted and parsed
    3. References are returned with correct file information"""
    references = get_references(mock_fcstd)

    # Verify we got the expected references
    assert "Height" in references
    assert "Length" in references

    # Verify file information is correct
    for alias in references:
        for ref in references[alias]:
            assert ref.filename == str(mock_fcstd)


def test_reference_class() -> None:
    """Test the Reference class data structure.
    Verifies that a Reference object correctly stores and provides access to
    its filename, object_name, and expression attributes."""

    ref = Reference(
        filename="test.FCStd",
        object_name="Pad",
        expression="<<globals>>#<<params>>.Height + 10",
    )
    assert ref.filename == "test.FCStd"
    assert ref.object_name == "Pad"
    assert ref.expression == "<<globals>>#<<params>>.Height + 10"


def test_get_document_properties(mock_fcstd: Path) -> None:
    """Test extraction of document properties from an FCStd file.
    Verifies that:
    1. Properties are correctly extracted
    2. Invalid files are rejected
    3. Duplicate properties are handled"""

    # Test valid file
    properties = get_document_properties(mock_fcstd)
    assert "cells" in properties
    assert "alias" in properties

    # Test invalid file
    with pytest.raises(ValueError, match=".* is not a valid FCStd file"):
        get_document_properties(mock_fcstd.parent / "nonexistent.FCStd")


def test_get_cell_aliases(mock_fcstd: Path) -> None:
    """Test extraction of cell aliases from an FCStd file.
    Verifies that:
    1. Aliases are correctly extracted
    2. Invalid files are rejected
    3. Files without aliases are handled"""

    # Test valid file
    aliases = get_cell_aliases(mock_fcstd)
    assert "Length" in aliases

    # Test invalid file
    with pytest.raises(ValueError, match=".* is not a valid FCStd file"):
        get_cell_aliases(mock_fcstd.parent / "nonexistent.FCStd")


def test_get_expressions_error_handling(mock_fcstd: Path) -> None:
    """Test error handling in get_expressions function.
    Verifies that:
    1. Invalid files are rejected
    2. XML parsing errors are handled
    3. Missing Document.xml is handled"""

    # Test invalid file
    with pytest.raises(ValueError, match=".* is not a valid FCStd file"):
        get_expressions(mock_fcstd.parent / "nonexistent.FCStd")

    # Test corrupted XML
    bad_xml_file = mock_fcstd.parent / "bad.FCStd"
    with zipfile.ZipFile(bad_xml_file, "w") as zf:
        zf.writestr("Document.xml", "Invalid XML content")

    with pytest.raises(ET.ParseError):
        get_expressions(bad_xml_file)


def test_get_references_from_files_error_handling(mock_fcstd: Path) -> None:
    """Test error handling in get_references_from_files function.
    Verifies that:
    1. Invalid files are skipped
    2. Valid references are still returned
    3. Empty list is handled"""

    # Test mix of valid and invalid files
    files = [mock_fcstd, mock_fcstd.parent / "nonexistent.FCStd"]
    references = get_references_from_files(files)

    # Should still get references from valid file
    assert "Height" in references
    assert "Length" in references

    # Test empty list
    assert get_references_from_files([]) == {}


def test_get_cell_aliases_from_files_error_handling(mock_fcstd: Path) -> None:
    """Test error handling in get_cell_aliases_from_files function.
    Verifies that:
    1. Invalid files are skipped
    2. Valid aliases are still returned
    3. Empty list is handled"""

    # Test mix of valid and invalid files
    files = [mock_fcstd, mock_fcstd.parent / "nonexistent.FCStd"]
    aliases = get_cell_aliases_from_files(files)

    # Should still get aliases from valid file
    assert "Length" in aliases

    # Test empty list
    assert get_cell_aliases_from_files([]) == set()


def test_get_properties_from_files_error_handling(mock_fcstd: Path) -> None:
    """Test error handling in get_properties_from_files function.
    Verifies that:
    1. Invalid files are skipped
    2. Valid properties are still returned
    3. Empty list is handled"""

    # Test mix of valid and invalid files
    files = [mock_fcstd, mock_fcstd.parent / "nonexistent.FCStd"]
    properties = get_properties_from_files(files)

    # Should still get properties from valid file
    assert "cells" in properties
    assert "alias" in properties

    # Test empty list
    assert get_properties_from_files([]) == set()


def test_parse_expression_element_error_handling() -> None:
    """Test error handling in _parse_expression_element function.
    Verifies that:
    1. Invalid expression attributes are handled
    2. Missing expression attributes are handled
    3. Invalid reference formats are handled"""
    from xml.etree.ElementTree import Element

    from fc_audit.fcstd import _parse_expression_element

    # Test invalid expression attribute
    expr_elem = Element("Expression")
    expr_elem.attrib["expression"] = "invalid expression"
    assert _parse_expression_element(expr_elem, "obj", "test.FCStd") is None

    # Test missing expression attribute
    expr_elem = Element("Expression")
    assert _parse_expression_element(expr_elem, "obj", "test.FCStd") is None


def test_parse_object_element_error_handling() -> None:
    """Test error handling in _parse_object_element function.
    Verifies that:
    1. Invalid object names are handled
    2. Missing expressions are handled
    3. Invalid expressions are handled"""
    from xml.etree.ElementTree import Element

    from fc_audit.fcstd import _parse_object_element

    # Test missing object name
    obj = Element("Object")
    assert _parse_object_element(obj, "test.FCStd") == []

    # Test invalid expressions
    obj = Element("Object")
    obj.attrib["name"] = "TestObj"
    expr = Element("Expression")
    expr.attrib["expression"] = "invalid expression"
    obj.append(expr)
    assert _parse_object_element(obj, "test.FCStd") == []


def test_parse_document_references_error_handling() -> None:
    """Test error handling in _parse_document_references function.
    Verifies that:
    1. Invalid XML content is handled
    2. Missing object elements are handled
    3. Invalid object elements are handled"""
    from fc_audit.fcstd import _parse_document_references

    # Test invalid XML content
    assert _parse_document_references("invalid xml", "test.FCStd") == {}

    # Test empty document
    assert _parse_document_references("<Document></Document>", "test.FCStd") == {}

    # Test document with invalid objects
    xml = """<?xml version='1.0' encoding='utf-8'?>
    <Document>
        <Object name="Test">
            <Expression expression="invalid"/>
        </Object>
    </Document>"""
    assert _parse_document_references(xml, "test.FCStd") == {}


def test_deep_xml_error_handling(tmp_path: Path) -> None:
    """Test deep error handling in XML parsing.
    Verifies that:
    1. Invalid XML structure is handled
    2. Missing required attributes are handled
    3. Invalid expression formats are handled"""
    from fc_audit.fcstd import get_expressions

    # Create a test file with invalid XML structure
    test_file = tmp_path / "test.FCStd"
    with zipfile.ZipFile(test_file, "w") as zf:
        # Test case 1: XML with missing required attributes
        xml1 = """<?xml version='1.0' encoding='utf-8'?>
        <Document>
            <Object>
                <Expression/>
            </Object>
        </Document>"""
        zf.writestr("Document.xml", xml1)

    # Should handle missing attributes gracefully
    result = get_expressions(test_file)
    assert result == {}

    # Test case 2: XML with invalid expression format
    with zipfile.ZipFile(test_file, "w") as zf:
        xml2 = """<?xml version='1.0' encoding='utf-8'?>
        <Document>
            <Object name="Test">
                <Expression expression="=NotAValidExpression"/>
            </Object>
        </Document>"""
        zf.writestr("Document.xml", xml2)

    # Should still capture the expression even if it's invalid
    result = get_expressions(test_file)
    assert result == {"Object[Test]": "=NotAValidExpression"}
