"""Module for handling references to FreeCAD spreadsheet cells.

This module provides the Reference class which represents a reference to a cell
in a FreeCAD spreadsheet. These references can be found in expressions within
FreeCAD documents, where one object refers to a value in a spreadsheet cell.

Example:
    ```python
    # A reference to a cell with alias 'Width' in 'Spreadsheet' of 'Body'
    ref = Reference(object_name="Body", expression="<<Spreadsheet>>.Width", spreadsheet="Spreadsheet", alias="Width")
    ```
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Reference:
    """A reference to a spreadsheet cell in a FreeCAD document.

    This class represents a reference from one object to a cell in a FreeCAD
    spreadsheet. It captures all the components needed to uniquely identify
    both the source and target of the reference.

    Attributes:
        object_name: Name of the object containing the reference (e.g., 'Body', 'Sketch')
        expression: The full expression string containing the reference (e.g., '<<Sheet>>.Width * 2')
        filename: Optional name of the file containing the reference, for external references
        spreadsheet: Optional name of the target spreadsheet (e.g., 'Sheet')
        alias: Optional alias name used in the reference (e.g., 'Width')

    Example:
        ```python
        # Internal reference to a cell in the same document
        ref = Reference(object_name="Sketch001", expression="<<Sheet>>.Length", spreadsheet="Sheet", alias="Length")

        # External reference to a cell in another document
        ref = Reference(
            object_name="Body",
            expression="<<../parts/base.FCStd#Sheet.Width>>",
            filename="../parts/base.FCStd",
            spreadsheet="Sheet",
            alias="Width",
        )
        ```
    """

    object_name: str
    expression: str
    filename: str | None = None
    spreadsheet: str | None = None
    alias: str = ""
