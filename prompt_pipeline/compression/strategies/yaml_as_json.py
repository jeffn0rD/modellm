"""YAML to JSON conversion compression strategy."""

import json
import yaml
from typing import Dict, Any
from .base import CompressionStrategy, CompressionContext, CompressionResult, create_compression_result


class YamlAsJsonStrategy(CompressionStrategy):
    """Converts YAML to JSON format (for prompt input)."""

    @property
    def name(self) -> str:
        """Return the name of the compression strategy."""
        return "yaml_as_json"

    @property
    def description(self) -> str:
        """Return a human-readable description of the strategy."""
        return "Converts YAML content to JSON format for prompt input"

    def compress(self, content: str, context: CompressionContext) -> CompressionResult:
        """
        Convert YAML content to JSON string.

        Args:
            content: YAML content as string
            context: Context information (not used)

        Returns:
            CompressionResult containing JSON string
        """
        try:
            # Parse YAML
            yaml_data = yaml.safe_load(content)

            # Convert to JSON with nice formatting
            json_str = json.dumps(yaml_data, indent=2, ensure_ascii=False)

            return create_compression_result(
                content=json_str,
                original_content=content,
                strategy_name=self.name,
            )

        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}")
        except Exception as e:
            raise ValueError(f"Error converting YAML to JSON: {e}")

    def decompress(self, compressed: str, context: CompressionContext) -> str:
        """
        Not applicable for this strategy.

        Args:
            compressed: Compressed content
            context: Context information

        Returns:
            Original content (no decompression available)
        """
        return compressed

    def get_compression_ratio(self) -> float:
        """
        Return compression ratio.

        Returns:
            1.0 since this is a conversion, not compression
        """
        return 1.0
