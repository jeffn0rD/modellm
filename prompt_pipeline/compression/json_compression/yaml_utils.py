"""
YAML utilities for JSON compression module.

This module provides utilities for converting YAML content to
JSON-compatible dictionaries.
"""

import json
from typing import Any, Dict

import yaml


def yaml_to_json_dict(yaml_content: str) -> Any:
    """Convert YAML content to JSON-compatible Python objects.
    
    This function parses YAML content and returns it as Python objects
    that are JSON-serializable (dict, list, str, int, float, bool, None).
    
    Args:
        yaml_content: YAML content as a string
        
    Returns:
        Python object representation of the YAML content
        
    Raises:
        yaml.YAMLError: If the YAML content is malformed
        ValueError: If the YAML content cannot be converted to JSON-compatible format
        
    Example:
        >>> yaml_content = "name: test\\nvalue: 42"
        >>> result = yaml_to_json_dict(yaml_content)
        >>> assert result == {"name": "test", "value": 42}
    """
    if not yaml_content:
        return {}
    
    # Parse YAML
    try:
        yaml_data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML content: {e}")
    
    if yaml_data is None:
        return {}
    
    # Ensure JSON compatibility by converting YAML-specific types
    return _make_json_compatible(yaml_data)


def _make_json_compatible(obj: Any) -> Any:
    """Recursively convert Python objects to JSON-compatible format.
    
    This function handles YAML-specific types like:
    - datetime objects (convert to ISO format strings)
    - OrderedDict (convert to dict)
    - set (convert to list)
    - tuple (convert to list)
    
    Args:
        obj: Python object to convert
        
    Returns:
        JSON-compatible Python object
    """
    if isinstance(obj, dict):
        # Recursively process dictionary values
        return {str(k): _make_json_compatible(v) for k, v in obj.items()}
    
    elif isinstance(obj, (list, tuple, set)):
        # Convert all sequences to lists
        return [_make_json_compatible(item) for item in obj]
    
    elif isinstance(obj, (str, int, float, bool, type(None))):
        # These types are already JSON-compatible
        return obj
    
    elif hasattr(obj, '__dict__'):
        # Handle objects with __dict__ (like datetime)
        try:
            # Try to convert to string representation
            return str(obj)
        except Exception:
            # Fallback to dict representation
            return _make_json_compatible(obj.__dict__)
    
    else:
        # For any other type, try to convert to string
        try:
            return str(obj)
        except Exception:
            return repr(obj)
