---
title: Command Line Parser
---

This page documents the command-line argument parser for fc-audit. The parser module handles:

- Definition of command-line arguments and subcommands
- Setting up format options (text, JSON, CSV)
- Setting default values for arguments
- Validation of input parameters

The module provides a clean interface for defining and parsing command-line arguments.

::: fc_audit.parser.parse_args
    options:
        show_root_heading: true
        show_source: true
