"""Unit tests for validation functions.

Tests:
- validate_base_url
- validate_credentials
- validate_timeout
- validate_operation_timeouts
"""

import pytest
from typedb_v3_client.validation import (
    validate_base_url,
    validate_credentials,
    validate_timeout,
    validate_operation_timeouts,
)
from typedb_v3_client.exceptions import TypeDBValidationError


@pytest.mark.unit
class TestValidateBaseUrl:
    """Tests for validate_base_url function."""
    
    def test_valid_http_url(self):
        """Test valid HTTP URL is accepted."""
        result = validate_base_url("http://localhost:8000")
        assert result == "http://localhost:8000"
    
    def test_valid_https_url(self):
        """Test valid HTTPS URL is accepted."""
        result = validate_base_url("https://example.com:8080")
        assert result == "https://example.com:8080"
    
    def test_url_without_scheme(self):
        """Test URL without scheme gets http:// added."""
        result = validate_base_url("localhost:8000")
        assert result == "http://localhost:8000"
    
    def test_url_without_trailing_slash(self):
        """Test trailing slash is removed."""
        result = validate_base_url("http://localhost:8000/")
        assert result == "http://localhost:8000"
    
    def test_empty_url_raises_error(self):
        """Test empty URL raises TypeDBValidationError."""
        with pytest.raises(TypeDBValidationError) as exc:
            validate_base_url("")
        assert "cannot be empty" in str(exc.value).lower()
    
    def test_invalid_scheme_raises_error(self):
        """Test invalid scheme raises TypeDBValidationError."""
        with pytest.raises(TypeDBValidationError) as exc:
            validate_base_url("ftp://localhost:8000")
        assert "invalid" in str(exc.value).lower()
    
    def test_javascript_injection_raises_error(self):
        """Test JavaScript injection raises error."""
        with pytest.raises(TypeDBValidationError) as exc:
            validate_base_url("javascript:alert(1)")
        assert "invalid url protocol" in str(exc.value).lower()
    
    def test_file_protocol_raises_error(self):
        """Test file:// protocol raises error."""
        with pytest.raises(TypeDBValidationError):
            validate_base_url("file:///etc/passwd")


@pytest.mark.unit
class TestValidateCredentials:
    """Tests for validate_credentials function."""
    
    def test_valid_credentials(self):
        """Test valid username and password are accepted."""
        validate_credentials("admin", "password")
    
    def test_both_none_allowed(self):
        """Test None/None is allowed for anonymous access."""
        validate_credentials(None, None)
    
    def test_username_only_raises_error(self):
        """Test username without password raises error."""
        with pytest.raises(TypeDBValidationError) as exc:
            validate_credentials("admin", None)
        assert "must be provided together" in str(exc.value).lower()
    
    def test_password_only_raises_error(self):
        """Test password without username raises error."""
        with pytest.raises(TypeDBValidationError) as exc:
            validate_credentials(None, "password")
        assert "must be provided together" in str(exc.value).lower()
    
    def test_empty_username_raises_error(self):
        """Test empty username raises error."""
        with pytest.raises(TypeDBValidationError) as exc:
            validate_credentials("", "password")
        assert "between 1 and 128" in str(exc.value).lower()
    
    def test_empty_password_raises_error(self):
        """Test empty password raises error."""
        with pytest.raises(TypeDBValidationError) as exc:
            validate_credentials("admin", "")
        assert "between 1 and 128" in str(exc.value).lower()
    
    def test_username_too_long_raises_error(self):
        """Test username over 128 chars raises error."""
        with pytest.raises(TypeDBValidationError) as exc:
            validate_credentials("a" * 129, "password")
        assert "between 1 and 128" in str(exc.value).lower()
    
    def test_sql_injection_raises_error(self):
        """Test SQL injection pattern raises error."""
        with pytest.raises(TypeDBValidationError):
            validate_credentials("admin' OR '1'='1", "password")
    
    def test_xss_pattern_raises_error(self):
        """Test XSS pattern raises error."""
        with pytest.raises(TypeDBValidationError):
            validate_credentials("<script>alert(1)</script>", "password")


@pytest.mark.unit
class TestValidateTimeout:
    """Tests for validate_timeout function."""
    
    def test_valid_timeout(self):
        """Test valid timeout is accepted."""
        result = validate_timeout(30)
        assert result == 30
    
    def test_timeout_as_string_converts_to_int(self):
        """Test string timeout is converted to int."""
        result = validate_timeout("30")
        assert result == 30
    
    def test_none_returns_default(self):
        """Test None returns default 30."""
        result = validate_timeout(None)
        assert result == 30
    
    def test_timeout_too_small_raises_error(self):
        """Test timeout less than 1 raises error."""
        with pytest.raises(TypeDBValidationError) as exc:
            validate_timeout(0)
        assert "at least 1 second" in str(exc.value).lower()
    
    def test_timeout_too_large_raises_error(self):
        """Test timeout over 300 raises error."""
        with pytest.raises(TypeDBValidationError) as exc:
            validate_timeout(301)
        assert "cannot exceed" in str(exc.value).lower()
    
    def test_invalid_type_raises_error(self):
        """Test non-numeric type raises error."""
        with pytest.raises(TypeDBValidationError) as exc:
            validate_timeout("invalid")
        assert "must be a number" in str(exc.value).lower()


@pytest.mark.unit
class TestValidateOperationTimeouts:
    """Tests for validate_operation_timeouts function."""
    
    def test_valid_timeouts(self):
        """Test valid operation timeouts are accepted."""
        result = validate_operation_timeouts({
            "read_operation": 60,
            "write_operation": 120
        })
        assert result["read_operation"] == 60
        assert result["write_operation"] == 120
    
    def test_unknown_operation_raises_error(self):
        """Test unknown operation raises error."""
        with pytest.raises(TypeDBValidationError) as exc:
            validate_operation_timeouts({"unknown_op": 30})
        assert "unknown timeout operation" in str(exc.value).lower()
    
    def test_timeout_out_of_range_raises_error(self):
        """Test timeout out of range raises error."""
        with pytest.raises(TypeDBValidationError) as exc:
            validate_operation_timeouts({"read_operation": 500})
        assert "must be between" in str(exc.value).lower()
    
    def test_empty_dict_uses_defaults(self):
        """Test empty dict returns all defaults."""
        result = validate_operation_timeouts({})
        assert "authentication" in result
        assert "read_operation" in result
