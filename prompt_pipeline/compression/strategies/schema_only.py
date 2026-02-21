"""
Schema-only compression strategy.

This strategy provides JSON schema + counts instead of full content.
Useful for well-defined structures where the LLM can look up details by ID.
"""

import json
import re
from typing import Any, Optional

from prompt_pipeline.compression.strategies.base import (
    CompressionContext,
    CompressionResult,
    CompressionStrategy,
    create_compression_result,
)


class SchemaOnlyCompressionStrategy(CompressionStrategy):
    """
    Schema-only compression strategy.
    
    Provides JSON schema + counts instead of full content.
    Assumes LLM can look up details by ID from the schema.
    Useful for well-defined structures with clear schemas.
    
    Compression ratio: ~0.1-0.2 (80-90% reduction)
    """
    
    @property
    def name(self) -> str:
        """Return the name of the compression strategy."""
        return "schema_only"
    
    @property
    def description(self) -> str:
        """Return a human-readable description of the strategy."""
        return (
            "Provides JSON schema + counts instead of full content. "
            "Assumes LLM can look up details by ID. "
            "Use for well-defined structures. "
            "Compression ratio: ~0.1-0.2 (80-90% reduction)."
        )
    
    def compress(self, content: str, context: CompressionContext) -> CompressionResult:
        """
        Compress the content to schema-only format.
        
        Args:
            content: The content to compress.
            context: Context information for the compression.
        
        Returns:
            CompressionResult with schema-only summary.
        """
        # Try to parse as JSON
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # Not JSON, return minimal text representation
            return self._compress_text(content, context)
        
        # Generate schema-only summary
        summary = self._generate_schema_summary(data, context.level)
        
        metadata = {
            "level": context.level,
            "content_type": context.content_type,
            "format": "schema_with_counts",
        }
        
        return create_compression_result(
            content=summary,
            original_content=content,
            strategy_name=self.name,
            metadata=metadata,
        )
    
    def decompress(self, compressed: str, context: CompressionContext) -> str:
        """
        Decompress the schema-only summary.
        
        Note: This is lossy compression - original content cannot be recovered.
        
        Args:
            compressed: The compressed schema summary.
            context: Context information for the decompression.
        
        Returns:
            Approximate original content.
        
        Raises:
            NotImplementedError: This strategy does not support decompression.
        """
        raise NotImplementedError(
            "Schema-only compression is lossy and does not support decompression. "
            "Original content cannot be recovered from schema summary."
        )
    
    def get_compression_ratio(self) -> float:
        """
        Get the typical compression ratio for this strategy.
        
        Returns:
            Expected compression ratio (0.15 = ~85% reduction).
        """
        return 0.15
    
    def get_supported_content_types(self) -> list[str]:
        """
        Get the list of content types supported by this strategy.
        
        Returns:
            List of supported content types.
        """
        return ["json", "yaml", "yml", "md", "text"]
    
    def _compress_text(self, content: str, context: CompressionContext) -> CompressionResult:
        """
        Compress text content to minimal representation.
        
        Args:
            content: Text content.
            context: Compression context.
        
        Returns:
            CompressionResult with minimal text summary.
        """
        lines = content.split("\n")
        
        # Generate minimal summary
        summary_lines = [
            "# Schema-Only Summary",
            "",
            f"Total lines: {len(lines)}",
            f"Total characters: {len(content)}",
        ]
        
        # Extract any structure
        headers = re.findall(r"^#+\s+(.+)$", content, re.MULTILINE)
        if headers:
            summary_lines.append(f"Sections: {len(headers)}")
        
        patterns = re.findall(r"\b[A-Z]{2}\d+\b", content)
        if patterns:
            unique_patterns = list(set(patterns))
            summary_lines.append(f"Pattern IDs: {len(unique_patterns)}")
            summary_lines.append(f"IDs: {', '.join(unique_patterns[:10])}")
        
        summary = "\n".join(summary_lines)
        
        return create_compression_result(
            content=summary,
            original_content=content,
            strategy_name=self.name,
            metadata={"level": context.level, "content_type": context.content_type},
        )
    
    def _generate_schema_summary(self, data: Any, level: int) -> str:
        """
        Generate schema-only summary from JSON data.
        
        Args:
            data: Parsed JSON data.
            level: Compression level.
        
        Returns:
            Schema-only summary string.
        """
        lines = [
            "# Schema-Only Summary",
            "",
        ]
        
        # Generate structure summary
        structure = self._analyze_structure(data)
        
        lines.append("## Structure")
        for key, value in structure.items():
            lines.append(f"- {key}: {value}")
        
        lines.append("")
        
        # Generate field schema
        fields = self._extract_fields(data)
        
        if fields:
            lines.append("## Fields")
            lines.append("")
            lines.append("| Field | Type | Count |")
            lines.append("| --- | --- | --- |")
            
            for field in fields:
                lines.append(f"| {field['name']} | {field['type']} | {field['count']} |")
        
        lines.append("")
        
        # Generate item counts
        counts = self._count_items(data)
        
        if counts:
            lines.append("## Item Counts")
            lines.append("")
            for item_type, count in counts.items():
                lines.append(f"- {item_type}: {count} items")
        
        return "\n".join(lines)
    
    def _analyze_structure(self, data: Any) -> dict[str, str]:
        """
        Analyze JSON structure.
        
        Args:
            data: Parsed JSON data.
        
        Returns:
            Dictionary of structure information.
        """
        structure = {}
        
        if isinstance(data, dict):
            structure["Type"] = "object"
            structure["Keys"] = str(len(data))
            structure["Top-level keys"] = ", ".join(list(data.keys())[:5])
        elif isinstance(data, list):
            structure["Type"] = "array"
            structure["Items"] = str(len(data))
            if data:
                structure["Item type"] = type(data[0]).__name__
        else:
            structure["Type"] = type(data).__name__
        
        return structure
    
    def _extract_fields(self, data: Any) -> list[dict[str, Any]]:
        """
        Extract field information from JSON.
        
        Args:
            data: Parsed JSON data.
        
        Returns:
            List of field dictionaries.
        """
        field_counts: dict[str, dict[str, Any]] = {}
        
        def extract_recursive(obj: Any) -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key not in field_counts:
                        field_counts[key] = {
                            "name": key,
                            "type": type(value).__name__,
                            "count": 0,
                        }
                    field_counts[key]["count"] += 1
                    extract_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_recursive(item)
        
        extract_recursive(data)
        
        # Sort by count and return top 20
        sorted_fields = sorted(field_counts.values(), key=lambda x: x["count"], reverse=True)
        return sorted_fields[:20]
    
    def _count_items(self, data: Any) -> dict[str, int]:
        """
        Count items in JSON by type.
        
        Args:
            data: Parsed JSON data.
        
        Returns:
            Dictionary of item counts.
        """
        counts: dict[str, int] = {}
        
        def count_recursive(obj: Any, path: str = "root") -> None:
            if isinstance(obj, dict):
                # Count by type field if present
                if "type" in obj:
                    type_name = str(obj["type"])
                    counts[type_name] = counts.get(type_name, 0) + 1
                
                # Recurse into values
                for value in obj.values():
                    count_recursive(value, path)
            elif isinstance(obj, list):
                counts[f"{path}_array"] = counts.get(f"{path}_array", 0) + len(obj)
                for item in obj:
                    count_recursive(item, path)
        
        count_recursive(data)
        return counts
    
    def validate_content(self, content: str, context: CompressionContext) -> bool:
        """
        Validate that the content can be compressed to schema-only.
        
        Args:
            content: The content to validate.
            context: Context information.
        
        Returns:
            True if content has structure for schema extraction.
        """
        try:
            json.loads(content)
            return True
        except json.JSONDecodeError:
            # Accept text with structure
            return bool(re.search(r"^#+\s+", content, re.MULTILINE)) or bool(re.search(r"\b[A-Z]{2}\d+\b", content))
