"""Tests for schema operations.

Tests:
- Get schema
- Parse schema for entity/relation types
"""

import pytest


class TestSchemaOperations:
    """Test suite for schema operations."""
    
    def test_get_schema_method_exists(self, client, db_with_schema):
        """Test that get_schema method exists on client."""
        assert hasattr(client, 'get_schema'), \
            "TypeDBClient should have get_schema method"
    
    def test_get_schema(self, client, db_with_schema):
        """Test fetching the database schema."""
        schema = client.get_schema(db_with_schema)
        
        assert schema is not None
        assert isinstance(schema, str)
        assert len(schema) > 0
    
    def test_schema_contains_entities(self, client, db_with_schema):
        """Test that schema contains entity definitions."""
        schema = client.get_schema(db_with_schema)
        
        # Our test schema has 'actor' entity
        assert "actor" in schema.lower()
    
    def test_schema_contains_relations(self, client, db_with_schema):
        """Test that schema contains relation definitions."""
        schema = client.get_schema(db_with_schema)
        
        # Our test schema has 'knows' relation
        assert "knows" in schema.lower()


class TestSchemaParsing:
    """Test suite for schema parsing utilities."""
    
    def test_parse_entity_types(self):
        """Test parsing entity types from schema string."""
        from typedb_client3.client import TypeDBClient
        
        # Create a mock client to test the parsing method
        schema = """
        define
        
        entity actor;
        entity action;
        entity message;
        """
        # Expected: ["actor", "action", "message"]
        # Use the _parse_schema_types method
        client = TypeDBClient.__new__(TypeDBClient)
        entity_types, relation_types = client._parse_schema_types(schema)
        
        assert "actor" in entity_types
        assert "action" in entity_types
        assert "message" in entity_types
    
    def test_parse_relation_types(self):
        """Test parsing relation types from schema string."""
        from typedb_client3.client import TypeDBClient
        
        schema = """
        define
        
        relation membership,
          relates member-of,
          relates member;
        relation ownership,
          relates owner,
          relates owned;
        """
        # Expected: ["membership", "ownership"]
        client = TypeDBClient.__new__(TypeDBClient)
        entity_types, relation_types = client._parse_schema_types(schema)
        
        assert "membership" in relation_types
        assert "ownership" in relation_types
    
    def test_parse_mixed_schema(self):
        """Test parsing a schema with both entities and relations."""
        from typedb_client3.client import TypeDBClient
        
        schema = """
        define
        
        entity actor,
            owns actor-id;
            
        relation membership,
            relates member-of,
            relates member;
        """
        client = TypeDBClient.__new__(TypeDBClient)
        entity_types, relation_types = client._parse_schema_types(schema)
        
        assert "actor" in entity_types
        assert "membership" in relation_types
    
    def test_parse_schema_with_subtypes(self):
        """Test parsing schema with subtype definitions."""
        from typedb_client3.client import TypeDBClient
        
        schema = """
        define
        
        entity design-concept @abstract,
            owns name;
            
        entity concept sub design-concept;
        entity actor sub design-concept;
        """
        client = TypeDBClient.__new__(TypeDBClient)
        entity_types, relation_types = client._parse_schema_types(schema)
        
        # Should find both abstract and concrete types
        assert "design-concept" in entity_types
        assert "concept" in entity_types
        assert "actor" in entity_types
