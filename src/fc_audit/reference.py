"""Reference class for FreeCAD spreadsheet cell references."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Reference:
    """A reference to a spreadsheet cell in a FreeCAD document."""

    object_name: str
    expression: str
    filename: str | None = None
    spreadsheet: str | None = None
    alias: str = ""
