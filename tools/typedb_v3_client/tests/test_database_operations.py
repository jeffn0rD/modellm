"""Comprehensive tests for database operations.

Tests for database creation, deletion, wiping, and verification functionality
in the TypeDB v3 client library.
"""

import pytest
import uuid
from pathlib import Path

from typedb_v3_client import TypeDBClient, TransactionType
from typedb_v3_client.exceptions import (
    TypeDBConnectionError,
    TypeDBQueryError,
    TypeDBValidationError
)


# Test configuration
TEST_BASE_URL = "http://localhost:8000"
TEST_USERNAME = "admin"
TEST_PASSWORD = "password"


@pytest.fixture
def client():
    """Create a TypeDB client for testing."""
    client = TypeDBClient(
        base_url=TEST_BASE_URL,
        username=TEST_USERNAME,
        password=TEST_PASSWORD
    )
    yield client
    client.close()


@pytest.fixture
def test_db_name():
    """Generate a unique test database name."""
    return f"test_db_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def created_db(client, test_db_name):
    """Create a test database and clean up after test."""
    client.create_database(test_db_name)
    yield test_db_name
    # Cleanup
    try:
        client.delete_database(test_db_name)
    except Exception:
        pass


class TestDatabaseOperations:
    """Test suite for basic database operations."""
    
    def test_create_database(self, client, test_db_name):
        """Test creating a new database."""
        # Database should not exist initially
        assert not client.database_exists(test_db_name)
        
        # Create database
        client.create_database(test_db_name)
        
        # Database should exist now
        assert client.database_exists(test_db_name)
        
        # Cleanup
        client.delete_database(test_db_name)
    
    def test_create_database_already_exists(self, client, created_db):
        """Test that creating an existing database raises error."""
        with pytest.raises(TypeDBValidationError):
            client.create_database(created_db)
    
    def test_delete_database(self, client, test_db_name):
        """Test deleting a database."""
        # Create database
        client.create_database(test_db_name)
        assert client.database_exists(test_db_name)
        
        # Delete database
        client.delete_database(test_db_name)
        
        # Database should not exist
        assert not client.database_exists(test_db_name)
    
    def test_delete_nonexistent_database(self, client, test_db_name):
        """Test that deleting a non-existent database raises error."""
        with pytest.raises(TypeDBValidationError):
            client.delete_database(test_db_name)
    
    def test_database_exists(self, client, created_db):
        """Test checking if database exists."""
        assert client.database_exists(created_db)
        assert not client.database_exists("nonexistent_db_12345")
    
    def test_list_databases(self, client, created_db):
        """Test listing databases."""
        databases = client.list_databases()
        assert isinstance(databases, list)
        assert created_db in databases


