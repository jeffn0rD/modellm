"""
Base compression strategy abstract class.

This module defines the interface that all compression strategies must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class CompressionResult:
    """Result of a compression operation."""
    
    content: str
    """The compressed content."""
    
    original_length: int
    """Length of the original content in characters."""
    
    compressed_length: int
    """Length of the compressed content in characters."""
    
    compression_ratio: float
    """Ratio of compressed to original (e.g., 0.5 means 50% of original size)."""
    
    strategy_name: str
    """Name of the compression strategy used."""
    
    metadata: Optional[dict[str, Any]] = None
    """Additional metadata about the compression."""
    
    def __post_init__(self) -> None:
        """Calculate compression ratio if not provided."""
        if self.compression_ratio == 0 and self.original_length > 0:
            self.compression_ratio = self.compressed_length / self.original_length


@dataclass
class CompressionContext:
    """Context information for compression operations."""
    
    content_type: str
    """Type of content being compressed (e.g., 'yaml', 'json', 'md')."""
    
    label: Optional[str] = None
    """Label associated with the content."""
    
    level: int = 1
    """Compression level (1=light, 2=medium, 3=aggressive)."""
    
    preserve_full: bool = False
    """Whether to preserve the full content alongside compressed."""
    
    extra: Optional[dict[str, Any]] = None
    """Additional context-specific data."""


class CompressionStrategy(ABC):
    """
    Abstract base class for compression strategies.
    
    All compression strategies must implement the compress and decompress methods.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of the compression strategy."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Return a human-readable description of the strategy."""
        pass
    
    @abstractmethod
    def compress(self, content: str, context: CompressionContext) -> CompressionResult:
        """
        Compress the given content.
        
        Args:
            content: The content to compress.
            context: Context information for the compression.
        
        Returns:
            CompressionResult containing the compressed content and metadata.
        """
        pass
    
    @abstractmethod
    def decompress(self, compressed: str, context: CompressionContext) -> str:
        """
        Decompress the given compressed content.
        
        Note: Not all strategies support decompression.
        This method may raise NotImplementedError for lossy compression.
        
        Args:
            compressed: The compressed content to decompress.
            context: Context information for the decompression.
        
        Returns:
            The decompressed content.
        
        Raises:
            NotImplementedError: If decompression is not supported.
        """
        pass
    
    def get_compression_ratio(self) -> float:
        """
        Get the typical compression ratio for this strategy.
        
        Returns:
            Expected compression ratio (e.g., 0.5 means ~50% of original size).
        """
        return 1.0  # Default: no compression
    
    def validate_content(self, content: str, context: CompressionContext) -> bool:
        """
        Validate that the content can be compressed by this strategy.
        
        Args:
            content: The content to validate.
            context: Context information.
        
        Returns:
            True if the content is valid for this strategy.
        """
        # Default implementation: accept any content
        return True
    
    def get_supported_content_types(self) -> list[str]:
        """
        Get the list of content types supported by this strategy.
        
        Returns:
            List of supported content types (e.g., ['yaml', 'json', 'md']).
        """
        # Default: support all types
        return []


def create_compression_result(
    content: str,
    original_content: str,
    strategy_name: str,
    metadata: Optional[dict[str, Any]] = None,
) -> CompressionResult:
    """
    Helper function to create a CompressionResult with automatic length calculation.
    
    Args:
        content: The compressed content.
        original_content: The original uncompressed content.
        strategy_name: Name of the compression strategy.
        metadata: Optional additional metadata.
    
    Returns:
        CompressionResult with calculated lengths and ratios.
    """
    original_length = len(original_content)
    compressed_length = len(content)
    
    compression_ratio = compressed_length / original_length if original_length > 0 else 1.0
    
    return CompressionResult(
        content=content,
        original_length=original_length,
        compressed_length=compressed_length,
        compression_ratio=compression_ratio,
        strategy_name=strategy_name,
        metadata=metadata,
    )
