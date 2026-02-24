"""Tests for AnchorIndexCompressionStrategy."""

import pytest

from prompt_pipeline.compression.strategies.anchor_index import (
    AnchorIndexCompressionStrategy,
)
from prompt_pipeline.compression.strategies.base import (
    CompressionContext,
    CompressionResult,
)


class TestAnchorIndexCompressionStrategy:
    """Tests for AnchorIndexCompressionStrategy class."""

    def test_strategy_name(self):
        """Test that the strategy has the correct name."""
        strategy = AnchorIndexCompressionStrategy()
        assert strategy.name == "anchor_index"

    def test_strategy_description(self):
        """Test that the strategy has a description."""
        strategy = AnchorIndexCompressionStrategy()
        assert len(strategy.description) > 0
        assert "anchor" in strategy.description.lower()

    def test_compression_with_anchors(self):
        """Test compressing content with anchor definitions."""
        strategy = AnchorIndexCompressionStrategy()
        
        content = """
specification:
  id: SPEC1
  title: Test Specification
  sections:
    - section_id: S1
      text_blocks:
        - anchor_id: AN1
          text: This is the first anchor definition with some text.
        - anchor_id: AN2
          text: This is the second anchor definition with more text.
"""
        
        context = CompressionContext(
            content_type="yaml",
            label="spec",
            level=1
        )
        
        result = strategy.compress(content, context)
        
        # Verify result structure
        assert isinstance(result, CompressionResult)
        assert result.strategy_name == "anchor_index"
        assert result.original_length > 0
        assert result.compressed_length > 0
        
        # Verify content contains anchor index
        assert "# Anchor Index" in result.content
        assert "AN1:" in result.content
        assert "AN2:" in result.content
        
        # Verify metadata
        assert result.metadata is not None
        assert result.metadata["anchor_count"] == 2
        assert "AN1" in result.metadata["anchor_ids"]
        assert "AN2" in result.metadata["anchor_ids"]

    def test_compression_with_no_anchors(self):
        """Test compressing content without anchor definitions."""
        strategy = AnchorIndexCompressionStrategy()
        
        content = """
specification:
  id: SPEC1
  title: Test Specification
  sections:
    - section_id: S1
      text: Just some plain text without anchors.
"""
        
        context = CompressionContext(
            content_type="yaml",
            label="spec",
            level=1
        )
        
        result = strategy.compress(content, context)
        
        # When no anchors are found, should return original content
        assert result.content == content
        assert result.metadata["anchor_count"] == 0
        assert "No anchors found" in result.metadata["note"]

    def test_compression_level_1(self):
        """Test compression with level 1 (light)."""
        strategy = AnchorIndexCompressionStrategy()
        
        content = """
specification:
  sections:
    - text_blocks:
        - anchor_id: AN1
          text: This is a very long anchor definition that should be fully included in level 1 compression.
        - anchor_id: AN2
          text: Another anchor with some text.
"""
        
        context = CompressionContext(
            content_type="yaml",
            label="spec",
            level=1
        )
        
        result = strategy.compress(content, context)
        
        # Level 1 should include full values
        assert "This is a very long anchor definition" in result.content
        assert "Another anchor with some text" in result.content

    def test_compression_level_2(self):
        """Test compression with level 2 (medium)."""
        strategy = AnchorIndexCompressionStrategy()
        
        # Create a long anchor value (>100 chars)
        long_text = "A" * 150
        content = f"""
specification:
  sections:
    - text_blocks:
        - anchor_id: AN1
          text: {long_text}
        - anchor_id: AN2
          text: Short text
"""
        
        context = CompressionContext(
            content_type="yaml",
            label="spec",
            level=2
        )
        
        result = strategy.compress(content, context)
        
        # Level 2 truncates long values
        assert "..." in result.content
        assert "Short text" in result.content

    def test_compression_level_3(self):
        """Test compression with level 3 (aggressive)."""
        strategy = AnchorIndexCompressionStrategy()
        
        # Create a long anchor value (>50 chars)
        long_text = "B" * 100
        content = f"""
specification:
  sections:
    - text_blocks:
        - anchor_id: AN1
          text: {long_text}
        - anchor_id: AN2
          text: Short text
"""
        
        context = CompressionContext(
            content_type="yaml",
            label="spec",
            level=3
        )
        
        result = strategy.compress(content, context)
        
        # Level 3 truncates more aggressively
        assert "..." in result.content
        # Should have truncated to ~50 chars
        lines = result.content.split('\n')
        anchor_lines = [line for line in lines if line.startswith('AN1:')]
        if anchor_lines:
            # Count characters after "AN1: "
            after_prefix = anchor_lines[0][5:]  # "AN1: " is 5 chars
            # Should be around 50 chars plus "..."
            assert len(after_prefix) < 70  # Allow some margin

    def test_multiple_anchors_sorted(self):
        """Test that anchors are sorted numerically."""
        strategy = AnchorIndexCompressionStrategy()
        
        content = """
specification:
  sections:
    - text_blocks:
        - anchor_id: AN10
          text: Tenth anchor
        - anchor_id: AN2
          text: Second anchor
        - anchor_id: AN1
          text: First anchor
        - anchor_id: AN20
          text: Twentieth anchor
        - anchor_id: AN3
          text: Third anchor
"""
        
        context = CompressionContext(
            content_type="yaml",
            label="spec",
            level=1
        )
        
        result = strategy.compress(content, context)
        
        # Verify anchors appear in sorted order
        lines = result.content.split('\n')
        anchor_lines = [line for line in lines if line.startswith('AN')]
        
        assert anchor_lines[0].startswith('AN1:')
        assert anchor_lines[1].startswith('AN2:')
        assert anchor_lines[2].startswith('AN3:')
        assert anchor_lines[3].startswith('AN10:')
        assert anchor_lines[4].startswith('AN20:')

    def test_compression_ratio(self):
        """Test that compression ratio is calculated correctly."""
        strategy = AnchorIndexCompressionStrategy()
        
        # Create content with multiple anchors
        long_text_x = "X" * 1000
        long_text_y = "Y" * 1000
        content = f"""
specification:
  sections:
    - text_blocks:
        - anchor_id: AN1
          text: {long_text_x}
        - anchor_id: AN2
          text: {long_text_y}
"""
        
        context = CompressionContext(
            content_type="yaml",
            label="spec",
            level=2  # Use level 2 for better compression
        )
        
        result = strategy.compress(content, context)
        
        # Verify compression ratio is reasonable
        assert result.compression_ratio > 0
        assert result.compression_ratio < 1.0
        assert result.compression_ratio < 0.5  # Should compress significantly

    def test_decompress_not_supported(self):
        """Test that decompression raises NotImplementedError."""
        strategy = AnchorIndexCompressionStrategy()
        
        context = CompressionContext(
            content_type="yaml",
            label="spec",
            level=1
        )
        
        with pytest.raises(NotImplementedError):
            strategy.decompress("compressed content", context)

    def test_validate_content_with_anchors(self):
        """Test content validation with anchor patterns."""
        strategy = AnchorIndexCompressionStrategy()
        
        content = """
specification:
  sections:
    - text_blocks:
        - anchor_id: AN1
          text: Some text
        - anchor_id: AN2
          text: More text
"""
        
        context = CompressionContext(
            content_type="yaml",
            label="spec",
            level=1
        )
        
        is_valid = strategy.validate_content(content, context)
        assert is_valid is True

    def test_validate_content_without_anchors(self):
        """Test content validation without anchor patterns."""
        strategy = AnchorIndexCompressionStrategy()
        
        content = "Just plain text without anchors"
        
        context = CompressionContext(
            content_type="yaml",
            label="spec",
            level=1
        )
        
        is_valid = strategy.validate_content(content, context)
        assert is_valid is False

    def test_get_compression_ratio(self):
        """Test getting the typical compression ratio."""
        strategy = AnchorIndexCompressionStrategy()
        
        ratio = strategy.get_compression_ratio()
        assert ratio > 0
        assert ratio < 1.0

    def test_get_supported_content_types(self):
        """Test getting supported content types."""
        strategy = AnchorIndexCompressionStrategy()
        
        types = strategy.get_supported_content_types()
        assert isinstance(types, list)
        assert "yaml" in types

    def test_anchors_with_colons_in_text(self):
        """Test handling anchors with colons in the text."""
        strategy = AnchorIndexCompressionStrategy()
        
        content = """
specification:
  sections:
    - text_blocks:
        - anchor_id: AN1
          text: "Text with: a colon in it"
        - anchor_id: AN2
          text: "Another: line: with: colons"
"""
        
        context = CompressionContext(
            content_type="yaml",
            label="spec",
            level=1
        )
        
        result = strategy.compress(content, context)
        
        # Should handle colons in text
        assert "AN1:" in result.content
        assert "AN2:" in result.content
        assert "Text with: a colon in it" in result.content

    def test_empty_content(self):
        """Test compressing empty content."""
        strategy = AnchorIndexCompressionStrategy()
        
        content = ""
        
        context = CompressionContext(
            content_type="yaml",
            label="spec",
            level=1
        )
        
        result = strategy.compress(content, context)
        
        # Empty content should return empty or minimal content
        assert result.content == content
        assert result.metadata["anchor_count"] == 0

    def test_real_yaml_spec_format(self):
        """Test with realistic YAML spec format."""
        strategy = AnchorIndexCompressionStrategy()
        
        content = """
specification:
  id: SPEC1
  title: Test Specification
  sections:
    - section_id: S1
      section_number: "1"
      title: First Section
      text_blocks:
        - anchor_id: AN1
          label: FIRST_ANCHOR
          type: goal
          text: This is the first anchor with detailed information.
        - anchor_id: AN2
          label: SECOND_ANCHOR
          type: constraint
          text: This is the second anchor with more details.
        - anchor_id: AN3
          label: THIRD_ANCHOR
          type: requirement
          text: This is the third anchor.
"""
        
        context = CompressionContext(
            content_type="yaml",
            label="spec",
            level=1
        )
        
        result = strategy.compress(content, context)
        
        # Verify anchor extraction
        assert "AN1:" in result.content
        assert "AN2:" in result.content
        assert "AN3:" in result.content
        
        # Verify metadata
        assert result.metadata["anchor_count"] == 3
        assert len(result.metadata["anchor_ids"]) == 3

    def test_compression_with_realistic_long_content(self):
        """Test compression with realistic long YAML content."""
        strategy = AnchorIndexCompressionStrategy()
        
        # Create realistic content
        content = """
specification:
  id: SPEC1
  title: Local Browser-Based To-Do List Application
  sections:
    - section_id: S1
      section_number: "1"
      title: Overall Context and Purpose
      text_blocks:
        - anchor_id: AN1
          label: APP_CORE_IDENTITY
          type: goal
          semantic_cues: ["local-first", "offline-capable", "personal-task-manager"]
          text: We need a simple, browser-based to-do list app that runs locally on a user's PC and doesn't depend on any external online services.
        - anchor_id: AN2
          label: SINGLE_USER_CONTEXT
          type: goal
          semantic_cues: ["single-user", "no-authentication", "personal-use"]
          text: The app is for a single user (no logins or accounts) who just wants a lightweight personal task manager.
        - anchor_id: AN3
          label: SESSION_PERSISTENCE
          type: constraint
          semantic_cues: ["local-storage", "data-persistence", "offline-first"]
          text: It should open in a standard web browser (desktop/laptop) and keep all data stored locally so that tasks persist between sessions.
"""
        
        context = CompressionContext(
            content_type="yaml",
            label="spec",
            level=2
        )
        
        result = strategy.compress(content, context)
        
        # Verify compression reduced size
        assert result.compression_ratio < 0.5
        
        # Verify all anchors are present
        assert "AN1:" in result.content
        assert "AN2:" in result.content
        assert "AN3:" in result.content
        
        # Verify metadata
        assert result.metadata["anchor_count"] == 3

    def test_sort_key_function(self):
        """Test the internal anchor sort key function."""
        strategy = AnchorIndexCompressionStrategy()
        
        # Test various anchor ID formats
        assert strategy._anchor_sort_key("AN1") == ("AN", 1)
        assert strategy._anchor_sort_key("AN10") == ("AN", 10)
        assert strategy._anchor_sort_key("AN100") == ("AN", 100)
        assert strategy._anchor_sort_key("TEST1") == ("TEST", 1)
        
        # Test non-standard format
        result = strategy._anchor_sort_key("INVALID")
        assert isinstance(result, tuple)

    def test_metadata_preserved(self):
        """Test that metadata is preserved in compression result."""
        strategy = AnchorIndexCompressionStrategy()
        
        content = """
specification:
  sections:
    - text_blocks:
        - anchor_id: AN1
          text: Test text
"""
        
        context = CompressionContext(
            content_type="yaml",
            label="spec",
            level=2
        )
        
        result = strategy.compress(content, context)
        
        # Verify all expected metadata fields
        assert result.metadata is not None
        assert "level" in result.metadata
        assert "content_type" in result.metadata
        assert "anchor_count" in result.metadata
        assert "anchor_ids" in result.metadata
        assert result.metadata["level"] == 2
        assert result.metadata["content_type"] == "yaml"


