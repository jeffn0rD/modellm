"""
Compression strategies for the prompt pipeline.

Each strategy implements a different compression approach:
- zero: No compression (returns content as-is)
- anchor_index: Extract anchor definitions from YAML specs
- concept_summary: Generate concept summary tables from JSON
- hierarchical: Layered compression with summaries
- schema_only: Schema-only references with counts
- differential: Only pass changes from previous version
- yaml_as_json: Convert YAML to JSON for prompt input
"""

from prompt_pipeline.compression.strategies.base import CompressionStrategy
from prompt_pipeline.compression.strategies.zero_compression import ZeroCompressionStrategy
from prompt_pipeline.compression.strategies.anchor_index import AnchorIndexCompressionStrategy
from prompt_pipeline.compression.strategies.concept_summary import ConceptSummaryCompressionStrategy
from prompt_pipeline.compression.strategies.hierarchical import HierarchicalCompressionStrategy
from prompt_pipeline.compression.strategies.schema_only import SchemaOnlyCompressionStrategy
from prompt_pipeline.compression.strategies.differential import DifferentialCompressionStrategy
from prompt_pipeline.compression.strategies.yaml_as_json import YamlAsJsonStrategy
from prompt_pipeline.compression.strategies.json_compact import JsonCompactStrategy

__all__ = [
    "CompressionStrategy",
    "ZeroCompressionStrategy",
    "AnchorIndexCompressionStrategy",
    "ConceptSummaryCompressionStrategy",
    "HierarchicalCompressionStrategy",
    "SchemaOnlyCompressionStrategy",
    "DifferentialCompressionStrategy",
    "YamlAsJsonStrategy",
    "JsonCompactStrategy",
]
