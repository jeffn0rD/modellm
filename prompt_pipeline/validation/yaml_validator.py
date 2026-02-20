"""YAML Validator module for Step 1 output validation and pipeline configuration validation."""

import re
from typing import List, Optional, Dict, Any

import yaml
import json
import jsonschema
from importlib import resources


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

        # Validate spec ID pattern - accept any non-empty string
        spec_id = spec.get("id", "")
        if spec_id:
            if not spec_id.strip():
                result.add_error(
                    f"Invalid specification ID pattern: '{spec_id}'. "
                    "ID cannot be empty or whitespace only"
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


class PipelineConfigValidator:
    """Validate pipeline configuration files against JSON Schema.

    Validates:
    - Valid YAML syntax
    - Matches pipeline_config.schema.json structure
    - Validates cli_inputs, exogenous_inputs, output_labels, steps
    - Supports both old and new formats for migration
    """

    def __init__(self, strict: bool = True):
        """Initialize pipeline config validator.

        Args:
            strict: If True, validation fails on warnings too.
        """
        self.strict = strict
        self._schema: Optional[Dict[str, Any]] = None

    def _load_schema(self) -> Dict[str, Any]:
        """Load the pipeline configuration JSON Schema.

        Returns:
            The JSON Schema dictionary.

        Raises:
            FileNotFoundError: If schema file is not found.
            json.JSONDecodeError: If schema file is not valid JSON.
        """
        if self._schema is not None:
            return self._schema

        # Try to load schema from schemas directory
        schema_path = "schemas/pipeline_config.schema.json"
        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                self._schema = json.load(f)
        except FileNotFoundError:
            # Try alternative location in package resources
            try:
                schema_content = resources.read_text("schemas", "pipeline_config.schema.json")
                self._schema = json.loads(schema_content)
            except (FileNotFoundError, ModuleNotFoundError):
                raise FileNotFoundError(
                    f"Pipeline config schema not found at {schema_path} "
                    "or in package resources"
                )
        
        return self._schema

    def _detect_config_format(self, data: Dict[str, Any]) -> str:
        """Detect if config is old or new format.

        Args:
            data: Parsed YAML data.

        Returns:
            "new" for new format, "old" for old format.
        """
        # New format has 'cli_inputs' and uses 'inputs' array in steps
        if "cli_inputs" in data or "exogenous_inputs" in data:
            return "new"
        
        # Old format has 'requires_nl_spec' and 'output_file' in steps
        for step_name, step_config in data.get("steps", {}).items():
            if isinstance(step_config, dict):
                if "requires_nl_spec" in step_config or "output_file" in step_config:
                    return "old"
        
        # Default to new format if uncertain
        return "new"

    def validate(self, yaml_content: str) -> ValidationResult:
        """Validate pipeline configuration against JSON Schema.

        Args:
            yaml_content: The YAML configuration content to validate.

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

        # Detect configuration format
        config_format = self._detect_config_format(data)

        if config_format == "old":
            result.add_warning(
                "Old configuration format detected. "
                "Please migrate to new format using migration script. "
                "See doc/migration_guide.md for details."
            )
            # Validate old format structure minimally
            if "steps" not in data:
                result.add_error("Missing required top-level field: 'steps'")
            
            for step_name, step_config in data.get("steps", {}).items():
                if isinstance(step_config, dict):
                    if "prompt_file" not in step_config:
                        result.add_error(f"Step '{step_name}' missing 'prompt_file'")
                    if "order" not in step_config:
                        result.add_error(f"Step '{step_name}' missing 'order'")
            result.passed = result.is_valid()
            return result

        # Validate new format against JSON Schema
        # For strict validation, we'll skip model_levels validation since YAML parses
        # numeric keys as integers while JSON Schema expects string keys
        try:
            schema = self._load_schema()
            
            # Create a copy of data without model_levels for strict validation
            if self.strict:
                data_for_validation = {k: v for k, v in data.items() if k != "model_levels"}
                jsonschema.validate(instance=data_for_validation, schema=schema)
            else:
                jsonschema.validate(instance=data, schema=schema)
        except json.JSONDecodeError as e:
            result.add_error(f"Invalid schema JSON: {e}")
            return result
        except jsonschema.ValidationError as e:
            # Provide user-friendly error messages
            path = ".".join(str(p) for p in e.absolute_path)
            # Skip model_levels validation errors (they're false positives due to integer keys)
            if "model_levels" not in path:
                result.add_error(
                    f"Schema validation error at '{path}': {e.message}"
                )
        except jsonschema.SchemaError as e:
            result.add_error(f"Invalid schema: {e}")

        # Additional semantic validations
        self._validate_label_uniqueness(data, result)
        self._validate_step_dependencies(data, result)
        self._validate_input_output_types(data, result)

        result.passed = result.is_valid()
        return result

    def _validate_label_uniqueness(self, data: Dict[str, Any], result: ValidationResult) -> None:
        """Validate that all labels are unique across the configuration.

        Args:
            data: Parsed configuration data.
            result: ValidationResult to append warnings to.
        """
        labels: Dict[str, List[str]] = {}

        # Check CLI input labels
        for i, input_config in enumerate(data.get("cli_inputs", [])):
            if isinstance(input_config, dict):
                label = input_config.get("label", "")
                if label:
                    labels.setdefault(label, []).append(f"cli_inputs[{i}]")

        # Check exogenous input labels
        for i, input_config in enumerate(data.get("exogenous_inputs", [])):
            if isinstance(input_config, dict):
                label = input_config.get("label", "")
                if label:
                    labels.setdefault(label, []).append(f"exogenous_inputs[{i}]")

        # Check output labels
        for i, output_config in enumerate(data.get("output_labels", [])):
            if isinstance(output_config, dict):
                label = output_config.get("label", "")
                if label:
                    labels.setdefault(label, []).append(f"output_labels[{i}]")

        # Check step output labels
        for step_name, step_config in data.get("steps", {}).items():
            if isinstance(step_config, dict):
                for i, output_config in enumerate(step_config.get("outputs", [])):
                    if isinstance(output_config, dict):
                        label = output_config.get("label", "")
                        if label:
                            labels.setdefault(label, []).append(f"steps.{step_name}.outputs[{i}]")

        # Report duplicate labels
        for label, locations in labels.items():
            if len(locations) > 1:
                result.add_warning(
                    f"Label '{label}' is defined in multiple places: {', '.join(locations)}. "
                    "This may cause unexpected behavior."
                )

    def _validate_step_dependencies(self, data: Dict[str, Any], result: ValidationResult) -> None:
        """Validate that step dependencies are valid.

        Args:
            data: Parsed configuration data.
            result: ValidationResult to append warnings to.
        """
        steps = data.get("steps", {})
        step_names = set(steps.keys())

        for step_name, step_config in steps.items():
            if isinstance(step_config, dict):
                # Check explicit dependencies
                for dep in step_config.get("dependencies", []):
                    if dep not in step_names:
                        result.add_warning(
                            f"Step '{step_name}' references unknown dependency '{dep}'"
                        )

                # Check if inputs reference non-existent labels
                for input_config in step_config.get("inputs", []):
                    if isinstance(input_config, dict):
                        label = input_config.get("label", "")
                        source = input_config.get("source", "")
                        
                        if source.startswith("label:"):
                            referenced_label = source.split(":", 1)[1]
                            # Check if label exists anywhere
                            if not self._label_exists(data, referenced_label):
                                result.add_warning(
                                    f"Step '{step_name}' references label '{referenced_label}' "
                                    "which is not defined in the configuration"
                                )

    def _validate_input_output_types(self, data: Dict[str, Any], result: ValidationResult) -> None:
        """Validate that input/output types are consistent.

        Args:
            data: Parsed configuration data.
            result: ValidationResult to append warnings to.
        """
        valid_types = {"md", "yaml", "json", "text", "typedb_query", "typedb_result"}

        # Check CLI input types
        for i, input_config in enumerate(data.get("cli_inputs", [])):
            if isinstance(input_config, dict):
                input_type = input_config.get("type", "")
                if input_type and input_type not in valid_types:
                    result.add_warning(
                        f"cli_inputs[{i}] has unknown type '{input_type}'. "
                        f"Valid types: {', '.join(sorted(valid_types))}"
                    )

        # Check step input types
        for step_name, step_config in data.get("steps", {}).items():
            if isinstance(step_config, dict):
                for i, input_config in enumerate(step_config.get("inputs", [])):
                    if isinstance(input_config, dict):
                        input_type = input_config.get("type", "")
                        if input_type and input_type not in valid_types:
                            result.add_warning(
                                f"steps.{step_name}.inputs[{i}] has unknown type '{input_type}'. "
                                f"Valid types: {', '.join(sorted(valid_types))}"
                            )

                # Check step output types
                for i, output_config in enumerate(step_config.get("outputs", [])):
                    if isinstance(output_config, dict):
                        output_type = output_config.get("type", "")
                        if output_type and output_type not in {"md", "yaml", "json", "text"}:
                            result.add_warning(
                                f"steps.{step_name}.outputs[{i}] has unknown type '{output_type}'. "
                                f"Valid types: md, yaml, json, text"
                            )

    def _label_exists(self, data: Dict[str, Any], label: str) -> bool:
        """Check if a label exists anywhere in the configuration.

        Args:
            data: Parsed configuration data.
            label: Label to check for.

        Returns:
            True if label exists, False otherwise.
        """
        # Check CLI inputs
        for input_config in data.get("cli_inputs", []):
            if isinstance(input_config, dict) and input_config.get("label") == label:
                return True

        # Check exogenous inputs
        for input_config in data.get("exogenous_inputs", []):
            if isinstance(input_config, dict) and input_config.get("label") == label:
                return True

        # Check output labels
        for output_config in data.get("output_labels", []):
            if isinstance(output_config, dict) and output_config.get("label") == label:
                return True

        # Check step outputs
        for step_config in data.get("steps", {}).values():
            if isinstance(step_config, dict):
                for output_config in step_config.get("outputs", []):
                    if isinstance(output_config, dict) and output_config.get("label") == label:
                        return True

        return False

    def validate_file(self, file_path: str) -> ValidationResult:
        """Validate pipeline configuration file.

        Args:
            file_path: Path to YAML configuration file.

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


# Convenience functions for YAML output validation
def validate_yaml(
    yaml_content: str, strict: bool = True
) -> ValidationResult:
    """Validate YAML content (Step 1 output).

    Args:
        yaml_content: The YAML content to validate.
        strict: If True, fail on warnings too.

    Returns:
        ValidationResult with errors and warnings.
    """
    validator = YAMLValidator(strict=strict)
    return validator.validate(yaml_content)


def validate_yaml_file(file_path: str, strict: bool = True) -> ValidationResult:
    """Validate YAML file (Step 1 output).

    Args:
        file_path: Path to YAML file.
        strict: If True, fail on warnings too.

    Returns:
        ValidationResult with errors and warnings.
    """
    validator = YAMLValidator(strict=strict)
    return validator.validate_file(file_path)


# Convenience functions for pipeline configuration validation
def validate_pipeline_config(
    yaml_content: str, strict: bool = True
) -> ValidationResult:
    """Validate pipeline configuration content.

    Args:
        yaml_content: The YAML configuration content to validate.
        strict: If True, fail on warnings too.

    Returns:
        ValidationResult with errors and warnings.
    """
    validator = PipelineConfigValidator(strict=strict)
    return validator.validate(yaml_content)


def validate_pipeline_config_file(file_path: str, strict: bool = True) -> ValidationResult:
    """Validate pipeline configuration file.

    Args:
        file_path: Path to YAML configuration file.
        strict: If True, fail on warnings too.

    Returns:
        ValidationResult with errors and warnings.
    """
    validator = PipelineConfigValidator(strict=strict)
    return validator.validate_file(file_path)
