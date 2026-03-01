"""
Configuration dataclasses for JSON compression strategies.

This module defines dataclasses for configuring various compression
strategies including filtering, flattening, key mapping, and tabular
array encoding.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class FilterConfig:
    """Configuration for field filtering during compression.
    
    Attributes:
        include_fields: List of field names to include (whitelist)
        exclude_fields: List of field names to exclude (blacklist)
    """
    include_fields: Optional[List[str]] = None
    exclude_fields: Optional[List[str]] = None


@dataclass
class FlattenConfig:
    """Configuration for flattening nested structures.
    
    Attributes:
        enabled: Whether to enable flattening
        delimiter: Delimiter to use for flattened keys (default: ".")
        max_depth: Maximum nesting depth to flatten (None = unlimited)
    """
    enabled: bool = False
    delimiter: str = "."
    max_depth: Optional[int] = None


@dataclass
class KeyMappingConfig:
    """Configuration for mapping field names to codes.
    
    Attributes:
        enabled: Whether to enable key mapping
        mapping: Manual mapping of field names to codes
        code_prefix: Prefix for generated field codes (default: "F")
        counter_start: Starting value for code counter (default: 0)
    """
    enabled: bool = True
    mapping: Optional[Dict[str, str]] = None
    code_prefix: str = "F"
    counter_start: int = 0


@dataclass
class TabularConfig:
    """Configuration for encoding tabular arrays.
    
    Attributes:
        enabled: Whether to enable tabular array encoding
        key_column: Column to use as the key (for mapping rows)
        tabular_fields: List of fields to encode as tabular
        compression_ratio: Target compression ratio (0.0-1.0)
    """
    enabled: bool = False
    key_column: Optional[str] = None
    tabular_fields: Optional[List[str]] = None
    compression_ratio: Optional[float] = None


@dataclass
class CompressionConfig:
    """Main configuration for JSON compression strategy.
    
    Attributes:
        strategy: Type of compression strategy ("json_compact", etc.)
        filter_config: Configuration for field filtering
        flatten_config: Configuration for flattening nested structures
        key_mapping_config: Configuration for field code mapping
        tabular_config: Configuration for tabular array encoding
        preserve_types: Whether to preserve type information
        compression_level: Overall compression level (0-100)
        custom_metadata: Additional metadata for the strategy
    """
    strategy: str
    filter_config: Optional[FilterConfig] = None
    flatten_config: Optional[FlattenConfig] = None
    key_mapping_config: Optional[KeyMappingConfig] = None
    tabular_config: Optional[TabularConfig] = None
    preserve_types: bool = True
    compression_level: int = 50
    custom_metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary representation.
        
        Returns:
            Dictionary representation of the configuration
        """
        result: Dict[str, Any] = {
            "strategy": self.strategy,
            "preserve_types": self.preserve_types,
            "compression_level": self.compression_level,
        }
        
        if self.filter_config:
            result["filter"] = {
                "include_fields": self.filter_config.include_fields,
                "exclude_fields": self.filter_config.exclude_fields,
            }
        
        if self.flatten_config:
            result["flatten"] = {
                "enabled": self.flatten_config.enabled,
                "delimiter": self.flatten_config.delimiter,
                "max_depth": self.flatten_config.max_depth,
            }
        
        if self.key_mapping_config:
            result["key_mapping"] = {
                "enabled": self.key_mapping_config.enabled,
                "mapping": self.key_mapping_config.mapping,
                "code_prefix": self.key_mapping_config.code_prefix,
                "counter_start": self.key_mapping_config.counter_start,
            }
        
        if self.tabular_config:
            result["tabular"] = {
                "enabled": self.tabular_config.enabled,
                "key_column": self.tabular_config.key_column,
                "tabular_fields": self.tabular_config.tabular_fields,
                "compression_ratio": self.tabular_config.compression_ratio,
            }
        
        if self.custom_metadata:
            result["metadata"] = self.custom_metadata
        
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CompressionConfig':
        """Create configuration from dictionary representation.
        
        Args:
            data: Dictionary representation of the configuration
            
        Returns:
            CompressionConfig instance
        """
        # Extract filter config
        filter_config = None
        if "filter" in data:
            filter_config = FilterConfig(
                include_fields=data["filter"].get("include_fields"),
                exclude_fields=data["filter"].get("exclude_fields"),
            )
        
        # Extract flatten config
        flatten_config = None
        if "flatten" in data:
            flatten_config = FlattenConfig(
                enabled=data["flatten"].get("enabled", False),
                delimiter=data["flatten"].get("delimiter", "."),
                max_depth=data["flatten"].get("max_depth"),
            )
        
        # Extract key mapping config
        key_mapping_config = None
        if "key_mapping" in data:
            key_mapping_config = KeyMappingConfig(
                enabled=data["key_mapping"].get("enabled", True),
                mapping=data["key_mapping"].get("mapping"),
                code_prefix=data["key_mapping"].get("code_prefix", "F"),
                counter_start=data["key_mapping"].get("counter_start", 0),
            )
        
        # Extract tabular config
        tabular_config = None
        if "tabular" in data:
            tabular_config = TabularConfig(
                enabled=data["tabular"].get("enabled", False),
                key_column=data["tabular"].get("key_column"),
                tabular_fields=data["tabular"].get("tabular_fields"),
                compression_ratio=data["tabular"].get("compression_ratio"),
            )
        
        return cls(
            strategy=data["strategy"],
            filter_config=filter_config,
            flatten_config=flatten_config,
            key_mapping_config=key_mapping_config,
            tabular_config=tabular_config,
            preserve_types=data.get("preserve_types", True),
            compression_level=data.get("compression_level", 50),
            custom_metadata=data.get("metadata"),
        )
