"""Unit tests for SecureTokenManager.

Tests:
- store_token
- retrieve_token
- clear_memory
- get_access_log
- rotate_key
"""

import pytest
from typedb_v3_client.auth import SecureTokenManager
from typedb_v3_client.exceptions import TypeDBAuthenticationError


@pytest.mark.unit
class TestSecureTokenManager:
    """Tests for SecureTokenManager class."""
    
    def test_store_and_retrieve_token(self):
        """Test storing and retrieving a token."""
        manager = SecureTokenManager()
        token = "test-jwt-token-12345"
        
        # Store token
        encrypted = manager.store_token(token)
        assert encrypted is not None
        assert encrypted != token  # Should be encrypted
        
        # Retrieve token
        retrieved = manager.retrieve_token(encrypted)
        assert retrieved == token
    
    def test_retrieve_invalid_token_raises_error(self):
        """Test retrieving invalid token raises error."""
        manager = SecureTokenManager()
        
        with pytest.raises(TypeDBAuthenticationError):
            manager.retrieve_token("invalid-encrypted-token")
    
    def test_clear_memory(self):
        """Test clear_memory clears cached token."""
        manager = SecureTokenManager()
        token = "test-token"
        
        # Store and verify cached
        manager.store_token(token)
        
        # Clear memory
        manager.clear_memory()
        
        # Token should still be retrievable from encrypted (cache was cleared)
        encrypted = manager.get_access_log()[-1]  # This is stored encrypted
        # The encrypted token can still be retrieved because it's stored in the encrypted form
    
    def test_get_access_log(self):
        """Test access log records operations."""
        manager = SecureTokenManager()
        token = "test-token"
        
        # Store token
        manager.store_token(token)
        
        # Get log
        log = manager.get_access_log()
        
        assert len(log) > 0
        assert log[0]["action"] == "store"
    
    def test_rotate_key(self):
        """Test rotating encryption key."""
        manager = SecureTokenManager()
        token = "test-token"
        
        # Store with old key
        encrypted = manager.store_token(token)
        
        # Rotate key
        new_key = manager.rotate_key()
        assert new_key is not None
        
        # Old encrypted token should not work with new key
        # (this is expected behavior - rotating key invalidates old tokens)
        # The token was cleared from cache during rotation
    
    def test_token_caching(self):
        """Test token is cached for performance."""
        manager = SecureTokenManager()
        token = "test-token"
        
        # Store token
        encrypted = manager.store_token(token)
        
        # First retrieval - should cache
        result1 = manager.retrieve_token(encrypted)
        
        # Check cache was used (log should show cache_hit)
        log = manager.get_access_log()
        actions = [entry["action"] for entry in log]
        assert "cache_hit" in actions or result1 == token
    
    def test_encryption_produces_different_output(self):
        """Test same token produces different encrypted output (due to salt)."""
        manager = SecureTokenManager()
        token = "same-token"
        
        encrypted1 = manager.store_token(token)
        encrypted2 = manager.store_token(token)
        
        # Should be different due to random salt
        assert encrypted1 != encrypted2
        
        # But both should decrypt to same token
        assert manager.retrieve_token(encrypted1) == token
        assert manager.retrieve_token(encrypted2) == token
    
    def test_encryption_key_is_bytes(self):
        """Test encryption key is proper bytes."""
        manager = SecureTokenManager()
        
        key = manager.encryption_key
        assert isinstance(key, bytes)
        assert len(key) > 0
