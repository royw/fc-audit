"""Tests for the FreeCAD document handling module."""

from __future__ import annotations

import re
from pathlib import Path
from zipfile import ZipFile

import pytest
from lxml import etree

from fc_audit.fcstd import (
    Reference,
    XMLParseError,
    _parse_document_references,
    _parse_expression_element,
    _parse_reference,
    get_cell_aliases,
    get_document_properties_with_context,
)
from fc_audit.validation import is_fcstd_file


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
def test_data_dir() -> Path:
    """Return the path to the test data directory."""
    return Path(__file__).parent / "data"


def create_fcstd_file(filepath: Path, xml_content: str) -> None:
    """Create a test FCStd file with the given XML content.

    Args:
        filepath: Path to create the file at
        xml_content: XML content to write to Document.xml
    """
    with ZipFile(filepath, "w") as zf:
        zf.writestr("Document.xml", xml_content)


def test__parse_reference_basic() -> None:
    """Test parsing of basic reference expressions."""
    root = etree.fromstring(
        b"""<?xml version='1.0' encoding='utf-8'?>
<Document>
    <Object name="Test">
        <Properties>
            <Property name="Test1" ExpressionEngine="&lt;&lt;globals&gt;&gt;#&lt;&lt;params&gt;&gt;.Length"/>
        </Properties>
    </Object>
</Document>"""
    )
    expr1 = root.find(".//Property[@name='Test1']")
    assert expr1 is not None
    assert _parse_reference(expr1) == "Length"


def test__parse_reference_with_spaces() -> None:
    """Test parsing of reference expressions with spaces."""
    # Test with spaces in the expression
    expr = "<<globals>>#<<params>>. Length "
    assert _parse_reference(expr) == "Length"

    # Test with spaces in XML
    root = etree.fromstring(
        b"""<?xml version='1.0' encoding='utf-8'?>
<Document>
    <Object name="Test">
        <Properties>
            <Property name="Test1" ExpressionEngine="&lt;&lt;globals&gt;&gt;#&lt;&lt;params&gt;&gt;. Length "/>
        </Properties>
    </Object>
</Document>"""
    )
    expr1 = root.find(".//Property[@name='Test1']")
    assert expr1 is not None
    assert _parse_reference(expr1) == "Length"


def test__parse_reference_with_special_chars() -> None:
    """Test parsing of reference expressions with special characters."""
    root = etree.fromstring(
        b"""<?xml version='1.0' encoding='utf-8'?>
<Document>
    <Object name="Test">
        <Properties>
            <Property name="Test1" ExpressionEngine="&lt;&lt;globals&gt;&gt;#&lt;&lt;params&gt;&gt;.Length_123"/>
        </Properties>
    </Object>
</Document>"""
    )
    expr = root.find(".//Property[@name='Test1']")
    assert expr is not None
    assert _parse_reference(expr) == "Length_123"


def test__parse_reference_with_math() -> None:
    """Test parsing of reference expressions with mathematical operations."""
    root = etree.fromstring(
        b"""<?xml version='1.0' encoding='utf-8'?>
<Document>
    <Object name="Test">
        <Properties>
            <Property name="Test1" ExpressionEngine="&lt;&lt;globals&gt;&gt;#&lt;&lt;params&gt;&gt;.Height + 10"/>
        </Properties>
    </Object>
</Document>"""
    )
    expr = root.find(".//Property[@name='Test1']")
    assert expr is not None
    assert _parse_reference(expr) == "Height"


def test__parse_reference_invalid() -> None:
    """Test parsing of invalid reference expressions.
    Verifies that None is returned for expressions that don't match
    the expected format (e.g., simple values, cell references, empty strings)."""

    root = etree.fromstring(
        b"""<?xml version='1.0' encoding='utf-8'?>
<Document>
    <Object name="Test">
        <Properties>
            <Property name="Test1" ExpressionEngine="5"/>
            <Property name="Test2" ExpressionEngine="=A1 * 2"/>
            <Property name="Test3" ExpressionEngine=""/>
        </Properties>
    </Object>
</Document>"""
    )

    expr1 = root.find(".//Property[@name='Test1']")
    assert expr1 is not None
    assert _parse_reference(expr1) is None

    expr2 = root.find(".//Property[@name='Test2']")
    assert expr2 is not None
    assert _parse_reference(expr2) is None

    expr3 = root.find(".//Property[@name='Test3']")
    assert expr3 is not None
    assert _parse_reference(expr3) is None


def test_parse_document_references(sample_xml: str) -> None:
    """Test parsing of XML content to extract references.
    Verifies that:
    1. References are correctly grouped by alias name
    2. Each reference contains the correct object name and expression
    3. Multiple references to the same alias are properly handled"""

    # Remove XML declaration to avoid encoding issues with lxml
    sample_xml = re.sub(r"<\?xml[^>]+\?>", "", sample_xml)
    references = _parse_document_references(sample_xml, "test.FCStd")

    # Verify we got the expected references
    assert len(references) > 0

    # Verify each reference has required fields
    assert "Length" in references
    assert "Height" in references
    for _alias, refs in references.items():
        for ref in refs:
            assert ref.object_name in {"Pad", "Sketch"}
            assert ref.expression in {"=<<globals>>#<<params>>.Height + 10", "=<<globals>>#<<params>>.Length * 2"}
            assert ref.filename == "test.FCStd"


