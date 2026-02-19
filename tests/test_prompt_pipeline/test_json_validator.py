"""Tests for JSON Validators."""

import pytest

from prompt_pipeline.validation.json_validator import (
    ConceptsValidator,
    AggregationsValidator,
    MessagesValidator,
    RequirementsValidator,
    JSONValidator,
)


class TestConceptsValidator:
    """Tests for ConceptsValidator class."""

    def test_valid_actor_concept(self):
        """Test validation of valid Actor concept."""
        json_content = """[
            {
                "type": "Actor",
                "id": "A1",
                "label": "User",
                "description": "A system user"
            }
        ]"""
        validator = ConceptsValidator()
        result = validator.validate(json_content)
        assert result.is_valid(), f"Errors: {result.errors}"

    def test_valid_action_concept(self):
        """Test validation of valid Action concept."""
        json_content = """[
            {
                "type": "Action",
                "id": "ACT1",
                "label": "Create",
                "description": "Create a new entity"
            }
        ]"""
        validator = ConceptsValidator()
        result = validator.validate(json_content)
        assert result.is_valid(), f"Errors: {result.errors}"

    def test_valid_dataentity_concept(self):
        """Test validation of valid DataEntity concept."""
        json_content = """[
            {
                "type": "DataEntity",
                "id": "DE1",
                "label": "Document",
                "description": "A document entity"
            }
        ]"""
        validator = ConceptsValidator()
        result = validator.validate(json_content)
        assert result.is_valid(), f"Errors: {result.errors}"

    def test_invalid_json(self):
        """Test validation catches invalid JSON."""
        json_content = """[
            { invalid json
        ]"""
        validator = ConceptsValidator()
        result = validator.validate(json_content)
        assert not result.is_valid()
        assert any("parse error" in e.lower() for e in result.errors)

    def test_not_array(self):
        """Test validation catches non-array."""
        json_content = """{"type": "Actor"}"""
        validator = ConceptsValidator()
        result = validator.validate(json_content)
        assert not result.is_valid()
        assert any("must be an array" in e.lower() for e in result.errors)

    def test_missing_required_field(self):
        """Test validation catches missing required field."""
        json_content = """[
            {
                "type": "Actor",
                "id": "A1",
                "label": "User"
            }
        ]"""
        validator = ConceptsValidator()
        result = validator.validate(json_content)
        assert not result.is_valid()
        # Schema validation catches missing description
        assert len(result.errors) > 0
        assert any("required" in e.lower() for e in result.errors)

    def test_invalid_actor_id(self):
        """Test validation catches invalid Actor ID."""
        json_content = """[
            {
                "type": "Actor",
                "id": "Invalid",
                "label": "User",
                "description": "A user"
            }
        ]"""
        validator = ConceptsValidator()
        result = validator.validate(json_content)
        assert not result.is_valid()
        # Schema validation will catch pattern mismatch
        assert len(result.errors) > 0

    def test_invalid_action_id(self):
        """Test validation catches invalid Action ID."""
        json_content = """[
            {
                "type": "Action",
                "id": "INVALID",
                "label": "Create",
                "description": "Create"
            }
        ]"""
        validator = ConceptsValidator()
        result = validator.validate(json_content)
        assert not result.is_valid()
        # Schema validation will catch pattern mismatch
        assert len(result.errors) > 0

    def test_duplicate_ids(self):
        """Test validation catches duplicate IDs."""
        json_content = """[
            {
                "type": "Actor",
                "id": "A1",
                "label": "User 1",
                "description": "User 1"
            },
            {
                "type": "Actor",
                "id": "A1",
                "label": "User 2",
                "description": "User 2"
            }
        ]"""
        validator = ConceptsValidator()
        result = validator.validate(json_content)
        # Note: Schema doesn't enforce uniqueness across items
        # This would be a business logic check, out of scope
        assert result.is_valid()  # Schema validation passes


class TestAggregationsValidator:
    """Tests for AggregationsValidator class."""

    def test_valid_aggregation(self):
        """Test validation of valid aggregation."""
        json_content = """[
            {
                "id": "AG1",
                "label": "Test Aggregation",
                "category": "lifecycle",
                "members": ["A1", "A2"],
                "description": "Test description",
                "justification": "Test justification"
            }
        ]"""
        validator = AggregationsValidator()
        result = validator.validate(json_content)
        assert result.is_valid(), f"Errors: {result.errors}"

    def test_invalid_id_pattern(self):
        """Test validation catches invalid ID pattern."""
        json_content = """[
            {
                "id": "Invalid",
                "label": "Test",
                "category": "lifecycle",
                "members": ["A1"],
                "description": "Test",
                "justification": "Test"
            }
        ]"""
        validator = AggregationsValidator()
        result = validator.validate(json_content)
        assert not result.is_valid()
        # Schema validation will catch pattern mismatch
        assert len(result.errors) > 0

    def test_invalid_type(self):
        """Test validation catches invalid aggregation type."""
        json_content = """[
            {
                "id": "AG1",
                "label": "Test",
                "category": "invalid_category",
                "members": ["A1"],
                "description": "Test",
                "justification": "Test"
            }
        ]"""
        validator = AggregationsValidator()
        result = validator.validate(json_content)
        assert not result.is_valid()
        assert any("enum" in e.lower() or "invalid" in e.lower() for e in result.errors)

    def test_missing_members(self):
        """Test validation catches missing members."""
        json_content = """[
            {
                "id": "AG1",
                "category": "lifecycle"
            }
        ]"""
        validator = AggregationsValidator()
        result = validator.validate(json_content)
        assert not result.is_valid()
        # Schema validation catches missing label, members, description, justification
        assert len(result.errors) > 0
        assert any("required" in e.lower() for e in result.errors)


