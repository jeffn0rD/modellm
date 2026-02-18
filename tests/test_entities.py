"""Unit tests for entities module"""

import pytest
# Use absolute imports from the package
from typedb_client3.entities import (
    Entity, Relation,
    Actor, Action, Message, DataEntity, Requirement,
    ActionAggregate, MessageAggregate, Constraint, Category,
    TextBlock, Concept, SpecDocument, SpecSection,
    Messaging, Anchoring, Membership, MembershipSeq,
    Outlining, Categorization, Requiring, ConstrainedBy,
    MessagePayload, Filesystem
)


class TestEntity:
    """Test Entity base class."""
    
    def test_entity_base_class_attributes(self):
        """Test that Entity has default class attributes."""
        assert Entity._type == ""
        assert Entity._key_attr is None
    
    def test_actor_entity_attributes(self):
        """Test Actor entity attributes."""
        assert Actor._type == "actor"
        assert Actor._key_attr == "actor-id"
    
    def test_action_entity_attributes(self):
        """Test Action entity attributes."""
        assert Action._type == "action"
        assert Action._key_attr == "action-id"
    
    def test_message_entity_attributes(self):
        """Test Message entity attributes."""
        assert Message._type == "message"
        assert Message._key_attr == "message-id"
    
    def test_data_entity_attributes(self):
        """Test DataEntity entity attributes."""
        assert DataEntity._type == "data-entity"
        assert DataEntity._key_attr == "data-entity-id"
    
    def test_requirement_entity_attributes(self):
        """Test Requirement entity attributes."""
        assert Requirement._type == "requirement"
        assert Requirement._key_attr == "requirement-id"
    
    def test_action_aggregate_attributes(self):
        """Test ActionAggregate entity attributes."""
        assert ActionAggregate._type == "action-aggregate"
        assert ActionAggregate._key_attr == "action-agg-id"
    
    def test_message_aggregate_attributes(self):
        """Test MessageAggregate entity attributes."""
        assert MessageAggregate._type == "message-aggregate"
        assert MessageAggregate._key_attr == "message-agg-id"
    
    def test_constraint_attributes(self):
        """Test Constraint entity attributes."""
        assert Constraint._type == "constraint"
        assert Constraint._key_attr == "constraint-id"
    
    def test_category_attributes(self):
        """Test Category entity attributes."""
        assert Category._type == "category"
        assert Category._key_attr == "name"
    
    def test_text_block_attributes(self):
        """Test TextBlock entity attributes."""
        assert TextBlock._type == "text-block"
        assert TextBlock._key_attr == "anchor-id"
    
    def test_concept_attributes(self):
        """Test Concept entity attributes."""
        assert Concept._type == "concept"
        assert Concept._key_attr == "concept-id"
    
    def test_spec_document_attributes(self):
        """Test SpecDocument entity attributes."""
        assert SpecDocument._type == "spec-document"
        assert SpecDocument._key_attr == "spec-doc-id"
    
    def test_spec_section_attributes(self):
        """Test SpecSection entity attributes."""
        assert SpecSection._type == "spec-section"
        assert SpecSection._key_attr == "spec-section-id"


class TestActorEntity:
    """Test Actor entity operations."""
    
    def test_actor_creation(self):
        """Test creating an Actor instance."""
        actor = Actor(
            actor_id="A1",
            id_label="User1",
            description="Test actor",
            justification="For testing"
        )
        assert actor.actor_id == "A1"
        assert actor.id_label == "User1"
        assert actor.description == "Test actor"
        assert actor.justification == "For testing"
    
    def test_actor_get_key_value(self):
        """Test getting key value from Actor."""
        actor = Actor(
            actor_id="A1",
            id_label="User1",
            description="Test",
            justification=""
        )
        assert actor.get_key_value() == "A1"
    
    def test_actor_to_insert_query(self):
        """Test generating INSERT query for Actor."""
        actor = Actor(
            actor_id="A1",
            id_label="User1",
            description="Test actor",
            justification="For testing"
        )
        query = actor.to_insert_query()
        assert "$a isa actor" in query
        assert 'has actor-id "A1"' in query
        assert 'has id-label "User1"' in query
        assert 'has description "Test actor"' in query
    
    def test_actor_to_match_query(self):
        """Test generating MATCH query for Actor."""
        actor = Actor(
            actor_id="A1",
            id_label="User1",
            description="Test",
            justification=""
        )
        query = actor.to_match_query()
        assert "match $a isa actor" in query
        assert 'has actor-id "A1"' in query


class TestActionEntity:
    """Test Action entity operations."""
    
    def test_action_creation(self):
        """Test creating an Action instance."""
        action = Action(
            action_id="ACT1",
            id_label="CreateUser",
            description="Creates a user",
            justification="For user management"
        )
        assert action.action_id == "ACT1"
        assert action.id_label == "CreateUser"
    
    def test_action_get_key_value(self):
        """Test getting key value from Action."""
        action = Action(
            action_id="ACT1",
            id_label="CreateUser",
            description="",
            justification=""
        )
        assert action.get_key_value() == "ACT1"
    
    def test_action_to_insert_query(self):
        """Test generating INSERT query for Action."""
        action = Action(
            action_id="ACT1",
            id_label="CreateUser",
            description="Creates a user",
            justification=""
        )
        query = action.to_insert_query()
        assert "$a isa action" in query
        assert 'has action-id "ACT1"' in query


