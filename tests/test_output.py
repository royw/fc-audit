"""Tests for output.py module."""

from __future__ import annotations

import json

import pytest

from fc_audit.reference_collector import Reference
from fc_audit.reference_outputter import ReferenceOutputter


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


def test_reference_outputter_init(sample_references: dict[str, list[Reference]]) -> None:
    """Test ReferenceOutputter initialization."""
    processed_files = {"Test1.FCStd"}
    outputter = ReferenceOutputter(sample_references, processed_files)
    assert outputter.references == sample_references
    assert outputter.processed_files == processed_files


def test_filter_references_single_pattern(sample_references: dict[str, list[Reference]]) -> None:
    """Test filtering references with a single pattern."""
    processed_files = {"Test1.FCStd"}
    outputter = ReferenceOutputter(sample_references, processed_files)

    outputter.filter_by_patterns(["Length"])
    filtered = outputter.references
    assert len(filtered) == 1
    assert "Length" in filtered


def test_filter_references_multiple_patterns(sample_references: dict[str, list[Reference]]) -> None:
    """Test filtering references with multiple patterns."""
    processed_files = {"Test1.FCStd"}
    outputter = ReferenceOutputter(sample_references, processed_files)

    outputter.filter_by_patterns(["Width", "Length"])
    filtered = outputter.references
    assert len(filtered) == 2
    assert "Width" in filtered
    assert "Length" in filtered


def test_filter_references_non_matching_pattern(sample_references: dict[str, list[Reference]]) -> None:
    """Test filtering references with a non-matching pattern."""
    processed_files = {"Test1.FCStd"}
    outputter = ReferenceOutputter(sample_references, processed_files)

    outputter.filter_by_patterns(["NonExistent"])
    filtered = outputter.references
    assert len(filtered) == 0


def test_filter_references_empty_patterns(sample_references: dict[str, list[Reference]]) -> None:
    """Test filtering references with empty patterns list."""
    processed_files = {"Test1.FCStd"}
    outputter = ReferenceOutputter(sample_references, processed_files)

    outputter.filter_by_patterns([])
    assert outputter.references == sample_references


def test_convert_references_to_json(sample_references: dict[str, list[Reference]]) -> None:
    """Test converting references to JSON format."""
    processed_files = {"Test1.FCStd"}
    outputter = ReferenceOutputter(sample_references, processed_files)
    json_str = outputter.to_json()
    json_data = json.loads(json_str)

    assert "Length" in json_data
    assert "Width" in json_data
    assert json_data["Length"][0]["expression"] == "<<globals>>#<<params>>.Length + 10"
    assert json_data["Width"][0]["expression"] == "<<globals>>#<<params>>.Width + 5"


def test_format_by_object(sample_references: dict[str, list[Reference]]) -> None:
    """Test formatting references by object."""
    processed_files = {"Test1.FCStd"}
    outputter = ReferenceOutputter(sample_references, processed_files)
    by_object = outputter.format_by_object()

    assert "Test1.FCStd" in by_object
    assert "Box" in by_object["Test1.FCStd"]
    assert "Length" in by_object["Test1.FCStd"]["Box"]
    assert "Width" in by_object["Test1.FCStd"]["Box"]


def test_format_by_file(sample_references: dict[str, list[Reference]]) -> None:
    """Test formatting references by file."""
    processed_files = {"Test1.FCStd"}
    outputter = ReferenceOutputter(sample_references, processed_files)
    by_file = outputter.format_by_file()

    assert "Test1.FCStd" in by_file
    assert "Length" in by_file["Test1.FCStd"]
    assert "Width" in by_file["Test1.FCStd"]


def test_empty_references() -> None:
    """Test handling of empty references."""
    processed_files: set[str] = set()
    outputter = ReferenceOutputter({}, processed_files)

    # Test JSON output
    assert outputter.to_json() == '{"message": "No alias references found"}'

    # Test by-object format
    assert outputter.format_by_object() == {}

    # Test by-file format
    assert outputter.format_by_file() == {}

    # Test empty files list
    outputter.print_empty_files()


def test_print_by_object(sample_references: dict[str, list[Reference]], capsys: pytest.CaptureFixture[str]) -> None:
    """Test printing references grouped by object."""
    processed_files = {"Test1.FCStd", "Empty.FCStd"}
    outputter = ReferenceOutputter(sample_references, processed_files)

    outputter.print_by_object()
    captured = capsys.readouterr()
    assert "Object: Box" in captured.out
    assert "File: Test1.FCStd" in captured.out
    assert "Alias: Length" in captured.out
    assert "Expression: <<globals>>#<<params>>.Length + 10" in captured.out