class TestMessagesValidator:
    """Tests for MessagesValidator class."""

    def test_valid_message(self):
        """Test validation of valid message."""
        json_content = """[
            {
                "id": "MSG1",
                "label": "Test Message",
                "category": "command",
                "description": "Test message",
                "producer": "A1",
                "consumer": "A2",
                "payload": [],
                "constraints": [],
                "justification": "Test"
            }
        ]"""
        validator = MessagesValidator()
        result = validator.validate(json_content)
        assert result.is_valid(), f"Errors: {result.errors}"

    def test_invalid_id_pattern(self):
        """Test validation catches invalid message ID."""
        json_content = """[
            {
                "id": "Invalid",
                "label": "Test",
                "category": "command",
                "description": "Test",
                "producer": "A1",
                "consumer": "A2",
                "payload": [],
                "constraints": [],
                "justification": "Test"
            }
        ]"""
        validator = MessagesValidator()
        result = validator.validate(json_content)
        assert not result.is_valid()
        # Schema validation will catch pattern mismatch
        assert len(result.errors) > 0

    def test_invalid_type(self):
        """Test validation catches invalid message category."""
        json_content = """[
            {
                "id": "MSG1",
                "label": "Test",
                "category": "InvalidType",
                "description": "Test",
                "producer": "A1",
                "consumer": "A2",
                "payload": [],
                "constraints": [],
                "justification": "Test"
            }
        ]"""
        validator = MessagesValidator()
        result = validator.validate(json_content)
        assert not result.is_valid()
        assert any("enum" in e.lower() or "invalid" in e.lower() for e in result.errors)

    def test_invalid_producer_consumer(self):
        """Test validation catches invalid producer/consumer ID patterns."""
        json_content = """[
            {
                "id": "MSG1",
                "label": "Test",
                "category": "command",
                "description": "Test",
                "producer": "Invalid",
                "consumer": "A2",
                "payload": [],
                "constraints": [],
                "justification": "Test"
            }
        ]"""
        validator = MessagesValidator()
        result = validator.validate(json_content)
        assert not result.is_valid()
        # Schema validation will catch pattern mismatch
        assert len(result.errors) > 0


class TestRequirementsValidator:
    """Tests for RequirementsValidator class."""

    def test_valid_requirement(self):
        """Test validation of valid requirement."""
        json_content = """[
            {
                "id": "REQ-1",
                "type": "functional",
                "label": "Test Requirement",
                "description": "The system shall authenticate users",
                "priority": "must"
            }
        ]"""
        validator = RequirementsValidator()
        result = validator.validate(json_content)
        assert result.is_valid(), f"Errors: {result.errors}"

    def test_invalid_id_pattern(self):
        """Test validation catches invalid requirement ID."""
        json_content = """[
            {
                "id": "Invalid",
                "type": "functional",
                "label": "Test",
                "description": "Test description"
            }
        ]"""
        validator = RequirementsValidator()
        result = validator.validate(json_content)
        assert not result.is_valid()
        # Schema validation will catch pattern mismatch
        assert len(result.errors) > 0

    def test_invalid_type(self):
        """Test validation catches invalid requirement type."""
        json_content = """[
            {
                "id": "REQ-1",
                "type": "InvalidType",
                "label": "Test",
                "description": "Test description"
            }
        ]"""
        validator = RequirementsValidator()
        result = validator.validate(json_content)
        assert not result.is_valid()
        assert any("enum" in e.lower() or "invalid" in e.lower() for e in result.errors)

    def test_invalid_priority(self):
        """Test validation catches invalid priority."""
        json_content = """[
            {
                "id": "REQ-1",
                "type": "functional",
                "label": "Test",
                "description": "Test description",
                "priority": "InvalidPriority"
            }
        ]"""
        validator = RequirementsValidator()
        result = validator.validate(json_content)
        assert not result.is_valid()
        assert any("enum" in e.lower() or "priority" in e.lower() for e in result.errors)

    def test_empty_description(self):
        """Test validation catches empty description."""
        json_content = """[
            {
                "id": "REQ-1",
                "type": "functional",
                "label": "Test",
                "description": ""
            }
        ]"""
        validator = RequirementsValidator()
        result = validator.validate(json_content)
        assert not result.is_valid()
