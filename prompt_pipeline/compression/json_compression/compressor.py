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


def _collect_logical_fields(
    data: Union[Dict[str, Any], List[Any]],
    config: CompressionConfig,
) -> List[str]:
    """Collect all logical field paths from data, optionally filtered by config.
    
    This function traverses the data structure and collects all field paths,
    applying filtering rules from the configuration.
    
    Args:
        data: JSON data to collect fields from
        config: Compression configuration
        
    Returns:
        List of field paths (e.g., ["user.name", "user.email", "items[].id"])
        
    Example:
        >>> data = {"user": {"name": "John", "email": "john@example.com"}}
        >>> config = CompressionConfig(strategy="test")
        >>> _collect_logical_fields(data, config)
        ["user.name", "user.email"]
    """
    field_paths: List[str] = []
    
    def traverse(obj: Any, parent_path: str = "") -> None:
        """Recursively traverse data and collect field paths."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                # Skip special metadata fields
                if key.startswith("_"):
                    continue
                
                # Build current field path
                current_path = f"{parent_path}.{key}" if parent_path else key
                
                # Apply filtering if configured
                should_include = True
                if config.filter_config:
                    # Check include filter
                    if config.filter_config.include_fields:
                        should_include = current_path in config.filter_config.include_fields
                    
                    # Check exclude filter
                    if config.filter_config.exclude_fields and current_path in config.filter_config.exclude_fields:
                        should_include = False
                
                if should_include:
                    # If value is a simple type, this is a leaf field
                    if isinstance(value, (str, int, float, bool, type(None))):
                        field_paths.append(current_path)
                    # If value is a dict, traverse deeper
                    elif isinstance(value, dict):
                        traverse(value, current_path)
                    # If value is a list, check first element
                    elif isinstance(value, list) and value:
                        if isinstance(value[0], dict):
                            # Array of objects - use [] notation
                            traverse(value[0], f"{current_path}[]")
                        elif isinstance(value[0], (str, int, float, bool, type(None))):
                            # Array of primitives
                            field_paths.append(current_path)
                    else:
                        # Empty list or other type
                        field_paths.append(current_path)
        
        elif isinstance(obj, list) and obj:
            # Handle root-level arrays
            if isinstance(obj[0], dict):
                traverse(obj[0], parent_path + "[]" if parent_path else "[]")
    
    traverse(data)
    
    # Apply flattening if enabled
    if config.flatten_config and config.flatten_config.enabled:
        field_paths = _flatten_field_paths(field_paths, config.flatten_config)
    
    return sorted(field_paths)


def _flatten_field_paths(
    field_paths: List[str],
    flatten_config: FlattenConfig,
) -> List[str]:
    """Flatten field paths using the configured delimiter.
    
    Args:
        field_paths: List of field paths
        flatten_config: Flatten configuration
        
    Returns:
        List of flattened field paths
    """
    if not flatten_config.enabled:
        return field_paths
    
    flattened: List[str] = []
    
    for path in field_paths:
        # Replace dots with the configured delimiter
        flattened_path = path.replace(".", flatten_config.delimiter)
        flattened.append(flattened_path)
    
    return flattened


def _encode_data_with_field_codes(
    data: Union[Dict[str, Any], List[Any]],
    path_to_code: Dict[str, str],
    prefix: str = "",
    sep: str = ".",
) -> Union[Dict[str, Any], List[Any]]:
    """Encode data by replacing field paths with field codes.
    
    Args:
        data: Data to encode
        path_to_code: Mapping from field paths to codes
        prefix: Prefix for nested paths (used internally for recursion)
        sep: Separator for nested paths
        
    Returns:
        Encoded data with field codes as keys
    """
    if isinstance(data, dict):
        result: Dict[str, Any] = {}
        
        for key, value in data.items():
            # Skip special metadata fields
            if key.startswith("_"):
                result[key] = value
                continue
            
            # Build current path
            current_path = f"{prefix}.{key}" if prefix else key
            
            # Check if this path exists in the mapping
            if current_path in path_to_code:
                # Use the field code
                code = path_to_code[current_path]
                
                # Recursively encode nested values
                if isinstance(value, (dict, list)):
                    result[code] = _encode_data_with_field_codes(value, path_to_code, current_path, sep)
                else:
                    result[code] = value
            else:
                # Check if this is a nested path that needs encoding
                nested_encoded = False
                
                if isinstance(value, (dict, list)):
                    # Try to encode recursively
                    encoded_value = _encode_data_with_field_codes(value, path_to_code, current_path, sep)
                    
                    # If any keys changed, this was encoded
                    if isinstance(encoded_value, dict):
                        # Check if any keys are different from original
                        if encoded_value != value:
                            # Merge the encoded value into the result
                            result.update(encoded_value)
                            nested_encoded = True
                
                # If not nested-encoded, keep the original key
                if not nested_encoded:
                    result[key] = value
        
        return result
    
    elif isinstance(data, list):
        # For lists, encode each item
        return [_encode_data_with_field_codes(item, path_to_code, prefix, sep) for item in data]
    
    return data


def _encode_tabular_arrays(
    data: Union[Dict[str, Any], List[Any]],
    path_to_code: Dict[str, str],
    config: CompressionConfig,
    sep: str = ".",
) -> Tuple[Union[Dict[str, Any], List[Any]], Dict[str, Any]]:
    """Encode arrays of objects as tabular structures.
    
    This function identifies arrays of objects in the data and encodes them
    as tabular structures (columnar format) for compression.
    
    Args:
        data: Data to encode
        path_to_code: Mapping from field paths to codes
        config: Compression configuration
        sep: Separator for nested paths
        
    Returns:
        Tuple of (encoded_data, tabular_metadata)
    """
    if not isinstance(data, dict):
        return data, {}
    
    result: Dict[str, Any] = {}
    tabular_metadata: Dict[str, Any] = {}
    
    # Check if tabular encoding is enabled
    if not config.tabular_config or not config.tabular_config.enabled:
        return data, {}
    
    for key, value in data.items():
        # Skip special metadata fields
        if key.startswith("_"):
            result[key] = value
            continue
        
        # Check if this is an array of objects that should be encoded as tabular
        if (
            isinstance(value, list)
            and value
            and isinstance(value[0], dict)
            and config.tabular_config.tabular_fields
            and key in config.tabular_config.tabular_fields
        ):
            # Encode this array as tabular
            encoded, metadata = _encode_single_tabular_array(
                value, path_to_code, key, config.tabular_config, sep
            )
            
            # Store in _tabular_arrays
            if "_tabular_arrays" not in result:
                result["_tabular_arrays"] = {}
            result["_tabular_arrays"][key] = encoded
            
            # Also store the encoded version directly (for backward compatibility)
            result[key] = encoded
            
            # Store metadata
            if metadata:
                tabular_metadata[key] = metadata
        else:
            # Recursively process nested data
            if isinstance(value, (dict, list)):
                processed, nested_meta = _encode_tabular_arrays(
                    value, path_to_code, config, sep
                )
                result[key] = processed
                if nested_meta:
                    tabular_metadata[key] = nested_meta
            else:
                result[key] = value
    
    return result, tabular_metadata


def _encode_single_tabular_array(
    data: List[Dict[str, Any]],
    path_to_code: Dict[str, str],
    array_key: str,
    tabular_config: TabularConfig,
    sep: str = ".",
) -> Tuple[List[List[Any]], Dict[str, Any]]:
    """Encode a single array of objects as a tabular structure.
    
    Args:
        data: Array of objects to encode
        path_to_code: Mapping from field paths to codes
        array_key: Key of this array in the parent object
        tabular_config: Tabular encoding configuration
        sep: Separator for nested paths
        
    Returns:
        Tuple of (tabular_data, metadata)
    """
    if not data:
        return [], {}
    
    # Collect all field paths from the first item
    first_item = data[0]
    field_paths: List[str] = []
    
    for key in first_item.keys():
        if not key.startswith("_"):
            field_paths.append(key)
    
    # Build a mapping of field paths to codes (with array context)
    array_path = array_key
    field_code_map: Dict[str, str] = {}
    
    for field in field_paths:
        full_path = f"{array_path}.{field}" if array_path else field
        if full_path in path_to_code:
            field_code_map[field] = path_to_code[full_path]
        else:
            # Use a default code if not found
            field_code_map[field] = field
    
    # Create columnar structure
    columns: List[List[Any]] = []
    field_order: List[str] = []
    
    # Sort fields for consistency
    sorted_fields = sorted(field_code_map.keys())
    
    for field in sorted_fields:
        field_order.append(field_code_map[field])
        column: List[Any] = []
        
        for item in data:
            value = item.get(field)
            column.append(value)
        
        columns.append(column)
    
    # Optionally compress by removing common values
    if tabular_config.compression_ratio:
        columns, field_order = _compress_tabular_columns(
            columns, field_order, tabular_config.compression_ratio
        )
    
    # Add key column mapping if specified
    key_index_map: Dict[Any, int] = {}
    key_column = None
    if tabular_config.key_column and tabular_config.key_column in field_code_map:
        key_code = field_code_map[tabular_config.key_column]
        key_column_idx = field_order.index(key_code) if key_code in field_order else -1
        
        if key_column_idx >= 0:
            key_values = columns[key_column_idx]
            
            for idx, val in enumerate(key_values):
                if val not in key_index_map:
                    key_index_map[val] = idx
            
            key_column = key_code
    
    # Create metadata
    metadata: Dict[str, Any] = {
        "fields": field_order,
        "columns": columns,
    }
    
    if key_index_map:
        metadata["key_index_map"] = key_index_map
    
    if key_column:
        metadata["key_column"] = key_column
    
    # Create encoded structure with 'columns' and 'fields' keys
    encoded_structure: Dict[str, Any] = {
        "columns": columns,
        "fields": field_order,
    }
    
    if key_index_map:
        encoded_structure["key_index_map"] = key_index_map
    
    if key_column:
        encoded_structure["key_column"] = key_column
    
    return encoded_structure, metadata


def _compress_tabular_columns(
    columns: List[List[Any]],
    field_order: List[str],
    compression_ratio: float,
) -> Tuple[List[List[Any]], List[str]]:
    """Compress tabular columns by removing common/redundant values.
    
    Args:
        columns: Columnar data
        field_order: Order of fields
        compression_ratio: Target compression ratio
        
    Returns:
        Tuple of (compressed_columns, compressed_field_order)
    """
    if compression_ratio <= 0:
        return columns, field_order
    
    compressed_columns: List[List[Any]] = []
    compressed_fields: List[str] = []
    
    for idx, column in enumerate(columns):
        # Count unique values
        unique_values = len(set(str(v) for v in column if v is not None))
        total_values = len(column)
        
        # Check if compression is beneficial
        if total_values > 0 and unique_values / total_values < (1.0 - compression_ratio):
            # Store only unique values and a reference array
            unique_list = list(set(v for v in column if v is not None))
            ref_array: List[Optional[int]] = []
            
            for val in column:
                if val is None:
                    ref_array.append(None)
                elif val in unique_list:
                    ref_array.append(unique_list.index(val))
                else:
                    ref_array.append(None)
            
            compressed_columns.append([{"_unique": unique_list, "_ref": ref_array}])
            compressed_fields.append(field_order[idx])
        else:
            # Keep column as-is
            compressed_columns.append(column)
            compressed_fields.append(field_order[idx])
    
    return compressed_columns, compressed_fields


def _build_schema_object(
    original_root_type: str,
    config: CompressionConfig,
    path_to_code: Dict[str, str],
    tabular_metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """Build schema object for compressed data.
    
    This function creates the schema object that describes the structure
    of the compressed data, including field mappings and tabular array info.
    
    Args:
        original_root_type: Type of the original root object ("dict" or "list")
        config: Compression configuration
        path_to_code: Mapping from field paths to codes
        tabular_metadata: Metadata about tabular arrays
        
    Returns:
        Schema object with version, fields, and structure info
    """
    schema: Dict[str, Any] = {}
    
    # Always include version
    schema["version"] = 1
    
    # Include original root type
    schema["original_root_type"] = original_root_type
    
    # Include compression configuration info
    schema["strategy"] = config.strategy
    schema["preserve_types"] = config.preserve_types
    schema["compression_level"] = config.compression_level
    
    # Include field mappings
    schema["fields"] = path_to_code
    
    # Include structure info if we have tabular arrays
    if tabular_metadata:
        structure: Dict[str, Any] = {
            "tabular_arrays": tabular_metadata,
        }
        
        # Add flatten config if enabled
        if config.flatten_config and config.flatten_config.enabled:
            structure["flattened"] = {
                "enabled": True,
                "delimiter": config.flatten_config.delimiter,
            }
        
        schema["structure"] = structure
    
    return schema


def init_compress_json(
    data: Union[Dict[str, Any], List[Any]],
    config: CompressionConfig,
) -> Tuple[Union[Dict[str, Any], List[Any]], List[str], Dict[str, Any], str]:
    """Initialize the compression process for JSON data.
    
    This function performs the initial steps of compression:
    1. Determine the original root type
    2. Apply filtering (if configured)
    3. Apply flattening (if configured)
    4. Collect logical field paths
    5. Build field code mapping
    6. Prepare metadata
    
    Args:
        data: JSON data as a dictionary or list
        config: Compression configuration
        
    Returns:
        Tuple of (filtered_data, field_paths, path_to_code, original_root_type)
        
    Raises:
        ValueError: If the data or configuration is invalid
    """
    if not data:
        return data, [], {}, ""
    
    if not isinstance(config, CompressionConfig):
        raise ValueError("config must be a CompressionConfig instance")
    
    # Determine original root type
    if isinstance(data, dict):
        original_root_type = "dict"
    elif isinstance(data, list):
        original_root_type = "list"
    else:
        raise ValueError("Data must be a dictionary or list")
    
    # Apply filtering
    if config.filter_config:
        data = _apply_filter(data, config.filter_config)
    
    # Apply flattening
    if config.flatten_config and config.flatten_config.enabled:
        data = _apply_flatten(data, config.flatten_config)
    
    # Collect logical field paths
    field_paths = _collect_logical_fields(data, config)
    
    # Build field code mapping
    path_to_code = _build_field_code_map(field_paths, config)
    
    return data, field_paths, path_to_code, original_root_type


def build_encoding_map(
    data: Union[Dict[str, Any], List[Any]],
    config: CompressionConfig,
) -> Dict[str, str]:
    """Build encoding map for field code mapping.
    
    This function collects field paths from the data and builds a mapping
    to field codes based on the compression configuration.
    
    Args:
        data: JSON data as a dictionary or list
        config: Compression configuration
        
    Returns:
        Dictionary mapping field paths to field codes
    """
    # Apply filtering and flattening first to get the correct field paths
    processed_data = data
    
    if config.filter_config:
        processed_data = _apply_filter(processed_data, config.filter_config)
    
    if config.flatten_config and config.flatten_config.enabled:
        processed_data = _apply_flatten(processed_data, config.flatten_config)
    
    # Collect field paths
    field_paths = _collect_logical_fields(processed_data, config)
    
    # Build field code mapping
    path_to_code = _build_field_code_map(field_paths, config)
    
    return path_to_code


def encode_data(
    data: Union[Dict[str, Any], List[Any]],
    path_to_code: Dict[str, str],
    config: CompressionConfig,
    original_root_type: str,
    sep: str = ".",
) -> Tuple[Union[Dict[str, Any], List[Any]], Dict[str, Any]]:
    """Encode data using field codes and optional tabular array encoding.
    
    This function encodes the data by:
    1. Applying field code mapping
    2. Applying tabular array encoding (if configured)
    3. Building schema object for the compressed data
    
    Args:
        data: JSON data to encode (should be filtered/flattened already)
        path_to_code: Mapping from field paths to field codes
        config: Compression configuration
        original_root_type: Type of the original root object ("dict" or "list")
        sep: Separator for nested paths
        
    Returns:
        Tuple of (encoded_data, schema)
    """
    if not isinstance(data, (dict, list)):
        raise ValueError("Data must be a dictionary or list")
    
    # Start with a copy of the data to avoid modifying the original
    encoded_data = data.copy() if isinstance(data, dict) else data[:]
    
    # Apply field code mapping
    if config.key_mapping_config and config.key_mapping_config.enabled and path_to_code:
        encoded_data = _encode_data_with_field_codes(encoded_data, path_to_code, "", sep)
    
    # Apply tabular array encoding
    tabular_metadata: Dict[str, Any] = {}
    if config.tabular_config and config.tabular_config.enabled:
        encoded_data, tabular_metadata = _encode_tabular_arrays(
            encoded_data, path_to_code, config, sep
        )
    
    # Add compression metadata
    if isinstance(encoded_data, dict):
        encoded_data["_compression_metadata"] = {
            "strategy": config.strategy,
            "preserve_types": config.preserve_types,
            "compression_level": config.compression_level,
        }
        
        # Store field codes in result if key mapping was applied
        if config.key_mapping_config and config.key_mapping_config.enabled and path_to_code:
            encoded_data["_field_codes"] = path_to_code
    
    # Build schema object
    schema = _build_schema_object(
        original_root_type=original_root_type,
        config=config,
        path_to_code=path_to_code,
        tabular_metadata=tabular_metadata,
    )
    
    return encoded_data, schema


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
    
    # Step 1: Initialize compression (filter, flatten, collect fields, build map)
    processed_data, field_paths, path_to_code, original_root_type = init_compress_json(data, config)
    
    # Step 2: Encode data using field codes and tabular arrays
    encoded_data, schema = encode_data(
        processed_data, path_to_code, config, original_root_type
    )
    
    # Step 3: Add schema to result (optional, based on config)
    if isinstance(encoded_data, dict):
        # Store schema in a separate field
        encoded_data["_schema"] = schema
    
    return encoded_data
