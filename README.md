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

The recommended way to install fc-audit is using [pipx](https://pypa.github.io/pipx/), which installs the tool in an isolated environment.

1. First, install pipx:

   **Linux**:

   Using package managers:
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install pipx
   pipx ensurepath

   # Fedora
   sudo dnf install pipx
   pipx ensurepath

   # Arch Linux
   sudo pacman -S python-pipx
   pipx ensurepath
   ```

   Or using pip:
   ```bash
   python3 -m pip install --user pipx
   python3 -m pipx ensurepath
   ```

   **macOS**:
   ```bash
   brew install pipx
   pipx ensurepath
   ```

   **Windows**:
   ```powershell
   py -3 -m pip install --user pipx
   py -3 -m pipx ensurepath
   ```

2. Then install fc-audit:
   ```bash
   pipx install fc-audit
   ```

After installation, verify it works:
```bash
fc-audit --version
```

Requirements:

- Python 3.11 or higher
- FreeCAD documents in [FCStd format](https://wiki.freecad.org/File_Format_FCStd)

## CLI Usage

### Aliases

Extract cell aliases from one or more FreeCAD documents:

```bash
fc-audit aliases file1.FCStd [file2.FCStd ...]
```

### Properties

Extract unique property names from one or more FreeCAD documents:

```bash
fc-audit properties file1.FCStd [file2.FCStd ...]
```

### References

Extract and analyze alias references from expressions in FreeCAD documents. For each alias, show which objects reference it and their expressions.

By default, all discovered aliases will be shown:
```bash
# Show all aliases found in the documents
fc-audit references file1.FCStd [file2.FCStd ...]
```

Use `--aliases` to filter and show only specific aliases:
```bash
# Filter to show only specific aliases
fc-audit references --aliases alias1,alias2 file1.FCStd [file2.FCStd ...]
```

Options:
- `--aliases`: Optional. Comma-separated list of aliases to show. When not specified, all discovered aliases will be shown. Supports wildcards like `*` and `?` (e.g., `Fan*` matches all aliases starting with "Fan").  Note, you should quote the list of aliases if you are using shell wildcards, for example: `--aliases "Fan*"`

Output Format Options:
You must choose exactly one of these output formats:

- `--by-alias`: Group output by alias (default)
- `--by-object`: Group output by file and object
- `--by-file`: Group output by file and alias
- `--json`: Output in JSON format for programmatic use
- `--csv`: Output as comma-separated values (CSV)

Note: These format options are mutually exclusive - you cannot use more than one at a time.

Examples:
```bash
# Show all Fan-related aliases (default format)
fc-audit references --aliases "Fan*" file.FCStd

# Show all Fan-related aliases grouped by file
fc-audit references --by-file --aliases "Fan*" file.FCStd

# Show all Fan-related aliases grouped by object
fc-audit references --by-object --aliases "Fan*" file.FCStd

# Get JSON output for programmatic use
fc-audit references --json --aliases "Fan*" file.FCStd > fan_refs.json

# Get CSV output for spreadsheet analysis
fc-audit references --csv --aliases "Fan*" file.FCStd > fan_refs.csv

# Show Hull width and length
fc-audit references --aliases "Hull[WL]*" file.FCStd

# Show multiple aliases
fc-audit references --aliases "Fan*,Hull*" file.FCStd
```

For more information on available commands:

```bash
fc-audit --help
```


### Text Output Formats

#### --by-alias (default)
Groups references by alias name, then by file and object:
```
Alias: FanDiameter
  File: DriveFans.FCStd
    Object: Sketch
      Expression: <<params>>.FanDiameter
      Expression: <<params>>.FanDiameter + 2 * <<params>>.WallThickness
    Object: Sketch002
      Expression: <<params>>.FanDiameter
```

#### --by-file
Groups references by file, then by alias and object:
```
File: DriveFans.FCStd
  Alias: FanDiameter
    Object: Sketch
      Expression: <<params>>.FanDiameter
      Expression: <<params>>.FanDiameter + 2 * <<params>>.WallThickness
    Object: Sketch002
      Expression: <<params>>.FanDiameter
```

#### --by-object
Groups references by object, then by file and alias:
```
Object: Sketch
  File: DriveFans.FCStd
    Alias: FanDiameter
      Expression: <<params>>.FanDiameter
      Expression: <<params>>.FanDiameter + 2 * <<params>>.WallThickness
```

### CSV output format

The CSV output has the following columns:

- `alias`: The name of the parameter
- `filename`: The FreeCAD file containing the reference
- `object_name`: The name of the object using the parameter
- `expression`: The expression containing the parameter reference

Example CSV output:
```csv
alias,filename,object_name,expression
"FanDiameter","file.FCStd","Sketch","<<params>>.FanDiameter"
"FanHeight","file.FCStd","Pad001","<<params>>.FanHeight"
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

## Development

### Setup

This example uses [uv](https://github.com/astral-sh/uv), but you can use any tool (hatch, poetry, etc.) you prefer.

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

# Or use the entry point script in your virtual environment's bin directory
fc-audit --help
```

### Development Tasks

This project uses [Task](https://taskfile.dev/) to manage development tasks. After installing Task, you can run:

```bash
# Show all available tasks
task --list-all

# Run all CI checks (recommended before submitting a PR)
task ci
```

The `task ci` command runs the following checks:

1. Code quality checks (ruff and mypy)
2. Code metrics
3. Tests with coverage report (minimum 85% coverage)
4. Documentation build
5. Package build

You can also run individual tasks:

```bash
# Run tests
task test

# Run tests with coverage report
task test:coverage

# Run linting
task lint

# Format code
task format

# Run type checks
task lint:mypy

# Build documentation
task docs:build

# Serve documentation locally
task docs
```

### Pre-commit Hooks

pre-commit hooks run automatically on `git commit` to ensure code quality and consistency. To set up:

```bash
# Install pre-commit in your environment
uv pip install pre-commit

# Optional: Run hooks on all files
pre-commit run --all-files

# Run specific hooks
pre-commit run ruff --all-files
pre-commit run mypy --all-files
```

Note: If you get a "No module named pre_commit" error, try running `pre-commit install` in your virtual environment.
Resetting your virtual environment may cause this error.

### Configured Hooks

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


### Documentation

We use [MkDocs](https://www.mkdocs.org/) with the [Material theme](https://squidfunk.github.io/mkdocs-material/) for documentation. The documentation includes:

- User Guide
- API Reference
- Development Guide

#### Building Documentation

```bash
# Build and serve documentation locally
task docs
```

#### Manual Steps

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
fc-audit -v references file.FCStd
```

Optionally, log to a file:
```bash
fc-audit --log-file audit.log references file.FCStd
```

## Contributing

Thank you for your interest in contributing to fc-audit! This document provides guidelines and instructions for contributing to the project.

### Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and quality checks:
   ```bash
   task ci
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
