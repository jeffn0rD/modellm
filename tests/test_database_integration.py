"""Integration tests for TypeDB database CRUD operations.

Tests:
- create_database
- delete_database
- database_exists
- list_databases
"""

import pytest
import uuid

from typedb_client3 import TypeDBClient
from typedb_client3.exceptions import TypeDBValidationError


# Test server configuration
TEST_BASE_URL = "http://localhost:8000"
TEST_USERNAME = "admin"
TEST_PASSWORD = "password"


def unique_db_name():
    """Generate unique database name."""
    return f"test_db_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def client():
    """Create a client for testing."""
    client = TypeDBClient(
        base_url=TEST_BASE_URL,
        username=TEST_USERNAME,
        password=TEST_PASSWORD
    )
    yield client
    client.close()


@pytest.fixture
def db_name():
    """Generate unique database name."""
    return unique_db_name()


@pytest.mark.integration
def test_create_database(client, db_name):
    """Test creating a new database."""
    # Database should not exist initially
    assert not client.database_exists(db_name)
    
    # Create database
    client.create_database(db_name)
    
    # Database should exist now
    assert client.database_exists(db_name)
    
    # Cleanup
    client.delete_database(db_name)


@pytest.mark.integration
def test_create_database_duplicate(client, db_name):
    """Test creating duplicate database is idempotent (no error)."""
    # Create database
    client.create_database(db_name)
    
    # Try to create again - TypeDB v3 may be idempotent and return 200 OK
    # Just verify the database exists
    client.create_database(db_name)
    assert client.database_exists(db_name)
    
    # Cleanup
    client.delete_database(db_name)


@pytest.mark.integration
def test_delete_database(client, db_name):
    """Test deleting a database."""
    # Create database
    client.create_database(db_name)
    assert client.database_exists(db_name)
    
    # Delete database
    client.delete_database(db_name)
    
    # Database should not exist
    assert not client.database_exists(db_name)


@pytest.mark.integration
def test_delete_nonexistent_database(client, db_name):
    """Test deleting non-existent database raises error."""
    with pytest.raises(TypeDBValidationError) as exc:
        client.delete_database(db_name)
    
    assert "does not exist" in str(exc.value).lower()


@pytest.mark.integration
def test_database_exists_true(client, db_name):
    """Test database_exists returns True for existing database."""
    client.create_database(db_name)
    
    assert client.database_exists(db_name) is True
    
    # Cleanup
    client.delete_database(db_name)


@pytest.mark.integration
def test_database_exists_false(client, db_name):
    """Test database_exists returns False for non-existing database."""
    assert client.database_exists(db_name) is False


@pytest.mark.integration
def test_list_databases(client, db_name):
    """Test listing databases includes our test database."""
    client.create_database(db_name)
    
    databases = client.list_databases()
    
    assert isinstance(databases, list)
    assert db_name in databases
    
    # Cleanup
    client.delete_database(db_name)


@pytest.mark.integration
def test_list_databases_empty(client):
    """Test listing databases returns list even when empty."""
    databases = client.list_databases()
    
    assert isinstance(databases, list)


@pytest.mark.integration
def test_database_lifecycle(client, db_name):
    """Test complete database lifecycle."""
    # Should not exist
    assert not client.database_exists(db_name)
    
    # Create
    client.create_database(db_name)
    assert client.database_exists(db_name)
    
    # Delete
    client.delete_database(db_name)
    assert not client.database_exists(db_name)


@pytest.mark.integration
def test_connect_database_creates_if_missing(client, db_name):
    """Test connect_database creates database if it doesn't exist."""
    # Ensure database doesn't exist
    assert not client.database_exists(db_name)
    
    # Connect (should create)
    result = client.connect_database(db_name)
    assert result is True
    assert client.database_exists(db_name)
    
    # Cleanup
    client.delete_database(db_name)