def test_get_cell_aliases(test_data_dir: Path) -> None:
    """Test extraction of cell aliases from an FCStd file.
    Verifies that:
    1. Aliases are correctly extracted
    2. Invalid files raise XMLParseError
    3. Files without aliases return empty set"""
    aliases = get_cell_aliases(test_data_dir / "Test1.FCStd")
    assert len(aliases) > 0
    assert "Length" in aliases
    assert "Height" in aliases

    # Test with empty file
    empty_aliases = get_cell_aliases(test_data_dir / "Empty.FCStd")
    assert len(empty_aliases) == 0

    # Test with invalid file
    with pytest.raises(XMLParseError):
        get_cell_aliases(test_data_dir / "Invalid.FCStd")


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


def test_parse_expression_element_error_handling() -> None:
    """Test error handling in _parse_expression_element function.
    Verifies that:
    1. Invalid expression attributes are handled
    2. Missing expression attributes are handled
    3. Invalid reference formats are handled"""
    from lxml.etree import _Element

    # Test invalid expression attribute
    expr_elem: _Element = etree.Element("Expression")
    expr_elem.attrib["expression"] = "invalid expression"
    assert _parse_expression_element(expr_elem, "obj", "test.FCStd") is None

    # Test missing expression attribute
    expr_elem_missing: _Element = etree.Element("Expression")
    assert _parse_expression_element(expr_elem_missing, "obj", "test.FCStd") is None

    # Test with invalid expression format
    assert _parse_reference("invalid.expression") is None


def test_is_fcstd_file_error_handling(tmp_path: Path) -> None:
    """Test error handling in is_fcstd_file function.

    Verifies that:
    1. Non-existent files are handled
    2. Invalid zip files are handled
    3. Zip files without Document.xml are handled
    """
    # Test non-existent file
    filepath = tmp_path / "nonexistent.FCStd"
    assert not is_fcstd_file(filepath)

    # Test invalid zip file
    filepath = tmp_path / "invalid.FCStd"
    filepath.write_bytes(b"This is not a zip file")
    assert not is_fcstd_file(filepath)

    # Test zip file without Document.xml
    empty_zip = tmp_path / "empty.FCStd"
    with ZipFile(empty_zip, "w") as zf:
        zf.writestr("dummy.txt", "")
    assert not is_fcstd_file(empty_zip)


def test_get_document_properties_with_context(test_data_dir: Path) -> None:
    """Test extraction of properties with their object context.

    Verifies that:
    1. Properties are correctly extracted with their object context
    2. Properties without values are handled
    3. Properties without object context are handled
    4. Invalid XML is handled
    """
    # Create a test file with properties
    test_file = test_data_dir / "test_properties.FCStd"
    xml_content = """<?xml version='1.0' encoding='utf-8'?>
<Document>
    <Object name="Test1">
        <Property name="Prop1">
            <String>Value1</String>
        </Property>
        <Property name="Prop2">
            <String>Value2</String>
        </Property>
    </Object>
    <Object name="Test2">
        <Property name="Prop1">
            <String>Value3</String>
        </Property>
        <Property name="NoValue">
        </Property>
    </Object>
    <Property name="OrphanProp">
        <String>OrphanValue</String>
    </Property>
</Document>"""
    create_fcstd_file(test_file, xml_content)

    # Test property extraction
    properties = get_document_properties_with_context(test_file)
    assert "Prop1" in properties
    assert len(properties["Prop1"]) == 2
    assert ("Test1", "Value1") in properties["Prop1"]
    assert ("Test2", "Value3") in properties["Prop1"]
    assert "Prop2" in properties
    assert properties["Prop2"] == [("Test1", "Value2")]
    assert "NoValue" in properties
    assert properties["NoValue"] == [("Test2", "")]
    assert "OrphanProp" in properties
    assert properties["OrphanProp"] == [("unknown", "OrphanValue")]

    # Test invalid XML
    invalid_file = test_data_dir / "invalid.FCStd"
    create_fcstd_file(invalid_file, "Invalid XML content")
    with pytest.raises(XMLParseError):
        get_document_properties_with_context(invalid_file)


