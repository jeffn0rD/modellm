"""
Compression module for the prompt pipeline.

This module provides various compression strategies to reduce context size
when sending prompts to LLMs.
"""

from prompt_pipeline.compression.strategies.base import (
    CompressionStrategy,
    CompressionResult,
    CompressionContext,
)
from prompt_pipeline.compression.strategies.zero_compression import ZeroCompressionStrategy
from prompt_pipeline.compression.strategies.anchor_index import AnchorIndexCompressionStrategy
from prompt_pipeline.compression.strategies.concept_summary import ConceptSummaryCompressionStrategy
from prompt_pipeline.compression.strategies.hierarchical import HierarchicalCompressionStrategy
from prompt_pipeline.compression.strategies.schema_only import SchemaOnlyCompressionStrategy
from prompt_pipeline.compression.strategies.differential import DifferentialCompressionStrategy
from prompt_pipeline.compression.strategies.json_compact import JsonCompactStrategy
from prompt_pipeline.compression.manager import (
    CompressionManager,
    CompressionConfig,
    CompressionMetrics,
)
from prompt_pipeline.compression.json_compression import (
    compress_json,
    decompress_json,
    yaml_to_json_dict,
    validate_yaml,
    load_yaml_config,
    yaml_to_json_file,
    parse_json_compact_strategy_config,
)

__all__ = [
    "CompressionStrategy",
    "CompressionResult",
    "CompressionContext",
    "ZeroCompressionStrategy",
    "AnchorIndexCompressionStrategy",
    "ConceptSummaryCompressionStrategy",
    "HierarchicalCompressionStrategy",
    "SchemaOnlyCompressionStrategy",
    "DifferentialCompressionStrategy",
    "JsonCompactStrategy",
    "CompressionManager",
    "CompressionConfig",
    "CompressionMetrics",
    "compress_json",
    "decompress_json",
    "yaml_to_json_dict",
    "validate_yaml",
    "load_yaml_config",
    "yaml_to_json_file",
    "parse_json_compact_strategy_config",
]
