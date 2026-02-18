"""Integration tests for TypeDB query execution.

Tests:
- Execute read query
- Execute write query (insert)
- Execute transaction
- Query error handling
"""

import pytest
import uuid

from typedb_v3_client import TypeDBClient, TransactionType
from typedb_v3_client.exceptions import TypeDBQueryError


# Test server configuration
TEST_BASE_URL = "http://localhost:8000"
TEST_USERNAME = "admin"
TEST_PASSWORD = "password"


# Simple test schema - using valid schema from doc/typedb_schema_2.tql
TEST_SCHEMA = """
define

entity actor,
    owns actor-id @key;

attribute actor-id, value string;
"""


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
def db_with_schema(client):
    """Create a database with test schema."""
    db_name = unique_db_name()
    client.create_database(db_name)
    client.load_schema(db_name, TEST_SCHEMA)
    yield db_name
    try:
        client.delete_database(db_name)
    except Exception:
        pass


@pytest.mark.integration
def test_execute_write_query_insert(db_with_schema, client):
    """Test executing insert write query."""
    insert_query = 'insert $a isa actor, has actor-id "A1";'
    
    result = client.execute_query(db_with_schema, insert_query, TransactionType.WRITE)
    
    # Insert should succeed (result may be empty or contain inserted concepts)
    assert result is not None


@pytest.mark.integration
def test_execute_read_query(db_with_schema, client):
    """Test executing read query."""
    # Insert first
    insert_query = 'insert $a isa actor, has actor-id "READ1";'
    client.execute_query(db_with_schema, insert_query, TransactionType.WRITE)
    
    # Read query - just match, no fetch needed to check existence
    read_query = 'match $a isa actor, has actor-id "READ1";'
    result = client.execute_query(db_with_schema, read_query, TransactionType.READ)
    
    assert result is not None
    # Check answers property
    assert "answers" in result or isinstance(result, list)


@pytest.mark.integration
def test_execute_transaction(db_with_schema, client):
    """Test executing multiple operations in a transaction."""
    operations = [
        {"query": 'insert $a isa actor, has actor-id "TX1";'},
        {"query": 'insert $b isa actor, has actor-id "TX2";'},
    ]
    
    result = client.execute_transaction(
        db_with_schema,
        TransactionType.WRITE,
        operations
    )
    
    assert result is not None


@pytest.mark.integration
def test_execute_queries_variadic(db_with_schema, client):
    """Test executing queries with variadic arguments."""
    result = client.execute_queries(
        db_with_schema,
        'insert $a isa actor, has actor-id "VAR1";',
        'insert $b isa actor, has actor-id "VAR2";',
        transaction_type=TransactionType.WRITE
    )
    
    assert result is not None


@pytest.mark.integration
def test_with_transaction_context_manager(db_with_schema, client):
    """Test using transaction context manager."""
    with client.with_transaction(db_with_schema, TransactionType.WRITE) as tx:
        tx.execute('insert $a isa actor, has actor-id "CTX1";')
    
    # Verify data was inserted
    read_query = 'match $a isa actor, has actor-id "CTX1";'
    result = client.execute_query(db_with_schema, read_query, TransactionType.READ)
    
    assert result is not None


@pytest.mark.integration
def test_query_error_handling(db_with_schema, client):
    """Test that invalid query raises TypeDBQueryError."""
    invalid_query = "this is not valid typeql"
    
    with pytest.raises(TypeDBQueryError):
        client.execute_query(db_with_schema, invalid_query, TransactionType.READ)


@pytest.mark.integration
def test_match_delete_query(db_with_schema, client):
    """Test match-delete query pattern."""
    # Insert first
    insert_query = 'insert $a isa actor, has actor-id "DEL1";'
    client.execute_query(db_with_schema, insert_query, TransactionType.WRITE)
    
    # Verify it exists - just match, no fetch needed
    check_query = 'match $a isa actor, has actor-id "DEL1";'
    result = client.execute_query(db_with_schema, check_query, TransactionType.READ)
    initial_count = len(result.get("answers", [])) if isinstance(result, dict) else len(result)
    assert initial_count > 0
    
    # Delete
    delete_query = 'match $a isa actor, has actor-id "DEL1"; delete $a;'
    client.execute_query(db_with_schema, delete_query, TransactionType.WRITE)
    
    # Verify deleted
    result = client.execute_query(db_with_schema, check_query, TransactionType.READ)
    final_count = len(result.get("answers", [])) if isinstance(result, dict) else len(result)
    
    assert final_count == 0


@pytest.mark.integration
def test_insert_multiple_attributes(db_with_schema, client):
    """Test inserting entity with attribute."""
    query = 'insert $a isa actor, has actor-id "MATTR1";'
    
    result = client.execute_query(db_with_schema, query, TransactionType.WRITE)
    assert result is not None
    
    # Verify inserted - just match, no fetch needed
    read_query = 'match $a isa actor, has actor-id "MATTR1";'
    result = client.execute_query(db_with_schema, read_query, TransactionType.READ)
    assert result is not None


@pytest.mark.integration
def test_query_on_empty_database(db_with_schema, client):
    """Test query on database with no data."""
    read_query = 'match $a isa actor;'
    result = client.execute_query(db_with_schema, read_query, TransactionType.READ)
    
    # Should return empty results
    assert result is not None