def test_print_by_file(sample_references: dict[str, list[Reference]], capsys: pytest.CaptureFixture[str]) -> None:
    """Test printing references grouped by file."""
    processed_files = {"Test1.FCStd", "Empty.FCStd"}
    outputter = ReferenceOutputter(sample_references, processed_files)

    outputter.print_by_file()
    captured = capsys.readouterr()
    assert "File: Test1.FCStd" in captured.out
    assert "Alias: Length" in captured.out
    assert "Object: Box" in captured.out
    assert "Expression: <<globals>>#<<params>>.Length + 10" in captured.out


def test_print_by_alias(sample_references: dict[str, list[Reference]], capsys: pytest.CaptureFixture[str]) -> None:
    """Test printing references grouped by alias."""
    processed_files = {"Test1.FCStd", "Empty.FCStd"}
    outputter = ReferenceOutputter(sample_references, processed_files)

    outputter.print_by_alias()
    captured = capsys.readouterr()
    assert "Alias: Length" in captured.out
    assert "File: Test1.FCStd" in captured.out
    assert "Object: Box" in captured.out
    assert "Expression: <<globals>>#<<params>>.Length + 10" in captured.out


def test_print_empty_files(sample_references: dict[str, list[Reference]], capsys: pytest.CaptureFixture[str]) -> None:
    """Test printing list of files with no references."""
    processed_files = {"Test1.FCStd", "Empty.FCStd"}
    outputter = ReferenceOutputter(sample_references, processed_files)

    outputter.print_empty_files()
    captured = capsys.readouterr()
    assert "Files with no references:" in captured.out
    assert "Empty.FCStd" in captured.out


def test_none_filename_handling(sample_references: dict[str, list[Reference]]) -> None:
    """Test handling of references with None filename."""
    # Add a reference with None filename
    sample_references["Height"] = [
        Reference(
            filename=None,
            object_name="Box",
            expression="<<globals>>#<<params>>.Height",
            spreadsheet="params",
            alias="Height",
        )
    ]
    processed_files = {"Test1.FCStd"}
    outputter = ReferenceOutputter(sample_references, processed_files)

    # Test by-object format
    by_obj = outputter.format_by_object()
    assert "Height" not in str(by_obj)

    # Test by-file format
    by_file = outputter.format_by_file()
    assert "Height" not in str(by_file)

    # Test JSON output
    json_out = outputter.to_json()
    assert "Height" in json_out
    assert '"filename": null' in json_out


def test_multiple_references_by_object(sample_references: dict[str, list[Reference]]) -> None:
    """Test handling of multiple references in by-object format."""
    # Add another reference with the same alias
    sample_references["Length"].append(
        Reference(
            filename="Test1.FCStd",
            object_name="Box",
            expression="<<globals>>#<<params>>.Length * 2",
            spreadsheet="params",
            alias="Length",
        )
    )
    processed_files = {"Test1.FCStd"}
    outputter = ReferenceOutputter(sample_references, processed_files)

    by_obj = outputter.format_by_object()
    box_refs = by_obj["Test1.FCStd"]["Box"]["Length"]
    assert len(box_refs) == 2
    assert any(r.expression == "<<globals>>#<<params>>.Length + 10" for r in box_refs)
    assert any(r.expression == "<<globals>>#<<params>>.Length * 2" for r in box_refs)


def test_multiple_references_by_file(sample_references: dict[str, list[Reference]]) -> None:
    """Test handling of multiple references in by-file format."""
    # Add another reference with the same alias
    sample_references["Length"].append(
        Reference(
            filename="Test1.FCStd",
            object_name="Box",
            expression="<<globals>>#<<params>>.Length * 2",
            spreadsheet="params",
            alias="Length",
        )
    )
    processed_files = {"Test1.FCStd"}
    outputter = ReferenceOutputter(sample_references, processed_files)

    by_file = outputter.format_by_file()
    length_refs = by_file["Test1.FCStd"]["Length"]
    assert len(length_refs) == 2
    assert any(r.expression == "<<globals>>#<<params>>.Length + 10" for r in length_refs)
    assert any(r.expression == "<<globals>>#<<params>>.Length * 2" for r in length_refs)
