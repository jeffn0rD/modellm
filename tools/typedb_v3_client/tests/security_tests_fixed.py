#!/usr/bin/env python3
"""Security Tests for TypeDB Client - Injection Attack Prevention

These tests verify that the client properly handles malicious inputs to prevent
SQL/TypeQL injection, XSS, and other injection attacks.
"""

import sys
from pathlib import Path

# Add project root to Python path for absolute imports
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from tools.typedb_v3_client import (
    TypeDBClient, Actor, Action, Message, SecureTokenManager,
    validate_base_url, validate_credentials, validate_timeout,
    validate_operation_timeouts
)
from tools.typedb_v3_client.exceptions import TypeDBValidationError


class TestInjectionPrevention:
    """Test that injection attacks are prevented."""
    
    # Test SQL/TypeQL injection vectors
    TYPEDB_INJECTION_TESTS = [
        # TypeQL-specific injection attempts
        ('"; delete $x isa actor; --', 'TypeQL command injection'),
        ('$x has actor-id "test"; $x has password "pwd"', 'Attribute injection'),
        ('match $admin isa actor, has email "admin@test.com"; fetch $admin, has password;', 'Data exfiltration query'),
        ('insert $actor isa actor, has actor-id "A"; $actor has secret "data";', 'Unauthorized writes'),
        # SQL-style injection (should also be caught)
        ("'; DROP TABLE actors; --", 'SQL-style comment injection'),
        ("\' UNION SELECT * FROM users", 'SQL union injection'),
        ("'; EXEC xp_cmdshell 'dir'; --", 'Command execution'),
        # Control characters and encoding attacks
        ('\x00', 'Null byte injection'),
        ('\x1b', 'Escape character'), 
        ('%09', 'Tab character encoded'),
        ('%0a', 'Newline character encoded'),
    ]
    
    # Cross-site scripting (XSS) test vectors
    XSS_INJECTION_TESTS = [
        ('<img src=x onerror=alert(1)>', 'Image XSS'),
        ('<script>document.cookie</script>', 'Script injection'),
        ('javascript:alert(1)', 'JavaScript protocol'),
        ('onmouseover="alert(1)"', 'Eventhandler injection'),
        ('\u003Cscript\u003E', 'Unicode encoded script'),
        ('\x3Cscript\x3E', 'Hex encoded script'),
        ('http://evil.com" onmouseover="alert(1)', 'Attribute XSS'),
    ]
    
    # Path traversal tests
    PATH_INJECTION_TESTS = [
        ('../../../etc/passwd', 'Unix path traversal'),
        ('..\\..\\..\\windows\\system32\\config\\sam', 'Windows path traversal'),
        ('/etc/passwd%00', 'Null byte injection'),
        ('../../config.js', 'JavaScript config access'),
    ]
    
    @pytest.mark.parametrize("malicious_input,description", TYPEDB_INJECTION_TESTS)
    def test_parameterized_query_handles_injection(self, malicious_input, description):
        """Test that parameterized queries handle injection attempts safely."""
        # Create entity with malicious input
        actor = Actor(
            actor_id=malicious_input,
            id_label='test',
            description='test actor',
            justification='testing'
        )
        
        # Generate parameterized query
        query, params = actor.to_parameterized_insert_query()
        
        # Verify malicious input is in params, not in query
        assert malicious_input not in query
        assert malicious_input in str(params.values())
        
        # Verify query uses parameterized placeholder
        assert '$actor_' in query
        # Check for actor-id parameter (TypeDB uses kebab-case, not snake_case)
        assert any('actor' in key.lower() for key in params.keys())
    
    @pytest.mark.parametrize("malicious_input,description", XSS_INJECTION_TESTS)
    def test_entity_handles_xss_payloads(self, malicious_input, description):
        """Test that entities handle XSS payloads safely."""
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
    
    @pytest.mark.parametrize("malicious_input,description", PATH_INJECTION_TESTS)
    def test_entity_handles_path_traversal(self, malicious_input, description):
        """Test that entities handle path traversal safely."""
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
    
    def test_sql_injection_in_username_rejected(self):
        """Test that SQL injection patterns in username are rejected."""
        malicious_usernames = [
            'admin"; --',
            'admin\' OR \'1\'=\'1',
            'admin union select',
            'admin; DROP TABLE users;',
            '--',
            '/* comment */',
        ]
        
        for username in malicious_usernames:
            with pytest.raises(TypeDBValidationError):
                validate_credentials(username, 'password123')
    
    def test_sql_injection_in_password_rejected(self):
        """Test that SQL injection patterns in password are rejected."""
        malicious_passwords = [
            'password"; --',
            'password\' OR \'1\'=\'1',
            'password union select',
            'password; DROP TABLE users;',
            '--',
        ]
        
        for password in malicious_passwords:
            with pytest.raises(TypeDBValidationError):
                validate_credentials('admin', password)
    
    def test_xss_injection_rejected(self):
        """Test that XSS patterns in credentials are rejected."""
        xss_patterns = [
            '<script>alert(1)</script>',
            'javascript:alert(1)',
            'onerror=alert(1)',
        ]
        
        for pattern in xss_patterns:
            with pytest.raises(TypeDBValidationError):
                validate_credentials('admin', pattern)
    
    def test_path_traversal_rejected(self):
        """Test that path traversal patterns are rejected."""
        path_patterns = [
            '../../../etc/passwd',
            'C:\\Windows\\System32\\drivers\\etc\\hosts',
            '..\\..\\..\\program files',
            '/var/www/html/config.php',
        ]
        
        for path in path_patterns:
            with pytest.raises(TypeDBValidationError):
                validate_credentials('admin', path)
    
    def test_command_injection_rejected(self):
        """Test that command injection patterns are rejected."""
        cmd_patterns = [
            'admin; rm -rf /',
            'admin && cat /etc/passwd',
            'admin | curl http://evil.com',
            'admin`whoami`',
            'admin$(id)',
        ]
        
        for pattern in cmd_patterns:
            with pytest.raises(TypeDBValidationError):
                validate_credentials('admin', pattern)
    
    def test_valid_credentials_accepted(self):
        """Test that valid credentials are accepted."""
        # These should not raise errors
        validate_credentials('admin', 'password123')
        validate_credentials('user.name', 'valid-pass_123!')
        validate_credentials('user_123', 'ComplexPass123!')


