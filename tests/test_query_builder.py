"""Unit tests for QueryBuilder module"""

import pytest
from typedb_v3_client.query_builder import QueryBuilder, Variable, RelationBuilder


class TestVariable:
    """Test Variable class."""
    
    def test_variable_str_with_type(self):
        """Test Variable string representation with type."""
        var = Variable("x")
        var.isa("actor")
        assert str(var) == "$x isa actor"
    
    def test_variable_str_with_type_and_attributes(self):
        """Test Variable string representation with type and attributes."""
        var = Variable("x")
        var.isa("actor")
        var.has("actor-id", "A1")
        var.has("id-label", "EndUser")
        expected = '$x isa actor, has actor-id "A1", has id-label "EndUser"'
        assert str(var) == expected
    
    def test_variable_str_with_label(self):
        """Test Variable string representation with label."""
        var = Variable("x")
        var.isa("user")
        var.label("$type_label")
        expected = '$x isa user, label $type_label'
        assert str(var) == expected
    
    def test_variable_escape_string(self):
        """Test string escaping in Variable."""
        var = Variable("x")
        var.isa("actor")
        var.has("description", 'He said "hello"')
        assert 'has description "He said \\"hello\\""' in str(var)
    
    def test_variable_escape_backslash(self):
        """Test backslash escaping in Variable."""
        var = Variable("x")
        var.isa("actor")
        var.has("path", r"C:\Users\test")
        assert r'has path "C:\\Users\\test"' in str(var)
    
    def test_variable_integer_value(self):
        """Test integer value handling."""
        var = Variable("x")
        var.isa("entity")
        var.has("count", 42)
        assert 'has count 42' in str(var)
    
    def test_variable_float_value(self):
        """Test float value handling."""
        var = Variable("x")
        var.isa("entity")
        var.has("price", 19.99)
        assert 'has price 19.99' in str(var)
    
    def test_variable_bool_value(self):
        """Test boolean value handling."""
        var = Variable("x")
        var.isa("entity")
        var.has("active", True)
        assert 'has active true' in str(var)
    
    def test_variable_unsupported_type(self):
        """Test unsupported value type raises error."""
        var = Variable("x")
        var.isa("entity")
        var.has("data", {"key": "value"})
        with pytest.raises(ValueError, match="Unsupported value type"):
            str(var)
    
    def test_variable_name_strips_dollar(self):
        """Test that $ prefix is stripped from variable name."""
        var = Variable("$x")
        assert var.name == "x"


class TestRelationBuilder:
    """Test RelationBuilder class."""
    
    def test_role_with_dollar_prefix(self):
        """Test role method with $ prefix in variable."""
        qb = QueryBuilder.match_template()
        rb = RelationBuilder(qb, "messaging")
        rb.role("producer", "$actor")
        assert rb.roles[0] == {"name": "producer", "variable": "actor"}
    
    def test_role_without_dollar_prefix(self):
        """Test role method without $ prefix in variable."""
        qb = QueryBuilder.match_template()
        rb = RelationBuilder(qb, "messaging")
        rb.role("producer", "actor")
        assert rb.roles[0] == {"name": "producer", "variable": "actor"}
    
    def test_links_keyword(self):
        """Test links method sets use_links flag."""
        qb = QueryBuilder.match_template()
        rb = RelationBuilder(qb, "messaging")
        rb.links()
        assert rb.use_links is True
    
    def test_as_variable(self):
        """Test as_variable method."""
        qb = QueryBuilder.match_template()
        rb = RelationBuilder(qb, "messaging")
        rb.as_variable("m")
        assert rb.var_name == "m"
    
    def test_end_relation(self):
        """Test end_relation returns to QueryBuilder."""
        qb = QueryBuilder.match_template()
        rb = RelationBuilder(qb, "messaging")
        rb.role("producer", "$actor")
        result = rb.end_relation()
        assert result is qb
        assert len(qb.relations) == 1
        assert qb.relations[0]["type"] == "messaging"


