# Announcing fc-audit, a command line tool for analyzing FreeCAD documents.

Package available on PyPI: https://pypi.org/project/fc-audit/

Source available on GitHub: https://github.com/royw/fc-audit/

Detailed instructions on both of the above sites.

## TL;DR

Requires python >= 3.11
```bash
pipx install fc-audit
fc-audit --help
```

## Examples

Note: using the --filter option to keep the output short.

### Aliases

The spreadsheet, params, is in globals.FCStd
```
➤ fc-audit aliases --filter "Hull*,Cabin*" globals.FCStd
CabinCornerRadius
CabinHeight
CabinLength
CabinWallThickness
CabinWidth
HullFullLength
HullFullWidth
HullHeight
HullLength
HullLowerLength
HullLowerWidth
HullWidth
```
---

### References --by-alias (default)

For references is ok to include the spreadsheet document file, but not necessary
```
➤ fc-audit references --filter "Hull*" data/LiftFan.FCStd globals.FCStd
Alias: HullFullLength
  File: LiftFan.FCStd
    Object: Sketch025
      Expression: <<globals>>#<<params>>.HullFullLength / 2
Alias: HullHeight
  File: Hull.FCStd
    Object: Pad002
      Expression: <<globals>>#<<params>>.HullHeight
    Object: Pocket
      Expression: <<globals>>#<<params>>.HullHeight - <<globals>>#<<params>>.DeckThickness
    Object: Sketch001
      Expression: -<<globals>>#<<params>>.HullHeight
  File: LiftFan.FCStd
    Object: Sketch020
      Expression: <<params>>.HullHeight
    Object: Sketch022
      Expression: <<globals>>#<<params>>.HullHeight
    Object: Sketch025
      Expression: <<params>>.HullHeight
Alias: HullLength
  File: Hull.FCStd
    Object: Sketch
      Expression: <<globals>>#<<params>>.HullLength
Alias: HullLowerLength
  File: Hull.FCStd
    Object: Sketch
      Expression: <<globals>>#<<params>>.HullLowerLength
Alias: HullLowerWidth
  File: Hull.FCStd
    Object: Sketch
      Expression: <<globals>>#<<params>>.HullLowerWidth
Alias: HullWidth
  File: Hull.FCStd
    Object: Sketch
      Expression: <<globals>>#<<params>>.HullWidth
```
---

### References --by-file

Not including globals.FCStd
```
➤ fc-audit references --filter "Hull*" --by-file Hull.FCStd LiftFan.FCStd
File: Hull.FCStd
  Alias: HullHeight
    Object: Pad002
      Expression: <<globals>>#<<params>>.HullHeight
    Object: Pocket
      Expression: <<globals>>#<<params>>.HullHeight - <<globals>>#<<params>>.DeckThickness
    Object: Sketch001
      Expression: -<<globals>>#<<params>>.HullHeight
  Alias: HullLength
    Object: Sketch
      Expression: <<globals>>#<<params>>.HullLength
  Alias: HullLowerLength
    Object: Sketch
      Expression: <<globals>>#<<params>>.HullLowerLength
  Alias: HullLowerWidth
    Object: Sketch
      Expression: <<globals>>#<<params>>.HullLowerWidth
  Alias: HullWidth
    Object: Sketch
      Expression: <<globals>>#<<params>>.HullWidth
File: LiftFan.FCStd
  Alias: HullFullLength
    Object: Sketch025
      Expression: <<globals>>#<<params>>.HullFullLength / 2
  Alias: HullHeight
    Object: Sketch020
      Expression: <<params>>.HullHeight
    Object: Sketch022
      Expression: <<globals>>#<<params>>.HullHeight
    Object: Sketch025
      Expression: <<params>>.HullHeight
```
---

### References --by-object

For brevity, only showing one file
```
➤ fc-audit references --filter "Hull*" --by-object LiftFan.FCStd
Object: Sketch020
  File: LiftFan.FCStd
    Alias: HullHeight
      Expression: <<params>>.HullHeight
Object: Sketch022
  File: LiftFan.FCStd
    Alias: HullHeight
      Expression: <<globals>>#<<params>>.HullHeight
Object: Sketch025
  File: LiftFan.FCStd
    Alias: HullFullLength
      Expression: <<globals>>#<<params>>.HullFullLength / 2
    Alias: HullHeight
      Expression: <<params>>.HullHeight
```
---

### References --csv

CSV is good for importing into other programs, like spreadsheets.
```
➤ fc-audit references --filter "Hull*" --csv Hull.FCStd LiftFan.FCStd
"alias","filename","object_name","expression"
"HullFullLength","LiftFan.FCStd","Sketch025","<<globals>>#<<params>>.HullFullLength / 2"
"HullHeight","Hull.FCStd","Pad002","<<globals>>#<<params>>.HullHeight"
"HullHeight","Hull.FCStd","Pocket","<<globals>>#<<params>>.HullHeight - <<globals>>#<<params>>.DeckThickness"
"HullHeight","Hull.FCStd","Sketch001","-<<globals>>#<<params>>.HullHeight"
"HullHeight","LiftFan.FCStd","Sketch020","<<params>>.HullHeight"
"HullHeight","LiftFan.FCStd","Sketch022","<<globals>>#<<params>>.HullHeight"
"HullHeight","LiftFan.FCStd","Sketch025","<<params>>.HullHeight"
"HullLength","Hull.FCStd","Sketch","<<globals>>#<<params>>.HullLength"
"HullLowerLength","Hull.FCStd","Sketch","<<globals>>#<<params>>.HullLowerLength"
"HullLowerWidth","Hull.FCStd","Sketch","<<globals>>#<<params>>.HullLowerWidth"
"HullWidth","Hull.FCStd","Sketch","<<globals>>#<<params>>.HullWidth"
```
---

### References --json

Also can output JSON
```
➤ fc-audit references --filter "Hull*" --json LiftFan.FCStd
{
  "HullHeight": [
    {
      "object_name": "Sketch020",
      "expression": "<<params>>.HullHeight",
      "filename": "LiftFan.FCStd",
      "spreadsheet": "params"
    },
    {
      "object_name": "Sketch022",
      "expression": "<<globals>>#<<params>>.HullHeight",
      "filename": "LiftFan.FCStd",
      "spreadsheet": "params"
    },
    {
      "object_name": "Sketch025",
      "expression": "<<params>>.HullHeight",
      "filename": "LiftFan.FCStd",
      "spreadsheet": "params"
    }
  ],
  "HullFullLength": [
    {
      "object_name": "Sketch025",
      "expression": "<<globals>>#<<params>>.HullFullLength / 2",
      "filename": "LiftFan.FCStd",
      "spreadsheet": "params"
    }
  ]
}

### Properties --filter

Not sure how useful this is, but here it is...
```
➤ fc-audit properties --filter "Link*" LiftFan.FCStd
LinkClaimChild
LinkCopyOnChange
LinkCopyOnChangeGroup
LinkCopyOnChangeSource
LinkCopyOnChangeTouched
LinkExecute
LinkPlacement
LinkTransform
LinkedObject
```
---

Enjoy!

Roy
