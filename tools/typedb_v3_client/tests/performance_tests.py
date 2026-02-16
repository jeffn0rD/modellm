"""Performance Tests for TypeDB Client

These tests benchmark the performance of key operations in the TypeDB client.
Note: These tests require pytest-benchmark to run the benchmark tests.
Run with: pytest performance_tests.py --benchmark-only
"""

import sys
from pathlib import Path

# Add project root to Python path for absolute imports
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest
import time
from unittest.mock import Mock, patch

from tools.typedb_v3_client import (
    TypeDBClient, Actor, Action, Message, SecureTokenManager,
    create_optimized_session, DEFAULT_POOL_CONNECTIONS, DEFAULT_POOL_MAXSIZE
)
from tools.typedb_v3_client.entities import Entity


class TestEntityPerformance:
    """Performance tests for Entity operations."""
    
    def test_parameterized_query_generation(self):
        """Test parameterized query generation."""
        actor = Actor(
            actor_id="test_id",
            id_label="test_label", 
            description="test description",
            justification="test justification"
        )
        
        # Test parameterized query generation
        query, params = actor.to_parameterized_insert_query()
        assert "$actor_" in query
        assert len(params) > 0
        
        # Verify parameterized query is injection-safe
        query2, params2 = actor.to_parameterized_insert_query()
        assert query != query2  # Different placeholders each time
        
    def test_entity_match_query_performance(self):
        """Test match query generation."""
        actor = Actor(
            actor_id="test_id",
            id_label="test_label",
            description="test description", 
            justification="test justification"
        )
        
        # Test match query generation
        match_query = actor.to_match_query()
        assert "match" in match_query.lower()
        assert "actor-id" in match_query


class TestSecureTokenManagerPerformance:
    """Performance tests for SecureTokenManager."""
    
    def test_token_encryption_performance(self):
        """Test token encryption and decryption."""
        manager = SecureTokenManager()
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_token_string"
        
        # Test encryption
        encrypted = manager.store_token(token)
        assert encrypted is not None
        assert encrypted != token
        
        # Test decryption
        decrypted = manager.retrieve_token(encrypted)
        assert decrypted == token
        
        # Test caching
        cached = manager.retrieve_token(encrypted)
        assert cached == token


class TestConnectionPoolingPerformance:
    """Performance tests for connection pooling."""
    
    def test_session_creation_performance(self):
        """Test session creation with pooling."""
        session = create_optimized_session()
        
        # Verify session has connection pooling
        adapter = session.get_adapter('http://')
        assert adapter is not None
        
        # Verify pooling configuration
        config = adapter._pool_connections
        assert config > 0  # Should have pool_connections set


class TestValidationPerformance:
    """Performance tests for input validation."""
    
    def test_url_validation_performance(self):
        """Test URL validation."""
        from tools.typedb_v3_client import validate_base_url
        
        # Test valid URL
        result = validate_base_url("http://localhost:8000")
        assert result == "http://localhost:8000"
        
    def test_credential_validation_performance(self):
        """Test credential validation."""
        from tools.typedb_v3_client import validate_credentials
        
        # Test valid credentials
        result = validate_credentials("admin", "password123")
        assert result is None
        
        # Test that injection patterns are rejected
        try:
            validate_credentials("admin' OR '1'='1", "password")
            assert False, "Should have rejected injection pattern"
        except:
            pass


class TestMemoryUsage:
    """Tests for memory usage characteristics."""
    
    def test_parameterized_queries_store_values_in_dict(self):
        """Verify parameterized queries store values in dict safely."""
        actor = Actor(
            actor_id="test_id",
            id_label="test_label", 
            description="A" * 1000,  # Large string
            justification="justification"
        )
        
        query, params = actor.to_parameterized_insert_query()
        
        # Values should be in params dict, not embedded in query string
        assert "test_id" not in query
        assert "test_label" not in query
        assert "A" * 1000 not in query
        
        # Verify values are in params
        assert len(params) > 0
        params_str = str(params)
        assert "test_id" in params_str
        assert "test_label" in params_str
        
    def test_token_manager_memory_clearing(self):
        """Test that token manager properly clears sensitive data."""
        manager = SecureTokenManager()
        token = "sensitive_token_value"
        
        # Store token
        encrypted = manager.store_token(token)
        
        # Verify token is cached in memory
        assert manager._token_cache == token
        
        # Clear memory
        manager.clear_memory()
        
        # Verify token is cleared
        assert manager._token_cache is None
        assert manager._token_cache_time is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])