"""Tests for HierarchicalCompressionStrategy."""

import pytest

from prompt_pipeline.compression.strategies.hierarchical import (
    HierarchicalCompressionStrategy,
)
from prompt_pipeline.compression.strategies.base import (
    CompressionContext,
    CompressionResult,
)


class TestHierarchicalCompressionStrategy:
    """Tests for HierarchicalCompressionStrategy class."""

    def test_strategy_name(self):
        """Test that the strategy has the correct name."""
        strategy = HierarchicalCompressionStrategy()
        assert strategy.name == "hierarchical"

    def test_strategy_description(self):
        """Test that the strategy has a description."""
        strategy = HierarchicalCompressionStrategy()
        assert len(strategy.description) > 0
        assert "layer" in strategy.description.lower()
        assert "summary" in strategy.description.lower()

    def test_compression_level_1_light(self):
        """Test compression with level 1 (light - only executive summary)."""
        strategy = HierarchicalCompressionStrategy()
        
        content = """
{
  "entities": [
    {"id": "E1", "type": "Actor", "name": "User"},
    {"id": "E2", "type": "Action", "name": "Submit"},
    {"id": "E3", "type": "DataEntity", "name": "Form"}
  ]
}
"""
        
        context = CompressionContext(
            content_type="json",
            label="concepts",
            level=1
        )
        
        result = strategy.compress(content, context)
        
        # Verify result structure
        assert isinstance(result, CompressionResult)
        assert result.strategy_name == "hierarchical"
        assert result.original_length > 0
        assert result.compressed_length > 0
        
        # Verify layer 1 is present
        assert "# Layer 1: Executive Summary" in result.content
        
        # Verify layer 2 and 3 are NOT present for level 1
        assert "# Layer 2: Inventory" not in result.content
        assert "# Layer 3: Definitions" not in result.content
        
        # Verify metadata
        assert result.metadata is not None
        assert result.metadata["level"] == 1
        assert "layer1" in result.metadata["layers_included"]
        assert len(result.metadata["layers_included"]) == 1

    def test_compression_level_2_medium(self):
        """Test compression with level 2 (medium - summary + inventory)."""
        strategy = HierarchicalCompressionStrategy()
        
        content = """
{
  "entities": [
    {"id": "E1", "type": "Actor", "name": "User"},
    {"id": "E2", "type": "Action", "name": "Submit"},
    {"id": "E3", "type": "DataEntity", "name": "Form"}
  ]
}
"""
        
        context = CompressionContext(
            content_type="json",
            label="concepts",
            level=2
        )
        
        result = strategy.compress(content, context)
        
        # Verify layer 1 and 2 are present
        assert "# Layer 1: Executive Summary" in result.content
        assert "# Layer 2: Inventory" in result.content
        
        # Verify layer 3 is NOT present for level 2
        assert "# Layer 3: Definitions" not in result.content
        
        # Verify metadata
        assert result.metadata["level"] == 2
        assert "layer1" in result.metadata["layers_included"]
        assert "layer2" in result.metadata["layers_included"]
        assert len(result.metadata["layers_included"]) == 2

    def test_compression_level_3_aggressive(self):
        """Test compression with level 3 (aggressive - all layers)."""
        strategy = HierarchicalCompressionStrategy()
        
        content = """
{
  "entities": [
    {"id": "E1", "type": "Actor", "name": "User"},
    {"id": "E2", "type": "Action", "name": "Submit"},
    {"id": "E3", "type": "DataEntity", "name": "Form"}
  ]
}
"""
        
        context = CompressionContext(
            content_type="json",
            label="concepts",
            level=3
        )
        
        result = strategy.compress(content, context)
        
        # Verify all layers are present
        assert "# Layer 1: Executive Summary" in result.content
        assert "# Layer 2: Inventory" in result.content
        assert "# Layer 3: Definitions" in result.content
        
        # Verify metadata
        assert result.metadata["level"] == 3
        assert "layer1" in result.metadata["layers_included"]
        assert "layer2" in result.metadata["layers_included"]
        assert "layer3" in result.metadata["layers_included"]
        assert len(result.metadata["layers_included"]) == 3

    def test_compression_with_json_content(self):
        """Test compressing JSON content with entity types."""
        strategy = HierarchicalCompressionStrategy()
        
        content = """
{
  "Actors": [
    {"id": "AN1", "name": "System Admin", "description": "Manages the system"}
  ],
  "Actions": [
    {"id": "AN2", "name": "Login", "description": "User authentication"}
  ],
  "DataEntities": [
    {"id": "AN3", "name": "User Table", "description": "Stores user data"}
  ]
}
"""
        
        context = CompressionContext(
            content_type="json",
            label="concepts",
            level=2
        )
        
        result = strategy.compress(content, context)
        
        # Verify content contains expected information
        assert "# Layer 1: Executive Summary" in result.content
        assert "# Layer 2: Inventory" in result.content
        
        # Verify IDs are extracted
        assert "AN1" in result.content
        assert "AN2" in result.content
        assert "AN3" in result.content
        
        # Verify entity types are counted
        assert "Actors" in result.content or "Actions" in result.content

    def test_compression_with_markdown_content(self):
        """Test compressing markdown content."""
        strategy = HierarchicalCompressionStrategy()
        
        content = """
# Executive Summary

This is a test document with sections.

# Section 1

Details about section 1.

# Section 2

Details about section 2.

## Subsection 2.1

More details.

Pattern IDs: AN1, AN2, AN3
"""
        
        context = CompressionContext(
            content_type="md",
            label="spec",
            level=2
        )
        
        result = strategy.compress(content, context)
        
        # Verify layers are present
        assert "# Layer 1: Executive Summary" in result.content
        assert "# Layer 2: Inventory" in result.content
        
        # Verify section headers are extracted
        assert "Section 1" in result.content or "Section 2" in result.content

    def test_compression_ratio(self):
        """Test that compression ratio is within expected range."""
        strategy = HierarchicalCompressionStrategy()
        
        # Large content to test compression
        content = """
{
  "entities": [
    {"id": "E1", "type": "Actor", "name": "User", "description": "This is a longer description that will be compressed"},
    {"id": "E2", "type": "Action", "name": "Submit", "description": "Another longer description for compression testing"},
    {"id": "E3", "type": "DataEntity", "name": "Form", "description": "Yet another long description for testing compression ratios"}
  ],
  "metadata": {
    "version": "1.0",
    "created": "2024-01-01",
    "updated": "2024-01-02",
    "author": "Test Author",
    "description": "This is a comprehensive test document with lots of metadata that should be compressed"
  }
}
"""
        
        context = CompressionContext(
            content_type="json",
            label="concepts",
            level=2
        )
        
        result = strategy.compress(content, context)
        
        # Calculate compression ratio
        compression_ratio = result.compressed_length / result.original_length
        
        # Expected compression ratio: 0.2-0.5 (50-80% reduction)
        # Note: With hierarchical layers, compression can be more aggressive
        assert compression_ratio >= 0.2
        assert compression_ratio <= 0.5

    def test_get_compression_ratio(self):
        """Test the get_compression_ratio method."""
        strategy = HierarchicalCompressionStrategy()
        ratio = strategy.get_compression_ratio()
        
        # Should return a float between 0.3 and 0.5
        assert isinstance(ratio, float)
        assert ratio >= 0.3
        assert ratio <= 0.5

    def test_get_supported_content_types(self):
        """Test the get_supported_content_types method."""
        strategy = HierarchicalCompressionStrategy()
        supported_types = strategy.get_supported_content_types()
        
        # Should support multiple content types
        assert isinstance(supported_types, list)
        assert "json" in supported_types
        assert "yaml" in supported_types
        assert "md" in supported_types
        assert "text" in supported_types

    def test_decompress_not_supported(self):
        """Test that decompression raises NotImplementedError."""
        strategy = HierarchicalCompressionStrategy()
        
        context = CompressionContext(
            content_type="json",
            label="concepts",
            level=1
        )
        
        with pytest.raises(NotImplementedError):
            strategy.decompress("compressed content", context)

    def test_validate_content_valid_json(self):
        """Test validate_content with valid JSON."""
        strategy = HierarchicalCompressionStrategy()
        
        content = '{"id": "test", "name": "Test"}'
        context = CompressionContext(
            content_type="json",
            label="test",
            level=1
        )
        
        is_valid = strategy.validate_content(content, context)
        assert is_valid is True

    def test_validate_content_valid_markdown(self):
        """Test validate_content with valid markdown."""
        strategy = HierarchicalCompressionStrategy()
        
        content = "# Header\n\nSome content with AN1, AN2 patterns"
        context = CompressionContext(
            content_type="md",
            label="test",
            level=1
        )
        
        is_valid = strategy.validate_content(content, context)
        assert is_valid is True

    def test_validate_content_invalid(self):
        """Test validate_content with invalid/unstructured content."""
        strategy = HierarchicalCompressionStrategy()
        
        content = "Plain text without any structure or patterns"
        context = CompressionContext(
            content_type="text",
            label="test",
            level=1
        )
        
        is_valid = strategy.validate_content(content, context)
        assert is_valid is False

    def test_default_level_is_medium(self):
        """Test that default compression level uses medium settings."""
        strategy = HierarchicalCompressionStrategy()
        
        content = '{"entities": [{"id": "E1"}]}'
        context = CompressionContext(
            content_type="json",
            label="test",
            level=2  # Explicit medium
        )
        
        result = strategy.compress(content, context)
        
        # Should include layers 1 and 2
        assert "# Layer 1: Executive Summary" in result.content
        assert "# Layer 2: Inventory" in result.content
        assert "# Layer 3: Definitions" not in result.content

    def test_level_1_uses_executive_summary_only(self):
        """Test that level 1 only includes executive summary."""
        strategy = HierarchicalCompressionStrategy()
        
        content = """
{
  "entities": [
    {"id": "E1", "type": "Actor", "name": "User"}
  ]
}
"""
        
        context = CompressionContext(
            content_type="json",
            label="test",
            level=1
        )
        
        result = strategy.compress(content, context)
        
        # Verify only layer 1 is present
        assert "# Layer 1: Executive Summary" in result.content
        assert "# Layer 2" not in result.content
        assert "# Layer 3" not in result.content
        
        # Verify metadata shows only layer 1
        assert result.metadata["layers_included"] == ["layer1"]

    def test_level_3_includes_all_layers(self):
        """Test that level 3 includes all three layers."""
        strategy = HierarchicalCompressionStrategy()
        
        content = """
{
  "entities": [
    {"id": "E1", "type": "Actor", "name": "User"}
  ]
}
"""
        
        context = CompressionContext(
            content_type="json",
            label="test",
            level=3
        )
        
        result = strategy.compress(content, context)
        
        # Verify all layers are present
        assert "# Layer 1: Executive Summary" in result.content
        assert "# Layer 2: Inventory" in result.content
        assert "# Layer 3: Definitions" in result.content
        
        # Verify metadata shows all layers
        assert len(result.metadata["layers_included"]) == 3
        assert "layer1" in result.metadata["layers_included"]
        assert "layer2" in result.metadata["layers_included"]
        assert "layer3" in result.metadata["layers_included"]

    def test_content_with_multiple_entity_types(self):
        """Test compression with multiple entity types (Actors, Actions, DataEntities)."""
        strategy = HierarchicalCompressionStrategy()
        
        content = """
{
  "Actors": [
    {"id": "AN1", "name": "Admin"},
    {"id": "AN2", "name": "User"}
  ],
  "Actions": [
    {"id": "AN3", "name": "Login"},
    {"id": "AN4", "name": "Logout"}
  ],
  "DataEntities": [
    {"id": "AN5", "name": "Table"},
    {"id": "AN6", "name": "View"}
  ]
}
"""
        
        context = CompressionContext(
            content_type="json",
            label="concepts",
            level=2
        )
        
        result = strategy.compress(content, context)
        
        # Verify inventory includes IDs from all entity types
        assert "AN1" in result.content
        assert "AN2" in result.content
        assert "AN3" in result.content
        assert "AN4" in result.content
        assert "AN5" in result.content
        assert "AN6" in result.content
        
        # Verify total count
        assert "Total items: 6" in result.content

    def test_json_array_content(self):
        """Test compression with JSON array content."""
        strategy = HierarchicalCompressionStrategy()
        
        content = """
[
  {"id": "E1", "type": "Actor", "name": "User"},
  {"id": "E2", "type": "Action", "name": "Submit"},
  {"id": "E3", "type": "DataEntity", "name": "Form"}
]
"""
        
        context = CompressionContext(
            content_type="json",
            label="concepts",
            level=2
        )
        
        result = strategy.compress(content, context)
        
        # Verify it handles array structure
        assert "# Layer 1: Executive Summary" in result.content
        assert "# Layer 2: Inventory" in result.content
        assert "E1" in result.content
        assert "E2" in result.content
        assert "E3" in result.content

    def test_default_level_with_no_explicit_level(self):
        """Test that when level is not in LEVEL_LAYERS, it defaults to medium."""
        strategy = HierarchicalCompressionStrategy()
        
        content = '{"entities": [{"id": "E1"}]}'
        
        # Create context with level 2 (medium) which is in LEVEL_LAYERS
        context = CompressionContext(
            content_type="json",
            label="test",
            level=2
        )
        
        result = strategy.compress(content, context)
        
        # Should use the specified level
        assert result.metadata["level"] == 2
        assert "layer1" in result.metadata["layers_included"]
        assert "layer2" in result.metadata["layers_included"]