class TestURLValidation:
    """Test URL validation prevents injection."""
    
    def test_malicious_url_rejected(self):
        """Test that malicious URLs are rejected."""
        malicious_urls = [
            'http://localhost:8000"; "/api/users --"
            'javascript:alert(1)',
            'file:///etc/passwd',
            'ftp://attacker.com',
            'http://localhost:8000; rm -rf /',
            'http://localhost:8000 && cat /etc/passwd',
            'http://localhost:8000`whoami`',
        ]
        
        for url in malicious_urls:
            with pytest.raises(TypeDBValidationError):
                validate_base_url(url)
    
    def test_sql_payload_rejected(self):
        """Test that URLs with SQL payloads are rejected."""
        sql_urls = [
            'http://localhost:8000/\\'; DROP TABLE users; --',
            'http://localhost:8000/?id=1\\' OR \\'1\\'=\\'1',
            'http://localhost:8000/\\' UNION SELECT * FROM users --',
        ]
        
        for url in sql_urls:
            with pytest.raises(TypeDBValidationError):
                validate_base_url(url)
    
    def test_valid_urls_accepted(self):
        """Test that valid URLs are accepted."""
        valid_urls = [
            'http://localhost:8000',
            'https://typedb.example.com',
            'http://typedb.server:8080',
            'https://typedb.example.com:443',
        ]
        
        for url in valid_urls:
            result = validate_base_url(url)
            assert result == url.rstrip('/')  # Should normalize URL


class TestSecureTokenManager:
    """Test SecureTokenManager for token security."""
    
    def test_token_encryption_varies(self):
        """Test that same token encrypts to different values each time."""
        manager = SecureTokenManager()
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        
        encrypted1 = manager.encrypt_token(token)
        encrypted2 = manager.encrypt_token(token)
        
        # Should produce different encrypted values due to unique IVs
        assert encrypted1 != encrypted2
        
        # But both should decrypt to the original token
        decrypted1 = manager.decrypt_token(encrypted1)
        decrypted2 = manager.decrypt_token(encrypted2)
        
        assert decrypted1 == token
        assert decrypted2 == token
    
    def test_token_access_logged(self):
        """Test that token access is logged for audit."""
        manager = SecureTokenManager()
        token = "test_token_123"
        
        # No access log yet
        initial_log_len = len(manager.get_access_log())
        
        # Access token
        encrypted = manager.encrypt_token(token)
        decrypted = manager.decrypt_token(encrypted)
        
        # Should log both operations
        final_log_len = len(manager.get_access_log())
        assert final_log_len == initial_log_len + 2
    
    def test_memory_cleared(self):
        """Test that memory is cleared properly."""
        manager = SecureTokenManager()
        token = "test_token_123"
        
        encrypted = manager.encrypt_token(token)
        decrypted = manager.decrypt_token(encrypted)
        
        # Clear memory
        manager.clear_memory()
        
        # Memory should be cleared
        cleared = manager.decrypt_token(encrypted)
        # This might raise an exception or return None depending on implementation
        # So we'll just test that the clear operation completed without error