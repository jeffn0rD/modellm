"""Input Type Validation Module for CLI Inputs.

This module validates that input content matches expected types
and provides clear error messages for type mismatches.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class InputValidationError(Exception):
    """Exception raised when input validation fails."""

    pass


class InputTypeValidator:
    """Validates input content against expected types."""

    # Type descriptions for error messages
    TYPE_DESCRIPTIONS = {
        "md": "Markdown file",
        "json": "JSON file",
        "yaml": "YAML file",
        "yml": "YAML file",
        "text": "Text file",
        "txt": "Text file",
    }

    # Valid file extensions for each type
    TYPE_EXTENSIONS = {
        "md": ["md", "txt", "markdown"],
        "json": ["json"],
        "yaml": ["yaml", "yml"],
        "yml": ["yaml", "yml"],
        "text": ["txt", "md", "text"],
    }

    @classmethod
    def validate_input_type(
        cls,
        label: str,
        expected_type: str,
        source: str,
        content_or_path: str,
    ) -> bool:
        """
        Validate input content matches expected type.

        Args:
            label: Input label.
            expected_type: Expected type (md, json, yaml, text).
            source: Source type (file, prompt, text, env).
            content_or_path: Either file path or actual content (depending on source).

        Returns:
            True if valid.

        Raises:
            InputValidationError: If validation fails.
        """
        # Normalize expected type
        expected_type = expected_type.lower()

        # Validate based on source type
        if source == "file":
            return cls._validate_file_input(
                label, expected_type, content_or_path
            )
        elif source in ("prompt", "text", "env"):
            return cls._validate_content_input(
                label, expected_type, content_or_path
            )
        else:
            # For unknown sources, don't validate
            return True

    @classmethod
    def _validate_file_input(
        cls,
        label: str,
        expected_type: str,
        file_path: str,
    ) -> bool:
        """
        Validate file input based on file extension and content.

        Args:
            label: Input label.
            expected_type: Expected type.
            file_path: Path to the file.

        Returns:
            True if valid.

        Raises:
            InputValidationError: If validation fails.
        """
        # Check if file exists
        if not os.path.exists(file_path):
            raise InputValidationError(
                f"File not found for label '{label}': {file_path}"
            )

        # Get file extension
        ext = Path(file_path).suffix.lower().lstrip(".")

        # Validate extension
        valid_extensions = cls.TYPE_EXTENSIONS.get(expected_type, [])
        if ext and ext not in valid_extensions:
            expected_desc = cls.TYPE_DESCRIPTIONS.get(expected_type, expected_type)
            actual_desc = cls.TYPE_DESCRIPTIONS.get(ext, f".{ext} file")
            raise InputValidationError(
                f"Type mismatch for label '{label}':\n"
                f"  Expected: {expected_desc}\n"
                f"  Got: {actual_desc} (file: {file_path})\n"
                f"  Fix: Use a file with extension: {', '.join(valid_extensions)}"
            )

        # For JSON and YAML, also validate content
        if expected_type in ("json", "yaml", "yml"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                if expected_type == "json":
                    try:
                        json.loads(content)
                    except json.JSONDecodeError as e:
                        raise InputValidationError(
                            f"Invalid JSON for label '{label}' in file {file_path}:\n"
                            f"  Error: {e}"
                        )
                elif expected_type in ("yaml", "yml"):
                    try:
                        yaml.safe_load(content)
                    except yaml.YAMLError as e:
                        raise InputValidationError(
                            f"Invalid YAML for label '{label}' in file {file_path}:\n"
                            f"  Error: {e}"
                        )
            except Exception as e:
                raise InputValidationError(
                    f"Failed to read or parse file {file_path}: {e}"
                )

        return True

    @classmethod
    def _validate_content_input(
        cls,
        label: str,
        expected_type: str,
        content: str,
    ) -> bool:
        """
        Validate content input (from prompt, text, or env).

        Args:
            label: Input label.
            expected_type: Expected type.
            content: Actual content.

        Returns:
            True if valid.

        Raises:
            InputValidationError: If validation fails.
        """
        # For text type, accept any content
        if expected_type in ("text", "txt"):
            return True

        # For JSON, validate content
        if expected_type == "json":
            try:
                json.loads(content)
            except json.JSONDecodeError as e:
                raise InputValidationError(
                    f"Invalid JSON for label '{label}':\n"
                    f"  Error: {e}"
                )

        # For YAML, validate content
        elif expected_type in ("yaml", "yml"):
            try:
                yaml.safe_load(content)
            except yaml.YAMLError as e:
                raise InputValidationError(
                    f"Invalid YAML for label '{label}':\n"
                    f"  Error: {e}"
                )

        # For markdown/text, minimal validation (just check if it's readable)
        elif expected_type in ("md", "markdown"):
            # Markdown can be anything, but we can check if it has at least some content
            if not content.strip():
                raise InputValidationError(
                    f"Empty content for label '{label}' (expected markdown)"
                )

        return True

    @classmethod
    def infer_type_from_value(
        cls,
        value: str,
        source: str,
    ) -> str:
        """
        Infer input type from value and source.

        Args:
            value: Input value (file path or content).
            source: Source type (file, text, env).

        Returns:
            Inferred type (md, json, yaml, text).
        """
        # For file sources, use file extension
        if source == "file" and "." in value:
            ext = Path(value).suffix.lower().lstrip(".")
            if ext in ["md", "txt", "markdown"]:
                return "md"
            elif ext == "json":
                return "json"
            elif ext in ["yaml", "yml"]:
                return "yaml"

        # For text sources, try to detect JSON
        if source in ("text", "prompt", "env"):
            # Try to parse as JSON
            try:
                json.loads(value)
                return "json"
            except (json.JSONDecodeError, TypeError):
                pass

            # Try to parse as YAML
            try:
                yaml.safe_load(value)
                return "yaml"
            except (yaml.YAMLError, TypeError):
                pass

        # Default to text
        return "text"

    @classmethod
    def get_type_description(cls, input_type: str) -> str:
        """
        Get human-readable description of input type.

        Args:
            input_type: Input type.

        Returns:
            Description string.
        """
        return cls.TYPE_DESCRIPTIONS.get(input_type, input_type)

    @classmethod
    def get_valid_extensions(cls, input_type: str) -> list:
        """
        Get valid file extensions for input type.

        Args:
            input_type: Input type.

        Returns:
            List of valid extensions.
        """
        return cls.TYPE_EXTENSIONS.get(input_type, [])
