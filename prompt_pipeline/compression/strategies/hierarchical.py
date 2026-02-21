"""
Hierarchical compression strategy.

This strategy provides layered context compression with summaries at different levels:
- Layer 1: Executive summary (always included)
- Layer 2: Concept inventory (IDs only)
- Layer 3: Detailed definitions (reference only)
- Layer 4: Source evidence (reference only)

Useful for multi-step pipelines where context needs to be progressively detailed.
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


class HierarchicalCompressionStrategy(CompressionStrategy):
    """
    Hierarchical context compression strategy.
    
    Provides layered compression with increasing detail:
    - Layer 1: Executive summary (always included)
    - Layer 2: Concept inventory (IDs only)
    - Layer 3: Detailed definitions (reference only)
    - Layer 4: Source evidence (reference only)
    
    Use for multi-step pipelines where context needs to be progressively detailed.
    
    Compression ratio: ~0.3-0.5 (50-70% reduction)
    """
    
    LEVEL_LAYERS = {
        1: ["layer1"],  # Light: only executive summary
        2: ["layer1", "layer2"],  # Medium: summary + inventory
        3: ["layer1", "layer2", "layer3"],  # Aggressive: all layers
    }
    
    @property
    def name(self) -> str:
        """Return the name of the compression strategy."""
        return "hierarchical"
    
    @property
    def description(self) -> str:
        """Return a human-readable description of the strategy."""
        return (
            "Layered compression with executive summary, concept inventory, "
            "detailed definitions, and source references. "
            "Use for multi-step pipelines. "
            "Compression ratio: ~0.3-0.5 (50-70% reduction)."
        )
    
    def compress(self, content: str, context: CompressionContext) -> CompressionResult:
        """
        Compress the content using hierarchical layers.
        
        Args:
            content: The content to compress.
            context: Context information for the compression.
        
        Returns:
            CompressionResult with hierarchical summary.
        """
        # Determine which layers to include
        layers_to_include = self.LEVEL_LAYERS.get(context.level, self.LEVEL_LAYERS[2])
        
        # Try to parse content as JSON first (for structured data)
        parsed_json = None
        try:
            parsed_json = json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # Build hierarchical summary
        summary_parts = []
        
        if "layer1" in layers_to_include:
            summary_parts.append(self._generate_layer1_executive_summary(content, parsed_json))
        
        if "layer2" in layers_to_include:
            summary_parts.append(self._generate_layer2_inventory(content, parsed_json))
        
        if "layer3" in layers_to_include:
            summary_parts.append(self._generate_layer3_definitions(content, parsed_json))
        
        # Join all layers
        compressed = "\n\n".join(summary_parts)
        
        metadata = {
            "level": context.level,
            "content_type": context.content_type,
            "layers_included": layers_to_include,
            "total_layers": 3,
        }
        
        return create_compression_result(
            content=compressed,
            original_content=content,
            strategy_name=self.name,
            metadata=metadata,
        )
    
    def decompress(self, compressed: str, context: CompressionContext) -> str:
        """
        Decompress the hierarchical summary.
        
        Note: This is lossy compression - original content cannot be fully recovered.
        
        Args:
            compressed: The compressed hierarchical summary.
            context: Context information for the decompression.
        
        Returns:
            Approximate original content.
        
        Raises:
            NotImplementedError: This strategy does not support full decompression.
        """
        raise NotImplementedError(
            "Hierarchical compression is lossy and does not support full decompression. "
            "Original content cannot be recovered from layered summary."
        )
    
    def get_compression_ratio(self) -> float:
        """
        Get the typical compression ratio for this strategy.
        
        Returns:
            Expected compression ratio (0.4 = ~60% reduction).
        """
        return 0.4
    
    def get_supported_content_types(self) -> list[str]:
        """
        Get the list of content types supported by this strategy.
        
        Returns:
            List of supported content types.
        """
        return ["json", "yaml", "yml", "md", "text"]
    
    def _generate_layer1_executive_summary(
        self, content: str, parsed_json: Optional[dict[str, Any]]
    ) -> str:
        """
        Generate Layer 1: Executive summary.
        
        Args:
            content: Raw content string.
            parsed_json: Parsed JSON if applicable.
        
        Returns:
            Executive summary string.
        """
        lines = [
            "# Layer 1: Executive Summary",
            "",
        ]
        
        if parsed_json is not None:
            # Generate summary from JSON
            summary = self._summarize_json(parsed_json)
            lines.extend(summary)
        else:
            # For non-JSON content, create a basic summary
            lines.append(f"Document length: {len(content)} characters")
            lines.append(f"Line count: {content.count(chr(10)) + 1} lines")
            
            # Extract any headers/structure
            headers = re.findall(r'^#+\s+(.+)$', content, re.MULTILINE)
            if headers:
                lines.append(f"Sections: {len(headers)}")
                lines.append("Section titles:")
                for header in headers[:5]:  # Limit to first 5
                    lines.append(f"  - {header}")
        
        return "\n".join(lines)
    
    def _generate_layer2_inventory(
        self, content: str, parsed_json: Optional[dict[str, Any]]
    ) -> str:
        """
        Generate Layer 2: Concept/Item inventory (IDs only).
        
        Args:
            content: Raw content string.
            parsed_json: Parsed JSON if applicable.
        
        Returns:
            Inventory string.
        """
        lines = [
            "# Layer 2: Inventory",
            "",
        ]
        
        if parsed_json is not None:
            # Extract IDs from JSON
            ids = self._extract_ids_from_json(parsed_json)
            lines.append(f"Total items: {len(ids)}")
            lines.append("")
            lines.append("## Item IDs")
            for item_id in ids[:50]:  # Limit to first 50
                lines.append(f"- {item_id}")
            if len(ids) > 50:
                lines.append(f"... and {len(ids) - 50} more")
        else:
            # Extract patterns from text
            patterns = re.findall(r'\b[A-Z]{2}\d+\b', content)
            unique_patterns = list(set(patterns))[:50]
            lines.append(f"Total patterns found: {len(patterns)}")
            lines.append("")
            lines.append("## Pattern IDs")
            for pattern in unique_patterns:
                lines.append(f"- {pattern}")
        
        return "\n".join(lines)
    
    def _generate_layer3_definitions(
        self, content: str, parsed_json: Optional[dict[str, Any]]
    ) -> str:
        """
        Generate Layer 3: Detailed definitions (reference format).
        
        Args:
            content: Raw content string.
            parsed_json: Parsed JSON if applicable.
        
        Returns:
            Definitions string.
        """
        lines = [
            "# Layer 3: Definitions (Reference)",
            "",
            "For detailed definitions, refer to original document.",
            "Key references:",
        ]
        
        if parsed_json is not None:
            # Generate reference table from JSON
            refs = self._generate_references_from_json(parsed_json)
            if refs:
                lines.append("")
                lines.append("| ID | Type | Key Fields |")
                lines.append("| --- | --- | --- |")
                for ref in refs[:20]:  # Limit to first 20
                    lines.append(f"| {ref['id']} | {ref['type']} | {ref['fields']} |")
        else:
            # For text content
            lines.append("- See original document for full details")
            lines.append("- Anchor references: AN* patterns")
            lines.append("- Section references: ## headings")
        
        return "\n".join(lines)
    
    def _summarize_json(self, data: dict[str, Any]) -> list[str]:
        """
        Generate summary from JSON data.
        
        Args:
            data: Parsed JSON.
        
        Returns:
            List of summary lines.
        """
        lines = []
        
        # Count top-level items
        if isinstance(data, list):
            lines.append(f"Array with {len(data)} items")
            if data and isinstance(data[0], dict):
                # Get common keys
                keys = set()
                for item in data[:10]:
                    if isinstance(item, dict):
                        keys.update(item.keys())
                if keys:
                    lines.append(f"Common fields: {', '.join(sorted(keys)[:5])}")
        elif isinstance(data, dict):
            lines.append(f"Object with {len(data)} top-level keys")
            lines.append(f"Keys: {', '.join(sorted(data.keys())[:5])}")
            
            # Check for nested arrays
            for key, value in list(data.items())[:3]:
                if isinstance(value, list):
                    lines.append(f"  - {key}: array of {len(value)} items")
        
        return lines
    
    def _extract_ids_from_json(self, data: Any) -> list[str]:
        """
        Extract IDs from JSON structure.
        
        Args:
            data: Parsed JSON.
        
        Returns:
            List of IDs found.
        """
        ids = []
        
        def extract_recursive(obj: Any) -> None:
            if isinstance(obj, dict):
                # Check for ID field
                for id_field in ["id", "ID", "identifier", "name", "label"]:
                    if id_field in obj:
                        val = obj[id_field]
                        if isinstance(val, str):
                            ids.append(val)
                        break
                # Recurse into values
                for value in obj.values():
                    extract_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_recursive(item)
        
        extract_recursive(data)
        return ids
    
    def _generate_references_from_json(
        self, data: dict[str, Any]
    ) -> list[dict[str, str]]:
        """
        Generate reference table from JSON.
        
        Args:
            data: Parsed JSON.
        
        Returns:
            List of reference dictionaries.
        """
        refs = []
        
        def extract_recursive(obj: Any) -> None:
            if isinstance(obj, dict):
                # Get ID and type
                item_id = obj.get("id") or obj.get("ID") or obj.get("name") or "unknown"
                item_type = obj.get("type", "item")
                
                # Get key fields for summary
                key_fields = []
                for field in ["label", "description", "name"]:
                    if field in obj and isinstance(obj[field], str):
                        val = obj[field]
                        if len(val) > 30:
                            val = val[:30] + "..."
                        key_fields.append(f"{field}: {val}")
                
                refs.append({
                    "id": str(item_id),
                    "type": str(item_type),
                    "fields": "; ".join(key_fields[:2]),
                })
                
                # Recurse
                for value in obj.values():
                    extract_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_recursive(item)
        
        extract_recursive(data)
        return refs
    
    def validate_content(self, content: str, context: CompressionContext) -> bool:
        """
        Validate that the content can be compressed hierarchically.
        
        Args:
            content: The content to validate.
            context: Context information.
        
        Returns:
            True if content has structure to extract.
        """
        # Check if content has any structure
        has_json = False
        try:
            json.loads(content)
            has_json = True
        except json.JSONDecodeError:
            pass
        
        # Content is valid if it's JSON or has patterns/structure
        return has_json or bool(re.search(r'\b[A-Z]{2}\d+\b', content)) or bool(re.search(r'^#+\s+', content, re.MULTILINE))
