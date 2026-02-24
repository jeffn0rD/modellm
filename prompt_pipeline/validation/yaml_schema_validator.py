"""YAML schema validation using jsonschema."""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List

import yaml
import jsonschema
from prompt_pipeline.validation.yaml_validator import ValidationResult


class YAMLSchemaValidator:
    """Validates YAML files against JSON schemas."""

    def __init__(self, schema_dir: str = "schemas"):
        self.schema_dir = Path(schema_dir)

    def validate_yaml_file(
        self,
        yaml_file: Path,
        schema_file: Path,
    ) -> ValidationResult:
        """
        Validate a YAML file against a JSON schema.

        Args:
            yaml_file: Path to the YAML file to validate
            schema_file: Path to the JSON schema file

        Returns:
            ValidationResult with success status and any errors
        """
        try:
            # Load YAML file
            with open(yaml_file, 'r', encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f)

            # Load JSON schema
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema = json.load(f)

            # Validate
            jsonschema.validate(instance=yaml_data, schema=schema)

            result = ValidationResult()
            return result

        except FileNotFoundError as e:
            result = ValidationResult()
            result.add_error(f"File not found: {e}")
            return result
        except yaml.YAMLError as e:
            result = ValidationResult()
            result.add_error(f"Invalid YAML syntax: {e}")
            return result
        except json.JSONDecodeError as e:
            result = ValidationResult()
            result.add_error(f"Invalid JSON schema: {e}")
            return result
        except jsonschema.ValidationError as e:
            result = ValidationResult()
            result.add_error(self._format_validation_error(e))
            return result
        except Exception as e:
            result = ValidationResult()
            result.add_error(f"Unexpected error: {e}")
            return result

    def validate_yaml_data(
        self,
        yaml_data: Dict[str, Any],
        schema_file: Path,
    ) -> ValidationResult:
        """
        Validate in-memory YAML data against a JSON schema.

        Args:
            yaml_data: Parsed YAML data (dict)
            schema_file: Path to the JSON schema file

        Returns:
            ValidationResult with success status and any errors
        """
        try:
            # Load JSON schema
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema = json.load(f)

            # Validate
            jsonschema.validate(instance=yaml_data, schema=schema)

            return ValidationResult(
                is_valid=True,
                message="YAML data is valid against schema"
            )

        except jsonschema.ValidationError as e:
            result = ValidationResult()
            result.add_error(self._format_validation_error(e))
            return result
        except Exception as e:
            result = ValidationResult()
            result.add_error(f"Error: {e}")
            return result

    def _format_validation_error(self, error: jsonschema.ValidationError) -> str:
        """Format a ValidationError into a readable message."""
        path = " -> ".join(str(p) for p in error.absolute_path)
        schema_path = " -> ".join(str(p) for p in error.absolute_schema_path)

        return (
            f"Validation error at '{path}': {error.message}\n"
            f"  Expected: {error.validator} {error.validator_value}\n"
            f"  Found: {error.instance}\n"
            f"  Schema path: {schema_path}"
        )

    def get_schema_errors(self, yaml_file: Path, schema_file: Path) -> List[str]:
        """
        Get detailed list of schema validation errors.

        Args:
            yaml_file: Path to YAML file
            schema_file: Path to JSON schema

        Returns:
            List of error messages
        """
        result = self.validate_yaml_file(yaml_file, schema_file)
        return result.errors if not result.is_valid else []
