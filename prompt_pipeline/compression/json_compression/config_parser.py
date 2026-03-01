"""
YAML configuration parser for JSON compression strategies.

This module provides utilities for parsing YAML configuration
files and converting them to CompressionConfig instances.
"""

import re
from typing import Any, Dict, List, Optional, Union

import yaml

from .config import (
    CompressionConfig,
    FilterConfig,
    FlattenConfig,
    KeyMappingConfig,
    TabularConfig,
)


def parse_yaml_config(yaml_content: str) -> CompressionConfig:
    """Parse YAML configuration and return a CompressionConfig instance.
    
    Args:
        yaml_content: YAML configuration content as a string
        
    Returns:
        CompressionConfig instance
        
    Raises:
        ValueError: If the YAML configuration is invalid
        yaml.YAMLError: If the YAML content is malformed
    """
    try:
        config_dict = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML configuration: {e}")
    
    if not config_dict:
        raise ValueError("Empty configuration")
    
    return from_dict(config_dict)


def from_dict(config_dict: Dict[str, Any]) -> CompressionConfig:
    """Create CompressionConfig from a dictionary.
    
    Args:
        config_dict: Configuration dictionary
        
    Returns:
        CompressionConfig instance
        
    Raises:
        ValueError: If required fields are missing or invalid
    """
    if "strategy" not in config_dict:
        raise ValueError("Configuration must specify a strategy")
    
    # Parse filter configuration
    filter_config = None
    if "filter" in config_dict:
        filter_dict = config_dict["filter"]
        filter_config = FilterConfig(
            include_fields=filter_dict.get("include_fields"),
            exclude_fields=filter_dict.get("exclude_fields"),
        )
    
    # Parse flatten configuration
    flatten_config = None
    if "flatten" in config_dict:
        flatten_dict = config_dict["flatten"]
        flatten_config = FlattenConfig(
            enabled=flatten_dict.get("enabled", False),
            delimiter=flatten_dict.get("delimiter", "."),
            max_depth=flatten_dict.get("max_depth"),
        )
    
    # Parse key mapping configuration
    key_mapping_config = None
    if "key_mapping" in config_dict:
        key_mapping_dict = config_dict["key_mapping"]
        
        # Handle manual field mappings if provided
        mapping = None
        if "field_mappings" in key_mapping_dict:
            mapping = key_mapping_dict["field_mappings"]
        
        key_mapping_config = KeyMappingConfig(
            enabled=key_mapping_dict.get("enabled", True),
            mapping=mapping,
            code_prefix=key_mapping_dict.get("code_prefix", "F"),
            counter_start=key_mapping_dict.get("counter_start", 0),
        )
    
    # Parse tabular configuration
    tabular_config = None
    if "tabular" in config_dict:
        tabular_dict = config_dict["tabular"]
        tabular_config = TabularConfig(
            enabled=tabular_dict.get("enabled", False),
            key_column=tabular_dict.get("key_column"),
            tabular_fields=tabular_dict.get("tabular_fields"),
            compression_ratio=tabular_dict.get("compression_ratio"),
        )
    
    # Parse custom metadata
    custom_metadata = None
    if "metadata" in config_dict:
        custom_metadata = config_dict["metadata"]
    
    return CompressionConfig(
        strategy=config_dict["strategy"],
        filter_config=filter_config,
        flatten_config=flatten_config,
        key_mapping_config=key_mapping_config,
        tabular_config=tabular_config,
        preserve_types=config_dict.get("preserve_types", True),
        compression_level=config_dict.get("compression_level", 50),
        custom_metadata=custom_metadata,
    )


def to_yaml(config: CompressionConfig) -> str:
    """Convert CompressionConfig to YAML string.
    
    Args:
        config: CompressionConfig instance
        
    Returns:
        YAML string representation
    """
    config_dict = config.to_dict()
    return yaml.dump(config_dict, default_flow_style=False, sort_keys=False)


def extract_field_codes(yaml_content: str) -> Dict[str, str]:
    """Extract field code mappings from YAML configuration.
    
    This function looks for field code mappings in the YAML content
    and returns them as a dictionary.
    
    Args:
        yaml_content: YAML configuration content
        
    Returns:
        Dictionary mapping field names to codes
    """
    try:
        config_dict = yaml.safe_load(yaml_content)
    except yaml.YAMLError:
        return {}
    
    field_codes: Dict[str, str] = {}
    
    # Check for key_mapping section
    if "key_mapping" in config_dict:
        key_mapping = config_dict["key_mapping"]
        
        # Check for manual mappings
        if "field_mappings" in key_mapping:
            field_codes = key_mapping["field_mappings"]
    
    return field_codes


