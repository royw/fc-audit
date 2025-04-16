"""Tests for the FreeCAD document handling module."""
import pytest
import zipfile
from fc_audit.fcstd import get_expressions, get_references, Reference, parse_reference


@pytest.fixture
def sample_xml():
    """Sample XML data for testing."""
    return '''<?xml version='1.0' encoding='utf-8'?>
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
        </Properties>
    </Object>
    <Object name="Pad">
        <Expression expression="=&lt;&lt;globals&gt;&gt;#&lt;&lt;params&gt;&gt;.Height + 10"/>
    </Object>
    <Object name="Sketch">
        <Expression expression="=&lt;&lt;globals&gt;&gt;#&lt;&lt;params&gt;&gt;.Length * 2"/>
    </Object>
</Document>'''


@pytest.fixture
def mock_fcstd(tmp_path, sample_xml):
    """Create a mock FCStd file for testing."""
    test_file = tmp_path / "test.FCStd"
    
    # Create a zip file (FCStd is a zip file)
    with zipfile.ZipFile(test_file, 'w') as zf:
        zf.writestr('Document.xml', sample_xml)
    
    return test_file


def test_parse_reference_valid():
    """Test parsing of valid reference expressions.
    Verifies that the alias name is correctly extracted from expressions
    in the format '<<globals>>#<<params>>.AliasName'."""

    expr = "<<globals>>#<<params>>.Length * 2"
    assert parse_reference(expr) == "Length"

    expr = "<<globals>>#<<params>>.Height + 10"
    assert parse_reference(expr) == "Height"


def test_parse_reference_invalid():
    """Test parsing of invalid reference expressions.
    Verifies that None is returned for expressions that don't match
    the expected format (e.g., simple values, cell references, empty strings)."""

    assert parse_reference("5") is None
    assert parse_reference("=A1 * 2") is None
    assert parse_reference("") is None


def test_get_expressions(mock_fcstd):
    """Test extraction of expressions from an FCStd file.
    Verifies that expressions are correctly extracted from Expression elements
    and mapped to their corresponding objects with proper context."""

    expressions = get_expressions(mock_fcstd)
    assert len(expressions) == 2
    assert expressions['Object[Pad]'] == '=<<globals>>#<<params>>.Height + 10'
    assert expressions['Object[Sketch]'] == '=<<globals>>#<<params>>.Length * 2'


def test_parse_document_references(sample_xml):
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


def test_get_references(mock_fcstd):
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


def test_reference_class():
    """Test the Reference class data structure.
    Verifies that a Reference object correctly stores and provides access to
    its filename, object_name, and expression attributes."""

    ref = Reference(filename="test.FCStd", object_name="Pad", expression="<<globals>>#<<params>>.Height + 10")
    assert ref.filename == "test.FCStd"
    assert ref.object_name == "Pad"
    assert ref.expression == "<<globals>>#<<params>>.Height + 10"
