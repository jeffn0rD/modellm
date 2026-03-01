"""
YAML utilities for JSON compression module.

This module provides utilities for converting YAML content to
JSON-compatible dictionaries.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

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


def validate_yaml(
    yaml_content: str,
    schema: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, Optional[str]]:
    """Validate YAML content, optionally against a JSON schema.
    
    This function validates YAML content for syntax correctness and
    optionally validates it against a provided JSON schema.
    
    Args:
        yaml_content: YAML content as a string
        schema: Optional JSON schema to validate against
        
    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if valid
        - (False, error_message) if invalid
        
    Example:
        >>> yaml_content = "name: test\\nvalue: 42"
        >>> is_valid, error = validate_yaml(yaml_content)
        >>> assert is_valid == True
    """
    # Check if content is empty
    if not yaml_content:
        return False, "YAML content is empty"
    
    # Parse YAML
    try:
        yaml_data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        return False, f"Invalid YAML syntax: {e}"
    
    if yaml_data is None:
        return False, "YAML content is null or empty"
    
    # Validate against schema if provided
    if schema:
        try:
            import jsonschema
            
            # Validate using jsonschema
            jsonschema.validate(instance=yaml_data, schema=schema)
        except jsonschema.ValidationError as e:
            return False, f"Schema validation failed: {e}"
        except jsonschema.SchemaError as e:
            return False, f"Invalid schema: {e}"
        except ImportError:
            # If jsonschema is not installed, skip schema validation
            # but still return True for valid YAML syntax
            pass
    
    return True, None


def load_yaml_config(
    file_path: Union[str, Path],
    encoding: str = "utf-8",
) -> Dict[str, Any]:
    """Load YAML configuration from a file.
    
    This function reads a YAML file and returns it as a Python dictionary.
    It handles file reading errors and YAML parsing errors gracefully.
    
    Args:
        file_path: Path to the YAML configuration file
        encoding: File encoding (default: utf-8)
        
    Returns:
        Python dictionary representation of the YAML content
        
    Raises:
        FileNotFoundError: If the file does not exist
        PermissionError: If the file cannot be read
        ValueError: If the YAML content is invalid
        yaml.YAMLError: If the YAML content is malformed
        
    Example:
        >>> config = load_yaml_config("path/to/config.yaml")
        >>> assert isinstance(config, dict)
    """
    # Convert to Path object
    path = Path(file_path) if isinstance(file_path, str) else file_path
    
    # Check if file exists
    if not path.exists():
        raise FileNotFoundError(f"YAML configuration file not found: {path}")
    
    # Check if it's a file (not a directory)
    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")
    
    # Read file content
    try:
        content = path.read_text(encoding=encoding)
    except PermissionError:
        raise PermissionError(f"Permission denied when reading file: {path}")
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {path}")
    except Exception as e:
        raise IOError(f"Error reading file {path}: {e}")
    
    # Parse YAML
    try:
        yaml_data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in file {path}: {e}")
    
    if yaml_data is None:
        return {}
    
    # Ensure JSON compatibility
    return _make_json_compatible(yaml_data)


def yaml_to_json_file(
    yaml_file_path: Union[str, Path],
    json_file_path: Optional[Union[str, Path]] = None,
    encoding: str = "utf-8",
) -> Path:
    """Convert a YAML file to a JSON file.
    
    This function reads a YAML file, converts it to JSON-compatible format,
    and writes it to a JSON file.
    
    Args:
        yaml_file_path: Path to the input YAML file
        json_file_path: Path to the output JSON file (optional, defaults to .json extension)
        encoding: File encoding (default: utf-8)
        
    Returns:
        Path to the generated JSON file
        
    Raises:
        FileNotFoundError: If the YAML file does not exist
        ValueError: If the YAML content is invalid
        IOError: If there are issues reading/writing files
        
    Example:
        >>> json_path = yaml_to_json_file("input.yaml", "output.json")
        >>> assert json_path.exists()
    """
    # Convert to Path objects
    yaml_path = Path(yaml_file_path) if isinstance(yaml_file_path, str) else yaml_file_path
    
    # Determine output path if not provided
    if json_file_path is None:
        json_path = yaml_path.with_suffix(".json")
    else:
        json_path = Path(json_file_path) if isinstance(json_file_path, str) else json_file_path
    
    # Read YAML file
    try:
        yaml_content = yaml_path.read_text(encoding=encoding)
    except FileNotFoundError:
        raise FileNotFoundError(f"YAML file not found: {yaml_path}")
    except Exception as e:
        raise IOError(f"Error reading YAML file {yaml_path}: {e}")
    
    # Convert YAML to JSON-compatible dict
    try:
        yaml_data = yaml_to_json_dict(yaml_content)
    except ValueError as e:
        raise ValueError(f"Failed to parse YAML file {yaml_path}: {e}")
    
    # Convert to JSON string
    try:
        json_content = json.dumps(yaml_data, indent=2, ensure_ascii=False)
    except Exception as e:
        raise ValueError(f"Failed to convert YAML data to JSON: {e}")
    
    # Write JSON file
    try:
        json_path.write_text(json_content, encoding=encoding)
    except Exception as e:
        raise IOError(f"Error writing JSON file {json_path}: {e}")
    
    return json_path