class TestTextBlockEntity:
    """Test TextBlock entity operations."""
    
    def test_text_block_creation(self):
        """Test creating a TextBlock instance."""
        tb = TextBlock(
            anchor_id="AN1",
            id_label="Goal1",
            anchor_type="goal",
            text="This is a goal",
            order=1
        )
        assert tb.anchor_id == "AN1"
        assert tb.order == 1
    
    def test_text_block_get_key_value(self):
        """Test getting key value from TextBlock."""
        tb = TextBlock(
            anchor_id="AN1",
            id_label="Goal1",
            anchor_type="goal",
            text="",
            order=0
        )
        assert tb.get_key_value() == "AN1"
    
    def test_text_block_to_insert_query(self):
        """Test generating INSERT query for TextBlock."""
        tb = TextBlock(
            anchor_id="AN1",
            id_label="Goal1",
            anchor_type="goal",
            text="Test text",
            order=1
        )
        query = tb.to_insert_query()
        assert "$t isa text-block" in query
        assert 'has anchor-id "AN1"' in query
        assert "has order 1" in query


class TestEntityEscapeValues:
    """Test value escaping in entities."""
    
    def test_escape_string(self):
        """Test string escaping."""
        actor = Actor(
            actor_id='A1',
            id_label='Test',
            description='He said "hello"',
            justification=''
        )
        query = actor.to_insert_query()
        assert '\\"hello\\"' in query
    
    def test_escape_backslash(self):
        """Test backslash escaping."""
        actor = Actor(
            actor_id='A1',
            id_label='Test',
            description='Path: C:\\test',
            justification=''
        )
        query = actor.to_insert_query()
        assert 'C:\\\\test' in query
    
    def test_escape_integer(self):
        """Test integer escaping."""
        tb = TextBlock(
            anchor_id="AN1",
            id_label="Test",
            anchor_type="goal",
            text="",
            order=42
        )
        query = tb.to_insert_query()
        assert "has order 42" in query
    
    def test_escape_boolean_true(self):
        """Test boolean true escaping."""
        # We don't have boolean fields in current entities
        # But test the base method
        actor = Actor(
            actor_id="A1",
            id_label="Test",
            description="",
            justification=""
        )
        # Boolean should lowercase
        assert actor._escape_value(True) == "true"
        assert actor._escape_value(False) == "false"


class TestRelationClasses:
    """Test Relation classes."""
    
    def test_messaging_relation(self):
        """Test Messaging relation attributes."""
        assert Messaging._type == "messaging"
        assert Messaging._roles == ["producer", "consumer", "message"]
    
    def test_anchoring_relation(self):
        """Test Anchoring relation attributes."""
        assert Anchoring._type == "anchoring"
        assert Anchoring._roles == ["anchor", "concept"]
    
    def test_membership_relation(self):
        """Test Membership relation attributes."""
        assert Membership._type == "membership"
        assert Membership._roles == ["member-of", "member"]
    
    def test_outlining_relation(self):
        """Test Outlining relation attributes."""
        assert Outlining._type == "outlining"
        assert Outlining._roles == ["section", "subsection"]
    
    def test_categorization_relation(self):
        """Test Categorization relation attributes."""
        assert Categorization._type == "categorization"
        assert Categorization._roles == ["category", "object"]
    
    def test_requiring_relation(self):
        """Test Requiring relation attributes."""
        assert Requiring._type == "requiring"
        assert Requiring._roles == ["required-by", "conceptualized-as"]
    
    def test_constrained_by_relation(self):
        """Test ConstrainedBy relation attributes."""
        assert ConstrainedBy._type == "constrained-by"
        assert ConstrainedBy._roles == ["constraint", "object"]
    
    def test_message_payload_relation(self):
        """Test MessagePayload relation attributes."""
        assert MessagePayload._type == "message-payload"
        assert MessagePayload._roles == ["message", "payload"]
    
    def test_filesystem_relation(self):
        """Test Filesystem relation attributes."""
        assert Filesystem._type == "filesystem"
        assert Filesystem._roles == ["folder", "entry"]
    
    def test_relation_to_insert_query(self):
        """Test Relation to_insert_query method."""
        actor = Actor(actor_id="A1", id_label="Test", description="", justification="")
        
        messaging = Messaging(
            producer=actor,
            consumer=actor,
            message=Message(message_id="M1", id_label="Test", description="", justification="")
        )
        
        variables = {
            "producer": "p",
            "consumer": "c",
            "message": "m"
        }
        
        query = messaging.to_insert_query(variables)
        assert "(producer: $p, consumer: $c, message: $m) isa messaging;" == query


class TestEntityNoKeyAttr:
    """Test Entity behavior without key attribute."""
    
    def test_entity_without_key_raises_on_get_key_value(self):
        """Test that getting key value raises without key attr."""
        # Entity base class has no key attr
        entity = Entity()
        with pytest.raises(ValueError, match="No key attribute"):
            entity.get_key_value()
    
    def test_entity_without_key_raises_on_match_query(self):
        """Test that match query raises without key attr."""
        entity = Entity()
        with pytest.raises(ValueError, match="No key attribute"):
            entity.to_match_query()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
