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
    
    # Pattern for YAML format: anchor_id: AN1 (without quotes)
    ANCHOR_PATTERN = re.compile(r'anchor_id:\s*([A-Z]{2}\d+)', re.MULTILINE)
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
        anchors = self._extract_anchors(content, context)
        
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
        self, content: str, context: CompressionContext
    ) -> dict[str, dict[str, Any]]:
        """
        Extract anchor definitions from content.
        
        Args:
            content: The content to extract from.
            context: Context information for the compression.
        
        Returns:
            Dictionary of anchor_id -> anchor_info.
        """
        anchors: dict[str, dict[str, Any]] = {}
        level = context.level
        
        # Try to parse as YAML using PyYAML
        try:
            import yaml
            
            spec = yaml.safe_load(content)
            
            # Recursively find all anchors in the spec
            def find_anchors_recursive(obj, section_context=None):
                """Recursively find all anchors in the object."""
                found_anchors = []
                
                if isinstance(obj, dict):
                    # Update section context if this is a section
                    if 'section_id' in obj:
                        section_context = {
                            'section_id': obj.get('section_id', 'Unknown'),
                            'section_title': obj.get('title', 'Unknown'),
                            'section_label': obj.get('label', None),
                        }
                    
                    # Check if this is a text_block with anchor_id
                    if 'anchor_id' in obj:
                        anchor_id = obj['anchor_id']
                        
                        # Extract text
                        text_value = obj.get('text', '')
                        if not text_value:
                            text_value = f"[Anchor {anchor_id} - no text found]"
                        
                        # Extract optional metadata
                        label_value = obj.get('label', None)
                        type_value = obj.get('type', None)
                        
                        # Get truncation length from context, or use level-based defaults
                        truncation_length = None
                        if context.extra and "truncation_length" in context.extra:
                            truncation_length = context.extra["truncation_length"]
                        
                        # For level 1, include more context
                        # For level 3, include minimal context
                        if truncation_length is not None:
                            # Use custom truncation length
                            # 0 means no truncation (full text)
                            if truncation_length == 0:
                                display_value = text_value
                            elif len(text_value) > truncation_length:
                                display_value = text_value[:truncation_length] + "..."
                            else:
                                display_value = text_value
                        elif level == 1:
                            # Include full value
                            display_value = text_value
                        elif level == 2:
                            # Truncate long values
                            display_value = text_value[:100] + "..." if len(text_value) > 100 else text_value
                        else:  # level 3
                            # Minimal: just first 50 chars
                            display_value = text_value[:50] + "..." if len(text_value) > 50 else text_value
                        
                        # Build anchor info with metadata
                        anchor_info = {
                            "value": text_value,
                            "display": display_value,
                            "length": len(text_value),
                        }
                        
                        # Add section context if available
                        if section_context:
                            anchor_info["section_id"] = section_context['section_id']
                            anchor_info["section_title"] = section_context['section_title']
                        
                        # Add optional metadata if present
                        if label_value:
                            anchor_info["label"] = label_value
                        if type_value:
                            anchor_info["type"] = type_value
                        
                        found_anchors.append((anchor_id, anchor_info))
                    
                    # Recursively search in all values
                    for value in obj.values():
                        found_anchors.extend(find_anchors_recursive(value, section_context))
                
                elif isinstance(obj, list):
                    # Recursively search in list items
                    for item in obj:
                        found_anchors.extend(find_anchors_recursive(item, section_context))
                
                return found_anchors
            
            # Find all anchors
            anchor_list = find_anchors_recursive(spec)
            
            # Convert to dictionary
            for anchor_id, anchor_info in anchor_list:
                anchors[anchor_id] = anchor_info
        
        except ImportError:
            # Fall back to regex-based extraction if PyYAML is not available
            pass
        
        # If YAML parsing failed or no anchors found, fall back to regex
        if not anchors:
            # Find all anchor patterns and their associated text
            lines = content.split('\n')
            
            i = 0
            current_section = None
            current_section_title = None
            
            while i < len(lines):
                line = lines[i]
                
                # Track section context
                if 'section_id:' in line and 'section_number:' in lines[i+1] if i+1 < len(lines) else False:
                    # Extract section title
                    for j in range(i, min(i+10, len(lines))):
                        if 'title:' in lines[j]:
                            current_section_title = lines[j].split('title:')[1].strip()
                            break
                
                # Check if this line contains anchor_id
                anchor_match = self.ANCHOR_PATTERN.search(line)
                if anchor_match:
                    anchor_id = anchor_match.group(1)
                    
                    # Look ahead for the text field and other metadata
                    text_value = ""
                    label_value = None
                    type_value = None
                    
                    j = i + 1
                    while j < len(lines):
                        text_line = lines[j].strip()
                        
                        # Check for label
                        if text_line.startswith('label:'):
                            label_value = text_line[6:].strip()
                            if label_value.startswith('"') and label_value.endswith('"'):
                                label_value = label_value[1:-1]
                            elif label_value.startswith("'") and label_value.endswith("'"):
                                label_value = label_value[1:-1]
                        
                        # Check for type
                        if text_line.startswith('type:'):
                            type_value = text_line[5:].strip()
                            if type_value.startswith('"') and type_value.endswith('"'):
                                type_value = type_value[1:-1]
                            elif type_value.startswith("'") and type_value.endswith("'"):
                                type_value = type_value[1:-1]
                        
                        # Check if this is a text field
                        if text_line.startswith('text:'):
                            # Extract text value (can be on same line or next line with >)
                            text_part = text_line[5:].strip()  # Remove 'text:'
                            
                            # Handle multiline text (indicated by > or |)
                            if text_part in ('>', '|', ''):
                                # Text continues on next lines with indentation
                                j += 1
                                # Look for lines with indentation (typically 10-14 spaces)
                                while j < len(lines):
                                    current_line = lines[j]
                                    stripped = current_line.strip()
                                    
                                    # Check if line has content (not just whitespace)
                                    if stripped:
                                        # Check for indentation (10-14 spaces is typical for YAML text blocks)
                                        has_indent = any(current_line.startswith(' ' * spaces) for spaces in range(10, 15))
                                        
                                        if has_indent:
                                            # Check if this is a new field (starts with word followed by :)
                                            # Stop if we hit another field like "concepts:", "label:", etc.
                                            if ':' in stripped and not stripped.startswith('-'):
                                                # This might be a new field
                                                field_name = stripped.split(':')[0].strip()
                                                # Stop if it's a known field that would indicate we've moved past the text
                                                if field_name in ('concepts', 'semantic_cues', 'anchor_id', 'section_id', 'text_blocks'):
                                                    break
                                            
                                            text_value += stripped + ' '
                                        else:
                                            # No more indented lines
                                            break
                                    j += 1
                            else:
                                # Text is on the same line
                                text_value = text_part
                                j += 1
                            
                            # Clean up the text value
                            text_value = text_value.strip()
                            
                            # Remove quotes if present
                            if text_value.startswith('"') and text_value.endswith('"'):
                                text_value = text_value[1:-1]
                            elif text_value.startswith("'") and text_value.endswith("'"):
                                text_value = text_value[1:-1]
                            
                            break
                        
                        # Stop if we hit another anchor or section
                        if 'anchor_id:' in text_line or 'section_id:' in text_line or text_line.startswith('-'):
                            break
                        
                        j += 1
                    
                    # If no text found, use a placeholder
                    if not text_value:
                        text_value = f"[Anchor {anchor_id} - no text found]"
                    
                    # Get truncation length from context, or use level-based defaults
                    truncation_length = None
                    if context.extra and "truncation_length" in context.extra:
                        truncation_length = context.extra["truncation_length"]
                    
                    # For level 1, include more context
                    # For level 3, include minimal context
                    if truncation_length is not None:
                        # Use custom truncation length
                        # 0 means no truncation (full text)
                        if truncation_length == 0:
                            display_value = text_value
                        elif len(text_value) > truncation_length:
                            display_value = text_value[:truncation_length] + "..."
                        else:
                            display_value = text_value
                    elif level == 1:
                        # Include full value
                        display_value = text_value
                    elif level == 2:
                        # Truncate long values
                        display_value = text_value[:100] + "..." if len(text_value) > 100 else text_value
                    else:  # level 3
                        # Minimal: just first 50 chars
                        display_value = text_value[:50] + "..." if len(text_value) > 50 else text_value
                    
                    # Build anchor info with metadata
                    anchor_info = {
                        "value": text_value,
                        "display": display_value,
                        "length": len(text_value),
                    }
                    
                    # Add optional metadata if present
                    if label_value:
                        anchor_info["label"] = label_value
                    if type_value:
                        anchor_info["type"] = type_value
                    if current_section_title:
                        anchor_info["section"] = current_section_title
                    
                    anchors[anchor_id] = anchor_info
                
                i += 1
        
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
