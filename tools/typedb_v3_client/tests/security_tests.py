#!/usr/bin/env python3
"""Security Tests for TypeDB Client - Injection Attack Prevention"""

import sys
from pathlib import Path

# Add project root to Python path for absolute imports
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest
from tools.typedb_v3_client import (
    TypeDBClient, Actor, SecureTokenManager,
    validate_base_url, validate_credentials, validate_timeout,
    validate_operation_timeouts
)
from tools.typedb_v3_client.exceptions import TypeDBValidationError


class TestInjectionPrevention:
    """Test that injection attacks are prevented."""
    
    # Test SQL/TypeQL injection vectors
    TYPEDB_INJECTION_TESTS = [
        ('"; delete $x isa actor; --', 'TypeQL command injection'),
        ('$x has actor-id \"test\"; $x has password \"pwd\"', 'Attribute injection'),
        ('match $admin isa actor, has email \"admin@test.com\"; fetch $admin, has password;', 'Data exfiltration query'),
        ('insert $actor isa actor, has actor-id \"A\"; $actor has secret \"data\";', 'Unauthorized writes'),
        ("'\"; DROP TABLE actors; --", 'SQL-style comment injection'),
        ("'\" UNION SELECT * FROM users", 'SQL union injection'),
        ('\\x00', 'Null byte injection'),
    ]
    
    # Cross-site scripting (XSS) test vectors
    XSS_INJECTION_TESTS = [
        ('<img src=x onerror=alert(1)>', 'Image XSS'),
        ('<script>document.cookie</script>', 'Script injection'),
        ('javascript:alert(1)', 'JavaScript protocol'),
        ('onmouseover="\"alert(1)"', 'Eventhandler injection'),
    ]
    
    # Path traversal tests
    PATH_INJECTION_TESTS = [
        ('../../../etc/passwd', 'Unix path traversal'),
        ('../\\../\\../\\windows\\system32\\config\\sam', 'Windows path traversal'),
        ('/etc/passwd\\x00', 'Null byte injection'),
        ('../../config.js', 'JavaScript config access'),
    ]
    
    def test_parameterized_query_handles_injection(self):
        """Test that parameterized queries handle injection attempts safely."""
        malicious_input = '"; delete $x isa actor; --'
        
        actor = Actor(
            actor_id=malicious_input,
            id_label='test',
            description='test actor',
            justification='testing'
        )
        
        query, params = actor.to_parameterized_insert_query()
        
        # Verify malicious input is in params, not in query
        assert malicious_input not in query
        assert malicious_input in str(params.values())
        
        # Verify query uses parameterized placeholder
        assert '$actor_' in query
        # Check for actor-related parameter
        assert any('actor' in key.lower() for key in params.keys())
    
    def test_entity_handles_xss_payloads(self):
        """Test that entities handle XSS payloads safely."""
        malicious_input = '<script>alert(1)</script>'
        
        actor = Actor(
            actor_id='test',
            id_label=malicious_input,
            description='test',
            justification='test'
        )
        
        query, params = actor.to_parameterized_insert_query()
        
        # XSS payload should be in params, not in query string
        assert malicious_input not in query
        assert malicious_input in str(params.values())
    
    def test_entity_handles_path_traversal(self):
        """Test that entities handle path traversal safely."""
        malicious_input = '../../../etc/passwd'
        
        actor = Actor(
            actor_id='test',
            id_label='test',
            description=malicious_input,
            justification='test'
        )
        
        query, params = actor.to_parameterized_insert_query()
        
        # Path should be in params, not directly in query
        assert malicious_input not in query
        assert malicious_input in str(params.values())


class TestCredentialValidation:
    """Test credential validation prevents injection."""
    
    def test_sql_injection_rejected(self):
        """Test that SQL injection patterns are rejected."""
        malicious_inputs = [
            'admin"; --',
            "admin' OR '1'='1",
            'admin union select',
            'admin; DROP TABLE users;',
            '--',
        ]
        
        for input_val in malicious_inputs:
            with pytest.raises(TypeDBValidationError):
                validate_credentials(input_val, 'password123')
    
    def test_xss_injection_rejected(self):
        """Test that XSS patterns are rejected."""
        xss_patterns = [
            '<script>alert(1)</script>',
            'javascript:alert(1)',
            'onerror=alert(1)',
        ]
        
        for pattern in xss_patterns:
            with pytest.raises(TypeDBValidationError):
                validate_credentials('admin', pattern)
    
    def test_valid_credentials_accepted(self):
        """Test that valid credentials are accepted."""
        # These should not raise errors
        validate_credentials('admin', 'password123')
        validate_credentials('user_123', 'ComplexPass123!')


class TestURLValidation:
    """Test URL validation prevents injection."""
    
    def test_malicious_url_rejected(self):
        """Test that malicious URLs are rejected."""
        malicious_urls = [
            'javascript:alert(1)',
            'file:///etc/passwd',
            'ftp://attacker.com',
        ]
        
        for url in malicious_urls:
            with pytest.raises(TypeDBValidationError):
                validate_base_url(url)


class TestSecureTokenManager:
    """Test SecureTokenManager for token security."""
    
    def test_token_encryption_varies(self):
        """Test that same token encrypts to different values each time."""
        manager = SecureTokenManager()
        token = "test_token_123"
        
        encrypted1 = manager.store_token(token)
        encrypted2 = manager.store_token(token)
        
        # Should produce different encrypted values due to unique IVs
        assert encrypted1 != encrypted2
        
        # But both should decrypt to the original token
        decrypted1 = manager.retrieve_token(encrypted1)
        decrypted2 = manager.retrieve_token(encrypted2)
        
        assert decrypted1 == token
        assert decrypted2 == token


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])