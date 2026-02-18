"""Tests for schema operations.

Tests:
- Get schema (requires get_schema method - not yet implemented)
- Parse schema for entity/relation types

Note: These tests require the get_schema() method to be implemented.
The get_schema method should call GET /v1/databases/{database}/schema
and return the TypeQL schema as a plain text string.
"""

import pytest


class TestSchemaOperations:
    """Test suite for schema operations."""
    
    def test_get_schema_method_exists(self, client, db_with_schema):
        """Test that get_schema method exists on client."""
        assert hasattr(client, 'get_schema'), \
            "TypeDBClient should have get_schema method"
    
    @pytest.mark.skip(reason="get_schema not yet implemented")
    def test_get_schema(self, client, db_with_schema):
        """Test fetching the database schema."""
        schema = client.get_schema(db_with_schema)
        
        assert schema is not None
        assert isinstance(schema, str)
        assert len(schema) > 0
    
    @pytest.mark.skip(reason="get_schema not yet implemented")
    def test_schema_contains_entities(self, client, db_with_schema):
        """Test that schema contains entity definitions."""
        schema = client.get_schema(db_with_schema)
        
        # Our test schema has 'actor' entity
        assert "actor" in schema.lower()
    
    @pytest.mark.skip(reason="get_schema not yet implemented")
    def test_schema_contains_relations(self, client, db_with_schema):
        """Test that schema contains relation definitions."""
        schema = client.get_schema(db_with_schema)
        
        # Our test schema has 'knows' relation
        assert "mebership" in schema.lower()


class TestSchemaParsing:
    """Test suite for schema parsing utilities."""
    
    @pytest.mark.skip(reason="Schema parsing utilities not yet implemented")
    def test_parse_entity_types(self):
        """Test parsing entity types from schema string."""
        schema = """
        define
        
        entity actor;
        entity action;
        """
        # Expected: ["actor", "action"]
        # This would use regex: r'(\w+)entity'
        pass
    
    @pytest.mark.skip(reason="Schema parsing utilities not yet implemented")
    def test_parse_relation_types(self):
        """Test parsing relation types from schema string."""
        schema = """
        define
        
        relation mebership,
          relates member-of,
          relates member;
        relation ownership,
          relates owner,
          relates owned;

        """
        # Expected: ["mebership", "ownership"]
        # This would use regex: r'(\w+)relation'
        pass
