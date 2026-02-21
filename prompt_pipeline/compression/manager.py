"""
Compression Manager for the prompt pipeline.

This module provides a high-level interface for managing compression operations
across the pipeline, including strategy selection, composition, and metrics tracking.
"""

from typing import Optional, Dict, Any, List, Union, Tuple
from dataclasses import dataclass, field

from prompt_pipeline.compression.strategies.base import (
    CompressionStrategy,
    CompressionContext,
    CompressionResult,
)
from prompt_pipeline.compression.strategies import (
    FullCompressionStrategy,
    AnchorIndexCompressionStrategy,
    ConceptSummaryCompressionStrategy,
    HierarchicalCompressionStrategy,
    SchemaOnlyCompressionStrategy,
    DifferentialCompressionStrategy,
)


@dataclass
class CompressionConfig:
    """Configuration for compression operations."""
    
    strategy: str = "full"
    """Name of the compression strategy to use."""
    
    level: int = 1
    """Compression level (1=light, 2=medium, 3=aggressive)."""
    
    preserve_full: bool = False
    """Whether to preserve full content alongside compressed version."""
    
    metadata: Optional[Dict[str, Any]] = None
    """Additional strategy-specific configuration."""
    
    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.level < 1 or self.level > 3:
            raise ValueError(f"Compression level must be between 1 and 3, got {self.level}")
        if self.level == 1:
            # Light compression - typically use less aggressive strategies
            pass
        elif self.level == 2:
            # Medium compression - balanced approach
            pass
        elif self.level == 3:
            # Aggressive compression - maximize reduction
            pass


@dataclass
class CompressionMetrics:
    """Metrics tracking for compression operations."""
    
    original_length: int = 0
    compressed_length: int = 0
    compression_ratio: float = 1.0
    strategy_used: str = "full"
    level: int = 1
    metadata: Optional[Dict[str, Any]] = None
    
    @property
    def reduction_percent(self) -> float:
        """Get reduction percentage (0-100)."""
        if self.original_length == 0:
            return 0.0
        return (1 - self.compression_ratio) * 100
    
    def __str__(self) -> str:
        """String representation of metrics."""
        return (
            f"CompressionMetrics("
            f"original={self.original_length}, "
            f"compressed={self.compressed_length}, "
            f"ratio={self.compression_ratio:.3f}, "
            f"reduction={self.reduction_percent:.1f}%, "
            f"strategy={self.strategy_used}, "
            f"level={self.level}"
            f")"
        )