def validate_config(config: CompressionConfig) -> List[str]:
    """Validate compression configuration.
    
    Args:
        config: CompressionConfig instance
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors: List[str] = []
    
    if not config.strategy:
        errors.append("Strategy must be specified")
    
    if config.compression_level < 0 or config.compression_level > 100:
        errors.append("Compression level must be between 0 and 100")
    
    if config.filter_config:
        if config.filter_config.include_fields and config.filter_config.exclude_fields:
            errors.append("Cannot specify both include_fields and exclude_fields")
    
    if config.flatten_config:
        if config.flatten_config.enabled and not config.flatten_config.delimiter:
            errors.append("Delimiter must be specified when flattening is enabled")
    
    if config.key_mapping_config:
        if config.key_mapping_config.code_prefix and len(config.key_mapping_config.code_prefix) == 0:
            errors.append("Code prefix cannot be empty")
    
    if config.tabular_config:
        if config.tabular_config.enabled:
            if config.tabular_config.compression_ratio is not None:
                if config.tabular_config.compression_ratio < 0 or config.tabular_config.compression_ratio > 1:
                    errors.append("Compression ratio must be between 0.0 and 1.0")
    
    return errors


def parse_json_compact_strategy_config(
    entity_config: Dict[str, Any],
    strategy_name: str,
) -> Tuple[Optional[CompressionConfig], Optional[str]]:
    """Parse JSON compact strategy configuration from entity config.
    
    This function parses the configuration for the json_compact strategy
    from a data entity configuration and returns a CompressionConfig
    instance along with the output entity name.
    
    Args:
        entity_config: Data entity configuration dictionary
        strategy_name: Name of the strategy to parse (e.g., "minimal_json")
        
    Returns:
        Tuple of (CompressionConfig, output_entity_name) or (None, None) if
        the strategy doesn't match json_compact
        
    Example:
        >>> entity_config = {
        ...     "type": "yaml",
        ...     "filename": "spec.yaml",
        ...     "compression_strategies": {
        ...         "minimal_json": {
        ...             "compression_params": {
        ...                 "key_mapping": {"enabled": true},
        ...                 "tabular": {"enabled": true, "tabular_fields": ["items"]}
        ...             }
        ...         }
        ...     }
        ... }
        >>> config, output_entity = parse_json_compact_strategy_config(
        ...     entity_config, "minimal_json"
        ... )
        >>> assert config is not None
        >>> assert output_entity == "spec_compact"
    """
    # Check if this is a json_compact strategy
    if strategy_name not in ["json_compact", "minimal_json"]:
        return None, None
    
    # Get the strategy configuration
    compression_strategies = entity_config.get("compression_strategies", {})
    strategy_config = compression_strategies.get(strategy_name, {})
    
    if not strategy_config:
        return None, None
    
    # Get compression params
    compression_params = strategy_config.get("compression_params", {})
    
    # Parse filter configuration
    filter_config = None
    if "filter" in compression_params:
        filter_dict = compression_params["filter"]
        filter_config = FilterConfig(
            include_fields=filter_dict.get("include_fields"),
            exclude_fields=filter_dict.get("exclude_fields"),
        )
    
    # Parse flatten configuration
    flatten_config = None
    if "flatten" in compression_params:
        flatten_dict = compression_params["flatten"]
        flatten_config = FlattenConfig(
            enabled=flatten_dict.get("enabled", False),
            delimiter=flatten_dict.get("delimiter", "."),
            max_depth=flatten_dict.get("max_depth"),
        )
    
    # Parse key mapping configuration
    key_mapping_config = None
    if "key_mapping" in compression_params:
        key_mapping_dict = compression_params["key_mapping"]
        key_mapping_config = KeyMappingConfig(
            enabled=key_mapping_dict.get("enabled", True),
            mapping=key_mapping_dict.get("mapping"),
            code_prefix=key_mapping_dict.get("code_prefix", "F"),
            counter_start=key_mapping_dict.get("counter_start", 0),
        )
    
    # Parse tabular configuration
    tabular_config = None
    if "tabular" in compression_params:
        tabular_dict = compression_params["tabular"]
        tabular_config = TabularConfig(
            enabled=tabular_dict.get("enabled", False),
            key_column=tabular_dict.get("key_column"),
            tabular_fields=tabular_dict.get("tabular_fields"),
            compression_ratio=tabular_dict.get("compression_ratio"),
        )
    
    # Determine output entity name
    filename = entity_config.get("filename", "")
    if filename:
        # Remove extension and add _compact
        import os
        base_name = os.path.splitext(filename)[0]
        output_entity = f"{base_name}_compact"
    else:
        # Fallback: use entity name if available
        entity_name = entity_config.get("name", "unknown")
        output_entity = f"{entity_name}_compact"
    
    # Create compression config
    config = CompressionConfig(
        strategy=strategy_name,
        filter_config=filter_config,
        flatten_config=flatten_config,
        key_mapping_config=key_mapping_config,
        tabular_config=tabular_config,
        preserve_types=compression_params.get("preserve_types", True),
        compression_level=compression_params.get("compression_level", 50),
        custom_metadata=compression_params.get("metadata"),
    )
    
    return config, output_entity
