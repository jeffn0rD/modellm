"""
Differential compression strategy.

This strategy provides only the changes (additions, modifications, deletions)
from a previous version. Useful for iterative refinement workflows where
only the delta needs to be communicated to the LLM.
"""

import json
from typing import Any, Optional

from prompt_pipeline.compression.strategies.base import (
    CompressionContext,
    CompressionResult,
    CompressionStrategy,
    create_compression_result,
)


class DifferentialCompressionStrategy(CompressionStrategy):
    """
    Differential compression strategy.
    
    Provides only changes from a previous version:
    - added: New items added
    - modified: Existing items changed
    - removed: Items that were deleted
    
    Requires base version to compute diff. Without base, shows full content.
    Useful for iterative refinement and version control scenarios.
    
    Compression ratio: ~0.05-0.1 (90-95% reduction)
    """
    
    @property
    def name(self) -> str:
        """Return the name of the compression strategy."""
        return "differential"
    
    @property
    def description(self) -> str:
        """Return a human-readable description of the strategy."""
        return (
            "Provides only changes (added, modified, removed) from previous version. "
            "Requires base version. Use for iterative refinement. "
            "Compression ratio: ~0.05-0.1 (90-95% reduction)."
        )
    
    def compress(self, content: str, context: CompressionContext) -> CompressionResult:
        """
        Compress the content using differential compression.
        
        Args:
            content: The new content to compress.
            context: Context information including extra['base_content'] for comparison.
        
        Returns:
            CompressionResult with differential summary.
        """
        # Check for base content in context extra
        base_content = None
        if context.extra and "base_content" in context.extra:
            base_content = context.extra["base_content"]
        
        if base_content is None:
            # No base content - return full content with note
            return create_compression_result(
                content=content,
                original_content=content,
                strategy_name=self.name,
                metadata={
                    "level": context.level,
                    "content_type": context.content_type,
                    "note": "No base content provided - returning full content",
                    "has_base": False,
                },
            )
        
        # Compute differential
        diff = self._compute_diff(base_content, content, context.level)
        
        metadata = {
            "level": context.level,
            "content_type": context.content_type,
            "has_base": True,
            "added_count": len(diff.get("added", [])),
            "modified_count": len(diff.get("modified", [])),
            "removed_count": len(diff.get("removed", [])),
        }
        
        return create_compression_result(
            content=diff["summary"],
            original_content=content,
            strategy_name=self.name,
            metadata=metadata,
        )
    
    def decompress(self, compressed: str, context: CompressionContext) -> str:
        """
        Decompress the differential content.
        
        Note: This requires base content to reconstruct the full content.
        
        Args:
            compressed: The compressed differential summary.
            context: Context information including extra['base_content'].
        
        Returns:
            Reconstructed content.
        
        Raises:
            NotImplementedError: If base content is not available.
        """
        base_content = None
        if context.extra and "base_content" in context.extra:
            base_content = context.extra["base_content"]
        
        if base_content is None:
            raise NotImplementedError(
                "Differential decompression requires base_content in context.extra. "
                "Please provide the base version to reconstruct the full content."
            )
        
        # Parse the diff summary and reconstruct
        return self._reconstruct(base_content, compressed)
    
    def get_compression_ratio(self) -> float:
        """
        Get the typical compression ratio for this strategy.
        
        Returns:
            Expected compression ratio (0.07 = ~93% reduction).
        """
        return 0.07
    
    def get_supported_content_types(self) -> list[str]:
        """
        Get the list of content types supported by this strategy.
        
        Returns:
            List of supported content types.
        """
        return ["json", "yaml", "yml", "md", "text"]
    
    def _compute_diff(self, base: str, current: str, level: int) -> dict[str, Any]:
        """
        Compute differential between base and current content.
        
        Args:
            base: Base/original content.
            current: New/current content.
            level: Compression level.
        
        Returns:
            Dictionary with diff summary.
        """
        # Try to parse as JSON
        base_json = None
        current_json = None
        
        try:
            base_json = json.loads(base)
        except json.JSONDecodeError:
            pass
        
        try:
            current_json = json.loads(current)
        except json.JSONDecodeError:
            pass
        
        if base_json is not None and current_json is not None:
            # JSON diff
            return self._compute_json_diff(base_json, current_json, level)
        else:
            # Text diff
            return self._compute_text_diff(base, current, level)
    
    def _compute_json_diff(
        self, base: Any, current: Any, level: int
    ) -> dict[str, Any]:
        """
        Compute JSON differential.
        
        Args:
            base: Base JSON.
            current: Current JSON.
            level: Compression level.
        
        Returns:
            Diff summary.
        """
        added: list[dict[str, Any]] = []
        modified: list[dict[str, Any]] = []
        removed: list[dict[str, Any]] = []
        
        # Convert to normalized form for comparison
        base_items = self._normalize_json(base)
        current_items = self._normalize_json(current)
        
        base_ids = {item["id"] for item in base_items if "id" in item}
        current_ids = {item["id"] for item in current_items if "id" in item}
        
        # Find added
        for item in current_items:
            if "id" in item and item["id"] not in base_ids:
                added.append(item)
        
        # Find removed
        for item in base_items:
            if "id" in item and item["id"] not in current_ids:
                removed.append(item)
        
        # Find modified
        base_by_id = {item["id"]: item for item in base_items if "id" in item}
        current_by_id = {item["id"]: item for item in current_items if "id" in item}
        
        for item_id in base_ids & current_ids:
            if base_by_id[item_id] != current_by_id[item_id]:
                modified.append({
                    "id": item_id,
                    "old": base_by_id[item_id],
                    "new": current_by_id[item_id],
                })
        
        return self._format_diff_summary(added, modified, removed, level)
    
    def _normalize_json(self, data: Any) -> list[dict[str, Any]]:
        """
        Normalize JSON to list of items.
        
        Args:
            data: Parsed JSON.
        
        Returns:
            List of items.
        """
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        elif isinstance(data, dict):
            # Check for common array keys
            for key in ["items", "concepts", "results", "data"]:
                if key in data and isinstance(data[key], list):
                    return [item for item in data[key] if isinstance(item, dict)]
            # Return as single item
            return [data] if isinstance(data, dict) else []
        return []
    
    def _compute_text_diff(self, base: str, current: str, level: int) -> dict[str, Any]:
        """
        Compute text differential.
        
        Args:
            base: Base text.
            current: Current text.
            level: Compression level.
        
        Returns:
            Diff summary.
        """
        base_lines = base.split("\n")
        current_lines = current.split("\n")
        
        base_set = set(base_lines)
        current_set = set(current_lines)
        
        added_lines = current_set - base_set
        removed_lines = base_set - current_set
        
        added = [{"line": line} for line in sorted(added_lines)]
        removed = [{"line": line} for line in sorted(removed_lines)]
        
        return self._format_diff_summary(added, [], removed, level)
    
    def _format_diff_summary(
        self,
        added: list[Any],
        modified: list[Any],
        removed: list[Any],
        level: int,
    ) -> dict[str, Any]:
        """
        Format diff into summary string.
        
        Args:
            added: Added items.
            modified: Modified items.
            removed: Removed items.
            level: Compression level.
        
        Returns:
            Dictionary with summary and diff components.
        """
        lines = [
            "# Differential Summary",
            "",
            f"Added: {len(added)} items",
            f"Modified: {len(modified)} items",
            f"Removed: {len(removed)} items",
            "",
        ]
        
        if added and level >= 1:
            lines.append("## Added")
            lines.append("")
            for item in added[:10]:  # Limit output
                lines.append(self._format_item(item, "added"))
            if len(added) > 10:
                lines.append(f"... and {len(added) - 10} more")
            lines.append("")
        
        if modified and level >= 2:
            lines.append("## Modified")
            lines.append("")
            for item in modified[:10]:
                lines.append(self._format_item(item, "modified"))
            if len(modified) > 10:
                lines.append(f"... and {len(modified) - 10} more")
            lines.append("")
        
        if removed and level >= 3:
            lines.append("## Removed")
            lines.append("")
            for item in removed[:10]:
                lines.append(self._format_item(item, "removed"))
            if len(removed) > 10:
                lines.append(f"... and {len(removed) - 10} more")
            lines.append("")
        
        return {
            "summary": "\n".join(lines),
            "added": added,
            "modified": modified,
            "removed": removed,
        }
    
    def _format_item(self, item: Any, diff_type: str) -> str:
        """
        Format a diff item for display.
        
        Args:
            item: The item to format.
            diff_type: Type of diff ('added', 'modified', 'removed').
        
        Returns:
            Formatted string.
        """
        if diff_type == "modified":
            item_id = item.get("id", "unknown")
            return f"- {item_id} (modified)"
        elif isinstance(item, dict):
            item_id = item.get("id", item.get("label", "unknown"))
            return f"- {item_id}"
        else:
            return f"- {item}"
    
    def _reconstruct(self, base: str, diff_summary: str) -> str:
        """
        Reconstruct content from base and diff.
        
        Note: This is a simplified reconstruction. Full reconstruction
        would require the complete diff data, not just the summary.
        
        Args:
            base: Base content.
            diff_summary: Differential summary.
        
        Returns:
            Best-effort reconstructed content.
        """
        # This is a placeholder - full reconstruction would require
        # storing the full diff, not just the summary
        return base
    
    def validate_content(self, content: str, context: CompressionContext) -> bool:
        """
        Validate that differential compression can be applied.
        
        Args:
            content: The content to validate.
            context: Context information.
        
        Returns:
            True if content can be compared.
        """
        # Can always attempt diff
        return True
