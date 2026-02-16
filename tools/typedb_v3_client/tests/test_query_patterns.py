"""Unit tests for query_patterns module"""

import pytest
from unittest.mock import Mock, patch
from ..query_patterns import (
    QueryPattern,
    MessagesByAction, ConceptsByAnchor, ConceptsByRequirement,
    MessagesByProducer, ActionsByAggregate, TextBlocksBySection,
    QUERY_PATTERNS
)
from ..client import TypeDBClient, TransactionType
from ..query_builder import QueryBuilder


class TestQueryPattern:
    """Test QueryPattern base class."""
    
    def test_query_pattern_requires_implementation(self):
        """Test that QueryPattern.execute raises NotImplementedError."""
        mock_client = Mock(spec=TypeDBClient)
        pattern = QueryPattern(mock_client, "test_db")
        
        with pytest.raises(NotImplementedError):
            pattern.execute()


class TestMessagesByAction:
    """Test MessagesByAction pattern."""
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock TypeDBClient."""
        return Mock(spec=TypeDBClient)
    
    @pytest.fixture
    def pattern(self, mock_client):
        """Create MessagesByAction pattern."""
        return MessagesByAction(mock_client, "test_db")
    
    def test_pattern_creation(self, pattern, mock_client):
        """Test MessagesByAction creation."""
        assert pattern.client is mock_client
        assert pattern.database == "test_db"
    
    def test_execute_builds_query(self, pattern, mock_client):
        """Test execute builds correct query."""
        mock_client.execute_query.return_value = {"answers": []}
        
        pattern.execute(action_id="ACT1")
        
        mock_client.execute_query.assert_called_once()
        call_kwargs = mock_client.execute_query.call_args
        assert call_kwargs.kwargs['database'] == "test_db"
        assert call_kwargs.kwargs['transaction_type'] == TransactionType.READ
        
        query = call_kwargs.kwargs['query']
        assert "match" in query
        assert "action" in query
        assert "message" in query
        assert "messaging" in query


class TestConceptsByAnchor:
    """Test ConceptsByAnchor pattern."""
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock TypeDBClient."""
        return Mock(spec=TypeDBClient)
    
    @pytest.fixture
    def pattern(self, mock_client):
        """Create ConceptsByAnchor pattern."""
        return ConceptsByAnchor(mock_client, "test_db")
    
    def test_pattern_creation(self, pattern, mock_client):
        """Test ConceptsByAnchor creation."""
        assert pattern.client is mock_client
        assert pattern.database == "test_db"
    
    def test_execute_builds_query(self, pattern, mock_client):
        """Test execute builds correct query."""
        mock_client.execute_query.return_value = {"answers": []}
        
        pattern.execute(anchor_id="AN1")
        
        mock_client.execute_query.assert_called_once()
        call_kwargs = mock_client.execute_query.call_args
        
        query = call_kwargs.kwargs['query']
        assert "match" in query
        assert "text-block" in query
        assert "concept" in query
        assert "anchoring" in query


class TestConceptsByRequirement:
    """Test ConceptsByRequirement pattern."""
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock TypeDBClient."""
        return Mock(spec=TypeDBClient)
    
    @pytest.fixture
    def pattern(self, mock_client):
        """Create ConceptsByRequirement pattern."""
        return ConceptsByRequirement(mock_client, "test_db")
    
    def test_pattern_creation(self, pattern, mock_client):
        """Test ConceptsByRequirement creation."""
        assert pattern.client is mock_client
        assert pattern.database == "test_db"
    
    def test_execute_builds_query(self, pattern, mock_client):
        """Test execute builds correct query."""
        mock_client.execute_query.return_value = {"answers": []}
        
        pattern.execute(requirement_id="REQ-1")
        
        mock_client.execute_query.assert_called_once()
        call_kwargs = mock_client.execute_query.call_args
        
        query = call_kwargs.kwargs['query']
        assert "match" in query
        assert "requirement" in query
        assert "concept" in query
        assert "requiring" in query


class TestMessagesByProducer:
    """Test MessagesByProducer pattern."""
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock TypeDBClient."""
        return Mock(spec=TypeDBClient)
    
    @pytest.fixture
    def pattern(self, mock_client):
        """Create MessagesByProducer pattern."""
        return MessagesByProducer(mock_client, "test_db")
    
    def test_pattern_creation(self, pattern, mock_client):
        """Test MessagesByProducer creation."""
        assert pattern.client is mock_client
        assert pattern.database == "test_db"
    
    def test_execute_builds_query(self, pattern, mock_client):
        """Test execute builds correct query."""
        mock_client.execute_query.return_value = {"answers": []}
        
        pattern.execute(actor_id="A1")
        
        mock_client.execute_query.assert_called_once()
        call_kwargs = mock_client.execute_query.call_args
        
        query = call_kwargs.kwargs['query']
        assert "match" in query
        assert "actor" in query
        assert "message" in query
        assert "messaging" in query
        assert "producer" in query