class CompressionManager:
    """
    Manager class for compression operations in the prompt pipeline.
    
    Handles:
    - Strategy selection based on configuration
    - Applying compression to content
    - Calculating compression metrics
    - Strategy composition
    - Compression level management
    """
    
    # Registry of available compression strategies
    _strategy_registry: Dict[str, CompressionStrategy] = field(default_factory=dict)
    
    def __init__(self) -> None:
        """Initialize the compression manager with default strategies."""
        self._strategy_registry = {}
        self._register_default_strategies()
    
    def _register_default_strategies(self) -> None:
        """Register the default compression strategies."""
        strategies = [
            FullCompressionStrategy(),
            AnchorIndexCompressionStrategy(),
            ConceptSummaryCompressionStrategy(),
            HierarchicalCompressionStrategy(),
            SchemaOnlyCompressionStrategy(),
            DifferentialCompressionStrategy(),
        ]
        
        for strategy in strategies:
            self.register_strategy(strategy)
    
    def register_strategy(self, strategy: CompressionStrategy) -> None:
        """
        Register a compression strategy.
        
        Args:
            strategy: The compression strategy to register.
        
        Raises:
            ValueError: If a strategy with the same name is already registered.
        """
        if strategy.name in self._strategy_registry:
            raise ValueError(
                f"Compression strategy '{strategy.name}' is already registered. "
                f"Available strategies: {list(self._strategy_registry.keys())}"
            )
        
        self._strategy_registry[strategy.name] = strategy
    
    def get_strategy(self, name: str) -> CompressionStrategy:
        """
        Get a compression strategy by name.
        
        Args:
            name: The name of the strategy.
        
        Returns:
            The compression strategy.
        
        Raises:
            ValueError: If the strategy is not found.
        """
        if name not in self._strategy_registry:
            available = list(self._strategy_registry.keys())
            raise ValueError(
                f"Compression strategy '{name}' not found. "
                f"Available strategies: {available}"
            )
        
        return self._strategy_registry[name]
    
    def list_strategies(self) -> List[str]:
        """
        List all available compression strategies.
        
        Returns:
            List of strategy names.
        """
        return list(self._strategy_registry.keys())
    
    def get_strategy_info(self, name: str) -> Dict[str, Any]:
        """
        Get information about a compression strategy.
        
        Args:
            name: The name of the strategy.
        
        Returns:
            Dictionary with strategy information.
        
        Raises:
            ValueError: If the strategy is not found.
        """
        strategy = self.get_strategy(name)
        
        return {
            "name": strategy.name,
            "description": strategy.description,
            "typical_ratio": strategy.get_compression_ratio(),
            "supported_types": strategy.get_supported_content_types(),
        }
    
    def compress(
        self,
        content: str,
        config: CompressionConfig,
        context: Optional[Dict[str, Any]] = None,
    ) -> CompressionResult:
        """
        Compress content using the specified configuration.
        
        Args:
            content: The content to compress.
            config: Compression configuration.
            context: Additional context information (label, content_type, etc.).
        
        Returns:
            CompressionResult containing compressed content and metrics.
        
        Raises:
            ValueError: If the strategy is not found.
            ValueError: If content type is not supported by the strategy.
        """
        # Get the strategy
        strategy = self.get_strategy(config.strategy)
        
        # Build compression context
        compression_context = self._build_context(config, context)
        
        # Validate content type
        self._validate_content_type(strategy, compression_context)
        
        # Apply compression
        result = strategy.compress(content, compression_context)
        
        return result
    
    def compress_with_metrics(
        self,
        content: str,
        config: CompressionConfig,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[CompressionResult, CompressionMetrics]:
        """
        Compress content and return both result and metrics.
        
        Args:
            content: The content to compress.
            config: Compression configuration.
            context: Additional context information.
        
        Returns:
            Tuple of (CompressionResult, CompressionMetrics).
        """
        result = self.compress(content, config, context)
        
        metrics = CompressionMetrics(
            original_length=result.original_length,
            compressed_length=result.compressed_length,
            compression_ratio=result.compression_ratio,
            strategy_used=result.strategy_name,
            level=config.level,
            metadata=result.metadata,
        )
        
        return result, metrics
    
    def compress_batch(
        self,
        contents: Dict[str, str],
        configs: Dict[str, CompressionConfig],
        context_map: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, CompressionResult]:
        """
        Compress multiple contents with different configurations.
        
        Args:
            contents: Dictionary mapping labels to content.
            configs: Dictionary mapping labels to compression configurations.
            context_map: Optional dictionary mapping labels to context information.
        
        Returns:
            Dictionary mapping labels to CompressionResults.
        
        Raises:
            ValueError: If a label has content but no config.
        """
        results = {}
        context_map = context_map or {}
        
        for label, content in contents.items():
            if label not in configs:
                raise ValueError(f"No compression config provided for label '{label}'")
            
            config = configs[label]
            context = context_map.get(label, {})
            context["label"] = label
            
            results[label] = self.compress(content, config, context)
        
        return results
    
    def get_compression_summary(
        self,
        results: Dict[str, CompressionResult],
        configs: Dict[str, CompressionConfig],
    ) -> Dict[str, Any]:
        """
        Generate a summary of compression operations.
        
        Args:
            results: Dictionary of compression results.
            configs: Dictionary of compression configurations.
        
        Returns:
            Summary dictionary with metrics and statistics.
        """
        total_original = 0
        total_compressed = 0
        strategy_counts: Dict[str, int] = {}
        
        for label, result in results.items():
            total_original += result.original_length
            total_compressed += result.compressed_length
            
            strategy = result.strategy_name
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        
        overall_ratio = (
            total_compressed / total_original if total_original > 0 else 1.0
        )
        
        return {
            "total_items": len(results),
            "total_original_length": total_original,
            "total_compressed_length": total_compressed,
            "overall_compression_ratio": overall_ratio,
            "overall_reduction_percent": (1 - overall_ratio) * 100,
            "strategy_counts": strategy_counts,
            "per_item_metrics": {
                label: {
                    "original_length": result.original_length,
                    "compressed_length": result.compressed_length,
                    "compression_ratio": result.compression_ratio,
                    "reduction_percent": (1 - result.compression_ratio) * 100,
                    "strategy": result.strategy_name,
                    "config_level": configs.get(label, CompressionConfig()).level,
                }
                for label, result in results.items()
            },
        }
    
    def decompress(
        self,
        compressed: str,
        strategy_name: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Decompress content using the specified strategy.
        
        Args:
            compressed: The compressed content.
            strategy_name: Name of the strategy used for compression.
            context: Additional context information.
        
        Returns:
            Decompressed content.
        
        Raises:
            ValueError: If the strategy is not found.
            NotImplementedError: If the strategy doesn't support decompression.
        """
        strategy = self.get_strategy(strategy_name)
        
        # Build compression context (level defaults to 1 for decompression)
        compression_context = CompressionContext(
            content_type=context.get("content_type", "text") if context else "text",
            label=context.get("label") if context else None,
            level=1,
            preserve_full=False,
            extra=context.get("extra") if context else None,
        )
        
        return strategy.decompress(compressed, compression_context)
    
    def _build_context(
        self,
        config: CompressionConfig,
        context: Optional[Dict[str, Any]],
    ) -> CompressionContext:
        """Build CompressionContext from config and additional context."""
        content_type = context.get("content_type", "text") if context else "text"
        label = context.get("label") if context else None
        extra = context.get("extra") if context else None
        
        return CompressionContext(
            content_type=content_type,
            label=label,
            level=config.level,
            preserve_full=config.preserve_full,
            extra={**config.metadata, **(extra or {})} if config.metadata else extra,
        )
    
    def _validate_content_type(
        self,
        strategy: CompressionStrategy,
        context: CompressionContext,
    ) -> None:
        """Validate that the content type is supported by the strategy."""
        supported_types = strategy.get_supported_content_types()
        
        # Empty list means support all types
        if not supported_types:
            return
        
        if context.content_type not in supported_types:
            raise ValueError(
                f"Content type '{context.content_type}' is not supported by "
                f"strategy '{strategy.name}'. Supported types: {supported_types}"
            )
    
    def validate_config(self, config: CompressionConfig) -> bool:
        """
        Validate a compression configuration.
        
        Args:
            config: The compression configuration to validate.
        
        Returns:
            True if valid.
        
        Raises:
            ValueError: If the configuration is invalid.
        """
        # Check level
        if config.level < 1 or config.level > 3:
            raise ValueError(
                f"Compression level must be between 1 and 3, got {config.level}"
            )
        
        # Check strategy exists
        if config.strategy not in self._strategy_registry:
            available = list(self._strategy_registry.keys())
            raise ValueError(
                f"Compression strategy '{config.strategy}' not found. "
                f"Available strategies: {available}"
            )
        
        return True
    
    def get_recommended_strategy(
        self,
        content_type: str,
        original_length: int,
        target_compression: Optional[float] = None,
    ) -> str:
        """
        Get a recommended compression strategy based on content type and size.
        
        Args:
            content_type: Type of content (e.g., 'yaml', 'json', 'md').
            original_length: Original content length in characters.
            target_compression: Target compression ratio (0.0-1.0). Optional.
        
        Returns:
            Name of recommended strategy.
        """
        # Very small content - no compression needed
        if original_length < 1000:
            return "full"
        
        # Large content with specific target
        if target_compression is not None:
            if target_compression <= 0.2:
                # Aggressive compression needed
                if content_type == "yaml":
                    return "anchor_index"
                elif content_type == "json":
                    return "concept_summary"
                else:
                    return "hierarchical"
            elif target_compression <= 0.5:
                # Medium compression
                if content_type == "yaml":
                    return "anchor_index"
                elif content_type == "json":
                    return "concept_summary"
                else:
                    return "hierarchical"
            else:
                # Light compression
                return "full"
        
        # Default recommendations based on content type
        if content_type == "yaml":
            return "anchor_index"
        elif content_type == "json":
            return "concept_summary"
        elif content_type == "md":
            return "hierarchical"
        else:
            return "full"
    
    def compose_strategies(
        self,
        first_strategy: str,
        second_strategy: str,
        content: str,
        context: Dict[str, Any],
    ) -> CompressionResult:
        """
        Compose two compression strategies (sequential application).
        
        Note: This is a placeholder for advanced composition.
        Most strategies are designed to be used independently.
        
        Args:
            first_strategy: Name of first strategy to apply.
            second_strategy: Name of second strategy to apply.
            content: Content to compress.
            context: Context information.
        
        Returns:
            CompressionResult from the second strategy.
        
        Raises:
            NotImplementedError: This feature is not yet fully implemented.
        """
        # Get strategies
        strategy1 = self.get_strategy(first_strategy)
        strategy2 = self.get_strategy(second_strategy)
        
        # Build contexts
        config1 = CompressionConfig(strategy=first_strategy, level=context.get("level", 1))
        config2 = CompressionConfig(strategy=second_strategy, level=context.get("level", 1))
        
        # Apply first strategy
        result1 = self.compress(content, config1, context)
        
        # Apply second strategy to the result of the first
        result2 = self.compress(result1.content, config2, context)
        
        return result2
