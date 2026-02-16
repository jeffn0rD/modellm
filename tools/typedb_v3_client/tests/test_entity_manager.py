"""Unit tests for entity_manager module"""

import pytest
from unittest.mock import Mock, MagicMock, patch
# Use absolute imports from the package
from tools.typedb_v3_client.entity_manager import EntityManager
from tools.typedb_v3_client.entities import Actor, Action, TextBlock
from tools.typedb_v3_client.client import TypeDBClient, TransactionType


class TestEntityManager:
    """Test EntityManager class."""
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock TypeDBClient."""
        return Mock(spec=TypeDBClient)
    
    @pytest.fixture
    def entity_manager(self, mock_client):
        """Create EntityManager with mock client."""
        return EntityManager(mock_client, "test_db")
    
    def test_entity_manager_creation(self, entity_manager, mock_client):
        """Test EntityManager initialization."""
        assert entity_manager.client is mock_client
        assert entity_manager.database == "test_db"
    
    def test_insert_entity(self, entity_manager, mock_client):
        """Test inserting an entity."""
        actor = Actor(
            actor_id="A1",
            id_label="User1",
            description="Test user",
            justification="For testing"
        )
        
        entity_manager.insert(actor)
        
        # Verify client.execute_query was called
        mock_client.execute_query.assert_called_once()
        call_kwargs = mock_client.execute_query.call_args
        assert call_kwargs.kwargs['database'] == "test_db"
        assert call_kwargs.kwargs['transaction_type'] == TransactionType.WRITE
        assert "insert" in call_kwargs.kwargs['query']
        assert 'actor-id "A1"' in call_kwargs.kwargs['query']
    
    def test_put_entity(self, entity_manager, mock_client):
        """Test putting an entity (idempotent)."""
        action = Action(
            action_id="ACT1",
            id_label="CreateUser",
            description="Creates a user",
            justification=""
        )
        
        entity_manager.put(action)
        
        mock_client.execute_query.assert_called_once()
        call_kwargs = mock_client.execute_query.call_args
        assert "put" in call_kwargs.kwargs['query']
        assert 'action-id "ACT1"' in call_kwargs.kwargs['query']
    
    def test_exists_returns_true(self, entity_manager, mock_client):
        """Test exists returns True when entity found."""
        mock_client.execute_query.return_value = {"answers": [{"id": "test"}]}
        
        result = entity_manager.exists(Actor, "A1")
        
        assert result is True
        mock_client.execute_query.assert_called_once()
    
    def test_exists_returns_false(self, entity_manager, mock_client):
        """Test exists returns False when entity not found."""
        mock_client.execute_query.return_value = {"answers": []}
        
        result = entity_manager.exists(Actor, "A1")
        
        assert result is False
    
    def test_delete_entity(self, entity_manager, mock_client):
        """Test deleting an entity."""
        actor = Actor(
            actor_id="A1",
            id_label="User1",
            description="",
            justification=""
        )
        
        entity_manager.delete(actor)
        
        mock_client.execute_query.assert_called_once()
        call_kwargs = mock_client.execute_query.call_args
        assert "delete" in call_kwargs.kwargs['query']
    
    def test_escape_value_string(self, entity_manager):
        """Test escaping string values."""
        result = entity_manager._escape_value('test"string')
        assert result == '"test\\"string"'
    
    def test_escape_value_integer(self, entity_manager):
        """Test escaping integer values."""
        result = entity_manager._escape_value(42)
        assert result == "42"
    
    def test_escape_value_float(self, entity_manager):
        """Test escaping float values."""
        result = entity_manager._escape_value(3.14)
        assert result == "3.14"
    
    def test_escape_value_boolean_true(self, entity_manager):
        """Test escaping boolean true."""
        result = entity_manager._escape_value(True)
        assert result == "true"
    
    def test_escape_value_boolean_false(self, entity_manager):
        """Test escaping boolean false."""
        result = entity_manager._escape_value(False)
        assert result == "false"
    
    def test_escape_value_unsupported(self, entity_manager):
        """Test escaping unsupported value type raises error."""
        with pytest.raises(ValueError, match="Unsupported value type"):
            entity_manager._escape_value([1, 2, 3])


class TestEntityManagerFetch:
    """Test EntityManager fetch methods."""
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock TypeDBClient."""
        return Mock(spec=TypeDBClient)
    
    @pytest.fixture
    def entity_manager(self, mock_client):
        """Create EntityManager with mock client."""
        return EntityManager(mock_client, "test_db")
    
    def test_fetch_one_returns_none_when_empty(self, entity_manager, mock_client):
        """Test fetch_one returns None when no results."""
        mock_client.execute_query.return_value = {"answers": []}
        
        result = entity_manager.fetch_one(Actor, {"actor-id": "A1"})
        
        assert result is None
    
    def test_fetch_all_returns_empty_list_when_empty(self, entity_manager, mock_client):
        """Test fetch_all returns empty list when no results."""
        mock_client.execute_query.return_value = {"answers": []}
        
        result = entity_manager.fetch_all(Actor)
        
        assert result == []
    
    def test_fetch_one_builds_correct_query(self, entity_manager, mock_client):
        """Test fetch_one builds correct query."""
        mock_client.execute_query.return_value = {"answers": []}
        
        entity_manager.fetch_one(Actor, {"actor-id": "A1", "id-label": "User1"})
        
        call_kwargs = mock_client.execute_query.call_args
        query = call_kwargs.kwargs['query']
        assert "match" in query
        assert "fetch" in query
        assert "actor" in query
    
    def test_fetch_all_builds_correct_query(self, entity_manager, mock_client):
        """Test fetch_all builds correct query."""
        mock_client.execute_query.return_value = {"answers": []}
        
        entity_manager.fetch_all(Actor, {"description": "test"})
        
        call_kwargs = mock_client.execute_query.call_args
        query = call_kwargs.kwargs['query']
        assert "match" in query
        assert "fetch" in query


class TestEntityManagerRelation:
    """Test EntityManager relation methods."""
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock TypeDBClient."""
        return Mock(spec=TypeDBClient)
    
    @pytest.fixture
    def entity_manager(self, mock_client):
        """Create EntityManager with mock client."""
        return EntityManager(mock_client, "test_db")
    
    def test_insert_relation_is_not_implemented(self, entity_manager):
        """Test insert_relation is not yet implemented."""
        from ..entities import Messaging, Actor, Message
        
        actor = Actor(actor_id="A1", id_label="Test", description="", justification="")
        message = Message(message_id="M1", id_label="Test", description="", justification="")
        
        messaging = Messaging(producer=actor, consumer=actor, message=message)
        
        # This should not raise but is not implemented
        entity_manager.insert_relation(messaging)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
