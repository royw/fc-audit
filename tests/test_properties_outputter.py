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


def test_output_csv(test_files: list[Path], capsys: pytest.CaptureFixture[str]) -> None:
    """Test CSV output format."""
    outputter = PropertiesOutputter(test_files)
    outputter.output_csv()
    captured = capsys.readouterr()

    # Split output into lines and verify
    lines = captured.out.splitlines()
    assert lines[0] == '"file","object","property"'
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
    assert captured.out.strip() == '"file","object","property"'


def test_output_text_format_via_args(test_files: list[Path], capsys: pytest.CaptureFixture[str]) -> None:
    """Test output method with text format (default)."""
    outputter = PropertiesOutputter(test_files)
    args = argparse.Namespace(json=False, csv=False)

    outputter.output(args)
    captured = capsys.readouterr()
    assert "Author" in captured.out


def test_output_json_via_args(test_files: list[Path], capsys: pytest.CaptureFixture[str]) -> None:
    """Test output method with JSON format."""
    outputter = PropertiesOutputter(test_files)
    args = argparse.Namespace(json=True, csv=False)

    outputter.output(args)
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert isinstance(output, list)


def test_output_csv_via_args(test_files: list[Path], capsys: pytest.CaptureFixture[str]) -> None:
    """Test output method with CSV format."""
    outputter = PropertiesOutputter(test_files)
    args = argparse.Namespace(json=False, csv=True)

    outputter.output(args)
    captured = capsys.readouterr()
    assert captured.out.startswith('"file","object","property"')
