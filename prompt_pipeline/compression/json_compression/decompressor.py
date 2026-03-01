"""
JSON decompression module.

This module provides decompression utilities for JSON data that was
compressed using the json_compression module.
"""

import json
from typing import Any, Dict, List, Optional, Union

from .config import (
    CompressionConfig,
    FilterConfig,
    FlattenConfig,
    KeyMappingConfig,
    TabularConfig,
)


def decompress_json(
    data: Union[Dict[str, Any], List[Any]],
    config: Optional[CompressionConfig] = None,
) -> Union[Dict[str, Any], List[Any]]:
    """Decompress JSON data that was compressed with compress_json.
    
    This function reverses the compression process including:
    - Restoring field names from field codes
    - Unflattening nested structures
    - Restoring tabular arrays to array-of-objects format
    
    Args:
        data: Compressed JSON data
        config: Compression configuration used for compression (optional)
                If not provided, configuration will be extracted from metadata
        
    Returns:
        Decompressed JSON data
        
    Raises:
        ValueError: If the data cannot be decompressed
    """
    if not data:
        return data
    
    # Extract configuration from metadata if not provided
    if config is None and isinstance(data, dict) and "_compression_metadata" in data:
        metadata = data["_compression_metadata"]
        config = CompressionConfig(
            strategy=metadata.get("strategy", "unknown"),
            preserve_types=metadata.get("preserve_types", True),
            compression_level=metadata.get("compression_level", 50),
        )
    
    if not isinstance(config, CompressionConfig):
        raise ValueError("config must be a CompressionConfig instance or metadata must be present")
    
    result = data
    
    # Reverse tabular encoding first
    if isinstance(result, dict) and "_tabular_arrays" in result:
        result = _reverse_tabular_encoding(result)
    
    # Reverse key mapping
    if isinstance(result, dict) and "_field_codes" in result:
        field_codes = result.pop("_field_codes")
        result = _reverse_key_mapping(result, field_codes)
    
    # Reverse flattening (if we know it was flattened)
    if config.flatten_config and config.flatten_config.enabled:
        result = _reverse_flatten(result, config.flatten_config)
    
    # Reverse filtering (filtering is not reversible in most cases)
    # We just remove metadata fields
    if isinstance(result, dict):
        result = {k: v for k, v in result.items() if not k.startswith("_")}
    
    # Remove compression metadata
    if isinstance(result, dict) and "_compression_metadata" in result:
        del result["_compression_metadata"]
    
    return result


def _reverse_tabular_encoding(
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """Reverse tabular array encoding.
    
    Args:
        data: Data with tabular arrays
        
    Returns:
        Data with tabular arrays restored to array-of-objects format
    """
    if "_tabular_arrays" not in data:
        return data
    
    result = {k: v for k, v in data.items() if k != "_tabular_arrays"}
    tabular_arrays = data["_tabular_arrays"]
    
    for field, encoded in tabular_arrays.items():
        if "columns" in encoded:
            columns = encoded["columns"]
            
            # Determine the number of rows
            num_rows = 0
            for col_values in columns.values():
                if isinstance(col_values, dict) and "_ref" in col_values:
                    num_rows = len(col_values["_ref"])
                elif isinstance(col_values, list):
                    num_rows = len(col_values)
                    break
            
            # Reconstruct array of objects
            reconstructed = []
            for i in range(num_rows):
                obj: Dict[str, Any] = {}
                for field_name, col_values in columns.items():
                    if isinstance(col_values, dict) and "_unique" in col_values:
                        # Decompressed column with unique values
                        unique_values = col_values["_unique"]
                        ref_idx = col_values["_ref"][i]
                        obj[field_name] = unique_values[ref_idx] if ref_idx is not None else None
                    elif isinstance(col_values, list):
                        # Regular column
                        obj[field_name] = col_values[i] if i < len(col_values) else None
                reconstructed.append(obj)
            
            result[field] = reconstructed
    
    return result


def _reverse_key_mapping(
    data: Dict[str, Any],
    field_codes: Dict[str, str],
) -> Dict[str, Any]:
    """Reverse key mapping by restoring original field names.
    
    Args:
        data: Data with mapped keys
        field_codes: Mapping from original field names to codes
        
    Returns:
        Data with original field names restored
    """
    # Invert the field_codes mapping
    code_to_field: Dict[str, str] = {code: field for field, code in field_codes.items()}
    
    def restore_keys(obj: Any) -> Any:
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                # Check if this key is a field code
                if key in code_to_field:
                    original_field = code_to_field[key]
                    result[original_field] = restore_keys(value)
                else:
                    # Keep special fields or unknown keys
                    result[key] = restore_keys(value)
            return result
        
        elif isinstance(obj, list):
            return [restore_keys(item) for item in obj]
        
        return obj
    
    return restore_keys(data)


def _reverse_flatten(
    data: Union[Dict[str, Any], List[Any]],
    flatten_config: FlattenConfig,
) -> Union[Dict[str, Any], List[Any]]:
    """Reverse flattening by reconstructing nested structures.
    
    Args:
        data: Flattened data
        flatten_config: Flatten configuration
        
    Returns:
        Data with nested structures restored
    """
    if not isinstance(data, dict):
        return data
    
    result: Dict[str, Any] = {}
    
    for key, value in data.items():
        # Skip special fields
        if key.startswith("_"):
            result[key] = value
            continue
        
        # Check if key contains the delimiter
        if flatten_config.delimiter in key:
            # Split the key and build nested structure
            parts = key.split(flatten_config.delimiter)
            
            # Navigate to the correct nested position
            current = result
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # Set the final value
            current[parts[-1]] = value
        else:
            # Simple key, just add it
            result[key] = value
    
    return result


def _make_json_compatible(obj: Any) -> Any:
    """Ensure object is JSON-compatible.
    
    This is a utility function to handle any type conversions
    needed before JSON serialization.
    
    Args:
        obj: Object to make JSON-compatible
        
    Returns:
        JSON-compatible object
    """
    if isinstance(obj, dict):
        return {k: _make_json_compatible(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_make_json_compatible(item) for item in obj]
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    else:
        return str(obj)