class TestQueryBuilder:
    """Test QueryBuilder class."""
    
    def test_match_query(self):
        """Test basic MATCH query."""
        query = (QueryBuilder()
            .match()
            .variable("x", "actor", {"actor-id": "A1"})
            .fetch(["x"])
            .build()
        )
        
        expected = 'match $x isa actor, has actor-id "A1"; fetch {"x": {$x.*}};'
        assert query == expected
    
    def test_insert_query(self):
        """Test basic INSERT query."""
        query = (QueryBuilder()
            .insert()
            .variable("a", "actor", {
                "actor-id": "A1",
                "id-label": "User1",
                "description": "Test user"
            })
            .build()
        )
        
        assert "insert" in query
        assert "$a isa actor" in query
        assert 'has actor-id "A1"' in query
        assert 'has id-label "User1"' in query
        assert 'has description "Test user"' in query
    
    def test_put_query(self):
        """Test PUT query (idempotent)."""
        query = (QueryBuilder()
            .put()
            .variable("a", "actor", {"actor-id": "A1"})
            .build()
        )
        
        assert "put" in query
        assert "$a isa actor" in query
    
    def test_delete_query(self):
        """Test DELETE query."""
        query = (QueryBuilder()
            .delete()
            .variable("x", "actor", {"actor-id": "A1"})
            .build()
        )
        
        assert "delete" in query
        assert "$x" in query
    
    def test_update_query(self):
        """Test UPDATE query."""
        query = (QueryBuilder()
            .match()
            .variable("a", "actor", {"actor-id": "A1"})
            .update()
            .variable("a", "actor", {"id-label": "UpdatedUser"})
            .build()
        )
        
        assert "update" in query
        assert "$a isa actor" in query
    
    def test_relation_with_links(self):
        """Test relation with links keyword."""
        query = (QueryBuilder()
            .match()
            .variable("p", "actor", {"actor-id": "A1"})
            .variable("m", "message", {"message-id": "MSG1"})
            .relation("messaging")
                .links()
                .role("producer", "$p")
                .role("message", "$m")
            .fetch(["m"])
            .build()
        )
        
        assert "links" in query
        assert "producer: $p" in query
        assert "message: $m" in query
    
    def test_relation_without_links(self):
        """Test relation without links keyword."""
        query = (QueryBuilder()
            .match()
            .variable("p", "actor", {"actor-id": "A1"})
            .variable("m", "message", {"message-id": "MSG1"})
            .relation("messaging")
                .role("producer", "$p")
                .role("message", "$m")
            .fetch(["m"])
            .build()
        )
        
        assert "links" not in query
        assert "(producer: $p, message: $m)" in query
    
    def test_order_by(self):
        """Test ORDER BY clause."""
        query = (QueryBuilder()
            .match()
            .variable("x", "actor")
            .order_by("x", "order")
            .fetch(["x"])
            .build()
        )
        
        assert "order by $x has order asc" in query
    
    def test_offset_and_limit(self):
        """Test OFFSET and LIMIT clauses."""
        query = (QueryBuilder()
            .match()
            .variable("x", "actor")
            .offset(10)
            .limit(5)
            .fetch(["x"])
            .build()
        )
        
        assert "offset 10" in query
        assert "limit 5" in query
    
    def test_reduce(self):
        """Test REDUCE clause."""
        query = (QueryBuilder()
            .match()
            .variable("f", "file")
            .variable("s", None)
            .reduce("$s", "sum", "f")
            .build()
        )
        
        assert "reduce sum($s) groupby $f" in query
    
    def test_reduce_without_groupby(self):
        """Test REDUCE clause without groupby."""
        query = (QueryBuilder()
            .match()
            .variable("x", "actor")
            .reduce("$x", "count")
            .build()
        )
        
        assert "reduce count($x)" in query
    
    def test_with_function(self):
        """Test WITH clause for functions."""
        query = (QueryBuilder()
            .with_function("fun path($start: node) -> { node }: match {}; return { $start };")
            .match()
            .variable("n", "node")
            .fetch(["n"])
            .build()
        )
        
        assert "with" in query
        assert "fun path($start: node)" in query
    
    def test_nested_fetch(self):
        """Test nested fetch structure."""
        query = (QueryBuilder()
            .match()
            .variable("p", "publisher")
            .fetch({
                "name": "$p.name",
                "titles": {
                    "a": "$b.title",
                    "b": "$c.title"
                }
            })
            .build()
        )
        
        assert 'fetch {' in query
        assert '"name": $p.name' in query
        assert '"titles": {' in query
    
    def test_get_tql(self):
        """Test get_tql method."""
        query = (QueryBuilder()
            .match()
            .variable("x", "actor", {"actor-id": "A1"})
            .variable("y", "actor", {"actor-id": "A2"})
            .fetch(["x", "y"])
        )
        
        tql = query.get_tql()
        expected = 'match $x isa actor, has actor-id "A1"; $y isa actor, has actor-id "A2"; fetch {"x": {$x.*}, "y": {$y.*}};'
        assert tql == expected
    
    def test_get_tql_cached(self):
        """Test that get_tql caches the query."""
        query = (QueryBuilder()
            .match()
            .variable("x", "actor", {"actor-id": "A1"})
            .fetch(["x"])
        )
        
        tql1 = query.get_tql()
        tql2 = query.get_tql()
        assert tql1 == tql2
    
    def test_update_variable_new(self):
        """Test update_variable creates new variable if it doesn't exist."""
        query = QueryBuilder.insert_template()
        var = query.update_variable("x", "actor", {"actor-id": "A1"})
        assert var.name == "x"
        assert var.type == "actor"
        assert var.attributes["actor-id"] == "A1"
    
    def test_update_variable_existing(self):
        """Test update_variable updates existing variable."""
        query = QueryBuilder.insert_template()
        query.variable("x", "actor")
        query.update_variable("x", "actor", {"actor-id": "A1"})
        tql = query.get_tql()
        assert 'has actor-id "A1"' in tql
    
    def test_update_variable_clears_cache(self):
        """Test update_variable clears the query cache."""
        query = QueryBuilder.insert_template()
        query.variable("x", "actor", {"actor-id": "A1"})
        tql1 = query.get_tql()
        
        query.update_variable("x", "actor", {"actor-id": "A2"})
        tql2 = query.get_tql()
        
        assert tql1 != tql2
        assert 'has actor-id "A1"' in tql1
        assert 'has actor-id "A2"' in tql2
    
    def test_clear_variable(self):
        """Test clear_variable removes variable."""
        query = QueryBuilder.insert_template()
        query.variable("x", "actor")
        assert "x" in query.variables
        
        query.clear_variable("x")
        assert "x" not in query.variables
    
    def test_clear_all_variables(self):
        """Test clear_all_variables removes all variables."""
        query = QueryBuilder.insert_template()
        query.variable("x", "actor")
        query.variable("y", "message")
        assert len(query.variables) == 2
        
        query.clear_all_variables()
        assert len(query.variables) == 0
    
    def test_get_variable(self):
        """Test get_variable returns variable."""
        query = QueryBuilder.insert_template()
        query.variable("x", "actor")
        var = query.get_variable("x")
        assert var is not None
        assert var.name == "x"
    
    def test_clone(self):
        """Test clone creates deep copy."""
        base = QueryBuilder.match_template()
        base.variable("x", "actor", {"actor-id": "A1"})
        
        clone = base.clone()
        assert clone is not base
        assert clone.variables is not base.variables
        
        # Modify clone and ensure base is unchanged
        clone.update_variable("x", "actor", {"actor-id": "A2"})
        
        base_tql = base.get_tql()
        clone_tql = clone.get_tql()
        
        assert 'has actor-id "A1"' in base_tql
        assert 'has actor-id "A2"' in clone_tql
    
    def test_class_methods(self):
        """Test class methods for creating templates."""
        match_qb = QueryBuilder.match_template()
        assert match_qb._mode == "match"
        
        insert_qb = QueryBuilder.insert_template()
        assert insert_qb._mode == "insert"
        
        put_qb = QueryBuilder.put_template()
        assert put_qb._mode == "put"
        
        delete_qb = QueryBuilder.delete_template()
        assert delete_qb._mode == "delete"
    
    def test_multiple_variables(self):
        """Test multiple variables in same query."""
        query = (QueryBuilder()
            .match()
            .variable("a", "actor", {"actor-id": "A1"})
            .variable("m", "message", {"message-id": "MSG1"})
            .fetch(["a", "m"])
            .build()
        )
        
        assert "$a isa actor" in query
        assert "$m isa message" in query
        assert "fetch {\"a\": {$a.*}, \"m\": {$m.*}}" in query
    
    def test_multiple_relations(self):
        """Test multiple relations in same query."""
        query = (QueryBuilder()
            .match()
            .variable("a1", "actor")
            .variable("a2", "actor")
            .variable("m", "message")
            .relation("messaging").links().role("producer", "$a1").role("message", "$m")
            .relation("messaging").links().role("consumer", "$a2").role("message", "$m")
            .fetch(["m"])
            .build()
        )
        
        assert query.count("messaging") == 2
    
    def test_escape_quotes_in_string(self):
        """Test that quotes are properly escaped in string values."""
        query = (QueryBuilder()
            .insert()
            .variable("a", "actor", {
                "id-label": 'User "Admin"',
                "description": "He said 'hello'"
            })
            .build()
        )
        
        assert 'has id-label "User \\"Admin\\""' in query
        assert "has description \"He said 'hello'\"" in query
    
    def test_undefine_query(self):
        """Test UNDEFINE query."""
        query = (QueryBuilder()
            .undefine()
            .variable("x", "actor")
            .build()
        )
        
        assert "undefine" in query
    
    def test_redefine_query(self):
        """Test REDEFINE query."""
        query = (QueryBuilder()
            .redefine()
            .variable("x", "actor")
            .build()
        )
        
        assert "redefine" in query
    
    def test_define_query(self):
        """Test DEFINE query."""
        query = (QueryBuilder()
            .define()
            .variable("x", "actor")
            .build()
        )
        
        assert "define" in query


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
