"""
JSON compression module with field code mapping and tabular array encoding.

This module provides compression utilities for JSON data using various
strategies including field code mapping, filtering, and tabular array
encoding.
"""

import json
from typing import Any, Dict, List, Optional, Tuple, Union

from .config import (
    CompressionConfig,
    FilterConfig,
    FlattenConfig,
    KeyMappingConfig,
    TabularConfig,
)


def compress_json(
    data: Union[Dict[str, Any], List[Any]],
    config: CompressionConfig,
) -> Union[Dict[str, Any], List[Any]]:
    """Compress JSON data using the specified configuration.
    
    This function applies compression strategies to JSON data including:
    - Field filtering (include/exclude fields)
    - Flattening nested structures
    - Field code mapping (reducing field name sizes)
    - Tabular array encoding (compressing array-of-objects)
    
    Args:
        data: JSON data as a dictionary or list
        config: Compression configuration
        
    Returns:
        Compressed JSON data
        
    Raises:
        ValueError: If the data or configuration is invalid
    """
    if not data:
        return data
    
    if not isinstance(config, CompressionConfig):
        raise ValueError("config must be a CompressionConfig instance")
    
    # Apply filtering
    if config.filter_config:
        data = _apply_filter(data, config.filter_config)
    
    # Apply flattening
    if config.flatten_config and config.flatten_config.enabled:
        data = _apply_flatten(data, config.flatten_config)
    
    # Apply key mapping
    if config.key_mapping_config and config.key_mapping_config.enabled:
        data, field_codes = _apply_key_mapping(data, config.key_mapping_config)
        # Store field codes in result metadata
        if isinstance(data, dict):
            data["_field_codes"] = field_codes
    
    # Apply tabular encoding
    if config.tabular_config and config.tabular_config.enabled:
        data = _apply_tabular_encoding(data, config.tabular_config)
    
    # Add compression metadata
    if isinstance(data, dict):
        data["_compression_metadata"] = {
            "strategy": config.strategy,
            "preserve_types": config.preserve_types,
            "compression_level": config.compression_level,
        }
    
    return data


def _apply_filter(
    data: Union[Dict[str, Any], List[Any]],
    filter_config: FilterConfig,
) -> Union[Dict[str, Any], List[Any]]:
    """Apply field filtering to data.
    
    Args:
        data: Data to filter
        filter_config: Filter configuration
        
    Returns:
        Filtered data
    """
    if isinstance(data, dict):
        result = {}
        
        # Apply filtering rules
        for key, value in data.items():
            # Skip special metadata fields
            if key.startswith("_"):
                result[key] = value
                continue
            
            # Check if field should be included
            if filter_config.include_fields:
                if key not in filter_config.include_fields:
                    continue
            
            # Check if field should be excluded
            if filter_config.exclude_fields and key in filter_config.exclude_fields:
                continue
            
            # Recursively filter nested values
            result[key] = _apply_filter(value, filter_config) if isinstance(value, (dict, list)) else value
        
        return result
    
    elif isinstance(data, list):
        return [_apply_filter(item, filter_config) for item in data]
    
    return data


def _apply_flatten(
    data: Union[Dict[str, Any], List[Any]],
    flatten_config: FlattenConfig,
    parent_key: str = "",
    depth: int = 0,
) -> Union[Dict[str, Any], List[Any]]:
    """Flatten nested structures in data.
    
    Args:
        data: Data to flatten
        flatten_config: Flatten configuration
        parent_key: Parent key for nested structures
        depth: Current nesting depth
        
    Returns:
        Flattened data
    """
    if not flatten_config.enabled:
        return data
    
    if flatten_config.max_depth is not None and depth >= flatten_config.max_depth:
        return data
    
    if isinstance(data, dict):
        result = {}
        
        for key, value in data.items():
            # Skip special metadata fields
            if key.startswith("_"):
                result[key] = value
                continue
            
            # Create new key
            new_key = f"{parent_key}{flatten_config.delimiter}{key}" if parent_key else key
            
            if isinstance(value, dict):
                # Recursively flatten nested dict
                flattened = _apply_flatten(value, flatten_config, new_key, depth + 1)
                if isinstance(flattened, dict):
                    result.update(flattened)
                else:
                    result[new_key] = flattened
            elif isinstance(value, list):
                # Handle lists - don't flatten them, just use the key
                result[new_key] = value
            else:
                result[new_key] = value
        
        return result
    
    elif isinstance(data, list):
        # For lists, flatten each item and keep them as separate items
        # This is a special case where we might want to wrap in a dict
        return data
    
    return data


