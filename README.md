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

## Usage

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

# JSON output format
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
1. File: The FCStd file containing the references
2. Object: The object within the file using the alias
3. Alias: The alias being referenced
4. Expressions: List of expressions using the alias

# Show Hull width and length
fc-audit get-references --aliases "Hull[WL]*" file.FCStd

# Multiple patterns
fc-audit get-references --aliases "Fan*,Hull*" file.FCStd
```

For more information on available commands:

```bash
fc-audit --help
```

## Development

### Setup

This example uses uv, but you can use any other tool you prefer.

```bash
# Create and activate virtual environment
uv venv
source .venv/bin/activate

# Install for development
uv pip install -e ".[dev]"

# Or install for use
uv pip install .
```

### Testing
```bash
# Run tests with coverage
pytest --cov=src.fc_audit

# Run tests verbosely
pytest -v

tox

uvx --python 3.11 tox
```


Current test coverage:
- Overall: 89%
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
