"""
Compression strategies for the prompt pipeline.

Each strategy implements a different compression approach:
- full: No compression (returns content as-is)
- anchor_index: Extract anchor definitions from YAML specs
- concept_summary: Generate concept summary tables from JSON
- hierarchical: Layered compression with summaries
- schema_only: Schema-only references with counts
- differential: Only pass changes from previous version
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
