---
title: FreeCAD Document Parser
---

This module provides functions for parsing FreeCAD document files (.FCStd) and extracting:

- Document properties
- Spreadsheet cell aliases
- References between documents

## Public Functions

::: fc_audit.fcstd.get_document_properties_with_context
    options:
      show_root_heading: true
      show_source: true

::: fc_audit.fcstd.get_cell_aliases
    options:
      show_root_heading: true
      show_source: true

## Protected Functions

These functions are for internal use within the module.
