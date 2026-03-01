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
    
    # Reverse key mapping first (keep tabular_arrays for later)
    if isinstance(result, dict) and "_field_codes" in result:
        field_codes = result.pop("_field_codes")
        # Invert the mapping: from {field_name: code} to {code: field_name}
        code_to_field = {code: field_name for field_name, code in field_codes.items()}
        
        # Store _tabular_arrays before removing metadata
        tabular_arrays = result.get("_tabular_arrays")
        
        # Remove metadata fields (except tabular_arrays which we need)
        result = {k: v for k, v in result.items() if not k.startswith("_") or k == "_tabular_arrays"}
        
        # Now decode data
        result = _decode_data_from_field_codes(result, code_to_field)
        
        # Reverse tabular encoding if present
        if isinstance(result, dict) and "_tabular_arrays" in result:
            # Extract tabular metadata from schema if available
            tabular_metadata: Dict[str, Any] = {}
            if isinstance(result, dict) and "_schema" in result:
                schema = result["_schema"]
                if "structure" in schema and "tabular_arrays" in schema["structure"]:
                    tabular_metadata = schema["structure"]["tabular_arrays"]
            
            result = _decode_tabular_arrays(result, code_to_field, tabular_metadata)
            
            # Remove _tabular_arrays from result
            result = {k: v for k, v in result.items() if k != "_tabular_arrays"}
    else:
        # Reverse tabular encoding without field codes
        if isinstance(result, dict) and "_tabular_arrays" in result:
            result = _reverse_tabular_encoding(result)
    
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
    
    # Remove schema
    if isinstance(result, dict) and "_schema" in result:
        del result["_schema"]
    
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


def _decode_tabular_arrays(
    data: Union[Dict[str, Any], List[Any]],
    code_to_path: Dict[str, str],
    tabular_metadata: Dict[str, Any],
    sep: str = ".",
) -> Union[Dict[str, Any], List[Any]]:
    """Decode tabular array structures back to array-of-objects format.
    
    This function reverses the tabular encoding process by converting
    columnar data back to array-of-objects format.
    
    Args:
        data: Data with tabular arrays to decode
        code_to_path: Mapping from field codes to paths
        tabular_metadata: Metadata about tabular arrays
        sep: Separator for nested paths
        
    Returns:
        Data with tabular arrays decoded
        
    Example:
        >>> data = {"items": [{"columns": {"F0": [1, 2], "F1": ["a", "b"]}}]}
        >>> code_to_path = {"F0": "items.id", "F1": "items.name"}
        >>> tabular_metadata = {"items": {"fields": ["F0", "F1"]}}
        >>> result = _decode_tabular_arrays(data, code_to_path, tabular_metadata)
        >>> # Returns: {"items": [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]}
    """
    if not isinstance(data, dict):
        return data
    
    # Get tabular arrays from data (they should be at the root or in _tabular_arrays)
    tabular_arrays: Dict[str, Any] = {}
    
    # Check if data has _tabular_arrays key
    if "_tabular_arrays" in data:
        tabular_arrays = data["_tabular_arrays"]
        # Remove the _tabular_arrays key from data
        data = {k: v for k, v in data.items() if k != "_tabular_arrays"}
    
    # Check if there are any encoded tabular arrays in the data itself
    keys_to_remove = []
    for key, value in data.items():
        if isinstance(value, dict) and "columns" in value and "fields" in value:
            # This looks like a tabular array that needs decoding
            tabular_arrays[key] = value
            # Mark for removal
            keys_to_remove.append(key)
    
    # Remove marked keys from data
    for key in keys_to_remove:
        del data[key]
    
    if not tabular_arrays:
        return data
    
    # Process each tabular array
    for field_code, encoded in tabular_arrays.items():
        # Get the original field path
        field_path = code_to_path.get(field_code, field_code)
        
        # Determine the field name from the path
        if "." in field_path:
            # Nested field - get the parent field name
            parts = field_path.split(sep)
            parent_field = parts[0] if parts else field_code
        else:
            # Simple field
            parent_field = field_path
        
        # Decode the tabular array
        if "columns" in encoded and "fields" in encoded:
            columns = encoded["columns"]
            fields = encoded["fields"]
            
            # Check if columns is a list or dict
            if isinstance(columns, list):
                # columns is a list of column values
                # Determine the number of rows
                num_rows = 0
                if columns:
                    first_col = columns[0]
                    if isinstance(first_col, dict) and "_ref" in first_col:
                        num_rows = len(first_col["_ref"])
                    elif isinstance(first_col, list):
                        num_rows = len(first_col)
                
                # Reconstruct array of objects
                reconstructed = []
                for i in range(num_rows):
                    obj: Dict[str, Any] = {}
                    for field_idx, field_code_name in enumerate(fields):
                        # Get the original field name for this code
                        original_field = code_to_path.get(field_code_name, field_code_name)
                        
                        # Get column data
                        if field_idx < len(columns):
                            col_data = columns[field_idx]
                        else:
                            col_data = None
                        
                        if col_data is not None:
                            if isinstance(col_data, dict) and "_unique" in col_data:
                                # Decompressed column with unique values
                                unique_values = col_data["_unique"]
                                ref_idx = col_data["_ref"][i] if i < len(col_data["_ref"]) else None
                                if ref_idx is not None:
                                    obj[original_field] = unique_values[ref_idx]
                                else:
                                    obj[original_field] = None
                            elif isinstance(col_data, list):
                                # Regular column
                                if i < len(col_data):
                                    obj[original_field] = col_data[i]
                                else:
                                    obj[original_field] = None
                    
                    reconstructed.append(obj)
            else:
                # columns is a dict (old format)
                # Determine the number of rows
                num_rows = 0
                for col_name, col_values in columns.items():
                    if isinstance(col_values, dict) and "_ref" in col_values:
                        num_rows = len(col_values["_ref"])
                    elif isinstance(col_values, list):
                        num_rows = len(col_values)
                        break
                
                # Reconstruct array of objects
                reconstructed = []
                for i in range(num_rows):
                    obj: Dict[str, Any] = {}
                    for field_idx, field_code_name in enumerate(fields):
                        # Get the original field name for this code
                        original_field = code_to_path.get(field_code_name, field_code_name)
                        
                        # Get column data
                        col_data = columns.get(str(field_idx))
                        
                        if col_data is None:
                            # Try by field index
                            col_data = columns.get(field_code_name)
                        
                        if col_data is None:
                            # Try by field name
                            field_path_parts = original_field.split(sep)
                            if len(field_path_parts) > 1:
                                # Get the field name (last part)
                                field_name = field_path_parts[-1]
                                col_data = columns.get(field_name)
                        
                        if col_data is not None:
                            if isinstance(col_data, dict) and "_unique" in col_data:
                                # Decompressed column with unique values
                                unique_values = col_data["_unique"]
                                ref_idx = col_data["_ref"][i] if i < len(col_data["_ref"]) else None
                                if ref_idx is not None:
                                    obj[original_field] = unique_values[ref_idx]
                                else:
                                    obj[original_field] = None
                            elif isinstance(col_data, list):
                                # Regular column
                                if i < len(col_data):
                                    obj[original_field] = col_data[i]
                                else:
                                    obj[original_field] = None
                    
                    reconstructed.append(obj)
            
            # Store the reconstructed array
            if parent_field in data:
                # If parent field already exists, append or merge
                if isinstance(data[parent_field], list):
                    data[parent_field].extend(reconstructed)
                else:
                    data[parent_field] = reconstructed
            else:
                data[parent_field] = reconstructed
    
    return data