class TestDatabaseWipe:
    """Test suite for database wipe functionality."""
    
    def test_wipe_empty_database(self, client, created_db):
        """Test wiping an empty database."""
        # Wipe should succeed even on empty database
        result = client.wipe_database(created_db, verify=True)
        assert result is True
    
    def test_wipe_database_with_entities(self, client, created_db):
        """Test wiping a database with entities."""
        # Insert test entities
        queries = [
            'insert $d isa spec-document, has spec-doc-id "TEST1";',
            'insert $a isa actor, has actor-id "ACTOR1";',
            'insert $ac isa action, has action-id "ACTION1";',
        ]
        
        for query in queries:
            client.execute_query(created_db, query, TransactionType.WRITE)
        
        # Verify data exists
        result = client.execute_query(
            created_db,
            "match $x isa spec-document; fetch $x;",
            TransactionType.READ
        )
        assert len(result.get("answers", [])) == 1
        
        # Wipe database
        result = client.wipe_database(created_db, verify=True)
        assert result is True
        
        # Verify data is gone
        result = client.execute_query(
            created_db,
            "match $x isa spec-document; fetch $x;",
            TransactionType.READ
        )
        assert len(result.get("answers", [])) == 0
    
    def test_wipe_database_with_relations(self, client, created_db):
        """Test wiping a database with relations."""
        # Insert entities
        query = '''
            insert 
                $d isa spec-document, has spec-doc-id "TEST1";
                $a isa actor, has actor-id "ACTOR1";
        '''
        client.execute_query(created_db, query, TransactionType.WRITE)
        
        # Create relation
        rel_query = '''
            match 
                $d isa spec-document, has spec-doc-id "TEST1";
                $a isa actor, has actor-id "ACTOR1";
            insert anchoring(anchor: $d, concept: $a);
        '''
        client.execute_query(created_db, rel_query, TransactionType.WRITE)
        
        # Verify relation exists
        result = client.execute_query(
            created_db,
            "match $r isa anchoring; fetch $r;",
            TransactionType.READ
        )
        assert len(result.get("answers", [])) == 1
        
        # Wipe database
        result = client.wipe_database(created_db, verify=True)
        assert result is True
        
        # Verify relation is gone
        result = client.execute_query(
            created_db,
            "match $r isa anchoring; fetch $r;",
            TransactionType.READ
        )
        assert len(result.get("answers", [])) == 0
    
    def test_wipe_comprehensive(self, client, created_db):
        """Test wiping a database with comprehensive data."""
        # Insert all entity types
        queries = [
            # Documents and sections
            '''
            insert 
                $folder isa fs-folder, has foldername "/test";
                $doc isa spec-document, has spec-doc-id "DOC1", has title "Test Doc";
                $sec isa spec-section, has spec-section-id "SEC1", has title "Section 1";
            ''',
            # Text blocks
            '''
            insert 
                $tb isa text-block, has anchor-id "TB1", has text "Text 1";
            ''',
            # Concepts
            '''
            insert 
                $c isa concept, has concept-id "CON1", has id-label "Concept 1";
            ''',
            # Actors
            '''
            insert 
                $a isa actor, has actor-id "ACTOR1", has id-label "Actor 1";
            ''',
            # Actions
            '''
            insert 
                $ac isa action, has action-id "ACTION1", has id-label "Action 1";
            ''',
            # Data entities
            '''
            insert 
                $de isa data-entity, has data-entity-id "DE1", has id-label "Data 1";
            ''',
            # Requirements
            '''
            insert 
                $r isa requirement, has requirement-id "REQ1", has id-label "Req 1";
            ''',
            # Constraints
            '''
            insert 
                $cn isa constraint, has constraint-id "CONS1", has id-label "Cons 1";
            ''',
            # Categories
            '''
            insert 
                $cat isa category, has name "Category1";
            ''',
            # Messages
            '''
            insert 
                $m isa message, has message-id "MSG1", has text "Message 1";
            ''',
            # Aggregates
            '''
            insert 
                $aa isa action-aggregate, has action-aggregate-id "AA1";
                $ma isa message-aggregate, has message-aggregate-id "MA1";
            '''
        ]
        
        for query in queries:
            client.execute_query(created_db, query, TransactionType.WRITE)
        
        # Create relations
        relation_queries = [
            # Outlining
            '''
            match 
                $doc isa spec-document, has spec-doc-id "DOC1";
                $sec isa spec-section, has spec-section-id "SEC1";
            insert outlining(section: $doc, subsection: $sec);
            ''',
            # Anchoring
            '''
            match 
                $tb isa text-block, has anchor-id "TB1";
                $c isa concept, has concept-id "CON1";
            insert anchoring(anchor: $tb, concept: $c);
            ''',
            # Categorization
            '''
            match 
                $cat isa category, has name "Category1";
                $act isa action, has action-id "ACTION1";
            insert categorization(category: $cat, object: $act);
            ''',
            # Messaging
            '''
            match 
                $a isa actor, has actor-id "ACTOR1";
                $m isa message, has message-id "MSG1";
            insert messaging(sender: $a, message: $m, order: 1);
            ''',
            # Message payload
            '''
            match 
                $m isa message, has message-id "MSG1";
                $de isa data-entity, has data-entity-id "DE1";
            insert message-payload(message: $m, payload: $de);
            ''',
            # Constrained by
            '''
            match 
                $m isa message, has message-id "MSG1";
                $cn isa constraint, has constraint-id "CONS1";
            insert constrained-by(constraint: $cn, object: $m);
            ''',
            # Requiring
            '''
            match 
                $ac isa action, has action-id "ACTION1";
                $r isa requirement, has requirement-id "REQ1";
            insert requiring(action: $ac, requirement: $r);
            '''
        ]
        
        for query in relation_queries:
            client.execute_query(created_db, query, TransactionType.WRITE)
        
        # Verify data exists before wipe
        result = client.execute_query(
            created_db,
            "match $x isa actor; fetch $x;",
            TransactionType.READ
        )
        assert len(result.get("answers", [])) == 1
        
        result = client.execute_query(
            created_db,
            "match $r isa anchoring; fetch $r;",
            TransactionType.READ
        )
        assert len(result.get("answers", [])) == 1
        
        # Wipe database
        result = client.wipe_database(created_db, verify=True)
        assert result is True
        
        # Verify all entities are gone
        entity_types = [
            "spec-document", "spec-section", "text-block", "concept",
            "actor", "action", "data-entity", "requirement", "constraint",
            "category", "message", "action-aggregate", "message-aggregate"
        ]
        
        for entity_type in entity_types:
            result = client.execute_query(
                created_db,
                f"match $x isa {entity_type}; fetch $x;",
                TransactionType.READ
            )
            assert len(result.get("answers", [])) == 0, f"Entity type {entity_type} still exists"
        
        # Verify all relations are gone
        relation_types = [
            "outlining", "anchoring", "categorization",
            "messaging", "message-payload", "constrained-by", "requiring"
        ]
        
        for rel_type in relation_types:
            result = client.execute_query(
                created_db,
                f"match $r isa {rel_type}; fetch $r;",
                TransactionType.READ
            )
            assert len(result.get("answers", [])) == 0, f"Relation type {rel_type} still exists"
    
    def test_wipe_without_verification(self, client, created_db):
        """Test wiping without verification."""
        # Insert test data
        query = 'insert $d isa spec-document, has spec-doc-id "TEST1";'
        client.execute_query(created_db, query, TransactionType.WRITE)
        
        # Wipe without verification
        result = client.wipe_database(created_db, verify=False)
        assert result is True
        
        # Data should still be gone (but we didn't verify)
        result = client.execute_query(
            created_db,
            "match $x isa spec-document; fetch $x;",
            TransactionType.READ
        )
        assert len(result.get("answers", [])) == 0


