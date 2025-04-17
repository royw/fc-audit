# FC-Audit

A command line tool for analyzing FreeCAD documents. FC-Audit helps you understand how your FreeCAD models are structured by extracting and analyzing:

- Property names used in objects
- Cell aliases in spreadsheets
- Expressions and their dependencies
- References between objects and spreadsheet cells

This is particularly useful for:
- Debugging complex parametric models
- Finding dependencies between parts
- Auditing spreadsheet usage
- Analyzing model structure

## Installation

TBD

Requirements:

- Python 3.10 or higher
- FreeCAD documents in FCStd format

## CLI Usage

### Get Properties

Extract unique property names from one or more FreeCAD documents:

```bash
fc-audit get-properties file1.FCStd [file2.FCStd ...]
```

### Get Cell Aliases

Extract cell aliases from one or more FreeCAD documents:

```bash
fc-audit get-aliases file1.FCStd [file2.FCStd ...]
```

### Get Expressions

Extract and unescape expressions from one or more FreeCAD documents:

```bash
fc-audit get-expressions file1.FCStd [file2.FCStd ...]
```

### Get References

Extract and analyze alias references from expressions in FreeCAD documents. For each alias, shows which objects reference it and their expressions.

By default, all discovered aliases will be shown:
```bash
# Show all aliases found in the documents
fc-audit get-references file1.FCStd [file2.FCStd ...]
```

Use `--aliases` to filter and show only specific aliases:
```bash
# Filter to show only specific aliases
fc-audit get-references --aliases alias1,alias2 file1.FCStd [file2.FCStd ...]
```

Options:
- `--aliases`: Optional. Comma-separated list of aliases to show. When not specified, all discovered aliases will be shown. Supports wildcards like `*` and `?` (e.g., `Fan*` matches all aliases starting with "Fan").

Output Format Options:
You must choose exactly one of these output formats:

- `--by-alias`: Group output by alias (default)
- `--by-object`: Group output by file and object
- `--by-file`: Group output by file and alias
- `--json`: Output in JSON format for programmatic use

Note: These format options are mutually exclusive - you cannot use more than one at a time.

Examples:
```bash
# Show all Fan-related aliases (default format)
fc-audit get-references --aliases "Fan*" file.FCStd

# Show all Fan-related aliases grouped by file
fc-audit get-references --by-file --aliases "Fan*" file.FCStd

# Show all Fan-related aliases grouped by object
fc-audit get-references --by-object --aliases "Fan*" file.FCStd

# Get JSON output for programmatic use
fc-audit get-references --json --aliases "Fan*" file.FCStd > fan_refs.json
```

### JSON output format

```json
{
  "alias_name": [
    {
      "filename": "filename.FCStd",
      "object_name": "object_name",
      "expression": "expression",
      "spreadsheet": "spreadsheet_name",
      "alias": "alias_name"
    }
  ]
}
```

The JSON output is organized by:

1. `filename`: The FCStd file containing the references
2. `object_name`: The object within the file using the alias
3. `alias_name`: The alias being referenced
4. `expressions`: List of expressions using the alias

### Show Hull width and length
```bash
fc-audit get-references --aliases "Hull[WL]*" file.FCStd
```

### Multiple patterns
```bash
fc-audit get-references --aliases "Fan*,Hull*" file.FCStd
```

For more information on available commands:

```bash
fc-audit --help
```

## Development

### Setup

This example uses [uv](https://github.com/astral-sh/uv), but you can use any other tool you prefer.

```bash
# Create and activate virtual environment
uv venv
source .venv/bin/activate

# Install for development
uv pip install -e ".[dev]"
```

### Running fc-audit in Development

After installing in development mode, you can run fc-audit directly:

```bash
# Run from the project root
python -m fc_audit --help

# Or use the entry point script
fc-audit --help
```

### Testing and Code Quality Tools

#### Running Tests with pytest
```bash
# Run all tests
pytest

# Run tests with coverage report
pytest --cov

# Run tests verbosely
pytest -v

# Run specific test file
pytest tests/test_cli.py

# Run specific test
pytest tests/test_cli.py::test_parse_args
```

#### Running Type Checks with mypy
```bash
# Check all files
mypy src tests

# Check specific file
mypy src/fc_audit/cli.py
```

#### Running Linting with ruff
```bash
# Check all files
ruff check src tests

# Fix issues automatically
ruff check --fix src tests

# Check specific file
ruff check src/fc_audit/cli.py
```

#### Setting up pre-commit hooks

pre-commit hooks run automatically on `git commit` to ensure code quality and consistency. To set up:

```bash
# Install pre-commit in your environment
pre-commit install

# Optional: Run hooks on all files
pre-commit run --all-files

# Run specific hooks
pre-commit run ruff --all-files
pre-commit run mypy --all-files
```

Configured hooks:

1. File Formatting and Validation:
   - Trailing whitespace removal
   - End of file fixing (ensures files end with newline)
   - YAML/TOML validation
   - Large file checks
   - Merge conflict detection
   - Debug statement detection
   - Case conflict detection
   - Mixed line ending fixing

2. Code Style (ruff):
   - PEP 8 style guide enforcement
   - Code formatting
   - Import sorting
   - Dead code elimination

3. Type Checking (mypy):
   - Static type checking
   - Strict mode enabled
   - Type stub validation

To bypass pre-commit hooks in emergency situations:
```bash
git commit -m "message" --no-verify
```

Note: Using `--no-verify` is discouraged as it skips important quality checks.

#### Running All Checks with tox
```bash
# Run all environments
tox

# Run specific environment
tox -e py312
tox -e lint
tox -e type

# Run with specific Python version
uvx --python 3.11 tox
```

Tox environments:
- `py310`, `py311`, `py312`: Run tests on different Python versions
- `lint`: Run code style checks with ruff
- `type`: Run type checks with mypy

Current test coverage:
- Overall: 89%

### Documentation

We use [MkDocs](https://www.mkdocs.org/) with the [Material theme](https://squidfunk.github.io/mkdocs-material/) for documentation. The documentation includes:

- User Guide
- API Reference
- Development Guide

#### Building Documentation
```bash
# Install documentation dependencies
uv pip install -e ".[dev]"

# Build the documentation
mkdocs build

# Serve documentation locally
mkdocs serve
```

After running `mkdocs serve`, visit [http://127.0.0.1:8000](http://127.0.0.1:8000) to view the documentation.

- cli.py: 88%
- fcstd.py: 91%

### Error Handling

The tool provides detailed error messages and handles common issues:

- Invalid FCStd files
- Missing or corrupted Document.xml
- Invalid XML content
- Missing attributes or elements

Use the `-v` or `--verbose` flag for detailed logging:
```bash
fc-audit -v get-references file.FCStd
```

Optionally, log to a file:
```bash
fc-audit --log-file audit.log get-references file.FCStd
```

## Contributing

Thank you for your interest in contributing to fc-audit! This document provides guidelines and instructions for contributing to the project.

### Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and quality checks:
   ```bash
   tox
   ```
5. Update documentation if needed
6. Submit a pull request

### Code Style and Quality

We use several tools to maintain code quality:

1. **pre-commit hooks**: Automatically check code style and quality on commit
2. **ruff**: Python linter and code formatter
3. **mypy**: Static type checker
4. **pytest**: Test framework

See the [Testing and Code Quality Tools](#testing-and-code-quality-tools) section for details on using these tools.
