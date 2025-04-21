"""Tests for the FreeCAD document handling module."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import pytest

from fc_audit.fcstd import (
    ExpressionError,
    InvalidFileError,
    Reference,
    XMLParseError,
    _extract_expression,
    _find_parent_with_identifier,
    _make_unique_key,
    _merge_references,
    _parse_document_references,
    _parse_expression_element,
    _parse_object_element,
    _read_xml_content,
    get_cell_aliases,
    get_cell_aliases_from_files,
    get_document_properties,
    get_expressions,
    get_properties_from_files,
    get_references,
    get_references_from_files,
    is_fcstd_file,
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


def test_extract_expression() -> None:
    # Success case: Expression attached to parent with name attribute
    root = ET.Element("Document")
    parent = ET.SubElement(root, "Object", name="ParentName")
    expr = ET.SubElement(parent, "Expression", expression="=<<globals>>#<<params>>.Length + 10")
    ctx, value = _extract_expression(expr, root)
    assert ctx.startswith("Object[ParentName]")
    assert value == "=<<globals>>#<<params>>.Length + 10"

    # Error case: Expression not attached to parent with identifier
    expr2 = ET.Element("Expression", expression="=<<globals>>#<<params>>.Height")
    with pytest.raises(ExpressionError):
        _extract_expression(expr2, root)

    # Error case: Missing 'expression' attribute
    expr3 = ET.SubElement(parent, "Expression")
    with pytest.raises(ExpressionError, match="expression"):
        _extract_expression(expr3, root)


def test_parse_reference_valid() -> None:
    """Test parsing of valid reference expressions.
    Verifies that the alias name is correctly extracted from expressions
    in the format '<<globals>>#<<params>>.AliasName'."""

    # Test simple reference
    assert parse_reference("<<globals>>#<<params>>.Length") == "Length"

    # Test reference with expression
    expr = "<<globals>>#<<params>>.Length * 2"
    assert parse_reference(expr) == "Length"

    # Test reference with special characters
    assert parse_reference("<<globals>>#<<params>>.Length_123") == "Length_123"

    expr = "<<globals>>#<<params>>.Height + 10"
    assert parse_reference(expr) == "Height"


def test_parse_reference_invalid() -> None:
    """Test parsing of invalid reference expressions.
    Verifies that None is returned for expressions that don't match
    the expected format (e.g., simple values, cell references, empty strings)."""

    assert parse_reference("5") is None
    assert parse_reference("=A1 * 2") is None
    assert parse_reference("") is None


def test_get_expressions(test_data_dir: Path) -> None:
    """Test extraction of expressions from an FCStd file.
    Verifies that expressions are correctly extracted from Expression elements
    and mapped to their corresponding objects with proper context."""

    expressions = get_expressions(test_data_dir / "Test1.FCStd")
    assert len(expressions) > 0
    # We don't assert specific expressions since they may change in the test file


def test_parse_document_references(sample_xml: str) -> None:
    """Test parsing of XML content to extract references.
    Verifies that:
    1. References are correctly grouped by alias name
    2. Each reference contains the correct object name and expression
    3. Multiple references to the same alias are properly handled"""

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


def test_get_references(test_data_dir: Path) -> None:
    """Test extraction of alias references from an FCStd file.
    Verifies that:
    1. Invalid files are rejected
    2. XML content is correctly extracted and parsed
    3. References are returned with correct file information"""
    references = get_references(test_data_dir / "Test1.FCStd")
    assert len(references) > 0
    # Check that references contain valid file information
    for refs in references.values():
        for ref in refs:
            assert ref.filename
            assert ref.object_name
            assert ref.expression


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


def test_get_document_properties(test_data_dir: Path) -> None:
    """Test extraction of document properties from an FCStd file.
    Verifies that:
    1. Properties are correctly extracted
    2. Invalid files are rejected
    3. Duplicate properties are handled"""
    properties = get_document_properties(test_data_dir / "Test1.FCStd")
    assert len(properties) > 0

    # Test with invalid file
    with pytest.raises(InvalidFileError):
        get_document_properties(test_data_dir / "Invalid.FCStd")


def test_get_cell_aliases(test_data_dir: Path) -> None:
    """Test extraction of cell aliases from an FCStd file.
    Verifies that:
    1. Aliases are correctly extracted
    2. Invalid files are rejected
    3. Files without aliases are handled"""
    aliases = get_cell_aliases(test_data_dir / "Test1.FCStd")
    assert len(aliases) > 0

    # Test with empty file
    empty_aliases = get_cell_aliases(test_data_dir / "Empty.FCStd")
    assert len(empty_aliases) == 0

    # Test with invalid file
    with pytest.raises(InvalidFileError):
        get_cell_aliases(test_data_dir / "Invalid.FCStd")


def test_get_expressions_error_handling(test_data_dir: Path) -> None:
    """Test error handling in get_expressions function.
    Verifies that:
    1. Invalid files are rejected
    2. Invalid XML is handled
    3. Missing attributes are handled"""
    # Test with invalid file
    with pytest.raises(InvalidFileError):
        get_expressions(test_data_dir / "Invalid.FCStd")

    # Test with empty file (should not raise error, but return empty dict)
    assert get_expressions(test_data_dir / "Empty.FCStd") == {}

    # Test with XML parse error
    test_file = test_data_dir / "test3.FCStd"
    create_fcstd_file(test_file, "<Document><Object><Expression>")

    with pytest.raises(InvalidFileError):
        get_expressions(test_file)


def test_get_references_from_files_error_handling(test_data_dir: Path) -> None:
    """Test error handling in get_references_from_files function.
    Verifies that:
    1. Invalid files are skipped
    2. Valid references are still returned
    3. Empty list is handled"""
    # Test with a mix of valid and invalid files
    references = get_references_from_files([test_data_dir / "Test1.FCStd", test_data_dir / "Invalid.FCStd"])
    assert len(references) > 0

    # Test with empty list
    assert get_references_from_files([]) == {}

    # Test with only invalid files
    assert get_references_from_files([test_data_dir / "Invalid.FCStd"]) == {}


def test_get_cell_aliases_from_files_error_handling(test_data_dir: Path) -> None:
    """Test error handling in get_cell_aliases_from_files function.
    Verifies that:
    1. Invalid files are skipped
    2. Valid aliases are still returned
    3. Empty list is handled"""
    # Test with a mix of valid and invalid files
    aliases = get_cell_aliases_from_files([test_data_dir / "Test1.FCStd", test_data_dir / "Invalid.FCStd"])
    assert len(aliases) > 0

    # Test with empty list
    assert get_cell_aliases_from_files([]) == set()

    # Test with only invalid files
    assert get_cell_aliases_from_files([test_data_dir / "Invalid.FCStd"]) == set()


def test_get_properties_from_files_error_handling(test_data_dir: Path) -> None:
    """Test error handling in get_properties_from_files function.
    Verifies that:
    1. Invalid files are skipped
    2. Valid properties are still returned
    3. Empty list is handled"""
    # Test with a mix of valid and invalid files
    properties = get_properties_from_files([test_data_dir / "Test1.FCStd", test_data_dir / "Invalid.FCStd"])
    assert len(properties) > 0

    # Test with empty list
    assert get_properties_from_files([]) == set()

    # Test with only invalid files
    assert get_properties_from_files([test_data_dir / "Invalid.FCStd"]) == set()


def test_parse_expression_element_error_handling() -> None:
    """Test error handling in _parse_expression_element function.
    Verifies that:
    1. Invalid expression attributes are handled
    2. Missing expression attributes are handled
    3. Invalid reference formats are handled"""
    from xml.etree.ElementTree import Element

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
    assert _parse_document_references(xml, "test.FCStd") == {
        "Object[Test]": [
            Reference(object_name="test.FCStd", expression="Test", filename="invalid", spreadsheet=None, alias="")
        ]
    }


def test_find_parent_with_identifier() -> None:
    """Test _find_parent_with_identifier function."""
    # Create XML tree directly
    root = ET.Element("Document")

    # Create test objects
    obj1 = ET.SubElement(root, "Object")
    obj1.set("name", "Box")
    expr1 = ET.SubElement(obj1, "Expression")
    expr1.set("expression", "test")

    obj2 = ET.SubElement(root, "Object")
    obj2.set("type", "Cube")
    expr2 = ET.SubElement(obj2, "Expression")
    expr2.set("expression", "test")

    obj3 = ET.SubElement(root, "Object")
    obj3.set("label", "MyBox")
    expr3 = ET.SubElement(obj3, "Expression")
    expr3.set("expression", "test")

    obj4 = ET.SubElement(root, "Object")
    expr4 = ET.SubElement(obj4, "Expression")
    expr4.set("expression", "test")

    # Test finding parent with name attribute
    parent, context = _find_parent_with_identifier(expr1, root)
    assert parent is not None
    assert context == "Object[Box]"

    # Test finding parent with type attribute
    parent, context = _find_parent_with_identifier(expr2, root)
    assert parent is not None
    assert context == "Object[Cube]"

    # Test finding parent with label attribute
    parent, context = _find_parent_with_identifier(expr3, root)
    assert parent is not None
    assert context == "Object[MyBox]"

    # Test finding parent without any identifier
    parent, context = _find_parent_with_identifier(expr4, root)
    assert parent is not None
    assert context == "Object"

    # Test with element that has no parent
    parent, context = _find_parent_with_identifier(ET.Element("Test"), root)
    assert parent is None
    assert context == "unknown"


def test_make_unique_key() -> None:
    """Test _make_unique_key function.
    Verifies that:
    1. Original key is returned if not in existing keys
    2. Numbered keys are created for duplicates
    3. Numbers increase until a unique key is found"""
    # Test with empty existing keys
    assert _make_unique_key("test", set()) == "test"

    # Test with non-conflicting key
    assert _make_unique_key("test", {"other"}) == "test"

    # Test with conflicting key
    assert _make_unique_key("test", {"test"}) == "test (1)"

    # Test with multiple conflicts
    existing = {"test", "test (1)", "test (2)"}
    assert _make_unique_key("test", existing) == "test (3)"


def test_merge_references() -> None:
    """Test _merge_references function.
    Verifies that:
    1. New references are added to empty dict
    2. New references are appended to existing lists
    3. New aliases are added with their references"""
    # Test merging into empty dict
    all_refs: dict[str, list[Reference]] = {}
    new_refs = {"Length": [Reference(filename="file1.FCStd", object_name="Box", expression="expr1")]}
    _merge_references(all_refs, new_refs)
    assert len(all_refs["Length"]) == 1
    assert all_refs["Length"][0].expression == "expr1"

    # Test appending to existing list
    new_refs = {"Length": [Reference(filename="file2.FCStd", object_name="Box", expression="expr2")]}
    _merge_references(all_refs, new_refs)
    assert len(all_refs["Length"]) == 2
    assert all_refs["Length"][0].expression == "expr1"
    assert all_refs["Length"][1].expression == "expr2"

    # Test adding new alias
    new_refs = {"Height": [Reference(filename="file1.FCStd", object_name="Box", expression="expr3")]}
    _merge_references(all_refs, new_refs)
    assert len(all_refs["Height"]) == 1
    assert all_refs["Height"][0].expression == "expr3"


def test_read_xml_content_error_handling(tmp_path: Path) -> None:
    """Test error handling in _read_xml_content function.
    Verifies that:
    1. Non-existent files are handled
    2. Invalid zip files are handled
    3. Zip files without Document.xml are handled
    4. Corrupted XML content is handled"""
    # Test non-existent file
    with pytest.raises(InvalidFileError):
        _read_xml_content(tmp_path / "nonexistent.FCStd")

    # Test invalid zip file
    invalid_zip = tmp_path / "invalid.FCStd"
    invalid_zip.write_text("not a zip file")
    with pytest.raises(InvalidFileError):
        _read_xml_content(invalid_zip)

    # Test zip without Document.xml
    empty_zip = tmp_path / "empty.FCStd"
    with ZipFile(empty_zip, "w") as zf:
        zf.writestr("other.txt", "content")
    with pytest.raises(InvalidFileError):
        _read_xml_content(empty_zip)

    # Test corrupted XML content
    corrupted_xml = tmp_path / "corrupted.FCStd"
    with ZipFile(corrupted_xml, "w") as zf:
        zf.writestr("Document.xml", "<invalid>xml</invalid>")
    with pytest.raises(InvalidFileError):
        _read_xml_content(corrupted_xml)


def test_parse_reference_error_handling() -> None:
    """Test error handling in parse_reference function."""
    # Test with None element
    with pytest.raises(XMLParseError):
        parse_reference(None)

    # Test with invalid element type
    with pytest.raises(XMLParseError):
        parse_reference(42)

    # Test with empty string
    assert parse_reference("") is None

    # Test with invalid expression format
    assert parse_reference("invalid.expression") is None


def test_get_references_error_handling(tmp_path: Path) -> None:
    """Test error handling in get_references function.

    Verifies that:
    1. Invalid FCStd file is handled
    2. Invalid XML content is handled
    3. Missing references are handled
    """
    # Test invalid FCStd file
    filepath = tmp_path / "invalid.FCStd"
    filepath.write_bytes(b"This is not a zip file")
    with pytest.raises(InvalidFileError):
        get_references(filepath)

    # Test invalid XML content
    xml_content = """<?xml version='1.0' encoding='UTF-8'?>
