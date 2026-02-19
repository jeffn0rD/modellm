"""Tests for YAML Validator."""

import pytest

from prompt_pipeline.validation.yaml_validator import (
    ValidationResult,
    YAMLValidator,
    validate_yaml,
    validate_yaml_file,
)


class TestValidationResult:
    """Tests for ValidationResult class."""

    def test_init(self):
        """Test ValidationResult initialization."""
        result = ValidationResult()
        assert result.errors == []
        assert result.warnings == []
        assert result.passed is False

    def test_add_error(self):
        """Test adding error messages."""
        result = ValidationResult()
        result.add_error("Test error")
        assert len(result.errors) == 1
        assert result.errors[0] == "Test error"
        assert result.passed is False

    def test_add_warning(self):
        """Test adding warning messages."""
        result = ValidationResult()
        result.add_warning("Test warning")
        assert len(result.warnings) == 1
        assert result.warnings[0] == "Test warning"

    def test_is_valid(self):
        """Test is_valid method."""
        result = ValidationResult()
        assert result.is_valid() is True
        result.add_error("Error")
        assert result.is_valid() is False


class TestYAMLValidator:
    """Tests for YAMLValidator class."""

    def test_valid_yaml(self):
        """Test validation of valid YAML."""
        yaml_content = """
specification:
  id: S1
  title: Test Spec
  sections:
    - id: S1
      title: Section 1
      text_blocks:
        - anchor_id: AN1
          text: Some text
"""
        validator = YAMLValidator()
        result = validator.validate(yaml_content)
        assert result.is_valid()

    def test_invalid_yaml_syntax(self):
        """Test validation catches YAML syntax errors."""
        yaml_content = """
specification:
  id: S1
  title: Test
  sections:
    - id: S1
      text_blocks:
        - anchor_id: AN1
          text: Some text
  invalid: [unclosed
"""
        validator = YAMLValidator()
        result = validator.validate(yaml_content)
        assert not result.is_valid()
        assert any("parse error" in e.lower() for e in result.errors)

    def test_missing_specification_field(self):
        """Test validation catches missing specification field."""
        yaml_content = """
other_field:
  id: S1
"""
        validator = YAMLValidator()
        result = validator.validate(yaml_content)
        assert not result.is_valid()
        assert any("specification" in e.lower() for e in result.errors)

    def test_missing_required_fields(self):
        """Test validation catches missing required fields."""
        yaml_content = """
specification:
  id: S1
"""
        validator = YAMLValidator()
        result = validator.validate(yaml_content)
        assert not result.is_valid()
        assert any("title" in e.lower() for e in result.errors)
        assert any("sections" in e.lower() for e in result.errors)

    def test_invalid_section_id_pattern(self):
        """Test validation catches invalid section ID pattern."""
        yaml_content = """
specification:
  id: S1
  title: Test
  sections:
    - id: Invalid
      title: Section 1
"""
        validator = YAMLValidator()
        result = validator.validate(yaml_content)
        assert not result.is_valid()
        assert any("invalid" in e.lower() for e in result.errors)

    def test_invalid_anchor_id_pattern(self):
        """Test validation catches invalid anchor ID pattern."""
        yaml_content = """
specification:
  id: S1
  title: Test
  sections:
    - id: S1
      title: Section 1
      text_blocks:
        - anchor_id: InvalidAnchor
          text: Some text
"""
        validator = YAMLValidator()
        result = validator.validate(yaml_content)
        assert not result.is_valid()
        assert any("anchor" in e.lower() for e in result.errors)

    def test_missing_text_field(self):
        """Test validation catches missing text field."""
        yaml_content = """
specification:
  id: S1
  title: Test
  sections:
    - id: S1
      title: Section 1
      text_blocks:
        - anchor_id: AN1
"""
        validator = YAMLValidator()
        result = validator.validate(yaml_content)
        assert not result.is_valid()
        assert any("text" in e.lower() for e in result.errors)

    def test_empty_text(self):
        """Test validation catches empty text."""
        yaml_content = """
specification:
  id: S1
  title: Test
  sections:
    - id: S1
      title: Section 1
      text_blocks:
        - anchor_id: AN1
          text: "   "
"""
        validator = YAMLValidator()
        result = validator.validate(yaml_content)
        assert not result.is_valid()
        assert any("empty" in e.lower() for e in result.errors)

    def test_duplicate_section_ids(self):
        """Test validation catches duplicate section IDs."""
        yaml_content = """
specification:
  id: S1
  title: Test
  sections:
    - id: S1
      title: Section 1
    - id: S1
      title: Section 2
"""
        validator = YAMLValidator()
        result = validator.validate(yaml_content)
        assert not result.is_valid()
        assert any("duplicate" in e.lower() for e in result.errors)

    def test_duplicate_anchor_ids(self):
        """Test validation catches duplicate anchor IDs in section."""
        yaml_content = """
specification:
  id: S1
  title: Test
  sections:
    - id: S1
      title: Section 1
      text_blocks:
        - anchor_id: AN1
          text: Text 1
        - anchor_id: AN1
          text: Text 2
"""
        validator = YAMLValidator()
        result = validator.validate(yaml_content)
        assert not result.is_valid()
        assert any("duplicate" in e.lower() for e in result.errors)

    def test_warnings_for_missing_title(self):
        """Test warnings for missing section title."""
        yaml_content = """
specification:
  id: S1
  title: Test
  sections:
    - id: S1
      text_blocks:
        - anchor_id: AN1
          text: Some text
"""
        validator = YAMLValidator()
        result = validator.validate(yaml_content)
        # Should pass but with warnings
        assert result.is_valid()
        assert any("title" in w.lower() for w in result.warnings)

    def test_valid_complex_yaml(self):
        """Test validation of complex valid YAML."""
        yaml_content = """
specification:
  id: S1
  title: Test Specification
  sections:
    - id: S1
      title: Introduction
      text_blocks:
        - anchor_id: AN1
          text: This is the introduction section.
        - anchor_id: AN2
          text: It contains important information.
    - id: S2
      title: Requirements
      text_blocks:
        - anchor_id: AN3
          text: The system shall meet these requirements.
"""
        validator = YAMLValidator()
        result = validator.validate(yaml_content)
        assert result.is_valid(), f"Errors: {result.errors}"


class TestValidateYamlFunction:
    """Tests for validate_yaml convenience function."""

    def test_convenience_function(self):
        """Test convenience function."""
        yaml_content = """
specification:
  id: S1
  title: Test
  sections:
    - id: S1
      title: Section 1
      text_blocks:
        - anchor_id: AN1
          text: Some text
"""
        result = validate_yaml(yaml_content)
        assert result.is_valid()


class TestYAMLValidatorFile:
    """Tests for YAMLValidator file validation."""

    def test_validate_nonexistent_file(self):
        """Test validation of nonexistent file."""
        validator = YAMLValidator()
        result = validator.validate_file("nonexistent.yaml")
        assert not result.is_valid()
        assert any("not found" in e.lower() for e in result.errors)

    def test_validate_valid_file(self, tmp_path):
        """Test validation of valid YAML file."""
        yaml_file = tmp_path / "spec.yaml"
        yaml_file.write_text("""
specification:
  id: S1
  title: Test
  sections:
    - id: S1
      title: Section 1
      text_blocks:
        - anchor_id: AN1
          text: Some text
""")
        validator = YAMLValidator()
        result = validator.validate_file(str(yaml_file))
        assert result.is_valid()
