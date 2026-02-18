"""Tests for query execution.

Tests:
- Execute read query
- Execute write query
- Execute transaction
- Query error handling
"""

import pytest

from typedb_v3_client import TypeDBClient, TransactionType
from typedb_v3_client.exceptions import TypeDBQueryError
from typing import Dict

class TestQueryExecution:
    """Test suite for query execution."""
    
    def test_execute_read_query(self, client, db_with_schema):
        """Test executing a read query."""
        # Insert some data first
        insert_query = 'insert $a isa actor, has actor-id "A1", has actor-name "Alice";'
        client.execute_query(db_with_schema, insert_query, TransactionType.WRITE)
        
        # Read query
        read_query = 'match $a isa actor; fetch {$a.*};'
        result = client.execute_query(db_with_schema, read_query, TransactionType.READ)
        
        assert result is not None
        assert len(result.get("answers", [])) > 0
        
    
    def test_execute_write_query(self, client, db_with_schema):
        """Test executing a write query."""
        insert_query = 'insert $a isa actor, has actor-id "A2", has actor-name "Bob";'
        result = client.execute_query(db_with_schema, insert_query, TransactionType.WRITE)
        
        # Write queries should return a result
        assert result is not None
    
    def test_query_error_handling(self, client, db_with_schema):
        """Test that invalid query raises TypeDBQueryError."""
        invalid_query = "this is not a valid typeql query"
        
        with pytest.raises(TypeDBQueryError) as exc_info:
            client.execute_query(db_with_schema, invalid_query, TransactionType.READ)
        
        assert "query" in str(exc_info.value).lower() or "failed" in str(exc_info.value).lower()
    
    def test_execute_transaction(self, client, db_with_schema):
        """Test executing multiple operations in a transaction."""
        operations = [
            {"query": 'insert $a isa actor, has actor-id "T1", has actor-name "Test1";'},
            {"query": 'insert $b isa actor, has actor-id "T2", has actor-name "Test2";'},
        ]
        
        result = client.execute_transaction(
            db_with_schema,
            TransactionType.WRITE,
            operations
        )
        
        assert result is not None
    
    def test_execute_queries_variadic(self, client, db_with_schema):
        """Test executing queries with variadic arguments."""
        result = client.execute_queries(
            db_with_schema,
            'insert $a isa actor, has actor-id "V1", has actor-name "Var1";',
            'insert $b isa actor, has actor-id "V2", has actor-name "Var2";',
            transaction_type=TransactionType.WRITE
        )
        
        assert result is not None
        assert isinstance(result, Dict)
    
    def test_with_transaction_context_manager(self, client, db_with_schema):
        """Test using transaction context manager."""
        with client.with_transaction(db_with_schema, TransactionType.WRITE) as tx:
            tx.execute('insert $a isa actor, has actor-id "C1", has actor-name "Context";')
        
        # Verify data was inserted
        read_query = 'match $a isa actor, has actor-id "C1"; fetch {$a.*};'
        result = client.execute_query(db_with_schema, read_query, TransactionType.READ)
        
        assert result is not None
        assert len(result.get("answers", [])) > 0


class TestQueryPatterns:
    """Test suite for different query patterns."""
    
    def test_insert_with_attributes(self, client, db_with_schema):
        """Test inserting entity with multiple attributes."""
        query = '''
        insert $a isa actor, 
            has actor-id "ATTR1", 
            has actor-name "Attribute Test";
        '''
        
        result = client.execute_query(db_with_schema, query, TransactionType.WRITE)
        assert result is not None
    
    def test_match_delete(self, client, db_with_schema):
        """Test match-delete query pattern."""
        # Insert first
        insert_query = 'insert $a isa actor, has actor-id "DEL1";'
        client.execute_query(db_with_schema, insert_query, TransactionType.WRITE)
        
        # Delete
        delete_query = 'match $a isa actor, has actor-id "DEL1"; delete $a;'
        client.execute_query(db_with_schema, delete_query, TransactionType.WRITE)
        
        # Verify deleted
        read_query = 'match $a isa actor, has actor-id "DEL1"; fetch {$a.*};'
        result = client.execute_query(db_with_schema, read_query, TransactionType.READ)
        
        assert len(result.get("answers", [])) == 0
