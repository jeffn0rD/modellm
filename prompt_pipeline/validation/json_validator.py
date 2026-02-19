"""JSON Validator module for pipeline output validation."""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import jsonschema

from prompt_pipeline.validation.yaml_validator import ValidationResult


# Default schemas directory (relative to project root)
DEFAULT_SCHEMAS_DIR = Path("schemas")


class JSONValidator:
    """Base JSON validator with optional schema support.

    Provides common JSON validation functionality that can be
    extended by specific validators for different output types.
    """

    # Default schema filename (to be overridden by subclasses)
    DEFAULT_SCHEMA_FILE: Optional[str] = None

    def __init__(self, schema_path: Optional[str] = None):
        """Initialize JSON validator.

        Args:
            schema_path: Optional path to JSON schema file.
                         If not provided, tries to load from default schema.
                         Use empty string "" to explicitly disable schema loading.
        """
        self.schema: Optional[Dict[str, Any]] = None

        # Explicit schema path provided (non-empty string)
        if schema_path and schema_path != "":
            if Path(schema_path).exists():
                with open(schema_path, "r", encoding="utf-8") as f:
                    self.schema = json.load(f)
        # Try to load default schema from schemas folder (only if schema_path is None)
        elif schema_path is None and self.DEFAULT_SCHEMA_FILE:
            default_path = DEFAULT_SCHEMAS_DIR / self.DEFAULT_SCHEMA_FILE
            if default_path.exists():
                with open(default_path, "r", encoding="utf-8") as f:
                    self.schema = json.load(f)

    def validate(self, json_content: str) -> ValidationResult:
        """Validate JSON structure.

        Args:
            json_content: The JSON content to validate.

        Returns:
            ValidationResult with errors and warnings.
        """
        result = ValidationResult()

        # Parse JSON
        try:
            data = json.loads(json_content)
        except json.JSONDecodeError as e:
            result.add_error(f"JSON parse error: {e}")
            return result

        if data is None:
            result.add_error("JSON content is empty")
            return result

        # Validate against schema if available
        if self.schema:
            self._validate_schema(data, result)

        result.passed = result.is_valid()
        return result

    def _validate_schema(self, data: Any, result: ValidationResult) -> None:
        """Validate against JSON schema using jsonschema library.

        Args:
            data: Parsed JSON data.
            result: ValidationResult to append errors to.
        """
        if not self.schema:
            return
        
        try:
            jsonschema.validate(instance=data, schema=self.schema)
        except jsonschema.exceptions.ValidationError as e:
            result.add_error(f"Schema validation failed: {e.message}")
            # Include path for more context
            if e.absolute_path:
                path = '.'.join(str(p) for p in e.absolute_path)
                result.add_error(f"  at path: {path}")

    def validate_file(self, file_path: str) -> ValidationResult:
        """Validate JSON file.

        Args:
            file_path: Path to JSON file.

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


class ConceptsValidator(JSONValidator):
    """Validate concepts.json output.
    
    Uses JSON Schema for validation - all constraints are defined in 
    schemas/concepts.schema.json
    """

    # Default schema file
    DEFAULT_SCHEMA_FILE = "concepts.schema.json"

    def __init__(self, schema_path: Optional[str] = None):
        """Initialize concepts validator.

        Args:
            schema_path: Optional path to JSON schema file.
        """
        super().__init__(schema_path)

    def validate(self, json_content: str) -> ValidationResult:
        """Validate concepts JSON.

        Args:
            json_content: The JSON content to validate.

        Returns:
            ValidationResult with errors and warnings.
        """
        result = ValidationResult()

        # Parse JSON
        try:
            data = json.loads(json_content)
        except json.JSONDecodeError as e:
            result.add_error(f"JSON parse error: {e}")
            return result

        # Check it's an array
        if not isinstance(data, list):
            result.add_error("concepts.json must be an array")
            return result

        if len(data) == 0:
            result.add_warning("No concepts defined")

        # Validate against schema
        if self.schema:
            self._validate_schema(data, result)

        result.passed = result.is_valid()
        return result


class AggregationsValidator(JSONValidator):
    """Validate aggregations.json output.
    
    Uses JSON Schema for validation - all constraints are defined in 
    schemas/aggregations.schema.json
    """

    # Default schema file
    DEFAULT_SCHEMA_FILE = "aggregations.schema.json"

    def __init__(self, schema_path: Optional[str] = None):
        """Initialize aggregations validator.

        Args:
            schema_path: Optional path to JSON schema file.
        """
        super().__init__(schema_path)

    def validate(self, json_content: str) -> ValidationResult:
        """Validate aggregations JSON.

        Args:
            json_content: The JSON content to validate.

        Returns:
            ValidationResult with errors and warnings.
        """
        result = ValidationResult()

        # Parse JSON
        try:
            data = json.loads(json_content)
        except json.JSONDecodeError as e:
            result.add_error(f"JSON parse error: {e}")
            return result

        # Check it's an array
        if not isinstance(data, list):
            result.add_error("aggregations.json must be an array")
            return result

        if len(data) == 0:
            result.add_warning("No aggregations defined")

        # Validate against schema
        if self.schema:
            self._validate_schema(data, result)

        result.passed = result.is_valid()
        return result


class MessagesValidator(JSONValidator):
    """Validate messages.json output.
    
    Uses JSON Schema for validation - all constraints are defined in 
    schemas/messages.schema.json
    """

    # Default schema file
    DEFAULT_SCHEMA_FILE = "messages.schema.json"

    def __init__(self, schema_path: Optional[str] = None):
        """Initialize messages validator.

        Args:
            schema_path: Optional path to JSON schema file.
        """
        super().__init__(schema_path)

    def validate(self, json_content: str) -> ValidationResult:
        """Validate messages JSON.

        Args:
            json_content: The JSON content to validate.

        Returns:
            ValidationResult with errors and warnings.
        """
        result = ValidationResult()

        # Parse JSON
        try:
            data = json.loads(json_content)
        except json.JSONDecodeError as e:
            result.add_error(f"JSON parse error: {e}")
            return result

        # Check it's an array
        if not isinstance(data, list):
            result.add_error("messages.json must be an array")
            return result

        if len(data) == 0:
            result.add_warning("No messages defined")

        # Validate against schema
        if self.schema:
            self._validate_schema(data, result)

        result.passed = result.is_valid()
        return result


class RequirementsValidator(JSONValidator):
    """Validate requirements.json output.
    
    Uses JSON Schema for validation - all constraints are defined in 
    schemas/requirements.schema.json
    """

    # Default schema file
    DEFAULT_SCHEMA_FILE = "requirements.schema.json"

    def __init__(self, schema_path: Optional[str] = None):
        """Initialize requirements validator.

        Args:
            schema_path: Optional path to JSON schema file.
        """
        super().__init__(schema_path)

    def validate(self, json_content: str) -> ValidationResult:
        """Validate requirements JSON.

        Args:
            json_content: The JSON content to validate.

        Returns:
            ValidationResult with errors and warnings.
        """
        result = ValidationResult()

        # Parse JSON
        try:
            data = json.loads(json_content)
        except json.JSONDecodeError as e:
            result.add_error(f"JSON parse error: {e}")
            return result

        # Check it's an array
        if not isinstance(data, list):
            result.add_error("requirements.json must be an array")
            return result

        if len(data) == 0:
            result.add_warning("No requirements defined")

        # Validate against schema
        if self.schema:
            self._validate_schema(data, result)

        result.passed = result.is_valid()
        return result


# Convenience functions
def validate_concepts(
    json_content: str, schema_path: Optional[str] = None
) -> ValidationResult:
    """Validate concepts JSON.

    Args:
        json_content: The JSON content to validate.
        schema_path: Optional path to JSON schema file.

    Returns:
        ValidationResult with errors and warnings.
    """
    validator = ConceptsValidator(schema_path)
    return validator.validate(json_content)


def validate_aggregations(
    json_content: str, schema_path: Optional[str] = None
) -> ValidationResult:
    """Validate aggregations JSON.

    Args:
        json_content: The JSON content to validate.
        schema_path: Optional path to JSON schema file.

    Returns:
        ValidationResult with errors and warnings.
    """
    validator = AggregationsValidator(schema_path)
    return validator.validate(json_content)


def validate_messages(
    json_content: str, schema_path: Optional[str] = None
) -> ValidationResult:
    """Validate messages JSON.

    Args:
        json_content: The JSON content to validate.
        schema_path: Optional path to JSON schema file.

    Returns:
        ValidationResult with errors and warnings.
    """
    validator = MessagesValidator(schema_path)
    return validator.validate(json_content)


def validate_requirements(
    json_content: str, schema_path: Optional[str] = None
) -> ValidationResult:
    """Validate requirements JSON.

    Args:
        json_content: The JSON content to validate.
        schema_path: Optional path to JSON schema file.

    Returns:
        ValidationResult with errors and warnings.
    """
    validator = RequirementsValidator(schema_path)
    return validator.validate(json_content)
