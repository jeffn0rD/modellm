"""
Anchor index compression strategy.

This strategy extracts anchor definitions from YAML specs and generates
a compact index format for reduced context size while preserving
enough information for the LLM to understand relationships.
"""

import re
from typing import Any, Optional

from prompt_pipeline.compression.strategies.base import (
    CompressionContext,
    CompressionResult,
    CompressionStrategy,
    create_compression_result,
)


class AnchorIndexCompressionStrategy(CompressionStrategy):
    """
    Anchor index compression strategy.
    
    Extracts anchor definitions (AN* patterns) from YAML specs and generates
    a compact index format. This is useful for:
    - Reducing YAML spec size while preserving anchor references
    - Providing a quick overview of all definitions
    - Enabling LLM to look up details by anchor ID
    
    Compression ratio: ~0.2-0.4 (60-80% reduction)
    """
    
    ANCHOR_PATTERN = re.compile(r'^([A-Z]{2}\d+):\s*(.+)$', re.MULTILINE)
    LEVEL_ADJUSTMENT = {
        1: 0.7,  # Light: include more context
        2: 0.4,  # Medium: balance
        3: 0.2,  # Aggressive: minimal context
    }
    
    @property
    def name(self) -> str:
        """Return the name of the compression strategy."""
        return "anchor_index"
    
    @property
    def description(self) -> str:
        """Return a human-readable description of the strategy."""
        return (
            "Extracts anchor definitions (AN* patterns) from YAML specs. "
            "Generates compact index format. Use for YAML specifications. "
            "Compression ratio: ~0.2-0.4 (60-80% reduction)."
        )
    
    def compress(self, content: str, context: CompressionContext) -> CompressionResult:
        """
        Compress the content by extracting anchor definitions.
        
        Args:
            content: The YAML content to compress.
            context: Context information for the compression.
        
        Returns:
            CompressionResult with the anchor index.
        """
        anchors = self._extract_anchors(content, context.level)
        
        if not anchors:
            # No anchors found, return full content
            return create_compression_result(
                content=content,
                original_content=content,
                strategy_name=self.name,
                metadata={
                    "level": context.level,
                    "content_type": context.content_type,
                    "note": "No anchors found - returning full content",
                    "anchor_count": 0,
                },
            )
        
        compressed = self._format_anchor_index(anchors, context.level)
        
        metadata = {
            "level": context.level,
            "content_type": context.content_type,
            "anchor_count": len(anchors),
            "anchor_ids": list(anchors.keys()),
        }
        
        return create_compression_result(
            content=compressed,
            original_content=content,
            strategy_name=self.name,
            metadata=metadata,
        )
    
    def decompress(self, compressed: str, context: CompressionContext) -> str:
        """
        Decompress the anchor index back to full YAML.
        
        Note: This is a best-effort decompression. The original formatting
        and non-anchor content cannot be fully recovered.
        
        Args:
            compressed: The compressed anchor index.
            context: Context information for the decompression.
        
        Returns:
            Approximate original YAML content.
        
        Raises:
            NotImplementedError: This strategy does not support decompression.
        """
        raise NotImplementedError(
            "Anchor index compression is lossy and does not support full decompression. "
            "Original content cannot be recovered from anchor index."
        )
    
    def get_compression_ratio(self) -> float:
        """
        Get the typical compression ratio for this strategy.
        
        Returns:
            Expected compression ratio (0.3 = ~70% reduction).
        """
        return 0.3
    
    def get_supported_content_types(self) -> list[str]:
        """
        Get the list of content types supported by this strategy.
        
        Returns:
            List of supported content types.
        """
        return ["yaml", "yml", "json", "md", "text"]
    
    def _extract_anchors(
        self, content: str, level: int
    ) -> dict[str, dict[str, Any]]:
        """
        Extract anchor definitions from content.
        
        Args:
            content: The content to extract from.
            level: Compression level (1-3).
        
        Returns:
            Dictionary of anchor_id -> anchor_info.
        """
        anchors: dict[str, dict[str, Any]] = {}
        
        # Find all anchor patterns
        matches = self.ANCHOR_PATTERN.finditer(content)
        
        for match in matches:
            anchor_id = match.group(1)
            anchor_value = match.group(2).strip()
            
            # For level 1, include more context
            # For level 3, include minimal context
            if level == 1:
                # Include full value
                display_value = anchor_value
            elif level == 2:
                # Truncate long values
                display_value = anchor_value[:100] + "..." if len(anchor_value) > 100 else anchor_value
            else:  # level 3
                # Minimal: just first 50 chars
                display_value = anchor_value[:50] + "..." if len(anchor_value) > 50 else anchor_value
            
            anchors[anchor_id] = {
                "value": anchor_value,
                "display": display_value,
                "length": len(anchor_value),
            }
        
        return anchors
    
    def _format_anchor_index(
        self, anchors: dict[str, dict[str, Any]], level: int
    ) -> str:
        """
        Format anchors into a compact index.
        
        Args:
            anchors: Dictionary of anchor information.
            level: Compression level.
        
        Returns:
            Formatted anchor index string.
        """
        if not anchors:
            return "# No anchors found in document\n"
        
        lines = [
            "# Anchor Index",
            f"# Total anchors: {len(anchors)}",
            "#",
            "# Format: AN_ID: <truncated value>",
            "# Full values can be looked up by anchor ID",
            "#",
        ]
        
        # Sort anchor IDs numerically
        sorted_anchors = sorted(anchors.items(), key=lambda x: self._anchor_sort_key(x[0]))
        
        for anchor_id, info in sorted_anchors:
            lines.append(f"{anchor_id}: {info['display']}")
        
        return "\n".join(lines)
    
    def _anchor_sort_key(self, anchor_id: str) -> tuple[int, str]:
        """
        Generate sort key for anchor ID.
        
        Args:
            anchor_id: The anchor ID (e.g., "AN1", "AN23").
        
        Returns:
            Tuple suitable for sorting.
        """
        match = re.match(r'([A-Z]+)(\d+)', anchor_id)
        if match:
            return (match.group(1), int(match.group(2)))
        return (anchor_id, 0)
    
    def validate_content(self, content: str, context: CompressionContext) -> bool:
        """
        Validate that the content contains anchors for compression.
        
        Args:
            content: The content to validate.
            context: Context information.
        
        Returns:
            True if content contains anchor patterns.
        """
        # Check if content has anchor patterns
        return bool(self.ANCHOR_PATTERN.search(content))
