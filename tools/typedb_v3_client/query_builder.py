"""TypeDB v3 Client Library - Query Builder

Implements fluent API for building TypeDB v3 queries with support for:
- fetch (replaces get)
- put (idempotent writes)
- links (role player connections)
- label (type labels)
- reduce (aggregation with grouping)
- with (ad-hoc functions)
"""

from typing import Optional, Union, Dict, List, Any, Tuple


class Variable:
    """Represents a TypeQL v3 variable with type and constraints.
    
    All variables must use $ prefix per TypeQL v3 specification.
    """
    
    def __init__(self, name: str):
        # Ensure name doesn't include $ (it's added automatically)
        self.name = name.lstrip('$')
        self.type: Optional[str] = None
        self.attributes: Dict[str, Any] = {}
        self.has_constraints: bool = False
        self.label_constraint: Optional[str] = None  # TypeDB v3: label keyword
    
    def isa(self, type_name: str) -> "Variable":
        """Set the TypeDB type of this variable (isa keyword).
        
        Args:
            type_name: Entity or relation type name
            
        Returns:
            Self for method chaining
        """
        self.type = type_name
        return self
    
    def has(self, attribute: str, value: Any) -> "Variable":
        """Add an attribute constraint (has keyword).
        
        Args:
            attribute: Attribute name
            value: Attribute value (will be properly escaped)
            
        Returns:
            Self for method chaining
        """
        self.attributes[attribute] = value
        self.has_constraints = True
        return self
    
    def label(self, type_label: str) -> "Variable":
        """Add a label constraint (TypeDB v3: label keyword).
        
        Args:
            type_label: Type label string
            
        Returns:
            Self for method chaining
        """
        self.label_constraint = type_label
        return self
    
    def __str__(self) -> str:
        """Generate TypeQL variable string.
        
        Examples:
            $x isa actor, has actor-id "A1"
            $u isa user, label $type_label
        """
        parts = [f"${self.name}"]
        type_or_label = []
        if self.type:
            type_or_label.append(f"isa {self.type}")
        if self.label_constraint:
            type_or_label.append(f"label {self.label_constraint}")
        
        # Build the final string
        result_parts = []
        
        # Variable name and type/label (ISA and LABEL are comma-separated when both present)
        if type_or_label:
            result_parts.append(f"${self.name} {', '.join(type_or_label)}")
        else:
            result_parts.append(f"${self.name}")
        
        # Attributes are comma-separated
        if self.attributes:
            attr_parts = []
            for attr, value in self.attributes.items():
                escaped = self._escape_value(value)
                attr_parts.append(f'has {attr} {escaped}')
            result_parts.append(", ".join(attr_parts))
        
        # Join with comma between type/label and attributes
        return ", ".join(result_parts)
    
    def _escape_value(self, value: Any) -> str:
        """Escape a value for TypeQL."""
        if isinstance(value, str):
            escaped = value.replace('\\', '\\\\').replace('"', '\\"')
            return f'"{escaped}"'
        elif isinstance(value, bool):
            return str(value).lower()
        elif isinstance(value, (int, float)):
            return str(value)
        else:
            raise ValueError(f"Unsupported value type: {type(value)}")