class TestActionsByAggregate:
    """Test ActionsByAggregate pattern."""
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock TypeDBClient."""
        return Mock(spec=TypeDBClient)
    
    @pytest.fixture
    def pattern(self, mock_client):
        """Create ActionsByAggregate pattern."""
        return ActionsByAggregate(mock_client, "test_db")
    
    def test_pattern_creation(self, pattern, mock_client):
        """Test ActionsByAggregate creation."""
        assert pattern.client is mock_client
        assert pattern.database == "test_db"
    
    def test_execute_builds_query(self, pattern, mock_client):
        """Test execute builds correct query."""
        mock_client.execute_query.return_value = {"answers": []}
        
        pattern.execute(aggregate_id="AG1")
        
        mock_client.execute_query.assert_called_once()
        call_kwargs = mock_client.execute_query.call_args
        
        query = call_kwargs.kwargs['query']
        assert "match" in query
        assert "action-aggregate" in query
        assert "action" in query
        assert "membership" in query


class TestTextBlocksBySection:
    """Test TextBlocksBySection pattern."""
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock TypeDBClient."""
        return Mock(spec=TypeDBClient)
    
    @pytest.fixture
    def pattern(self, mock_client):
        """Create TextBlocksBySection pattern."""
        return TextBlocksBySection(mock_client, "test_db")
    
    def test_pattern_creation(self, pattern, mock_client):
        """Test TextBlocksBySection creation."""
        assert pattern.client is mock_client
        assert pattern.database == "test_db"
    
    def test_execute_builds_query(self, pattern, mock_client):
        """Test execute builds correct query."""
        mock_client.execute_query.return_value = {"answers": []}
        
        pattern.execute(section_id="S1")
        
        mock_client.execute_query.assert_called_once()
        call_kwargs = mock_client.execute_query.call_args
        
        query = call_kwargs.kwargs['query']
        assert "match" in query
        assert "spec-section" in query
        assert "text-block" in query
        assert "outlining" in query


class TestQueryPatternsRegistry:
    """Test QUERY_PATTERNS registry."""
    
    def test_query_patterns_contains_all_patterns(self):
        """Test QUERY_PATTERNS contains all patterns."""
        expected_patterns = [
            "messages_by_action",
            "concepts_by_anchor",
            "concepts_by_requirement",
            "messages_by_producer",
            "actions_by_aggregate",
            "text_blocks_by_section"
        ]
        
        for pattern_name in expected_patterns:
            assert pattern_name in QUERY_PATTERNS
    
    def test_query_patterns_returns_correct_classes(self):
        """Test QUERY_PATTERNS returns correct classes."""
        assert QUERY_PATTERNS["messages_by_action"] == MessagesByAction
        assert QUERY_PATTERNS["concepts_by_anchor"] == ConceptsByAnchor
        assert QUERY_PATTERNS["concepts_by_requirement"] == ConceptsByRequirement
        assert QUERY_PATTERNS["messages_by_producer"] == MessagesByProducer
        assert QUERY_PATTERNS["actions_by_aggregate"] == ActionsByAggregate
        assert QUERY_PATTERNS["text_blocks_by_section"] == TextBlocksBySection
    
    def test_can_instantiate_from_registry(self):
        """Test patterns can be instantiated from registry."""
        mock_client = Mock(spec=TypeDBClient)
        
        for pattern_class in QUERY_PATTERNS.values():
            pattern = pattern_class(mock_client, "test_db")
            assert pattern.client is mock_client
            assert pattern.database == "test_db"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
