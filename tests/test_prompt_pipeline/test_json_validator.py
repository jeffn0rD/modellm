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
                "description": "A system user",
                "role": "end-user",
                "permissions": ["read", "write"]
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
                "description": "Create a new entity",
                "inputs": ["entity_data"],
                "outputs": ["entity_id"]
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
                "description": "A document entity",
                "attributes": ["title", "content"]
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
        assert any("description" in e.lower() for e in result.errors)

    def test_invalid_actor_id(self):
        """Test validation catches invalid Actor ID."""
        json_content = """[
            {
                "type": "Actor",
                "id": "Invalid",
                "label": "User",
                "description": "A user",
                "role": "user",
                "permissions": []
            }
        ]"""
        validator = ConceptsValidator()
        result = validator.validate(json_content)
        assert not result.is_valid()
        assert any("invalid" in e.lower() for e in result.errors)

    def test_invalid_action_id(self):
        """Test validation catches invalid Action ID."""
        json_content = """[
            {
                "type": "Action",
                "id": "A1",
                "label": "Create",
                "description": "Create",
                "inputs": [],
                "outputs": []
            }
        ]"""
        validator = ConceptsValidator()
        result = validator.validate(json_content)
        assert not result.is_valid()

    def test_duplicate_ids(self):
        """Test validation catches duplicate IDs."""
        json_content = """[
            {
                "type": "Actor",
                "id": "A1",
                "label": "User 1",
                "description": "User 1",
                "role": "user",
                "permissions": []
            },
            {
                "type": "Actor",
                "id": "A1",
                "label": "User 2",
                "description": "User 2",
                "role": "admin",
                "permissions": []
            }
        ]"""
        validator = ConceptsValidator()
        result = validator.validate(json_content)
        assert not result.is_valid()
        assert any("duplicate" in e.lower() for e in result.errors)

    def test_missing_type_properties(self):
        """Test validation catches missing type-specific properties."""
        json_content = """[
            {
                "type": "Actor",
                "id": "A1",
                "label": "User",
                "description": "A user"
            }
        ]"""
        validator = ConceptsValidator()
        result = validator.validate(json_content)
        assert not result.is_valid()
        assert any("role" in e.lower() or "permissions" in e.lower() for e in result.errors)


class TestAggregationsValidator:
    """Tests for AggregationsValidator class."""

    def test_valid_aggregation(self):
        """Test validation of valid aggregation."""
        json_content = """[
            {
                "id": "AG1",
                "type": "CompositeActor",
                "members": ["A1", "A2"]
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
                "type": "CompositeActor",
                "members": []
            }
        ]"""
        validator = AggregationsValidator()
        result = validator.validate(json_content)
        assert not result.is_valid()

    def test_invalid_type(self):
        """Test validation catches invalid aggregation type."""
        json_content = """[
            {
                "id": "AG1",
                "type": "InvalidType",
                "members": []
            }
        ]"""
        validator = AggregationsValidator()
        result = validator.validate(json_content)
        assert not result.is_valid()
        assert any("invalid" in e.lower() for e in result.errors)

    def test_missing_members(self):
        """Test validation catches missing members."""
        json_content = """[
            {
                "id": "AG1",
                "type": "CompositeActor"
            }
        ]"""
        validator = AggregationsValidator()
        result = validator.validate(json_content)
        assert not result.is_valid()


class TestMessagesValidator:
    """Tests for MessagesValidator class."""

    def test_valid_message(self):
        """Test validation of valid message."""
        json_content = """[
            {
                "id": "MSG1",
                "type": "Command",
                "producer": "A1",
                "consumer": "A2",
                "payload": {"action": "create"}
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
                "type": "Command",
                "producer": "A1",
                "consumer": "A2",
                "payload": {}
            }
        ]"""
        validator = MessagesValidator()
        result = validator.validate(json_content)
        assert not result.is_valid()

    def test_invalid_type(self):
        """Test validation catches invalid message type."""
        json_content = """[
            {
                "id": "MSG1",
                "type": "InvalidType",
                "producer": "A1",
                "consumer": "A2",
                "payload": {}
            }
        ]"""
        validator = MessagesValidator()
        result = validator.validate(json_content)
        assert not result.is_valid()

    def test_invalid_producer_consumer(self):
        """Test validation warns on invalid producer/consumer."""
        json_content = """[
            {
                "id": "MSG1",
                "type": "Command",
                "producer": "Invalid",
                "consumer": "A2",
                "payload": {}
            }
        ]"""
        validator = MessagesValidator()
        result = validator.validate(json_content)
        # Should pass but with warnings
        assert result.is_valid()
        assert len(result.warnings) > 0


class TestRequirementsValidator:
    """Tests for RequirementsValidator class."""

    def test_valid_requirement(self):
        """Test validation of valid requirement."""
        json_content = """[
            {
                "id": "REQ-1",
                "type": "Functional",
                "statement": "The system shall authenticate users",
                "priority": "High"
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
                "type": "Functional",
                "statement": "Requirement statement",
                "priority": "High"
            }
        ]"""
        validator = RequirementsValidator()
        result = validator.validate(json_content)
        assert not result.is_valid()

    def test_invalid_type(self):
        """Test validation catches invalid requirement type."""
        json_content = """[
            {
                "id": "REQ-1",
                "type": "InvalidType",
                "statement": "Requirement statement",
                "priority": "High"
            }
        ]"""
        validator = RequirementsValidator()
        result = validator.validate(json_content)
        assert not result.is_valid()

    def test_invalid_priority(self):
        """Test validation warns on invalid priority."""
        json_content = """[
            {
                "id": "REQ-1",
                "type": "Functional",
                "statement": "Requirement statement",
                "priority": "InvalidPriority"
            }
        ]"""
        validator = RequirementsValidator()
        result = validator.validate(json_content)
        # Should pass but with warnings
        assert result.is_valid()
        assert any("priority" in w.lower() for w in result.warnings)

    def test_empty_statement(self):
        """Test validation catches empty statement."""
        json_content = """[
            {
                "id": "REQ-1",
                "type": "Functional",
                "statement": "",
                "priority": "High"
            }
        ]"""
        validator = RequirementsValidator()
        result = validator.validate(json_content)
        assert not result.is_valid()
