"""Module for handling FreeCAD document files."""
import html
import logging
import re
import xml.etree.ElementTree as etree
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


def is_fcstd_file(filepath: Path) -> bool:
    """Check if a file is a valid FCStd file.
    
    Args:
        filepath: Path to file to check
        
    Returns:
        True if file is a valid FCStd file, False otherwise
    """
    if not zipfile.is_zipfile(filepath):
        return False
        
    with zipfile.ZipFile(filepath) as zf:
        return "Document.xml" in zf.namelist()


def get_document_properties(filepath: Path) -> Set[str]:
    """Extract unique property names from a FreeCAD document.
    
    Args:
        filepath: Path to FCStd file
        
    Returns:
        Set of unique property names found in the document
        
    Raises:
        ValueError: If file is not a valid FCStd file
    """
    if not is_fcstd_file(filepath):
        raise ValueError(f"{filepath} is not a valid FCStd file")
        
    properties = set()
    with zipfile.ZipFile(filepath) as zf:
            
        with zf.open("Document.xml") as f:
            tree = etree.parse(f)
            root = tree.getroot()
            
            # Find all Property elements
            for prop in root.findall(".//Property"):
                if "name" in prop.attrib:
                    properties.add(prop.attrib["name"])
                    
    return properties


def get_cell_aliases(filepath: Path) -> Set[str]:
    """Extract unique cell aliases from a FreeCAD document.
    
    Args:
        filepath: Path to FCStd file
        
    Returns:
        Set of unique cell aliases found in the document
        
    Raises:
        ValueError: If file is not a valid FCStd file
    """
    if not is_fcstd_file(filepath):
        raise ValueError(f"{filepath} is not a valid FCStd file")
        
    aliases = set()
    with zipfile.ZipFile(filepath) as zf:
            
        with zf.open("Document.xml") as f:
            tree = etree.parse(f)
            root = tree.getroot()
            
            # Find all Cell elements with alias attributes
            for cell in root.findall(".//Cell[@alias]"):
                aliases.add(cell.attrib["alias"])
                    
    return aliases


def _find_parent_with_identifier(element: etree.Element, root: etree.Element) -> tuple[etree.Element | None, str]:
    """Find the nearest ancestor with an identifying attribute and its context string.
    
    An identifying attribute is one of:
    - name: The name of the object or element
    - type: The type of the object or element
    - label: A human-readable label for the object
    
    Args:
        element: Element to find parent for
        root: Root element of the XML tree
        
    Returns:
        Tuple of (parent element or None, context string)
        The context string is formatted as 'Tag[identifier]' where identifier
        is the value of the first identifying attribute found (name, type, or label)
    """
    for ancestor in root.findall(".//*"):
        for child in ancestor.findall(".//*"):
            if child == element:
                # Build context string from the ancestor's attributes
                if 'name' in ancestor.attrib:
                    return ancestor, f"{ancestor.tag}[{ancestor.attrib['name']}]"
                elif 'type' in ancestor.attrib:
                    return ancestor, f"{ancestor.tag}[{ancestor.attrib['type']}]"
                elif 'label' in ancestor.attrib:
                    return ancestor, f"{ancestor.tag}[{ancestor.attrib['label']}]"
                else:
                    return ancestor, ancestor.tag
    return None, "unknown"


def get_expressions(filepath: Path) -> Dict[str, str]:
    """Extract expressions from a FreeCAD document.
    
    Args:
        filepath: Path to FCStd file
        
    Returns:
        Dictionary mapping expression elements to their unescaped expressions
        
    Raises:
        ValueError: If file is not a valid FCStd file
    """
    if not is_fcstd_file(filepath):
        raise ValueError(f"{filepath} is not a valid FCStd file")
        
    expressions = {}
    with zipfile.ZipFile(filepath) as zf:
            
        with zf.open("Document.xml") as f:
            content = f.read().decode('utf-8')
            tree = etree.fromstring(content)
            root = tree
            
            # Find all Expression elements with expression attributes
            for expr in root.findall(".//Expression[@expression]"):
                # Find parent context
                _, context = _find_parent_with_identifier(expr, root)
                
                # Unescape the expression value
                value = html.unescape(expr.attrib["expression"])
                
                # Create a unique key by combining context with expression count
                key = context
                base_key = key
                counter = 1
                while key in expressions:
                    counter += 1
                    key = f"{base_key} ({counter})"
                
                expressions[key] = value
                    
    return expressions


@dataclass
class Reference:
    """A reference to a spreadsheet cell in a FreeCAD document.
    
    Attributes:
        object_name: Name of the object containing the reference
        expression: The full expression string containing the reference
        filename: Optional name of the file containing the reference
        spreadsheet: Optional name of the spreadsheet containing the referenced cell
        alias: The alias name of the referenced cell (empty if not found)
    """
    object_name: str
    expression: str
    filename: Optional[str] = None
    spreadsheet: Optional[str] = None
    alias: str = ''


def parse_reference(expr: str) -> Optional[str]:
    """Parse a reference from an expression.
    
    Format: [<<filename>>]#[<<spreadsheet>>].alias
    
    Args:
        expr: Expression to parse
        
    Returns:
        Alias name if found, None otherwise
    """
    # Pattern for optional <<name>> or name followed by # then optional <<name>> or name then . then name
    pattern = r'(?:<<([^>]+)>>|([^#]+))?#(?:<<([^>]+)>>|([^.]+))\.([^\s+\-*/()]+)'
    match = re.search(pattern, expr)
    if match:
        # The alias is always the last group
        return match.group(5)
    return None