class RelationBuilder:
    """Builder for relations in queries."""
    
    def __init__(self, query_builder: "QueryBuilder", relation_type: str):
        self.query_builder = query_builder
        self.relation_type = relation_type
        self.roles: List[Dict[str, str]] = []
        self.var_name: Optional[str] = None
        self.use_links: bool = False
    
    def role(self, role_name: str, variable: str) -> "RelationBuilder":
        """Add a role to the relation.
        
        Args:
            role_name: Role name (e.g., "producer", "consumer")
            variable: Variable name (e.g., "$actor")
            
        Returns:
            Self for method chaining
        """
        # Strip $ prefix if present
        var_name = variable.lstrip('$')
        self.roles.append({"name": role_name, "variable": var_name})
        return self
    
    def links(self) -> "RelationBuilder":
        """Use TypeDB v3 links keyword for role players.
        
        Returns:
            Self for method chaining
        """
        self.use_links = True
        return self
    
    def as_variable(self, var_name: str) -> "RelationBuilder":
        """Assign this relation to a variable name.
        
        Args:
            var_name: Variable name (without $)
            
        Returns:
            Self for method chaining
        """
        self.var_name = var_name
        return self
    
    def end_relation(self) -> "QueryBuilder":
        """Finish defining relation and return to QueryBuilder."""
        relation_def = {
            "type": self.relation_type,
            "roles": self.roles,
            "var_name": self.var_name,
            "use_links": self.use_links
        }
        self.query_builder.relations.append(relation_def)
        return self.query_builder
    
    # Alias for convenience
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_relation()
        return False
    
    def __getattr__(self, name: str):
        """Forward unknown methods to QueryBuilder after ending the relation.
        
        This allows chaining like:
            .relation("type").role(...).fetch(["x"])
        where .fetch() is actually called on the QueryBuilder.
        """
        # First, end this relation
        self.end_relation()
        # Then forward the method call to QueryBuilder
        return getattr(self.query_builder, name)