class TestWipeVerification:
    """Test suite for wipe verification functionality."""
    
    def test_verify_empty_database(self, client, created_db):
        """Test verification on an empty database."""
        result = client._verify_wipe(created_db)
        assert result is True
    
    def test_verify_database_with_data(self, client, created_db):
        """Test verification detects remaining data."""
        # Insert test data
        query = 'insert $d isa spec-document, has spec-doc-id "TEST1";'
        client.execute_query(created_db, query, TransactionType.WRITE)
        
        # Verification should fail
        with pytest.raises(TypeDBQueryError):
            client._verify_wipe(created_db)


class TestDatabaseOperationsIntegration:
    """Integration tests for database operations."""
    
    def test_full_lifecycle(self, client, test_db_name):
        """Test full database lifecycle: create, insert, wipe, verify, delete."""
        # Create database
        client.create_database(test_db_name)
        assert client.database_exists(test_db_name)
        
        # Insert data
        query = 'insert $d isa spec-document, has spec-doc-id "TEST1";'
        client.execute_query(test_db_name, query, TransactionType.WRITE)
        
        # Verify data exists
        result = client.execute_query(
            test_db_name,
            "match $x isa spec-document; fetch $x;",
            TransactionType.READ
        )
        assert len(result.get("answers", [])) == 1
        
        # Wipe database
        client.wipe_database(test_db_name, verify=True)
        
        # Verify data is gone
        result = client.execute_query(
            test_db_name,
            "match $x isa spec-document; fetch $x;",
            TransactionType.READ
        )
        assert len(result.get("answers", [])) == 0
        
        # Delete database
        client.delete_database(test_db_name)
        assert not client.database_exists(test_db_name)
    
    def test_wipe_nonexistent_database(self, client, test_db_name):
        """Test wiping a non-existent database."""
        with pytest.raises(TypeDBQueryError):
            client.wipe_database(test_db_name, verify=True)


class TestQueryExecution:
    """Test suite for query execution."""
    
    def test_execute_read_query(self, client, created_db):
        """Test executing a read query."""
        # Insert data
        query = 'insert $a isa actor, has actor-id "ACTOR1";'
        client.execute_query(created_db, query, TransactionType.WRITE)
        
        # Read data
        result = client.execute_query(
            created_db,
            "match $a isa actor; fetch $a;",
            TransactionType.READ
        )
        
        assert "answers" in result
        assert len(result["answers"]) == 1
    
    def test_execute_write_query(self, client, created_db):
        """Test executing a write query."""
        query = 'insert $a isa actor, has actor-id "ACTOR1";'
        result = client.execute_query(created_db, query, TransactionType.WRITE)
        
        # Verify insert was successful
        result = client.execute_query(
            created_db,
            "match $a isa actor; fetch $a;",
            TransactionType.READ
        )
        assert len(result["answers"]) == 1
    
    def test_execute_transaction(self, client, created_db):
        """Test executing multiple operations in a transaction."""
        operations = [
            {"query": 'insert $a isa actor, has actor-id "ACTOR1";'},
            {"query": 'insert $a isa actor, has actor-id "ACTOR2";'},
        ]
        
        result = client.execute_transaction(
            created_db,
            TransactionType.WRITE,
            operations
        )
        
        # Verify both inserts succeeded
        result = client.execute_query(
            created_db,
            "match $a isa actor; fetch $a;",
            TransactionType.READ
        )
        assert len(result["answers"]) == 2
    
    def test_execute_queries(self, client, created_db):
        """Test executing multiple queries."""
        result = client.execute_queries(
            created_db,
            'insert $a isa actor, has actor-id "ACTOR1";',
            'insert $a isa actor, has actor-id "ACTOR2";',
            transaction_type=TransactionType.WRITE
        )
        
        # Verify both inserts succeeded
        result = client.execute_query(
            created_db,
            "match $a isa actor; fetch $a;",
            TransactionType.READ
        )
        assert len(result["answers"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