def _apply_key_mapping(
    data: Union[Dict[str, Any], List[Any]],
    key_mapping_config: KeyMappingConfig,
    field_counter: Optional[int] = None,
) -> Tuple[Union[Dict[str, Any], List[Any]], Dict[str, str]]:
    """Apply key mapping to data using field codes.
    
    Args:
        data: Data to map
        key_mapping_config: Key mapping configuration
        field_counter: Optional counter for generating field codes
        
    Returns:
        Tuple of (mapped_data, field_codes_dict)
    """
    if field_counter is None:
        field_counter = key_mapping_config.counter_start
    
    field_codes: Dict[str, str] = {}
    field_counter_ref = {"value": field_counter}  # Use dict to make it mutable
    
    def map_keys(obj: Any, depth: int = 0) -> Any:
        nonlocal field_counter_ref
        
        if isinstance(obj, dict):
            result = {}
            
            for key, value in obj.items():
                # Skip special metadata fields
                if key.startswith("_"):
                    result[key] = value
                    continue
                
                # Get or create field code
                if key_mapping_config.mapping and key in key_mapping_config.mapping:
                    field_code = key_mapping_config.mapping[key]
                elif key in field_codes:
                    field_code = field_codes[key]
                else:
                    field_code = f"{key_mapping_config.code_prefix}{field_counter_ref['value']}"
                    field_codes[key] = field_code
                    field_counter_ref["value"] += 1
                
                # Recursively map nested values
                if isinstance(value, (dict, list)):
                    result[field_code] = map_keys(value, depth + 1)
                else:
                    result[field_code] = value
            
            return result
        
        elif isinstance(obj, list):
            return [map_keys(item, depth + 1) for item in obj]
        
        return obj
    
    mapped_data = map_keys(data)
    return mapped_data, field_codes


def _apply_tabular_encoding(
    data: Union[Dict[str, Any], List[Any]],
    tabular_config: TabularConfig,
) -> Union[Dict[str, Any], List[Any]]:
    """Apply tabular array encoding to data.
    
    Tabular encoding compresses arrays of objects by extracting common
    fields and encoding them as separate arrays (columnar format).
    
    Args:
        data: Data to encode
        tabular_config: Tabular encoding configuration
        
    Returns:
        Tabular encoded data
    """
    if not isinstance(data, dict):
        return data
    
    result = {}
    tabular_arrays: Dict[str, Any] = {}
    
    for key, value in data.items():
        # Skip special metadata fields
        if key.startswith("_"):
            result[key] = value
            continue
        
        # Check if this is a list that should be encoded as tabular
        if (
            isinstance(value, list)
            and value
            and isinstance(value[0], dict)
            and tabular_config.tabular_fields
            and key in tabular_config.tabular_fields
        ):
            # Encode this array as tabular
            encoded = _encode_tabular_array(value, tabular_config)
            tabular_arrays[key] = encoded
        else:
            result[key] = value
    
    # Add encoded tabular arrays to result
    if tabular_arrays:
        result["_tabular_arrays"] = tabular_arrays
    
    return result


def _encode_tabular_array(
    data: List[Dict[str, Any]],
    tabular_config: TabularConfig,
) -> Dict[str, Any]:
    """Encode an array of objects as a tabular structure.
    
    Args:
        data: Array of objects to encode
        tabular_config: Tabular encoding configuration
        
    Returns:
        Tabular encoded structure
    """
    if not data:
        return {}
    
    # Extract all field names
    field_names = set()
    for item in data:
        field_names.update(item.keys())
    
    # Remove special fields
    field_names = {f for f in field_names if not f.startswith("_")}
    
    # Create columnar structure
    columns: Dict[str, List[Any]] = {field: [] for field in field_names}
    
    for item in data:
        for field in field_names:
            columns[field].append(item.get(field))
    
    # Optionally compress by removing common values
    if tabular_config.compression_ratio:
        columns = _compress_columns(columns, tabular_config.compression_ratio)
    
    # Add key column mapping if specified
    result = {"columns": columns}
    
    if tabular_config.key_column and tabular_config.key_column in columns:
        # Create key-to-index mapping
        key_values = columns[tabular_config.key_column]
        key_index_map = {val: idx for idx, val in enumerate(key_values)}
        result["key_index_map"] = key_index_map
    
    return result


def _compress_columns(
    columns: Dict[str, List[Any]],
    compression_ratio: float,
) -> Dict[str, List[Any]]:
    """Compress columns by removing common/redundant values.
    
    Args:
        columns: Columnar data
        compression_ratio: Target compression ratio
        
    Returns:
        Compressed columns
    """
    # Simple implementation: identify columns with mostly same values
    compressed: Dict[str, List[Any]] = {}
    
    for field, values in columns.items():
        # Count unique values
        unique_values = len(set(str(v) for v in values if v is not None))
        total_values = len(values)
        
        # If compression ratio suggests compressing this field
        if unique_values / total_values < (1.0 - compression_ratio):
            # Store only the unique values and a reference array
            unique_list = list(set(v for v in values if v is not None))
            ref_array = [unique_list.index(v) if v in unique_list else None for v in values]
            compressed[field] = {"_unique": unique_list, "_ref": ref_array}
        else:
            compressed[field] = values
    
    return compressed


def _build_field_code_map(
    paths: List[str],
    config: CompressionConfig,
) -> Dict[str, str]:
    """Build a mapping of field paths to field codes.
    
    This function is used to pre-build field codes for known field paths,
    ensuring consistent encoding across multiple compressions.
    
    Args:
        paths: List of field paths (e.g., ["user.name", "user.email"])
        config: Compression configuration
        
    Returns:
        Dictionary mapping field paths to field codes
    """
    field_codes: Dict[str, str] = {}
    
    if not config.key_mapping_config:
        return field_codes
    
    key_mapping_config = config.key_mapping_config
    
    # Initialize counter
    counter = key_mapping_config.counter_start
    
    # Process each path
    for path in paths:
        # Check if manual mapping exists
        if key_mapping_config.mapping and path in key_mapping_config.mapping:
            field_codes[path] = key_mapping_config.mapping[path]
        else:
            # Generate code
            code = f"{key_mapping_config.code_prefix}{counter}"
            field_codes[path] = code
            counter += 1
    
    return field_codes
