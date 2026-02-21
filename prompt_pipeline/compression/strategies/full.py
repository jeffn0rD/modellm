"""
Full compression strategy (no compression).

This strategy returns the content as-is without any compression.
Use this as a baseline or when no compression is needed.
"""

from prompt_pipeline.compression.strategies.base import (
    CompressionContext,
    CompressionResult,
    CompressionStrategy,
    create_compression_result,
)


class FullCompressionStrategy(CompressionStrategy):
    """
    No compression strategy.
    
    Returns content exactly as provided. This is useful as:
    - A baseline for comparing compression ratios
    - When content is already small enough
    - When full context is required (e.g., initial extraction steps)
    """
    
    @property
    def name(self) -> str:
        """Return the name of the compression strategy."""
        return "full"
    
    @property
    def description(self) -> str:
        """Return a human-readable description of the strategy."""
        return "No compression - returns content as-is. Use as baseline or when full context is required."
    
    def compress(self, content: str, context: CompressionContext) -> CompressionResult:
        """
        Compress the content (returns unchanged).
        
        Args:
            content: The content to compress (returned unchanged).
            context: Context information for the compression.
        
        Returns:
            CompressionResult with the original content.
        """
        return create_compression_result(
            content=content,
            original_content=content,
            strategy_name=self.name,
            metadata={
                "level": context.level,
                "content_type": context.content_type,
                "note": "No compression applied - content returned as-is",
            },
        )
    
    def decompress(self, compressed: str, context: CompressionContext) -> str:
        """
        Decompress the content (returns unchanged since no compression was applied).
        
        Args:
            compressed: The compressed content to decompress.
            context: Context information for the decompression.
        
        Returns:
            The original content (unchanged).
        """
        return compressed
    
    def get_compression_ratio(self) -> float:
        """
        Get the typical compression ratio for this strategy.
        
        Returns:
            1.0 (no compression).
        """
        return 1.0
    
    def get_supported_content_types(self) -> list[str]:
        """
        Get the list of content types supported by this strategy.
        
        Returns:
            Empty list - supports all content types.
        """
        return []  # Supports all types
