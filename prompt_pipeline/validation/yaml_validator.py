"""YAML Validator module for Step 1 output validation."""

import re
from typing import List, Optional

import yaml


class ValidationResult:
    """Container for validation results."""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.passed: bool = False

    def is_valid(self) -> bool:
        """Check if validation passed."""
        return len(self.errors) == 0

    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)
        self.passed = len(self.errors) == 0

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)


class YAMLValidator:
    """Validate YAML specification output from Step 1.

    Validates:
    - Valid YAML syntax
    - Required top-level fields (specification)
    - Specification fields (id, title, sections)
    - Hierarchical IDs (S*, AN*)
    - Anchor patterns (AN followed by digits)
    - Required text block fields (anchor_id, text)
    """

    # ID pattern: S followed by digits for sections
    SECTION_ID_PATTERN = re.compile(r"^S\d+$")
    # ID pattern: AN followed by digits for anchors
    ANCHOR_ID_PATTERN = re.compile(r"^AN\d+$")

    def __init__(self, strict: bool = True):
        """Initialize YAML validator.

        Args:
            strict: If True, validation fails on warnings too.
        """
        self.strict = strict

    def validate(self, yaml_content: str) -> ValidationResult:
        """Validate YAML structure and content.

        Args:
            yaml_content: The YAML content to validate.

        Returns:
            ValidationResult with errors and warnings.
        """
        result = ValidationResult()

        # Parse YAML
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            result.add_error(f"YAML parse error: {e}")
            return result

        if data is None:
            result.add_error("YAML content is empty")
            return result

        # Check required top-level fields
        if "specification" not in data:
            result.add_error("Missing required top-level field: 'specification'")
            return result

        spec = data.get("specification", {})

        # Check spec fields
        required_fields = ["id", "title", "sections"]
        for field in required_fields:
            if field not in spec:
                result.add_error(f"Missing required spec field: '{field}'")

        # Validate spec ID pattern (should be S* or AN*)
        spec_id = spec.get("id", "")
        if spec_id and not self.ANCHOR_ID_PATTERN.match(spec_id) and not self.SECTION_ID_PATTERN.match(spec_id):
            result.add_error(
                f"Invalid specification ID pattern: '{spec_id}'. "
                "Expected format: S followed by digits (e.g., S1, S2) or AN followed by digits (e.g., AN1, AN2)"
            )

        # Validate title
        title = spec.get("title", "")
        if not title or not isinstance(title, str):
            result.add_warning("Specification title is missing or empty")

        # Validate sections
        if "sections" in spec:
            self._validate_sections(spec["sections"], result)

        result.passed = result.is_valid()
        return result

    def _validate_sections(
        self, sections: List[dict], result: ValidationResult, section_ids: Optional[set] = None
    ) -> None:
        """Validate sections array.

        Args:
            sections: List of section dictionaries.
            result: ValidationResult to append errors to.
            section_ids: Set of section IDs for duplicate checking (shared across recursion).
        """
        if not isinstance(sections, list):
            result.add_error("'sections' must be an array")
            return

        if len(sections) == 0:
            result.add_warning("No sections defined in specification")

        if section_ids is None:
            section_ids = set()

        for i, section in enumerate(sections):
            if not isinstance(section, dict):
                result.add_error(f"Section {i} is not a dictionary")
                continue

            # Check required section fields (support both 'id' and 'section_id')
            if "section_id" not in section and "id" not in section:
                result.add_error(f"Section {i} missing required field: 'section_id' or 'id'")
            else:
                section_id = section.get("section_id") or section.get("id", "")
                # Validate section ID pattern
                if not self.SECTION_ID_PATTERN.match(section_id):
                    result.add_error(
                        f"Invalid section ID: '{section_id}'. "
                        f"Expected format: S followed by digits (e.g., S1)"
                    )
                # Check for duplicate IDs
                elif section_id in section_ids:
                    result.add_error(f"Duplicate section ID: '{section_id}'")
                section_ids.add(section_id)

            # Validate title
            if "title" not in section or not section.get("title"):
                result.add_warning(f"Section {i} missing 'title'")

            # Validate text_blocks
            if "text_blocks" in section:
                self._validate_text_blocks(section["text_blocks"], i, result)
            
            # Recursively validate nested sections
            if "sections" in section:
                self._validate_sections(section["sections"], result, section_ids)

    def _validate_text_blocks(
        self, text_blocks: List[dict], section_index: int, result: ValidationResult
    ) -> None:
        """Validate text blocks in a section.

        Args:
            text_blocks: List of text block dictionaries.
            section_index: Index of parent section for error messages.
            result: ValidationResult to append errors to.
        """
        if not isinstance(text_blocks, list):
            result.add_error(
                f"Section {section_index}: 'text_blocks' must be an array"
            )
            return

        anchor_ids = set()
        for j, block in enumerate(text_blocks):
            if not isinstance(block, dict):
                result.add_error(
                    f"Section {section_index}, block {j} is not a dictionary"
                )
                continue

            # Check required block fields
            if "anchor_id" not in block:
                result.add_error(
                    f"Section {section_index}, block {j} missing 'anchor_id'"
                )
            else:
                anchor_id = block.get("anchor_id", "")
                # Validate anchor ID pattern
                if anchor_id and not self.ANCHOR_ID_PATTERN.match(anchor_id):
                    result.add_error(
                        f"Invalid anchor_id: '{anchor_id}'. "
                        f"Expected format: AN followed by digits (e.g., AN1, AN2)"
                    )
                # Check for duplicate anchor IDs
                elif anchor_id and anchor_id in anchor_ids:
                    result.add_error(
                        f"Duplicate anchor_id in section {section_index}: '{anchor_id}'"
                    )
                anchor_ids.add(anchor_id)

            # Check text content
            text = block.get("text")
            if text is None:
                result.add_error(
                    f"Section {section_index}, block {j} missing 'text' field"
                )
            elif not isinstance(text, str):
                result.add_error(
                    f"Section {section_index}, block {j}: 'text' must be a string"
                )
            elif not text.strip():
                result.add_error(
                    f"Section {section_index}, block {j} has empty 'text'"
                )

    def validate_file(self, file_path: str) -> ValidationResult:
        """Validate YAML file.

        Args:
            file_path: Path to YAML file.

        Returns:
            ValidationResult with errors and warnings.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return self.validate(content)
        except FileNotFoundError:
            result = ValidationResult()
            result.add_error(f"File not found: {file_path}")
            return result
        except Exception as e:
            result = ValidationResult()
            result.add_error(f"Error reading file: {e}")
            return result


# Convenience function
def validate_yaml(
    yaml_content: str, strict: bool = True
) -> ValidationResult:
    """Validate YAML content.

    Args:
        yaml_content: The YAML content to validate.
        strict: If True, fail on warnings too.

    Returns:
        ValidationResult with errors and warnings.
    """
    validator = YAMLValidator(strict=strict)
    return validator.validate(yaml_content)


def validate_yaml_file(file_path: str, strict: bool = True) -> ValidationResult:
    """Validate YAML file.

    Args:
        file_path: Path to YAML file.
        strict: If True, fail on warnings too.

    Returns:
        ValidationResult with errors and warnings.
    """
    validator = YAMLValidator(strict=strict)
    return validator.validate_file(file_path)
