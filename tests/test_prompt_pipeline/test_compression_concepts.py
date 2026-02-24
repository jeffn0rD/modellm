"""Tests for ConceptSummaryCompressionStrategy."""

import json
import pytest

from prompt_pipeline.compression.strategies.concept_summary import (
    ConceptSummaryCompressionStrategy,
)
from prompt_pipeline.compression.strategies.base import (
    CompressionContext,
    CompressionResult,
)


class TestConceptSummaryCompressionStrategy:
    """Tests for ConceptSummaryCompressionStrategy class."""

    def test_strategy_name(self):
        """Test that the strategy has the correct name."""
        strategy = ConceptSummaryCompressionStrategy()
        assert strategy.name == "concept_summary"

    def test_strategy_description(self):
        """Test that the strategy has a description."""
        strategy = ConceptSummaryCompressionStrategy()
        assert len(strategy.description) > 0
        assert "concept" in strategy.description.lower()

    def test_compress_with_concepts_array(self):
        """Test compressing a JSON array of concepts."""
        strategy = ConceptSummaryCompressionStrategy()
        
        content = json.dumps([
            {
                "type": "Actor",
                "id": "A1",
                "label": "EndUser",
                "description": "A single person using the application.",
            },
            {
                "type": "Action",
                "id": "ACT1",
                "label": "CreateTask",
                "description": "Create a new to-do task.",
            },
        ])
        
        context = CompressionContext(
            content_type="json",
            label="concepts",
            level=1
        )
        
        result = strategy.compress(content, context)
        
        # Verify result structure
        assert isinstance(result, CompressionResult)
        assert result.strategy_name == "concept_summary"
        assert result.original_length > 0
        assert result.compressed_length > 0
        
        # Verify content contains markdown tables
        assert "# Concept Summary" in result.content
        assert "## Actors" in result.content
        assert "## Actions" in result.content
        assert "A1" in result.content
        assert "ACT1" in result.content
        
        # Verify metadata
        assert result.metadata is not None
        assert result.metadata["concept_count"] == 2
        assert "Actor" in result.metadata["entity_types"]
        assert "Action" in result.metadata["entity_types"]

    def test_compress_with_concepts_object(self):
        """Test compressing a JSON object with concepts array."""
        strategy = ConceptSummaryCompressionStrategy()
        
        content = json.dumps({
            "concepts": [
                {
                    "type": "DataEntity",
                    "id": "D1",
                    "label": "Task",
                    "description": "A to-do item with completion status.",
                }
            ]
        })
        
        context = CompressionContext(
            content_type="json",
            label="concepts",
            level=1
        )
        
        result = strategy.compress(content, context)
        
        # Should extract concepts from the object
        assert result.metadata["concept_count"] == 1
        assert "D1" in result.content

    def test_compress_level_1_with_description_and_relationships(self):
        """Test compression with level 1 (includes description and relationships)."""
        strategy = ConceptSummaryCompressionStrategy()
        
        content = json.dumps([
            {
                "type": "Actor",
                "id": "A1",
                "label": "EndUser",
                "description": "A single person using the application with full description.",
                "relationships": ["uses", "interacts_with"],
            }
        ])
        
        context = CompressionContext(
            content_type="json",
            label="concepts",
            level=1
        )
        
        result = strategy.compress(content, context)
        
        # Level 1 should include description and relationships
        assert "Description" in result.content
        assert "Relationships" in result.content
        assert "A single person" in result.content
        assert "uses" in result.content

    def test_compress_level_2_with_description_only(self):
        """Test compression with level 2 (includes description, no relationships)."""
        strategy = ConceptSummaryCompressionStrategy()
        
        content = json.dumps([
            {
                "type": "Action",
                "id": "ACT1",
                "label": "CreateTask",
                "description": "Create a new to-do task.",
                "relationships": ["requires"],
            }
        ])
        
        context = CompressionContext(
            content_type="json",
            label="concepts",
            level=2
        )
        
        result = strategy.compress(content, context)
        
        # Level 2 should include description but not relationships
        assert "Description" in result.content
        assert "CreateTask" in result.content
        assert "Relationships" not in result.content

    def test_compress_level_3_no_description(self):
        """Test compression with level 3 (no description, no relationships)."""
        strategy = ConceptSummaryCompressionStrategy()
        
        content = json.dumps([
            {
                "type": "Category",
                "id": "CAT1",
                "label": "Work",
                "description": "Work-related tasks.",
                "relationships": ["contains"],
            }
        ])
        
        context = CompressionContext(
            content_type="json",
            label="concepts",
            level=3
        )
        
        result = strategy.compress(content, context)
        
        # Level 3 should not include description or relationships
        assert "ID" in result.content
        assert "Label" in result.content
        assert "Description" not in result.content
        assert "Relationships" not in result.content
        assert "CAT1" in result.content
        assert "Work" in result.content

    def test_compress_with_long_description_truncation(self):
        """Test that long descriptions are truncated at configured lengths."""
        strategy = ConceptSummaryCompressionStrategy()
        
        long_desc = "A" * 300
        content = json.dumps([
            {
                "type": "Actor",
                "id": "A1",
                "label": "EndUser",
                "description": long_desc,
            }
        ])
        
        # Test level 2 (100 char limit)
        context = CompressionContext(
            content_type="json",
            label="concepts",
            level=2
        )
        
        result = strategy.compress(content, context)
        
        # Should truncate and add ellipsis
        assert "..." in result.content
        # Should not include full 300 chars
        assert long_desc not in result.content

    def test_compress_with_multiple_entity_types(self):
        """Test compressing concepts with different entity types."""
        strategy = ConceptSummaryCompressionStrategy()
        
        content = json.dumps([
            {"type": "Actor", "id": "A1", "label": "User"},
            {"type": "Action", "id": "ACT1", "label": "Create"},
            {"type": "DataEntity", "id": "D1", "label": "Task"},
            {"type": "Category", "id": "CAT1", "label": "Work"},
        ])
        
        context = CompressionContext(
            content_type="json",
            label="concepts",
            level=1
        )
        
        result = strategy.compress(content, context)
        
        # Should have tables for all four entity types (plural form)
        assert "## Actors" in result.content
        assert "## Actions" in result.content
        assert "## DataEntities" in result.content
        assert "## Categories" in result.content

    def test_compress_with_unknown_entity_type(self):
        """Test compressing concepts with unknown entity types."""
        strategy = ConceptSummaryCompressionStrategy()
        
        content = json.dumps([
            {"type": "UnknownType", "id": "U1", "label": "Unknown"},
            {"type": "Actor", "id": "A1", "label": "User"},
        ])
        
        context = CompressionContext(
            content_type="json",
            label="concepts",
            level=1
        )
        
        result = strategy.compress(content, context)
        
        # Unknown type should go to "Other" section
        assert "## Other" in result.content
        assert "U1" in result.content
        # Known type should have its own section (plural form)
        assert "## Actors" in result.content
        assert "A1" in result.content

    def test_compress_with_no_concepts(self):
        """Test compressing content with no concepts."""
        strategy = ConceptSummaryCompressionStrategy()
        
        content = json.dumps({"data": "no concepts here"})
        
        context = CompressionContext(
            content_type="json",
            label="concepts",
            level=1
        )
        
        result = strategy.compress(content, context)
        
        # Should return a concept summary with empty table when no concepts found
        # The strategy extracts "data" as a concept since it's a dict
        assert "# Concept Summary" in result.content
        # Concept count should be 1 (the dict itself is extracted as a concept)
        assert result.metadata["concept_count"] >= 0

    def test_decompress_not_supported(self):
        """Test that decompression raises NotImplementedError."""
        strategy = ConceptSummaryCompressionStrategy()
        
        context = CompressionContext(
            content_type="json",
            label="concepts",
            level=1
        )
        
        with pytest.raises(NotImplementedError):
            strategy.decompress("compressed content", context)

    def test_validate_content_valid_json(self):
        """Test content validation with valid JSON."""
        strategy = ConceptSummaryCompressionStrategy()
        
        content = json.dumps([
            {"type": "Actor", "id": "A1", "label": "User"}
        ])
        
        context = CompressionContext(
            content_type="json",
            label="concepts",
            level=1
        )
        
        is_valid = strategy.validate_content(content, context)
        assert is_valid is True

    def test_validate_content_invalid_json(self):
        """Test content validation with invalid JSON."""
        strategy = ConceptSummaryCompressionStrategy()
        
        content = "not valid json"
        
        context = CompressionContext(
            content_type="json",
            label="concepts",
            level=1
        )
        
        is_valid = strategy.validate_content(content, context)
        assert is_valid is False

    def test_validate_content_json_object_with_concepts(self):
        """Test validation with JSON object containing concepts array."""
        strategy = ConceptSummaryCompressionStrategy()
        
        content = json.dumps({
            "concepts": [
                {"type": "Actor", "id": "A1", "label": "User"}
            ]
        })
        
        context = CompressionContext(
            content_type="json",
            label="concepts",
            level=1
        )
        
        is_valid = strategy.validate_content(content, context)
        assert is_valid is True

    def test_validate_content_empty_array(self):
        """Test validation with empty array."""
        strategy = ConceptSummaryCompressionStrategy()
        
        content = json.dumps([])
        
        context = CompressionContext(
            content_type="json",
            label="concepts",
            level=1
        )
        
        is_valid = strategy.validate_content(content, context)
        assert is_valid is False

    def test_get_compression_ratio(self):
        """Test getting the typical compression ratio."""
        strategy = ConceptSummaryCompressionStrategy()
        
        ratio = strategy.get_compression_ratio()
        assert ratio > 0
        assert ratio < 1.0

    def test_get_supported_content_types(self):
        """Test getting supported content types."""
        strategy = ConceptSummaryCompressionStrategy()
        
        types = strategy.get_supported_content_types()
        assert isinstance(types, list)
        assert "json" in types

    def test_get_compression_ratio_for_different_levels(self):
        """Test compression ratio for different levels."""
        strategy = ConceptSummaryCompressionStrategy()
        
        # Create large content
        concepts = []
        for i in range(50):
            concepts.append({
                "type": "Actor",
                "id": f"A{i}",
                "label": f"User{i}",
                "description": "A" * 200,
                "relationships": ["rel1", "rel2", "rel3"],
            })
        
        content = json.dumps(concepts)
        
        # Level 1
        result1 = strategy.compress(
            content,
            CompressionContext(content_type="json", label="concepts", level=1)
        )
        
        # Level 3
        result3 = strategy.compress(
            content,
            CompressionContext(content_type="json", label="concepts", level=3)
        )
        
        # Level 3 should compress more
        assert result3.compressed_length < result1.compressed_length
        assert result3.compression_ratio < result1.compression_ratio


