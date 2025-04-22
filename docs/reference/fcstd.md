---
title: FreeCAD Document Handling
---

This page documents the FreeCAD document handling functionality. The fcstd module is responsible for:

- Parsing FreeCAD document files (FCStd format)
- Extracting properties, aliases, and expressions
- Analyzing references between objects
- Managing document context and state

This module is the core of fc-audit's functionality, providing a high-level API for working with FreeCAD documents.

::: fc_audit.fcstd
    options:
      show_root_heading: true
      show_source: true
