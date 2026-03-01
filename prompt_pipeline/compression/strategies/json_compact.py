"""
JSON Compact compression strategy.

This module implements the CompressionStrategy interface for the json_compact strategy,
which uses field code mapping and tabular array encoding to compress JSON/YAML data.
"""

from typing import Any, Dict, Optional

from prompt_pipeline.compression.json_compression import (
    CompressionConfig,
    FilterConfig,
    FlattenConfig,
    KeyMappingConfig,
    TabularConfig,
    compress_json,
    decompress_json,
    parse_json_compact_strategy_config,
    yaml_to_json_dict,
)
from prompt_pipeline.compression.strategies.base import (
    CompressionContext,
    CompressionResult,
    CompressionStrategy,
    create_compression_result,
)


class JsonCompactStrategy(CompressionStrategy):
    """
    JSON Compact compression strategy using field code mapping and tabular encoding.
    
    This strategy compresses JSON/YAML data by:
    1. Converting YAML to JSON (if needed)
    2. Applying field code mapping to reduce field name size
    3. Encoding arrays of objects as tabular structures
    4. Optional filtering and flattening
    """
    
    @property
    def name(self) -> str:
        """Return the name of the compression strategy."""
        return "json_compact"
    
    @property
    def description(self) -> str:
        """Return a human-readable description of the strategy."""
        return "Compress JSON/YAML data using field code mapping and tabular array encoding"
    
    def compress(self, content: str, context: CompressionContext) -> CompressionResult:
        """
        Compress the given content using json_compact strategy.
        
        Args:
            content: The content to compress (JSON or YAML string).
            context: Context information for the compression.
        
        Returns:
            CompressionResult containing the compressed content and metadata.
        """
        try:
            # Parse the content as JSON or YAML
            if context.content_type == 'yaml':
                # Convert YAML to JSON-compatible dict
                data = yaml_to_json_dict(content)
            elif context.content_type == 'json':
                import json
                data = json.loads(content)
            else:
                raise ValueError(f"Unsupported content type: {context.content_type}")
            
            # Create compression config based on context
            config = self._create_config_from_context(context)
            
            # Apply compression (returns compressed JSON with metadata)
            compressed_data = compress_json(data, config)
            
            # Remove only the schema and compression_metadata fields
            # Keep _tabular_arrays and _field_codes for decompression
            compressed_data_no_meta = {
                k: v for k, v in compressed_data.items() 
                if k not in ["_schema", "_compression_metadata"]
            }
            
            # Convert back to JSON string (minified to save space)
            import json
            compressed_json = json.dumps(compressed_data_no_meta, ensure_ascii=False, separators=(',', ':'))
            
            # Calculate compression metrics
            original_length = len(content)
            compressed_length = len(compressed_json)
            compression_ratio = compressed_length / original_length if original_length > 0 else 1.0
            
            # Build metadata
            metadata = {
                "original_type": context.content_type,
                "strategy": "json_compact",
                "config": {
                    "key_mapping": config.key_mapping_config.enabled if config.key_mapping_config else False,
                    "tabular": config.tabular_config.enabled if config.tabular_config else False,
                    "flatten": config.flatten_config.enabled if config.flatten_config else False,
                },
                "data_size": len(data) if isinstance(data, dict) else None,
            }
            
            return CompressionResult(
                content=compressed_json,
                original_length=original_length,
                compressed_length=compressed_length,
                compression_ratio=compression_ratio,
                strategy_name=self.name,
                metadata=metadata,
            )
            
        except Exception as e:
            # If compression fails, return original content
            original_length = len(content)
            return CompressionResult(
                content=content,
                original_length=original_length,
                compressed_length=original_length,
                compression_ratio=1.0,
                strategy_name=self.name,
                metadata={"error": str(e), "strategy": "none"},
            )
    
    def decompress(self, compressed: str, context: CompressionContext) -> str:
        """
        Decompress the given compressed content.
        
        Args:
            compressed: The compressed content to decompress.
            context: Context information for the decompression.
        
        Returns:
            The decompressed content.
        
        Raises:
            NotImplementedError: If decompression is not supported.
        """
        try:
            import json
            
            # Parse compressed JSON
            compressed_data = json.loads(compressed)
            
            # Create config for decompression
            config = self._create_config_from_context(context)
            
            # Apply decompression
            decompressed_data = decompress_json(compressed_data, config)
            
            # Convert back to original format
            if context.content_type == 'yaml':
                import yaml
                # Convert to YAML
                yaml_content = yaml.safe_dump(
                    decompressed_data,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )
                return yaml_content
            elif context.content_type == 'json':
                # Convert back to JSON string
                return json.dumps(decompressed_data, ensure_ascii=False, indent=2)
            else:
                raise ValueError(f"Unsupported content type: {context.content_type}")
                
        except Exception as e:
            # If decompression fails, raise error
            raise NotImplementedError(f"Decompression not supported for {self.name}: {e}")
    
    def get_compression_ratio(self) -> float:
        """
        Get the typical compression ratio for this strategy.
        
        Returns:
            Expected compression ratio (e.g., 0.3 means ~30% of original size).
        """
        return 0.5  # Typical: 50% of original size
    
    def validate_content(self, content: str, context: CompressionContext) -> bool:
        """
        Validate that the content can be compressed by this strategy.
        
        Args:
            content: The content to validate.
            context: Context information.
        
        Returns:
            True if the content is valid for this strategy.
        """
        # Check if content type is supported
        if context.content_type not in ['yaml', 'json']:
            return False
        
        # Try to parse the content
        try:
            if context.content_type == 'yaml':
                import yaml
                yaml.safe_load(content)
            elif context.content_type == 'json':
                import json
                json.loads(content)
            return True
        except:
            return False
    
    def get_supported_content_types(self) -> list[str]:
        """
        Get the list of content types supported by this strategy.
        
        Returns:
            List of supported content types.
        """
        return ['yaml', 'json']
    
    def _create_config_from_context(self, context: CompressionContext) -> CompressionConfig:
        """
        Create CompressionConfig from context.
        
        Args:
            context: Compression context.
        
        Returns:
            CompressionConfig instance.
        """
        # Default configuration for json_compact
        key_mapping = KeyMappingConfig(enabled=True)
        
        # Enable tabular encoding for root-level arrays
        tabular = TabularConfig(
            enabled=False,  # Disabled by default
            tabular_fields=None,
        )
        
        # Optionally enable flatten
        flatten = FlattenConfig(
            enabled=False,  # Disabled by default
            delimiter=".",
        )
        
        # Parse extra configuration from context
        if context.extra:
            if "key_mapping" in context.extra:
                if context.extra["key_mapping"] is False:
                    key_mapping.enabled = False
                else:
                    key_mapping.enabled = True
            
            if "tabular" in context.extra:
                if isinstance(context.extra["tabular"], dict):
                    tabular.enabled = context.extra["tabular"].get("enabled", False)
                    tabular.tabular_fields = context.extra["tabular"].get("tabular_fields")
                else:
                    tabular.enabled = context.extra["tabular"]
            
            if "flatten" in context.extra:
                flatten.enabled = context.extra["flatten"]
        
        return CompressionConfig(
            strategy="json_compact",
            key_mapping_config=key_mapping,
            tabular_config=tabular,
            flatten_config=flatten,
            preserve_types=True,
            compression_level=2,  # Default to medium
        )
