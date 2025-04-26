"""Tests for the AliasOutputter class."""

from __future__ import annotations

import argparse
import json

import pytest

from fc_audit.alias_outputter import AliasOutputter


@pytest.fixture
def sample_aliases() -> set[str]:
    """Sample aliases for testing."""
    return {"Width", "Height", "Length"}


@pytest.fixture
def empty_aliases() -> set[str]:
    """Empty set of aliases for testing."""
    return set()


def test_init(sample_aliases: set[str]) -> None:
    """Test AliasOutputter initialization."""
    outputter = AliasOutputter(sample_aliases)
    assert outputter.aliases == sample_aliases


def test_output_json(sample_aliases: set[str], capsys: pytest.CaptureFixture[str]) -> None:
    """Test JSON output format."""
    outputter = AliasOutputter(sample_aliases)
    outputter._output_json()
    captured = capsys.readouterr()
    output = json.loads(captured.out)

    assert isinstance(output, dict)
    assert "aliases" in output
    assert isinstance(output["aliases"], list)
    assert set(output["aliases"]) == sample_aliases
    assert output["aliases"] == sorted(sample_aliases)  # Check sorting


def test_output_json_empty(empty_aliases: set[str], capsys: pytest.CaptureFixture[str]) -> None:
    """Test JSON output with empty aliases."""
    outputter = AliasOutputter(empty_aliases)
    outputter._output_json()
    captured = capsys.readouterr()
    output = json.loads(captured.out)

    assert output == {"aliases": []}


def test_output_text(sample_aliases: set[str], capsys: pytest.CaptureFixture[str]) -> None:
    """Test text output format."""
    outputter = AliasOutputter(sample_aliases)
    outputter._output_text()
    captured = capsys.readouterr()
    lines = captured.out.splitlines()

    assert len(lines) > 0
    assert {line.strip() for line in lines} == sample_aliases


def test_output_text_empty(empty_aliases: set[str], capsys: pytest.CaptureFixture[str]) -> None:
    """Test text output with empty aliases."""
    outputter = AliasOutputter(empty_aliases)
    outputter._output_text()
    captured = capsys.readouterr()
    lines = captured.out.splitlines()

    assert len(lines) == 0  # no aliases


def test_output_csv(sample_aliases: set[str], capsys: pytest.CaptureFixture[str]) -> None:
    """Test CSV output format."""
    outputter = AliasOutputter(sample_aliases)
    outputter._output_csv()
    captured = capsys.readouterr()
    lines = captured.out.splitlines()

    assert lines[0] == "Alias"  # Header
    assert set(lines[1:]) == sample_aliases
    assert lines[1:] == sorted(lines[1:])  # Check sorting


def test_output_csv_empty(empty_aliases: set[str], capsys: pytest.CaptureFixture[str]) -> None:
    """Test CSV output with empty aliases."""
    outputter = AliasOutputter(empty_aliases)
    outputter._output_csv()
    captured = capsys.readouterr()
    lines = captured.out.splitlines()

    assert lines[0] == "Alias"  # Header
    assert len(lines) == 1  # Only header, no aliases


def test_output_json_format(sample_aliases: set[str], capsys: pytest.CaptureFixture[str]) -> None:
    """Test output method with JSON format."""
    outputter = AliasOutputter(sample_aliases)
    args = argparse.Namespace(json=True, csv=False)
    outputter.output(args)
    captured = capsys.readouterr()
    output = json.loads(captured.out)

    assert isinstance(output, dict)
    assert "aliases" in output
    assert set(output["aliases"]) == sample_aliases


def test_output_csv_format(sample_aliases: set[str], capsys: pytest.CaptureFixture[str]) -> None:
    """Test output method with CSV format."""
    outputter = AliasOutputter(sample_aliases)
    args = argparse.Namespace(json=False, csv=True)
    outputter.output(args)
    captured = capsys.readouterr()
    lines = captured.out.splitlines()

    assert lines[0] == "Alias"
    assert set(lines[1:]) == sample_aliases


def test_output_text_format(sample_aliases: set[str], capsys: pytest.CaptureFixture[str]) -> None:
    """Test output method with text format."""
    outputter = AliasOutputter(sample_aliases)
    args = argparse.Namespace(json=False, csv=False)
    outputter.output(args)
    captured = capsys.readouterr()
    lines = captured.out.splitlines()

    assert len(lines) > 0
    assert {line.strip() for line in lines} == sample_aliases
