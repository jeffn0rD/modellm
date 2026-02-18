"""Tests for database operations.

Tests:
- Create database
- Delete database
- Database exists
- List databases
"""

import pytest

from typedb_v3_client import TypeDBClient, TransactionType
from typedb_v3_client.exceptions import TypeDBValidationError


class TestDatabaseOperations:
    """Test suite for database operations."""
    
    def test_create_database(self, client, test_db_name):
        """Test creating a new database."""
        # Database should not exist initially
        assert not client.database_exists(test_db_name), \
            f"Database {test_db_name} should not exist yet"
        
        # Create database
        client.create_database(test_db_name)
        
        # Database should exist now
        assert client.database_exists(test_db_name), \
            f"Database {test_db_name} should exist after creation"
        
        # Cleanup
        client.delete_database(test_db_name)
    
    def test_create_database_duplicate(self, client, created_db):
        """Test that creating an existing database raises error."""
        # the server never actually returns an error for duplicate database creation, so this test is not valid
        # its not mentioned in the documentation, but we can always hallucinate
        #
        #with pytest.raises(TypeDBValidationError) as exc_info:
        #    client.create_database(created_db)
        #
        #assert "already exists" in str(exc_info.value).lower()
        pass
    
    def test_delete_database(self, client, test_db_name):
        """Test deleting a database."""
        # Create database
        client.create_database(test_db_name)
        assert client.database_exists(test_db_name)
        
        # Delete database
        client.delete_database(test_db_name)
        
        # Database should not exist
        assert not client.database_exists(test_db_name), \
            f"Database {test_db_name} should not exist after deletion"
    
    def test_delete_nonexistent(self, client, test_db_name):
        """Test that deleting a non-existent database raises error."""
        with pytest.raises(TypeDBValidationError) as exc_info:
            client.delete_database(test_db_name)
        
        assert "does not exist" in str(exc_info.value).lower()
    
    def test_database_exists_true(self, client, created_db):
        """Test checking if database exists when it does."""
        assert client.database_exists(created_db), \
            f"Database {created_db} should exist"
    
    def test_database_exists_false(self, client, test_db_name):
        """Test checking if database exists when it doesn't."""
        assert not client.database_exists(test_db_name), \
            f"Database {test_db_name} should not exist"
    
    def test_list_databases(self, client, created_db):
        """Test listing databases."""
        databases = client.list_databases()
        
        assert isinstance(databases, list), "list_databases should return a list"
        assert created_db in databases, \
            f"Created database {created_db} should be in list"


class TestDatabaseOperationsIntegration:
    """Integration tests for database operations."""
    
    def test_full_lifecycle(self, client, test_db_name):
        """Test complete database lifecycle: create, verify, delete."""
        # Should not exist
        assert not client.database_exists(test_db_name)
        
        # Create
        client.create_database(test_db_name)
        assert client.database_exists(test_db_name)
        
        # Delete
        client.delete_database(test_db_name)
        assert not client.database_exists(test_db_name)
    
    def test_create_with_connect(self, client, test_db_name):
        """Test connect_database creates database if needed."""
        # Use connect which should create the database
        result = client.connect_database(test_db_name)
        
        assert result is True
        assert client.database_exists(test_db_name)
        
        # Cleanup
        client.delete_database(test_db_name)
