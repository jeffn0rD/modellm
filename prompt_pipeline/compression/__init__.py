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
from prompt_pipeline.compression.strategies.full import FullCompressionStrategy
from prompt_pipeline.compression.strategies.anchor_index import AnchorIndexCompressionStrategy
from prompt_pipeline.compression.strategies.concept_summary import ConceptSummaryCompressionStrategy
from prompt_pipeline.compression.strategies.hierarchical import HierarchicalCompressionStrategy
from prompt_pipeline.compression.strategies.schema_only import SchemaOnlyCompressionStrategy
from prompt_pipeline.compression.strategies.differential import DifferentialCompressionStrategy
from prompt_pipeline.compression.manager import (
    CompressionManager,
    CompressionConfig,
    CompressionMetrics,
)

__all__ = [
    "CompressionStrategy",
    "CompressionResult",
    "CompressionContext",
    "FullCompressionStrategy",
    "AnchorIndexCompressionStrategy",
    "ConceptSummaryCompressionStrategy",
    "HierarchicalCompressionStrategy",
    "SchemaOnlyCompressionStrategy",
    "DifferentialCompressionStrategy",
    "CompressionManager",
    "CompressionConfig",
    "CompressionMetrics",
]
