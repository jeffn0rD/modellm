"""
Compression module for the prompt pipeline.

This module provides various compression strategies to reduce context size
when sending prompts to LLMs.
"""

from prompt_pipeline.compression.strategies.base import CompressionStrategy
from prompt_pipeline.compression.strategies.full import FullCompressionStrategy
from prompt_pipeline.compression.strategies.anchor_index import AnchorIndexCompressionStrategy
from prompt_pipeline.compression.strategies.concept_summary import ConceptSummaryCompressionStrategy
from prompt_pipeline.compression.strategies.hierarchical import HierarchicalCompressionStrategy
from prompt_pipeline.compression.strategies.schema_only import SchemaOnlyCompressionStrategy
from prompt_pipeline.compression.strategies.differential import DifferentialCompressionStrategy

__all__ = [
    "CompressionStrategy",
    "FullCompressionStrategy",
    "AnchorIndexCompressionStrategy",
    "ConceptSummaryCompressionStrategy",
    "HierarchicalCompressionStrategy",
    "SchemaOnlyCompressionStrategy",
    "DifferentialCompressionStrategy",
]
