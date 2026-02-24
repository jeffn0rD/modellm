"""
Concept summary compression strategy.

This strategy parses Concepts.json and generates markdown tables
grouped by entity type (Actors, Actions, DataEntities, Categories).
Useful for reducing token count while preserving essential concept information.
"""

import json
from typing import Any, Optional

from prompt_pipeline.compression.strategies.base import (
    CompressionContext,
    CompressionResult,
    CompressionStrategy,
    create_compression_result,
)


class ConceptSummaryCompressionStrategy(CompressionStrategy):
    """
    Concept summary compression strategy.
    
    Parses Concepts.json and generates markdown tables grouped by entity type.
    This is useful for:
    - Reducing token count for concept-heavy prompts
    - Providing a quick overview of all concepts
    - Grouping concepts by type for easier reference
    
    Compression ratio: ~0.4-0.5 (50-60% reduction)
    """
    
    # Entity type groupings (both singular and plural forms)
    ENTITY_TYPES = ["Actors", "Actions", "DataEntities", "Categories"]
    ENTITY_TYPE_MAP = {
        "Actor": "Actors",
        "Action": "Actions",
        "DataEntity": "DataEntities",
        "Category": "Categories",
    }
    
    LEVEL_CONFIG = {
        1: {"include_description": True, "include_relationships": True, "max_desc_length": 200},
        2: {"include_description": True, "include_relationships": False, "max_desc_length": 100},
        3: {"include_description": False, "include_relationships": False, "max_desc_length": 0},
    }
    
    @property
    def name(self) -> str:
        """Return the name of the compression strategy."""
        return "concept_summary"
    
    @property
    def description(self) -> str:
        """Return a human-readable description of the strategy."""
        return (
            "Generates markdown tables from Concepts.json grouped by entity type. "
            "Use for concept-heavy prompts. "
            "Compression ratio: ~0.4-0.5 (50-60% reduction)."
        )
    
    def compress(self, content: str, context: CompressionContext) -> CompressionResult:
        """
        Compress the content by generating concept summary tables.
        
        Args:
            content: The JSON content to compress.
            context: Context information for the compression.
        
        Returns:
            CompressionResult with the concept summary.
        """
        # Try to parse as JSON
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # Not JSON, return as-is
            return create_compression_result(
                content=content,
                original_content=content,
                strategy_name=self.name,
                metadata={
                    "level": context.level,
                    "content_type": context.content_type,
                    "error": "Content is not valid JSON",
                },
            )
        
        # Extract concepts from various JSON structures
        concepts = self._extract_concepts(data)
        
        if not concepts:
            # No concepts found, return full content
            return create_compression_result(
                content=content,
                original_content=content,
                strategy_name=self.name,
                metadata={
                    "level": context.level,
                    "content_type": context.content_type,
                    "note": "No concepts found - returning full content",
                    "concept_count": 0,
                },
            )
        
        # Generate summary tables
        level_config = self.LEVEL_CONFIG.get(context.level, self.LEVEL_CONFIG[2])
        summary = self._generate_summary(concepts, level_config)
        
        metadata = {
            "level": context.level,
            "content_type": context.content_type,
            "concept_count": len(concepts),
            "entity_types": list(set(c.get("type") for c in concepts if c.get("type"))),
        }
        
        return create_compression_result(
            content=summary,
            original_content=content,
            strategy_name=self.name,
            metadata=metadata,
        )
    
    def decompress(self, compressed: str, context: CompressionContext) -> str:
        """
        Decompress the concept summary back to JSON.
        
        Note: This is lossy compression - original structure cannot be fully recovered.
        
        Args:
            compressed: The compressed concept summary.
            context: Context information for the decompression.
        
        Returns:
            Approximate original JSON content.
        
        Raises:
            NotImplementedError: This strategy does not support full decompression.
        """
        raise NotImplementedError(
            "Concept summary compression is lossy and does not support full decompression. "
            "Original JSON structure cannot be recovered."
        )
    
    def get_compression_ratio(self) -> float:
        """
        Get the typical compression ratio for this strategy.
        
        Returns:
            Expected compression ratio (0.45 = ~55% reduction).
        """
        return 0.45
    
    def get_supported_content_types(self) -> list[str]:
        """
        Get the list of content types supported by this strategy.
        
        Returns:
            List of supported content types.
        """
        return ["json", "md", "text"]
    
    def _extract_concepts(self, data: Any) -> list[dict[str, Any]]:
        """
        Extract concepts from various JSON structures.
        
        Args:
            data: Parsed JSON data.
        
        Returns:
            List of concept dictionaries.
        """
        concepts = []
        
        # Handle array of concepts
        if isinstance(data, list):
            concepts = [c for c in data if isinstance(c, dict)]
        
        # Handle object with concepts array
        elif isinstance(data, dict):
            # Check common keys
            for key in ["concepts", "items", "results", "data"]:
                if key in data and isinstance(data[key], list):
                    concepts = [c for c in data[key] if isinstance(c, dict)]
                    if concepts:
                        break
            
            # If still no concepts, treat the object itself as a concept
            if not concepts:
                concepts = [data]
        
        return concepts
    
    def _generate_summary(
        self, concepts: list[dict[str, Any]], config: dict[str, Any]
    ) -> str:
        """
        Generate markdown summary tables from concepts.
        
        Args:
            concepts: List of concept dictionaries.
            config: Configuration for what to include.
        
        Returns:
            Markdown-formatted concept summary.
        """
        # Group concepts by type (convert to plural form)
        by_type: dict[str, list[dict[str, Any]]] = {}
        
        for concept in concepts:
            singular_type = concept.get("type", "Unknown")
            # Convert to plural form if mapping exists
            concept_type = self.ENTITY_TYPE_MAP.get(singular_type, singular_type)
            if concept_type not in by_type:
                by_type[concept_type] = []
            by_type[concept_type].append(concept)
        
        # Generate tables for each type
        lines = ["# Concept Summary", ""]
        
        for entity_type in self.ENTITY_TYPES:
            if entity_type not in by_type:
                continue
            
            type_concepts = by_type[entity_type]
            lines.append(f"## {entity_type}")
            lines.append("")
            
            # Build table header
            headers = ["ID", "Label"]
            if config["include_description"]:
                headers.append("Description")
            if config["include_relationships"]:
                headers.append("Relationships")
            
            lines.append("| " + " | ".join(headers) + " |")
            lines.append("|" + "|".join([" --- " for _ in headers]) + "|")
            
            # Add rows
            for concept in type_concepts:
                row = [
                    concept.get("id", ""),
                    concept.get("label", ""),
                ]
                
                if config["include_description"]:
                    desc = concept.get("description", "")
                    max_len = config["max_desc_length"]
                    if max_len and len(desc) > max_len:
                        desc = desc[:max_len] + "..."
                    row.append(desc)
                
                if config["include_relationships"]:
                    rels = concept.get("relationships", [])
                    if isinstance(rels, list):
                        rels = ", ".join(str(r) for r in rels)
                    row.append(str(rels))
                
                lines.append("| " + " | ".join(row) + " |")
            
            lines.append("")
        
        # Add any ungrouped concepts
        ungrouped = []
        for entity_type, type_concepts in by_type.items():
            if entity_type not in self.ENTITY_TYPES:
                ungrouped.extend(type_concepts)
        
        if ungrouped:
            lines.append("## Other")
            lines.append("")
            lines.append("| ID | Label | Description |")
            lines.append("| --- | --- | --- |")
            for concept in ungrouped:
                desc = concept.get("description", "")[:100]
                if len(concept.get("description", "")) > 100:
                    desc += "..."
                lines.append(f"| {concept.get('id', '')} | {concept.get('label', '')} | {desc} |")
            lines.append("")
        
        return "\n".join(lines)
    
    def validate_content(self, content: str, context: CompressionContext) -> bool:
        """
        Validate that the content can be parsed as JSON concepts.
        
        Args:
            content: The content to validate.
            context: Context information.
        
        Returns:
            True if content looks like concepts JSON.
        """
        try:
            data = json.loads(content)
            # Check if it looks like concepts
            if isinstance(data, list):
                return len(data) > 0 and isinstance(data[0], dict)
            elif isinstance(data, dict):
                return "concepts" in data or "items" in data
            return False
        except json.JSONDecodeError:
            return False