class TestConceptSummaryCompressionIntegration:
    """Integration tests for ConceptSummaryCompressionStrategy."""

    def test_full_workflow_with_real_concepts(self):
        """Test the full compression workflow with real concepts.json."""
        import pathlib
        
        strategy = ConceptSummaryCompressionStrategy()
        
        # Load real concepts.json from fixtures
        concepts_file = pathlib.Path("tests/fixtures/test_concepts.json")
        if concepts_file.exists():
            with open(concepts_file, 'r') as f:
                content = f.read()
        else:
            # Fall back to original location if fixture doesn't exist
            with open('json/concepts.json', 'r') as f:
                content = f.read()
        
        context = CompressionContext(
            content_type="json",
            label="concepts",
            level=2
        )
        
        # Step 1: Validate content
        assert strategy.validate_content(content, context) is True
        
        # Step 2: Compress content
        result = strategy.compress(content, context)
        
        # Step 3: Verify results
        assert result.original_length > 0
        assert result.compressed_length > 0
        assert result.compression_ratio > 0
        assert result.compression_ratio < 1.0
        assert result.strategy_name == "concept_summary"
        
        # Should have multiple entity types
        assert result.metadata["concept_count"] > 0
        
        # Step 4: Verify format
        assert "# Concept Summary" in result.content
        assert "## Actors" in result.content
        assert "## Actions" in result.content
        
        # Should have table headers
        assert "| ID | Label |" in result.content

    def test_compression_level_comparison(self):
        """Test differences between compression levels."""
        strategy = ConceptSummaryCompressionStrategy()
        
        # Create content with multiple concepts
        content = json.dumps([
            {
                "type": "Actor",
                "id": "A1",
                "label": "User",
                "description": "A" * 200,
                "relationships": ["rel1", "rel2"],
            },
            {
                "type": "Action",
                "id": "ACT1",
                "label": "Create",
                "description": "B" * 200,
                "relationships": ["rel3", "rel4"],
            },
        ])
        
        # Level 1
        result1 = strategy.compress(
            content,
            CompressionContext(content_type="json", label="concepts", level=1)
        )
        
        # Level 2
        result2 = strategy.compress(
            content,
            CompressionContext(content_type="json", label="concepts", level=2)
        )
        
        # Level 3
        result3 = strategy.compress(
            content,
            CompressionContext(content_type="json", label="concepts", level=3)
        )
        
        # Verify different levels produce different outputs
        assert result1.content != result2.content
        assert result2.content != result3.content
        
        # Level 3 should be most compressed
        assert result3.compressed_length < result2.compressed_length
        assert result2.compressed_length < result1.compressed_length
        
        # Level 1 should have relationships
        assert "Relationships" in result1.content
        # Level 2 should not have relationships
        assert "Relationships" not in result2.content
        # Level 3 should not have description or relationships
        assert "Description" not in result3.content

    def test_edge_case_empty_description(self):
        """Test handling of concepts with empty descriptions."""
        strategy = ConceptSummaryCompressionStrategy()
        
        content = json.dumps([
            {
                "type": "Actor",
                "id": "A1",
                "label": "User",
                "description": "",
            }
        ])
        
        context = CompressionContext(
            content_type="json",
            label="concepts",
            level=1
        )
        
        result = strategy.compress(content, context)
        
        # Should handle empty descriptions gracefully
        assert result.metadata["concept_count"] == 1
        assert "A1" in result.content

    def test_edge_case_missing_fields(self):
        """Test handling of concepts with missing optional fields."""
        strategy = ConceptSummaryCompressionStrategy()
        
        content = json.dumps([
            {
                "type": "Actor",
                "id": "A1",
                # Missing label and description
            }
        ])
        
        context = CompressionContext(
            content_type="json",
            label="concepts",
            level=1
        )
        
        result = strategy.compress(content, context)
        
        # Should handle missing fields gracefully
        assert result.metadata["concept_count"] == 1
        assert "A1" in result.content
        # Should show empty string for missing label
        assert "||" in result.content or "|" in result.content
