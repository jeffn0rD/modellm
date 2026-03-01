"""
Compression strategy classes for JSON compression module.

This module defines the base CompressionStrategy class and the
JsonCompactStrategy implementation for JSON compression.
"""

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from .config import CompressionConfig
from .config import KeyMappingConfig as _KeyMappingConfig
from .compressor import compress_json
from .decompressor import decompress_json


class CompressionStrategy(ABC):
    """Abstract base class for compression strategies.
    
    This class defines the interface that all compression strategies
    must implement.
    """
    
    @abstractmethod
    def compress(self, data: Union[Dict[str, Any], List[Any]]) -> Union[Dict[str, Any], List[Any]]:
        """Compress data using the strategy.
        
        Args:
            data: Data to compress
            
        Returns:
            Compressed data
        """
        pass
    
    @abstractmethod
    def decompress(self, data: Union[Dict[str, Any], List[Any]]) -> Union[Dict[str, Any], List[Any]]:
        """Decompress data using the strategy.
        
        Args:
            data: Compressed data
            
        Returns:
            Decompressed data
        """
        pass
    
    @abstractmethod
    def get_config(self) -> CompressionConfig:
        """Get the compression configuration.
        
        Returns:
            Compression configuration
        """
        pass


class JsonCompactStrategy(CompressionStrategy):
    """JSON compact compression strategy.
    
    This strategy uses field code mapping to reduce the size of JSON
    data by replacing long field names with short codes.
    
    Features:
    - Field code mapping (e.g., "fieldName" -> "F0")
    - Optional filtering of fields
    - Optional flattening of nested structures
    - Tabular array encoding for arrays of objects
    """
    
    def __init__(
        self,
        config: Optional[CompressionConfig] = None,
    ):
        """Initialize the JSON compact strategy.
        
        Args:
            config: Compression configuration
        """
        if config is None:
            # Default configuration for JSON compact strategy
            config = CompressionConfig(
                strategy="json_compact",
                key_mapping_config=_KeyMappingConfig(enabled=True),
            )
        
        self.config = config
    
    def compress(self, data: Union[Dict[str, Any], List[Any]]) -> Union[Dict[str, Any], List[Any]]:
        """Compress data using JSON compact strategy.
        
        Args:
            data: Data to compress
            
        Returns:
            Compressed data
        """
        return compress_json(data, self.config)
    
    def decompress(self, data: Union[Dict[str, Any], List[Any]]) -> Union[Dict[str, Any], List[Any]]:
        """Decompress data using JSON compact strategy.
        
        Args:
            data: Compressed data
            
        Returns:
            Decompressed data
        """
        return decompress_json(data, self.config)
    
    def get_config(self) -> CompressionConfig:
        """Get the compression configuration.
        
        Returns:
            Compression configuration
        """
        return self.config
    
    def get_supported_content_types(self) -> List[str]:
        """Get the list of supported content types for this strategy.
        
        Returns:
            List of supported content types (e.g., ["yaml", "json"])
        """
        return ["yaml", "json"]
    
    @classmethod
    def from_config_dict(cls, config_dict: Dict[str, Any]) -> 'JsonCompactStrategy':
        """Create strategy from configuration dictionary.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            JsonCompactStrategy instance
        """
        from .config import (
            FilterConfig,
            FlattenConfig,
            KeyMappingConfig,
            TabularConfig,
        )
        
        # Parse filter config
        filter_config = None
        if "filter" in config_dict:
            filter_config = FilterConfig(
                include_fields=config_dict["filter"].get("include_fields"),
                exclude_fields=config_dict["filter"].get("exclude_fields"),
            )
        
        # Parse flatten config
        flatten_config = None
        if "flatten" in config_dict:
            flatten_config = FlattenConfig(
                enabled=config_dict["flatten"].get("enabled", False),
                delimiter=config_dict["flatten"].get("delimiter", "."),
                max_depth=config_dict["flatten"].get("max_depth"),
            )
        
        # Parse key mapping config
        key_mapping_config = None
        if "key_mapping" in config_dict:
            key_mapping_config = KeyMappingConfig(
                enabled=config_dict["key_mapping"].get("enabled", True),
                mapping=config_dict["key_mapping"].get("mapping"),
                code_prefix=config_dict["key_mapping"].get("code_prefix", "F"),
                counter_start=config_dict["key_mapping"].get("counter_start", 0),
            )
        
        # Parse tabular config
        tabular_config = None
        if "tabular" in config_dict:
            tabular_config = TabularConfig(
                enabled=config_dict["tabular"].get("enabled", False),
                key_column=config_dict["tabular"].get("key_column"),
                tabular_fields=config_dict["tabular"].get("tabular_fields"),
                compression_ratio=config_dict["tabular"].get("compression_ratio"),
            )
        
        config = CompressionConfig(
            strategy=config_dict.get("strategy", "json_compact"),
            filter_config=filter_config,
            flatten_config=flatten_config,
            key_mapping_config=key_mapping_config,
            tabular_config=tabular_config,
            preserve_types=config_dict.get("preserve_types", True),
            compression_level=config_dict.get("compression_level", 50),
            custom_metadata=config_dict.get("metadata"),
        )
        
        return cls(config)
