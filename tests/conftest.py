"""Pytest configuration and fixtures for TypeDB client tests.

Provides:
- Server availability check
- Client fixture
- Database name fixtures with automatic cleanup
"""

import pytest
import uuid

from typedb_client3 import TypeDBClient, TransactionType


# Test server configuration
TEST_BASE_URL = "http://localhost:8000"
TEST_USERNAME = "admin"
TEST_PASSWORD = "password"


@pytest.fixture(scope="session")
def test_server_available():
    """Verify test server is running before tests.
    
    Skips all tests if server is not available.
    """
    import requests
    try:
        response = requests.get(TEST_BASE_URL, timeout=5)
        if response.status_code != 200:
            pytest.skip(f"Test server returned status {response.status_code}")
    except Exception as e:
        pytest.skip(f"Test server not available: {e}")
    return True


@pytest.fixture
def client(test_server_available):
    """Create a TypeDB client for each test.
    
    Automatically closes the client after the test.
    """
    client = TypeDBClient(
        base_url=TEST_BASE_URL,
        username=TEST_USERNAME,
        password=TEST_PASSWORD
    )
    yield client
    client.close()


@pytest.fixture
def test_db_name():
    """Generate a unique database name for a test.
    
    Uses UUID to ensure uniqueness.
    """
    return f"test_db_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def created_db(client, test_db_name):
    """Create a test database, yield, then cleanup.
    
    Creates the database before the test and deletes it after.
    """
    client.create_database(test_db_name)
    yield test_db_name
    # Cleanup - try to delete, ignore errors
    try:
        client.delete_database(test_db_name)
    except Exception:
        pass


@pytest.fixture
def db_with_schema(client, test_db_name):
    """Create a database with a test schema.
    
    Creates a simple schema with actor entity for testing.
    """
    from pathlib import Path
    import tempfile
    
    schema = """
    define
    
    entity actor,
        owns actor-id,
        owns actor-name;
    
    attribute actor-id, value string;
    attribute actor-name, value string;
    
    relation knows,
        relates friend;
    """
    
    client.create_database(test_db_name)
    
    # Write schema to temp file and load
    with tempfile.NamedTemporaryFile(mode='w', suffix='.tql', delete=False) as f:
        f.write(schema)
        schema_path = Path(f.name)
    
    # Load schema
    client.load_schema(test_db_name, schema_path)
    
    # Remove temp file
    schema_path.unlink()
    
    yield test_db_name
    
    # Cleanup
    try:
        client.delete_database(test_db_name)
    except Exception:
        pass
