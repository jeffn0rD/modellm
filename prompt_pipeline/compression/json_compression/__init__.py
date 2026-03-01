"""
JSON Compression Module

This module provides compression and decompression utilities for JSON data,
with support for various strategies including field code mapping, tabular
array encoding, and custom compression configurations.

Classes:
    CompressionConfig: Configuration for compression strategies
    FilterConfig: Configuration for field filtering
    FlattenConfig: Configuration for flattening nested structures
    KeyMappingConfig: Configuration for key mapping
    TabularConfig: Configuration for tabular array encoding
    CompressionStrategy: Base class for compression strategies
    JsonCompactStrategy: JSON compact compression strategy

Functions:
    compress_json: Compress JSON data using a configuration
    decompress_json: Decompress JSON data using a configuration
    yaml_to_json_dict: Convert YAML content to JSON-compatible dict
"""

from .config import (
    CompressionConfig,
    FilterConfig,
    FlattenConfig,
    KeyMappingConfig,
    TabularConfig,
)
from .compressor import compress_json
from .decompressor import decompress_json
from .strategy import CompressionStrategy, JsonCompactStrategy
from .yaml_utils import yaml_to_json_dict

__all__ = [
    "CompressionConfig",
    "FilterConfig",
    "FlattenConfig",
    "KeyMappingConfig",
    "TabularConfig",
    "CompressionStrategy",
    "JsonCompactStrategy",
    "compress_json",
    "decompress_json",
    "yaml_to_json_dict",
]
