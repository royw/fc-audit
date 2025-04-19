"""Tests for reference_collector module."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from fc_audit.reference_collector import Reference, ReferenceCollector


@pytest.fixture
def sample_references() -> dict[str, list[Reference]]:
    """Sample references for testing."""
    return {
        "Length": [
            Reference(
                filename="Test1.FCStd",
                object_name="Box",
                expression="<<globals>>#<<params>>.Length + 10",
                spreadsheet="params",
                alias="Length",
            )
        ],
        "Width": [
            Reference(
                filename="Test1.FCStd",
                object_name="Box",
                expression="<<globals>>#<<params>>.Width + 5",
                spreadsheet="params",
                alias="Width",
            )
        ],
    }


def test_reference_class() -> None:
    """Test Reference class initialization and comparison."""
    ref = Reference(
        filename="test.FCStd",
        object_name="Box",
        expression="test_expr",
        spreadsheet="Sheet",
        alias="test",
    )

    assert ref.filename == "test.FCStd"
    assert ref.object_name == "Box"
    assert ref.expression == "test_expr"
    assert ref.spreadsheet == "Sheet"
    assert ref.alias == "test"

    # Test comparison
    ref2 = Reference(
        filename="test.FCStd",
        object_name="Box",
        expression="test_expr",
        spreadsheet="Sheet",
        alias="test",
    )
    assert ref == ref2


def test_reference_collector_init(tmp_path: Path) -> None:
    """Test ReferenceCollector initialization."""
    file = tmp_path / "test.FCStd"
    file.touch()
    collector = ReferenceCollector([file])
    assert collector.references == {}
    assert collector.processed_files == set()


def test_collect_references(tmp_path: Path) -> None:
    """Test collecting references from files."""
    # Create test FCStd files
    file1 = tmp_path / "test1.FCStd"
    file2 = tmp_path / "test2.FCStd"

    # Create FCStd files with expressions
    xml_content1 = """
    <Document>
        <Object name="Box">
            <Expression expression="=&lt;&lt;globals&gt;&gt;#&lt;&lt;params&gt;&gt;.Length"/>
        </Object>
    </Document>
    """
    xml_content2 = """
    <Document>
        <Object name="Box">
            <Expression expression="=&lt;&lt;globals&gt;&gt;#&lt;&lt;params&gt;&gt;.Width"/>
        </Object>
    </Document>
    """

    with zipfile.ZipFile(file1, "w") as zf:
        zf.writestr("Document.xml", xml_content1)
    with zipfile.ZipFile(file2, "w") as zf:
        zf.writestr("Document.xml", xml_content2)

    collector = ReferenceCollector([file1, file2])
    refs = collector.collect()

    assert len(refs) == 2
    assert "Length" in refs
    assert "Width" in refs
    assert len(collector.processed_files) == 2
    assert file1.name in collector.processed_files
    assert file2.name in collector.processed_files


def test_process_file(tmp_path: Path) -> None:
    """Test processing individual files."""
    file = tmp_path / "test.FCStd"

    # Create FCStd file with expressions
    xml_content = """
    <Document>
        <Object name="Box">
            <Expression expression="=&lt;&lt;globals&gt;&gt;#&lt;&lt;params&gt;&gt;.Length"/>
        </Object>
    </Document>
    """

    with zipfile.ZipFile(file, "w") as zf:
        zf.writestr("Document.xml", xml_content)

    collector = ReferenceCollector([file])
    collector._process_file(file)

    assert "Length" in collector.references
    assert file.name in collector.processed_files
    assert file.name in collector.processed_files


def test_error_handling(tmp_path: Path) -> None:
    """Test error handling for invalid files."""
    # Test with non-existent file
    non_existent = tmp_path / "non_existent.FCStd"
    collector = ReferenceCollector([non_existent])

    # This should log an error but not raise an exception
    collector.collect()
    assert str(non_existent) not in collector.processed_files
    assert collector.references == {}
