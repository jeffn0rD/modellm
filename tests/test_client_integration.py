"""Integration tests for TypeDB client authentication.

Tests:
- Authentication with valid credentials
- Authentication with invalid credentials
- Token is stored encrypted after authentication
- Token access log is recorded
"""

import pytest
from typedb_v3_client import TypeDBClient
from typedb_v3_client.exceptions import TypeDBConnectionError, TypeDBAuthenticationError


# Test server configuration
TEST_BASE_URL = "http://localhost:8000"
TEST_USERNAME = "admin"
TEST_PASSWORD = "password"


@pytest.fixture(scope="module")
def server_available():
    """Check if test server is available."""
    import requests
    try:
        response = requests.get(TEST_BASE_URL, timeout=5)
        return response.status_code == 200
    except Exception:
        return False


@pytest.mark.integration
def test_authenticate_success(server_available):
    """Test successful authentication with valid credentials."""
    if not server_available:
        pytest.skip("Test server not available")
    
    client = TypeDBClient(
        base_url=TEST_BASE_URL,
        username=TEST_USERNAME,
        password=TEST_PASSWORD
    )
    
    # Verify client has token
    assert client._token is not None
    assert len(client._token) > 0
    
    # Verify token is encrypted for storage
    assert client._token_encrypted is not None
    assert client._token_encrypted != client._token
    
    # Verify we can list databases (proves token works)
    databases = client.list_databases()
    assert isinstance(databases, list)
    
    client.close()


@pytest.mark.integration
def test_authenticate_failure(server_available):
    """Test authentication fails with invalid credentials."""
    if not server_available:
        pytest.skip("Test server not available")
    
    with pytest.raises((TypeDBConnectionError, TypeDBAuthenticationError)):
        client = TypeDBClient(
            base_url=TEST_BASE_URL,
            username="invalid_user",
            password="wrong_password"
        )
        # Force authentication attempt
        client._authenticate()


@pytest.mark.integration
def test_token_encrypted_stored(server_available):
    """Test that encrypted token is stored after authentication."""
    if not server_available:
        pytest.skip("Test server not available")
    
    client = TypeDBClient(
        base_url=TEST_BASE_URL,
        username=TEST_USERNAME,
        password=TEST_PASSWORD
    )
    
    # Get encrypted token
    encrypted = client.get_encrypted_token()
    assert encrypted is not None
    
    # Verify it's different from raw token
    assert encrypted != client._token
    
    # Verify we can retrieve it
    client.set_encrypted_token(encrypted)
    assert client._token is not None
    
    client.close()


@pytest.mark.integration
def test_token_access_log(server_available):
    """Test token access is logged for audit."""
    if not server_available:
        pytest.skip("Test server not available")
    
    client = TypeDBClient(
        base_url=TEST_BASE_URL,
        username=TEST_USERNAME,
        password=TEST_PASSWORD
    )
    
    # Check access log
    log = client.get_token_access_log()
    assert len(log) > 0
    
    # First entry should be 'store'
    assert log[0]["action"] == "store"
    
    client.close()


@pytest.mark.integration
def test_client_without_credentials(server_available):
    """Test client can be created without credentials (anonymous)."""
    if not server_available:
        pytest.skip("Test server not available")
    
    # Some servers may allow anonymous access
    # This test verifies the client can be created without credentials
    try:
        client = TypeDBClient(base_url=TEST_BASE_URL)
        # If we get here, anonymous access is allowed
        client.close()
    except (TypeDBConnectionError, TypeDBAuthenticationError):
        # Anonymous access not allowed - this is expected for TypeDB
        pass
