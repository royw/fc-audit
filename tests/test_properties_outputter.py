"""Tests for properties_outputter.py module."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from fc_audit.properties_outputter import PropertiesOutputter


@pytest.fixture
def test_files() -> list[Path]:
    """Create test files with properties."""
    return [Path("tests/data/Test1.FCStd")]


def test_properties_outputter_init(test_files: list[Path]) -> None:
    """Test PropertiesOutputter initialization."""
    outputter = PropertiesOutputter(test_files)
    assert len(outputter.file_properties) > 0


def test_output_text(test_files: list[Path], capsys: pytest.CaptureFixture[str]) -> None:
    """Test text output format."""
    outputter = PropertiesOutputter(test_files)
    outputter.output_text()
    captured = capsys.readouterr()

    # Verify output structure - just a list of properties
    lines = captured.out.splitlines()
    assert "Author" in lines
    assert "Comment" in lines
    assert "Company" in lines


def test_output_by_file(test_files: list[Path], capsys: pytest.CaptureFixture[str]) -> None:
    """Test by-file output format."""
    outputter = PropertiesOutputter(test_files)
    outputter.output_by_file()
    captured = capsys.readouterr()

    # Verify output structure
    lines = captured.out.splitlines()
    assert any(line.startswith("File: ") for line in lines)
    assert any(line.strip().startswith("Property: ") for line in lines)


def test_output_by_object(test_files: list[Path], capsys: pytest.CaptureFixture[str]) -> None:
    """Test by-object output format."""
    outputter = PropertiesOutputter(test_files)
    outputter.output_by_object()
    captured = capsys.readouterr()

    # Verify output structure
    lines = captured.out.splitlines()
    assert any(line.startswith("File: ") for line in lines)
    assert any(line.strip().startswith("Object: ") for line in lines)


def test_output_json(test_files: list[Path], capsys: pytest.CaptureFixture[str]) -> None:
    """Test JSON output format."""
    outputter = PropertiesOutputter(test_files)
    outputter.output_json()
    captured = capsys.readouterr()

    # Parse JSON output and verify structure
    output = json.loads(captured.out)
    assert isinstance(output, list)
    for file_data in output:
        assert "file" in file_data
        assert "properties" in file_data
        for prop in file_data["properties"]:
            assert "name" in prop
            assert "object" in prop
            assert "value" in prop


def test_output_csv(test_files: list[Path], capsys: pytest.CaptureFixture[str]) -> None:
    """Test CSV output format."""
    outputter = PropertiesOutputter(test_files)
    outputter.output_csv()
    captured = capsys.readouterr()

    # Split output into lines and verify
    lines = captured.out.splitlines()
    assert lines[0] == '"file","object","property","value"'
    assert len(lines) > 1  # At least header + one data row


def test_empty_properties(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test handling of empty properties."""
    empty_file = tmp_path / "empty.FCStd"
    empty_file.touch()
    outputter = PropertiesOutputter([empty_file])

    # Test text output - should be empty
    outputter.output_text()
    captured = capsys.readouterr()
    assert not captured.out.strip()

    # Test JSON output - should be empty list
    outputter.output_json()
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert output == []

    # Test CSV output - should only have header
    outputter.output_csv()
    captured = capsys.readouterr()
    assert captured.out.strip() == '"file","object","property","value"'


def test_output_method(test_files: list[Path], capsys: pytest.CaptureFixture[str]) -> None:
    """Test output method with different formats."""
    outputter = PropertiesOutputter(test_files)

    # Test with text format (default)
    args = argparse.Namespace(json=False, csv=False, by_file=False, by_object=False)
    outputter.output(args)
    captured = capsys.readouterr()
    assert "Author" in captured.out

    # Test with by-file format
    args = argparse.Namespace(json=False, csv=False, by_file=True, by_object=False)
    outputter.output(args)
    captured = capsys.readouterr()
    assert "File:" in captured.out
    assert "Property:" in captured.out

    # Test with by-object format
    args = argparse.Namespace(json=False, csv=False, by_file=False, by_object=True)
    outputter.output(args)
    captured = capsys.readouterr()
    assert "File:" in captured.out
    assert "Object:" in captured.out

    # Test with JSON format
    args = argparse.Namespace(json=True, csv=False, by_file=False, by_object=False)
    outputter.output(args)
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert isinstance(output, list)

    # Test with CSV format
    args = argparse.Namespace(json=False, csv=True, by_file=False, by_object=False)
    outputter.output(args)
    captured = capsys.readouterr()
    assert captured.out.startswith('"file","object","property","value"')
