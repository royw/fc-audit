# FC-Audit

A command line tool for analyzing FreeCAD documents.

## Installation

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

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
  "references": {
    "filename.FCStd": {
      "object_name": {
        "alias_name": [
          "expression1",
          "expression2"
        ]
      }
    }
  }
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

Run tests:
```bash
pytest
```