def test_read_xml_content_error_handling(tmp_path: Path) -> None:
    """Test error handling in _read_xml_content function.

    Verifies that:
    1. Non-existent files are handled
    2. Invalid zip files are handled
    3. Missing Document.xml is handled
    """
    from fc_audit.exceptions import InvalidFileError
    from fc_audit.fcstd import _read_xml_content

    # Test non-existent file
    with pytest.raises(InvalidFileError, match=r"Failed to read.*No such file or directory"):
        _read_xml_content(tmp_path / "nonexistent.FCStd")

    # Test invalid zip file
    invalid_zip = tmp_path / "invalid.FCStd"
    invalid_zip.write_bytes(b"Not a zip file")
    with pytest.raises(InvalidFileError, match=r"Failed to read.*not a zip file"):
        _read_xml_content(invalid_zip)

    # Test zip file without Document.xml
    empty_zip = tmp_path / "empty.FCStd"
    with ZipFile(empty_zip, "w") as zf:
        zf.writestr("dummy.txt", "")
    with pytest.raises(InvalidFileError, match=r"Document.xml not found"):
        _read_xml_content(empty_zip)


def test_parse_xml_content_error_handling() -> None:
    """Test error handling in _parse_xml_content function.

    Verifies that:
    1. Invalid XML content is handled
    2. Empty content is handled
    3. Malformed XML is handled
    """
    from fc_audit.fcstd import _parse_xml_content

    # Test invalid XML
    with pytest.raises(XMLParseError):
        _parse_xml_content("Invalid XML content")

    # Test empty content
    with pytest.raises(XMLParseError):
        _parse_xml_content("")

    # Test malformed XML
    with pytest.raises(XMLParseError):
        _parse_xml_content("<root><unclosed>")


def test_merge_references() -> None:
    """Test merging of reference dictionaries.

    Verifies that:
    1. New references are added correctly
    2. Existing references are updated
    3. Empty dictionaries are handled
    """
    from fc_audit.fcstd import _merge_references

    # Create test references
    ref1 = Reference("file1.FCStd", "obj1", "expr1")
    ref2 = Reference("file1.FCStd", "obj2", "expr2")
    ref3 = Reference("file2.FCStd", "obj3", "expr3")

    # Test merging new references
    all_refs = {"alias1": [ref1]}
    new_refs = {"alias2": [ref2], "alias3": [ref3]}
    _merge_references(all_refs, new_refs)
    assert len(all_refs) == 3
    assert all_refs["alias1"] == [ref1]
    assert all_refs["alias2"] == [ref2]
    assert all_refs["alias3"] == [ref3]

    # Test updating existing references
    new_refs = {"alias1": [ref2]}
    _merge_references(all_refs, new_refs)
    assert all_refs["alias1"] == [ref1, ref2]

    # Test empty dictionaries
    _merge_references(all_refs, {})
    assert len(all_refs) == 3
    _merge_references({}, new_refs)
    assert len(new_refs) == 1


def test_parse_expression_element_error_handling_extended() -> None:
    """Test error handling in _parse_expression_element function.

    Verifies that:
    1. Missing expression attributes are handled
    2. Invalid reference formats are handled
    3. Invalid XML content is handled
    """
    from fc_audit.fcstd import _parse_expression_element

    # Test missing expression attribute
    elem = etree.Element("Expression")
    assert _parse_expression_element(elem, "TestObj", "test.FCStd") is None

    # Test invalid reference format
    elem = etree.Element("Expression", {"expression": "invalid_format"})
    assert _parse_expression_element(elem, "TestObj", "test.FCStd") is None

    # Test malformed expression
    elem = etree.Element("Expression", {"expression": "<<globals>>#<<params>>."})
    assert _parse_expression_element(elem, "TestObj", "test.FCStd") is None


def test_parse_object_element_error_handling() -> None:
    """Test error handling in _parse_object_element function.

    Verifies that:
    1. Objects without name attributes are handled
    2. Objects without expressions are handled
    3. Invalid expressions are handled
    """
    from fc_audit.fcstd import _parse_object_element

    # Test object without name
    obj = etree.Element("Object")
    assert _parse_object_element(obj, "test.FCStd") == []

    # Test object without expressions
    obj = etree.Element("Object", {"name": "TestObj"})
    assert _parse_object_element(obj, "test.FCStd") == []

    # Test object with invalid expressions
    obj = etree.Element("Object", {"name": "TestObj"})
    etree.SubElement(obj, "Expression", {"expression": "invalid_format"})
    assert _parse_object_element(obj, "test.FCStd") == []


def test_parse_document_references_error_handling() -> None:
    """Test error handling in _parse_document_references function.

    Verifies that:
    1. Invalid XML content is handled
    2. Missing Object elements are handled
    3. Invalid Object elements are handled
    """
    from fc_audit.fcstd import _parse_document_references

    # Test invalid XML
    with pytest.raises(XMLParseError):
        _parse_document_references("Invalid XML", "test.FCStd")

    # Test empty document
    xml = "<?xml version='1.0'?><Document></Document>"
    assert _parse_document_references(xml, "test.FCStd") == {}

    # Test document with invalid objects
    xml = """<?xml version='1.0'?>
    <Document>
        <Object>
            <Expression expression="invalid"/>
        </Object>
    </Document>"""
    assert _parse_document_references(xml, "test.FCStd") == {}