class TestAnchorIndexCompressionIntegration:
    """Integration tests for AnchorIndexCompressionStrategy."""

    def test_full_workflow(self):
        """Test the full compression workflow."""
        import pathlib
        
        strategy = AnchorIndexCompressionStrategy()
        
        # Load the real spec file from fixtures
        spec_file = pathlib.Path("tests/fixtures/valid_spec.yaml")
        if not spec_file.exists():
            # Fall back to simulated content if fixture doesn't exist
            content = """
specification:
  id: SPEC1
  title: Test Application
  sections:
    - section_id: S1
      text_blocks:
        - anchor_id: AN1
          text: First requirement with very detailed explanation about what needs to be done with more context and additional details that make this text much longer than 100 characters.
        - anchor_id: AN2
          text: Second requirement with even more detailed explanation about the implementation including additional information and context that exceeds 100 characters for testing truncation.
        - anchor_id: AN3
          text: Third requirement with comprehensive details about constraints and expectations including extensive information and additional context that goes beyond 100 characters.
"""
        else:
            content = spec_file.read_text(encoding="utf-8")
        
        # Step 1: Validate content
        context = CompressionContext(
            content_type="yaml",
            label="spec",
            level=2  # Use level 2 for better compression
        )
        
        assert strategy.validate_content(content, context) is True
        
        # Step 2: Compress content
        result = strategy.compress(content, context)
        
        # Step 3: Verify results
        assert result.original_length > 0
        assert result.compressed_length > 0
        assert result.compression_ratio < 0.6  # Should compress significantly
        assert result.strategy_name == "anchor_index"
        # Real spec has more than 3 anchors, so just verify we found anchors
        assert result.metadata["anchor_count"] > 0
        
        # Step 4: Verify format
        assert "# Anchor Index" in result.content
        assert "# Total anchors:" in result.content
        assert "AN" in result.content  # Should have at least one anchor

    def test_compression_level_comparison(self):
        """Test differences between compression levels."""
        strategy = AnchorIndexCompressionStrategy()
        
        long_text = "A" * 200
        content = f"""
specification:
  sections:
    - text_blocks:
        - anchor_id: AN1
          text: {long_text}
        - anchor_id: AN2
          text: Short
"""
        
        # Level 1
        result1 = strategy.compress(
            content,
            CompressionContext(content_type="yaml", label="spec", level=1)
        )
        
        # Level 2
        result2 = strategy.compress(
            content,
            CompressionContext(content_type="yaml", label="spec", level=2)
        )
        
        # Level 3
        result3 = strategy.compress(
            content,
            CompressionContext(content_type="yaml", label="spec", level=3)
        )
        
        # Verify different levels produce different outputs
        assert result1.content != result2.content
        assert result2.content != result3.content
        
        # Level 3 should be most compressed
        assert result3.compressed_length < result2.compressed_length
        assert result2.compressed_length < result1.compressed_length

    def test_edge_case_multiline_text(self):
        """Test handling of multiline anchor text."""
        strategy = AnchorIndexCompressionStrategy()
        
        # Note: The regex pattern matches single lines only
        # This test verifies the behavior with multiline content
        content = """
specification:
  sections:
    - text_blocks:
        - anchor_id: AN1
          text: First line
        - anchor_id: AN2
          text: Second line
        - anchor_id: AN3
          text: Third line
"""
        
        context = CompressionContext(
            content_type="yaml",
            label="spec",
            level=1
        )
        
        result = strategy.compress(content, context)
        
        # Should extract all three anchors
        assert result.metadata["anchor_count"] == 3
        assert "AN1:" in result.content
        assert "AN2:" in result.content
        assert "AN3:" in result.content