def _decode_data_from_field_codes(
    data: Union[Dict[str, Any], List[Any]],
    code_to_path: Dict[str, str],
    sep: str = ".",
) -> Union[Dict[str, Any], List[Any]]:
    """Decode data by restoring original field names from field codes.
    
    This function reverses the key mapping process by replacing field codes
    with their original field names.
    
    Args:
        data: Data with field codes as keys
        code_to_path: Mapping from field codes to original paths
        sep: Separator for nested paths
        
    Returns:
        Data with original field names restored
        
    Example:
        >>> data = {"F0": "John", "F1": "john@example.com"}
        >>> code_to_path = {"F0": "user.name", "F1": "user.email"}
        >>> result = _decode_data_from_field_codes(data, code_to_path)
        >>> # Returns: {"user": {"name": "John", "email": "john@example.com"}}
    """
    if isinstance(data, dict):
        result: Dict[str, Any] = {}
        
        for key, value in data.items():
            # Skip special metadata fields
            if key.startswith("_"):
                result[key] = value
                continue
            
            # Check if this key is a field code
            if key in code_to_path:
                # Get the original field path
                original_path = code_to_path[key]
                
                # If the path is simple (no dots), just use it directly
                if sep not in original_path:
                    if isinstance(value, (dict, list)):
                        result[original_path] = _decode_data_from_field_codes(value, code_to_path, sep)
                    else:
                        result[original_path] = value
                else:
                    # Nested path - build nested structure
                    parts = original_path.split(sep)
                    current = result
                    
                    # Navigate to the correct nested position
                    for part in parts[:-1]:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
                    
                    # Set the final value
                    if isinstance(value, (dict, list)):
                        current[parts[-1]] = _decode_data_from_field_codes(value, code_to_path, sep)
                    else:
                        current[parts[-1]] = value
            else:
                # Key is not a field code, keep it as is
                if isinstance(value, (dict, list)):
                    result[key] = _decode_data_from_field_codes(value, code_to_path, sep)
                else:
                    result[key] = value
        
        return result
    
    elif isinstance(data, list):
        return [_decode_data_from_field_codes(item, code_to_path, sep) for item in data]
    
    return data