class QueryBuilder:
    """Fluent API for building TypeQL v3 queries.
    
    Key Features:
    - Reusable query instances: Build once, execute many times
    - Parameter updates: Modify variables before each execution
    - TQL output: Get the TypeQL string before execution
    - TypeDB v3 Compliance: fetch, put, links, label, reduce, with, update
    """
    
    def __init__(self, mode: Optional[str] = None):
        """Initialize QueryBuilder with optional mode.
        
        Args:
            mode: Optional query mode (match, insert, delete, put, update)
        """
        self.variables: Dict[str, Variable] = {}
        self.relations: List[Dict[str, Any]] = []
        self._mode: Optional[str] = mode
        self._fetch_vars: Optional[Union[List[str], Dict[str, Any]]] = None
        self._order_by: Optional[Tuple[str, str]] = None
        self._offset: Optional[int] = None
        self._limit: Optional[int] = None
        self._reduce: Optional[Dict[str, Any]] = None
        self._with_clauses: List[str] = []
        self._built_query: Optional[str] = None  # Cache built query
    
    # Class methods for creating reusable query templates
    @classmethod
    def match_template(cls) -> "QueryBuilder":
        """Create a reusable MATCH query template."""
        return cls(mode="match")
    
    @classmethod
    def insert_template(cls) -> "QueryBuilder":
        """Create a reusable INSERT query template."""
        return cls(mode="insert")
    
    @classmethod
    def put_template(cls) -> "QueryBuilder":
        """Create a reusable PUT query template."""
        return cls(mode="put")
    
    @classmethod
    def delete_template(cls) -> "QueryBuilder":
        """Create a reusable DELETE query template."""
        return cls(mode="delete")
    
    def match(self) -> "QueryBuilder":
        """Start a MATCH query."""
        self._mode = "match"
        return self
    
    def insert(self) -> "QueryBuilder":
        """Start an INSERT query."""
        self._mode = "insert"
        return self
    
    def put(self) -> "QueryBuilder":
        """Start a PUT query (TypeDB v3: idempotent write).
        
        PUT checks if a pattern exists before inserting,
        preventing duplicates across concurrent transactions.
        """
        self._mode = "put"
        return self
    
    def delete(self) -> "QueryBuilder":
        """Start a DELETE query."""
        self._mode = "delete"
        return self
    
    def update(self) -> "QueryBuilder":
        """Start an UPDATE query (TypeDB v3: modify existing data).
        
        UPDATE is specialized for modifying data with cardinality at most 1.
        """
        self._mode = "update"
        return self
    
    def define(self) -> "QueryBuilder":
        """Start a DEFINE query (schema definition)."""
        self._mode = "define"
        return self
    
    def undefine(self) -> "QueryBuilder":
        """Start a UNDEFINE query (schema removal)."""
        self._mode = "undefine"
        return self
    
    def redefine(self) -> "QueryBuilder":
        """Start a REDEFINE query (schema modification)."""
        self._mode = "redefine"
        return self
    
    def variable(
        self,
        name: str,
        type_name: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> "QueryBuilder":
        """Define a variable in the query.
        
        Args:
            name: Variable name (without $)
            type_name: Optional TypeDB type
            attributes: Optional attribute constraints
            
        Returns:
            Self for method chaining
            
        Note:
            To access the Variable object, use get_variable(name)
        """
        var = Variable(name)
        if type_name:
            var.isa(type_name)
        if attributes:
            for attr, value in attributes.items():
                var.has(attr, value)
        self.variables[name] = var
        return self
    
    def relation(self, relation_type: str) -> "RelationBuilder":
        """Start defining a relation.
        
        Args:
            relation_type: TypeDB relation type name
            
        Returns:
            RelationBuilder for chaining
        """
        return RelationBuilder(self, relation_type)
    
    def fetch(self, variables: Union[List[str], Dict[str, Any]]) -> "QueryBuilder":
        """Add FETCH clause (TypeDB v3 syntax).
        
        Args:
            variables: List of variable names or dict for nested fetch
            
        Returns:
            Self for method chaining
            
        Example:
            .fetch(["message", "aggregate"])
            # or for nested fetch:
            .fetch({
                "name": "$p.name",
                "titles": {
                    "match": [...],
                    "fetch": [...]
                }
            })
        """
        self._fetch_vars = variables
        return self
    
    def order_by(self, variable: str, attribute: str) -> "QueryBuilder":
        """Add ORDER BY clause.
        
        Args:
            variable: Variable name
            attribute: Attribute to order by
            
        Returns:
            Self for method chaining
        """
        self._order_by = (variable, attribute)
        return self
    
    def offset(self, count: int) -> "QueryBuilder":
        """Add OFFSET clause.
        
        Args:
            count: Number of rows to skip
            
        Returns:
            Self for method chaining
        """
        self._offset = count
        return self
    
    def limit(self, count: int) -> "QueryBuilder":
        """Add LIMIT clause.
        
        Args:
            count: Maximum number of rows to return
            
        Returns:
            Self for method chaining
        """
        self._limit = count
        return self
    
    def reduce(self, variable: str, aggregation: str, groupby: Optional[str] = None) -> "QueryBuilder":
        """Add REDUCE clause for aggregation.
        
        Args:
            variable: Variable to aggregate (e.g., "$s")
            aggregation: Aggregation function (e.g., "sum", "count", "mean")
            groupby: Optional variable to group by
            
        Returns:
            Self for method chaining
            
        Example:
            .reduce("$s", "sum", "$f")  # sum($s) groupby $f
        """
        self._reduce = {
            "variable": variable,
            "aggregation": aggregation,
            "groupby": groupby
        }
        return self
    
    def with_function(self, fun_def: str) -> "QueryBuilder":
        """Add WITH clause for ad-hoc function definition.
        
        Args:
            fun_def: Function definition string
            
        Returns:
            Self for method chaining
            
        Example:
            .with_function("fun path($start: node) -> { node }: ...")
        """
        self._with_clauses.append(fun_def)
        return self
    
    def build(self) -> str:
        """Build and return the complete TypeQL query string.
        
        Returns:
            Valid TypeDB v3 TypeQL query string
        """
        if not self._mode:
            raise ValueError("Query mode not set (match/insert/delete/put/update)")
        
        # Use a list to collect query segments
        segments = []
        
        # Build WITH preamble (for functions)
        if self._with_clauses:
            segments.append("with")
            segments.append("; ".join(self._with_clauses))
        
        # Build MATCH clause
        if self._mode in ["match", "delete", "update", "undefine"]:
            match_parts = []
            for name, var in self.variables.items():
                if var.type or var.attributes or var.label_constraint:
                    match_parts.append(str(var))
            for rel in self.relations:
                match_parts.append(self._build_relation_match(rel))
            
            if match_parts:
                # Combine match keyword with first pattern (no semicolon between)
                segments.append("match " + match_parts[0])
                # Add remaining patterns with semicolons
                for part in match_parts[1:]:
                    segments.append(part)
        
        # Build INSERT/PUT/UPDATE/DEFINE/UNDEFINE/REDEFINE clause
        if self._mode in ["insert", "put", "update", "define", "undefine", "redefine"]:
            insert_parts = []
            for name, var in self.variables.items():
                if var.type or var.attributes:
                    insert_parts.append(str(var))
            for rel in self.relations:
                insert_parts.append(self._build_relation_insert(rel))
            
            if insert_parts:
                # Combine mode keyword with first part
                segments.append(f"{self._mode} {insert_parts[0]}")
                # Add remaining parts
                for part in insert_parts[1:]:
                    segments.append(part)
        
        # Build DELETE clause
        if self._mode == "delete":
            delete_parts = []
            for name, var in self.variables.items():
                delete_parts.append(f"${name}")
            for rel in self.relations:
                delete_parts.append(f"${rel.get('var_name', 'r')}")
            
            if delete_parts:
                segments.append("delete")
                segments.append(", ".join(delete_parts))
        
        # Build REDUCE clause (TypeDB v3)
        if self._reduce and self._mode == "match":
            agg_var = self._reduce["variable"]
            agg_func = self._reduce["aggregation"]
            groupby = self._reduce.get("groupby")
            
            if groupby:
                segments.append(f"reduce {agg_func}({agg_var}) groupby ${groupby}")
            else:
                segments.append(f"reduce {agg_func}({agg_var})")
        
        # Build FETCH clause (TypeDB v3)
        if self._mode == "match" and self._fetch_vars:
            if isinstance(self._fetch_vars, dict):
                # Nested fetch structure
                fetch_parts = self._build_nested_fetch(self._fetch_vars)
                segments.append(f"fetch { {fetch_parts} }")
            else:
                # Simple list fetch
                fetch_vars = [f'"{var}": {{${var}.*}}' for var in self._fetch_vars]
                segments.append(f"fetch {{{', '.join(fetch_vars)}}}")
        
        # Build ORDER BY clause
        if self._order_by:
            var_name, attr = self._order_by
            segments.append(f"order by ${var_name} has {attr} asc")
        
        # Build OFFSET clause
        if self._offset is not None:
            segments.append(f"offset {self._offset}")
        
        # Build LIMIT clause
        if self._limit is not None:
            segments.append(f"limit {self._limit}")
        
        return "; ".join(segments) + ";"
    
    def _build_nested_fetch(self, fetch_dict: Dict[str, Any], indent: int = 0) -> str:
        """Build nested fetch structure for complex JSON output.
        
        Args:
            fetch_dict: Dictionary defining fetch structure
            indent: Current indentation level
            
        Returns:
            TypeQL fetch string
        """
        lines = []
        indent_str = "  " * indent
        
        for key, value in fetch_dict.items():
            if isinstance(value, str):
                # Simple variable reference
                lines.append(f'{indent_str}"{key}": {value}')
            elif isinstance(value, dict):
                # Nested structure
                nested = self._build_nested_fetch(value, indent + 1)
                lines.append(f'{indent_str}"{key}": {nested}')
            elif isinstance(value, list):
                # Array of variables
                items = [f"${v}" for v in value]
                lines.append(f'{indent_str}"{key}": [{", ".join(items)}]')
        
        return "{{\n" + ",\n".join(lines) + "\n" + indent_str + "}}"
    
    def _build_relation_match(self, rel: Dict[str, Any]) -> str:
        """Build relation constraint for MATCH clause."""
        var_name = rel.get('var_name', 'r')
        rel_type = rel.get('type')
        roles = rel.get('roles', [])
        use_links = rel.get('use_links', False)
        
        if use_links:
            # TypeDB v3: use links keyword
            role_parts = []
            for role in roles:
                role_parts.append(f"{role['name']}: ${role['variable']}")
            return f"${var_name} isa {rel_type}, links ({', '.join(role_parts)});"
        else:
            # Legacy syntax (for compatibility)
            role_parts = []
            for role in roles:
                role_parts.append(f"{role['name']}: ${role['variable']}")
            return f"${var_name} isa {rel_type}, ({', '.join(role_parts)});"
    
    def _build_relation_insert(self, rel: Dict[str, Any]) -> str:
        """Build relation for INSERT clause."""
        rel_type = rel.get('type')
        roles = rel.get('roles', [])
        
        role_parts = []
        for role in roles:
            role_parts.append(f"{role['name']}: ${role['variable']}")
        
        return f"({', '.join(role_parts)}) isa {rel_type};"
    
    # Requirement: Get TQL string from query instance
    def get_tql(self) -> str:
        """Get the TypeQL string from the query instance.
        
        Returns:
            TypeQL query string (may be cached)
        
        Example:
            query = QueryBuilder().match().variable("x", "actor").build()
            tql = query.get_tql()
            # Returns: 'match $x isa actor;'
        """
        if self._built_query is None:
            self._built_query = self.build()
        return self._built_query
    
    # Requirement: Update variable parameters for reuse
    def update_variable(
        self,
        name: str,
        type_name: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Variable:
        """Update an existing variable's type or attributes.
        
        Args:
            name: Variable name (without $)
            type_name: New TypeDB type (or None to keep existing)
            attributes: New attributes (or None to keep existing)
            
        Returns:
            Updated Variable object
            
        Example:
            # Create reusable insert template
            insert_query = QueryBuilder.insert_template()
            
            # Use for first entity
            insert_query.update_variable(
                "a", "actor", {"actor-id": "A1", "id-label": "User1"}
            )
            tql1 = insert_query.get_tql()
            
            # Update for second entity (reuse query structure)
            insert_query.update_variable(
                "a", "actor", {"actor-id": "A2", "id-label": "User2"}
            )
            tql2 = insert_query.get_tql()
        """
        if name not in self.variables:
            # Create new variable if it doesn't exist
            var = Variable(name)
            if type_name:
                var.isa(type_name)
            if attributes:
                for attr, value in attributes.items():
                    var.has(attr, value)
            self.variables[name] = var
            return var
        
        var = self.variables[name]
        
        # Update type if provided
        if type_name is not None:
            var.isa(type_name)
        
        # Update attributes if provided
        if attributes is not None:
            var.attributes = attributes
        
        # Clear cached query since we modified it
        self._built_query = None
        
        return var
    
    def clear_variable(self, name: str) -> None:
        """Remove a variable from the query.
        
        Args:
            name: Variable name (without $)
        """
        if name in self.variables:
            del self.variables[name]
            self._built_query = None
    
    def clear_all_variables(self) -> None:
        """Remove all variables from the query."""
        self.variables.clear()
        self._built_query = None
    
    def get_variable(self, name: str) -> Optional[Variable]:
        """Get a variable by name.
        
        Args:
            name: Variable name (without $)
            
        Returns:
            Variable object or None
        """
        return self.variables.get(name)
    
    def clone(self) -> "QueryBuilder":
        """Create a deep copy of this query builder for reuse.
        
        Returns:
            New QueryBuilder instance with same configuration
            
        Example:
            # Create base template
            base_query = QueryBuilder.match_template()
            base_query.variable("x", "actor")
            
            # Clone for different executions
            query1 = base_query.clone()
            query1.update_variable("x", "actor", {"actor-id": "A1"})
            
            query2 = base_query.clone()
            query2.update_variable("x", "actor", {"actor-id": "A2"})
        """
        clone = QueryBuilder(mode=self._mode)
        clone.variables = {
            name: Variable(var.name)
            for name, var in self.variables.items()
        }
        # Copy variable state
        for name, var in self.variables.items():
            clone_var = clone.variables[name]
            clone_var.type = var.type
            clone_var.attributes = var.attributes.copy()
            clone_var.label_constraint = var.label_constraint
        
        clone.relations = self.relations.copy()
        clone._fetch_vars = self._fetch_vars.copy() if isinstance(self._fetch_vars, dict) else self._fetch_vars
        clone._order_by = self._order_by
        clone._offset = self._offset
        clone._limit = self._limit
        clone._reduce = self._reduce.copy() if self._reduce else None
        clone._with_clauses = self._with_clauses.copy()
        
        return clone
