"""Label Registry Module for tracking output labels across pipeline steps.

This module provides a system for managing output labels that enable
cross-step dependencies and label-based input resolution.

Key Features:
- Track labels across steps
- Validate label uniqueness within a pipeline
- Resolve label references to file paths
- Support both file-based and label-based input resolution
- Integration with orchestrator for dependency management

Reference: implementation_guide.md section 4.1
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Any


@dataclass
class LabelInfo:
    """Information about a registered label."""
    
    label: str
    step_name: str
    file_path: Path
    file_type: str
    order: int = 0
    
    def __str__(self) -> str:
        return f"{self.label} (step: {self.step_name}, file: {self.file_path})"


class LabelRegistry:
    """Registry for tracking output labels across pipeline steps.
    
    The label registry:
    1. Validates that labels are unique within a pipeline
    2. Tracks which step produced each label
    3. Maps labels to file paths
    4. Resolves label references for input resolution
    5. Supports querying labels by step or file
    
    Usage:
        registry = LabelRegistry()
        registry.register_label("spec", "step1", Path("spec_1.yaml"), "yaml", order=1)
        registry.register_label("concepts", "stepC3", Path("concepts.json"), "json", order=4)
        
        # Resolve label to file path
        spec_path = registry.resolve_label("spec")
        
        # Get all labels
        all_labels = registry.get_all_labels()
        
        # Get labels for a specific step
        step_labels = registry.get_labels_for_step("stepC3")
        
        # Check if label exists
        if registry.has_label("spec"):
            print("Label 'spec' exists")
    """
    
    def __init__(self):
        """Initialize empty label registry."""
        self._labels: Dict[str, LabelInfo] = {}
        self._step_labels: Dict[str, List[str]] = {}
        self._file_to_label: Dict[Path, str] = {}
        self._validation_errors: List[str] = []
    
    def register_label(
        self,
        label: str,
        step_name: str,
        file_path: Path,
        file_type: str,
        order: int = 0,
    ) -> bool:
        """Register a label for an output.
        
        Args:
            label: Unique label identifier (e.g., "spec", "concepts")
            step_name: Name of the step producing this output
            file_path: Path to the output file
            file_type: Type of output (yaml, json, md, text, etc.)
            order: Step execution order number
            
        Returns:
            True if label was successfully registered, False if validation failed
            
        Raises:
            ValueError: If label already exists with different configuration
        """
        # Validate label format
        if not label:
            self._validation_errors.append(f"Empty label for step {step_name}")
            return False
        
        # Check for duplicate label with different file
        if label in self._labels:
            existing = self._labels[label]
            if existing.file_path != file_path:
                error = (
                    f"Label '{label}' already exists with different file path. "
                    f"Existing: {existing.file_path}, New: {file_path}"
                )
                self._validation_errors.append(error)
                return False
            # Same label, same file - allow (idempotent)
            return True
        
        # Check for duplicate file path with different label
        if file_path in self._file_to_label:
            existing_label = self._file_to_label[file_path]
            if existing_label != label:
                error = (
                    f"File path '{file_path}' already registered with label '{existing_label}'. "
                    f"Cannot register with different label '{label}'"
                )
                self._validation_errors.append(error)
                return False
        
        # Register the label
        label_info = LabelInfo(
            label=label,
            step_name=step_name,
            file_path=file_path,
            file_type=file_type,
            order=order,
        )
        self._labels[label] = label_info
        
        # Track labels per step
        if step_name not in self._step_labels:
            self._step_labels[step_name] = []
        self._step_labels[step_name].append(label)
        
        # Track file to label mapping
        self._file_to_label[file_path] = label
        
        return True
    
    def resolve_label(self, label: str) -> Optional[Path]:
        """Resolve a label to its file path.
        
        Args:
            label: Label identifier to resolve
            
        Returns:
            File path if label exists, None otherwise
        """
        if label in self._labels:
            return self._labels[label].file_path
        return None
    
    def get_label_info(self, label: str) -> Optional[LabelInfo]:
        """Get complete information about a label.
        
        Args:
            label: Label identifier
            
        Returns:
            LabelInfo object if label exists, None otherwise
        """
        return self._labels.get(label)
    
    def has_label(self, label: str) -> bool:
        """Check if a label exists in the registry.
        
        Args:
            label: Label identifier to check
            
        Returns:
            True if label exists, False otherwise
        """
        return label in self._labels
    
    def get_all_labels(self) -> List[str]:
        """Get all registered labels.
        
        Returns:
            List of all label identifiers
        """
        return list(self._labels.keys())
    
    def get_labels_for_step(self, step_name: str) -> List[str]:
        """Get all labels produced by a specific step.
        
        Args:
            step_name: Name of the step
            
        Returns:
            List of labels produced by this step
        """
        return self._step_labels.get(step_name, [])
    
    def get_label_for_file(self, file_path: Path) -> Optional[str]:
        """Get the label associated with a file path.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Label if file is registered, None otherwise
        """
        return self._file_to_label.get(file_path)
    
    def get_files_for_step(self, step_name: str) -> List[Path]:
        """Get all file paths produced by a specific step.
        
        Args:
            step_name: Name of the step
            
        Returns:
            List of file paths produced by this step
        """
        labels = self._step_labels.get(step_name, [])
        return [self._labels[label].file_path for label in labels]
    
    def get_step_for_label(self, label: str) -> Optional[str]:
        """Get the step that produced a label.
        
        Args:
            label: Label identifier
            
        Returns:
            Step name if label exists, None otherwise
        """
        if label in self._labels:
            return self._labels[label].step_name
        return None
    
    def get_step_for_file(self, file_path: Path) -> Optional[str]:
        """Get the step that produced a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Step name if file is registered, None otherwise
        """
        label = self._file_to_label.get(file_path)
        if label and label in self._labels:
            return self._labels[label].step_name
        return None
    
    def get_validation_errors(self) -> List[str]:
        """Get all validation errors.
        
        Returns:
            List of validation error messages
        """
        return self._validation_errors.copy()
    
    def has_validation_errors(self) -> bool:
        """Check if registry has validation errors.
        
        Returns:
            True if there are validation errors, False otherwise
        """
        return len(self._validation_errors) > 0
    
    def clear_validation_errors(self) -> None:
        """Clear all validation errors."""
        self._validation_errors.clear()
    
    def merge_from_config(self, config: Dict[str, Any]) -> bool:
        """Merge labels from pipeline configuration.
        
        Expected config format:
        {
            "output_labels": [
                {"step": "step1", "label": "spec"},
                {"step": "stepC3", "label": "concepts"},
            ],
            ...
        }
        
        Args:
            config: Pipeline configuration dictionary
            
        Returns:
            True if all labels were successfully merged, False if any failed
        """
        if "output_labels" not in config:
            return True
        
        success = True
        for label_spec in config["output_labels"]:
            step = label_spec.get("step")
            label = label_spec.get("label")
            
            if not step or not label:
                success = False
                self._validation_errors.append(
                    f"Invalid label spec: missing step or label in {label_spec}"
                )
                continue
            
            # Note: This method only registers the label mapping
            # The actual file path will be registered when the step executes
            # For now, we use a placeholder path that will be updated later
            placeholder_path = Path(f"output_{step}_{label}.placeholder")
            
            # Try to get file type from step config (if available)
            file_type = "text"  # Default
            
            if not self.register_label(
                label=label,
                step_name=step,
                file_path=placeholder_path,
                file_type=file_type,
            ):
                success = False
        
        return success
    
    def update_label_file(
        self,
        label: str,
        file_path: Path,
        file_type: Optional[str] = None,
    ) -> bool:
        """Update the file path for an existing label.
        
        This is useful when the actual output file path differs from the
        placeholder path registered during configuration merge.
        
        Args:
            label: Label to update
            file_path: New file path
            file_type: Optional new file type
            
        Returns:
            True if label was updated, False if label doesn't exist
        """
        if label not in self._labels:
            return False
        
        # Remove old file mapping
        old_file_path = self._labels[label].file_path
        if old_file_path in self._file_to_label:
            del self._file_to_label[old_file_path]
        
        # Update label info
        self._labels[label].file_path = file_path
        if file_type:
            self._labels[label].file_type = file_type
        
        # Add new file mapping
        self._file_to_label[file_path] = label
        
        return True
    
    def get_sorted_labels_by_step(self) -> List[tuple]:
        """Get all labels sorted by step order.
        
        Returns:
            List of (label, step_name, order, file_path) tuples sorted by order
        """
        label_items = []
        for label, info in self._labels.items():
            label_items.append((label, info.step_name, info.order, info.file_path))
        
        # Sort by order
        label_items.sort(key=lambda x: x[2])  # x[2] is order
        return label_items
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert registry to dictionary representation.
        
        Returns:
            Dictionary with registry contents
        """
        return {
            "labels": {
                label: {
                    "step_name": info.step_name,
                    "file_path": str(info.file_path),
                    "file_type": info.file_type,
                    "order": info.order,
                }
                for label, info in self._labels.items()
            },
            "step_labels": self._step_labels,
            "file_to_label": {str(path): label for path, label in self._file_to_label.items()},
            "validation_errors": self._validation_errors,
        }
    
    def __str__(self) -> str:
        """String representation of the registry."""
        if not self._labels:
            return "LabelRegistry (empty)"
        
        lines = ["LabelRegistry:"]
        for label, info in sorted(self._labels.items()):
            lines.append(f"  {label}: {info}")
        
        return "\n".join(lines)
    
    def __len__(self) -> int:
        """Get number of registered labels."""
        return len(self._labels)