def _parse_expression_element(expr_elem: etree.Element, obj_name: str, filename: str) -> Optional[Tuple[str, Reference]]:
    """Parse an Expression element and create a Reference if it contains an alias.
    
    Args:
        expr_elem: Expression element from XML containing an 'expression' attribute
        obj_name: Name of the parent Object containing this expression
        filename: Name of the FCStd file being parsed
        
    Returns:
        If the expression contains a valid alias reference:
            A tuple of (alias_name, Reference)
            where Reference contains the full context of the reference
        If no valid alias reference is found:
            None
    """
    try:
        expr = html.unescape(expr_elem.attrib["expression"])
        alias = parse_reference(expr)
        if alias:
            ref = Reference(
                object_name=obj_name,
                expression=expr,
                filename=filename
            )
            return alias, ref
    except KeyError:
        logging.warning(f"Expression element missing 'expression' attribute in {filename}")
    except Exception as e:
        logging.warning(f"Error parsing expression in {filename}: {e}")
    return None


def _parse_object_element(obj: etree.Element, filename: str) -> List[Tuple[str, Reference]]:
    """Parse an Object element and extract all references from its expressions.
    
    Args:
        obj: Object element from XML that may contain Expression elements
        filename: Name of the FCStd file being parsed
        
    Returns:
        List of (alias, Reference) tuples for each valid alias reference found
        in any Expression elements within this Object. Returns an empty list
        if no valid references are found or if the Object has no name attribute.
    """
    refs = []
    try:
        obj_name = obj.attrib["name"]
        for expr_elem in obj.findall(".//Expression[@expression]"):
            result = _parse_expression_element(expr_elem, obj_name, filename)
            if result:
                refs.append(result)
    except KeyError:
        logging.warning(f"Object element missing 'name' attribute in {filename}")
    except Exception as e:
        logging.warning(f"Error parsing object in {filename}: {e}")
    return refs


def _parse_document_references(content: str, filename: str) -> Dict[str, List[Reference]]:
    """Parse XML content to extract all alias references from a Document.
    
    Args:
        content: XML content from Document.xml as a string
        filename: Name of the FCStd file being parsed
        
    Returns:
        Dictionary mapping alias names to lists of Reference objects.
        Each Reference object contains the full context of where and how
        the alias is referenced. Returns an empty dict if the content
        is not valid XML or contains no valid references.
    """
    references: Dict[str, List[Reference]] = {}
    try:
        root = etree.fromstring(content)
        
        # Find all Expression elements with expression attributes
        for obj in root.findall(".//Object[@name]"):
            for alias, ref in _parse_object_element(obj, filename):
                if alias not in references:
                    references[alias] = []
                references[alias].append(ref)
                
        if not references:
            logging.info(f"No alias references found in {filename}")
    except etree.ParseError as e:
        logging.error(f"Failed to parse XML content from {filename}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error parsing {filename}: {e}")
    
    return references


def get_references(filepath: Path) -> Dict[str, List[Reference]]:
    """Extract alias references from a FreeCAD document.
    
    Args:
        filepath: Path to FCStd file
        
    Returns:
        Dictionary mapping alias names to list of references
        
    Raises:
        ValueError: If file is not a valid FCStd file
    """
    if not is_fcstd_file(filepath):
        raise ValueError(f"{filepath} is not a valid FCStd file")
    
    with zipfile.ZipFile(filepath) as zf:
        with zf.open('Document.xml') as f:
            content = f.read().decode('utf-8')
            return _parse_document_references(content, str(filepath))


def get_references_from_files(filepaths: List[Path]) -> Dict[str, List[Reference]]:
    """Extract alias references from multiple FreeCAD documents.
    
    Args:
        filepaths: List of paths to FCStd files
        
    Returns:
        Dictionary mapping alias names to list of references
    """
    all_references: Dict[str, List[Reference]] = {}
    for filepath in filepaths:
        try:
            file_refs = get_references(filepath)
            for alias, refs in file_refs.items():
                if alias not in all_references:
                    all_references[alias] = []
                # Add filename to each reference
                for ref in refs:
                    ref.filename = filepath.name
                all_references[alias].extend(refs)
        except ValueError as e:
            logging.warning(f"{e}")
            continue
            
    return all_references


def get_cell_aliases_from_files(filepaths: List[Path]) -> Set[str]:
    """Extract unique cell aliases from multiple FreeCAD documents.
    
    Args:
        filepaths: List of paths to FCStd files
        
    Returns:
        Set of unique cell aliases found across all documents
    """
    all_aliases = set()
    for filepath in filepaths:
        try:
            aliases = get_cell_aliases(filepath)
            all_aliases.update(aliases)
        except (ValueError, etree.ParseError) as e:
            logging.warning(f"{e}")
            continue
            
    return all_aliases


def get_properties_from_files(filepaths: List[Path]) -> Set[str]:
    """Extract unique property names from multiple FreeCAD documents.
    
    Args:
        filepaths: List of paths to FCStd files
        
    Returns:
        Set of unique property names found across all documents
    """
    all_properties = set()
    for filepath in filepaths:
        try:
            props = get_document_properties(filepath)
            all_properties.update(props)
        except ValueError as e:
            logging.warning(f"{e}")
            continue
            
    return all_properties