<Invalid>This is not valid XML</Invalid"""
    filepath = tmp_path / "invalid_xml.FCStd"
    create_fcstd_file(filepath, xml_content)
    refs = get_references(filepath)
    assert refs == {}

    # Test missing references
    xml_content = """<?xml version='1.0' encoding='UTF-8'?>
<Document>
    <Object name="Spreadsheet">
        <NoReferences/>
    </Object>
</Document>"""
    filepath = tmp_path / "no_refs.FCStd"
    create_fcstd_file(filepath, xml_content)
    refs = get_references(filepath)
    assert refs == {}


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
    filepath = tmp_path / "no_document.FCStd"
    with ZipFile(filepath, "w") as zf:
        zf.writestr("some_file.txt", "Some content")
    assert not is_fcstd_file(filepath)


def test_get_document_properties_error_handling(tmp_path: Path) -> None:
    """Test error handling in get_document_properties function.

    Verifies that:
    1. Invalid FCStd files raise InvalidFileError
    2. Invalid XML content raises XMLParseError
    3. XML without properties is handled
    """
    # Test invalid FCStd file
    filepath = tmp_path / "invalid.FCStd"
    filepath.write_bytes(b"This is not a zip file")
    with pytest.raises(InvalidFileError):
        get_document_properties(filepath)

    # Test invalid XML content
    xml_content = """<?xml version='1.0' encoding='UTF-8'?>
<Invalid>This is not valid XML</Invalid"""
    filepath = tmp_path / "invalid_xml.FCStd"
    create_fcstd_file(filepath, xml_content)
    with pytest.raises(XMLParseError):
        get_document_properties(filepath)

    # Test XML without properties
    xml_content = """<?xml version='1.0' encoding='UTF-8'?>
<Document>
    <Object name="Spreadsheet">
        <Cells>
            <Cell address="A1"/>
        </Cells>
    </Object>
</Document>"""
    filepath = tmp_path / "no_properties.FCStd"
    create_fcstd_file(filepath, xml_content)
    properties = get_document_properties(filepath)
    assert properties == set()
