"""TypeDB v3 Client Library - Entity Manager

High-level API for entity operations using the TypeDB client.
"""

from typing import Type, TypeVar, Optional, List, Dict, Any

from .client import TypeDBClient, TransactionType
from .entities import Entity, Relation
from .query_builder import QueryBuilder

T = TypeVar('T', bound=Entity)


class EntityManager:
    """High-level API for entity operations."""
    
    def __init__(self, client: TypeDBClient, database: str):
        self.client = client
        self.database = database
    
    def insert(self, entity: Entity) -> None:
        """Insert an entity.
        
        Args:
            entity: Entity instance to insert
            
        Raises:
            TypeDBQueryError: If entity already exists
        """
        query = entity.to_insert_query()
        self.client.execute_query(
            database=self.database,
            query=query,
            transaction_type=TransactionType.WRITE
        )
    
    def put(self, entity: Entity) -> None:
        """Put an entity (idempotent - checks existence first).
        
        Args:
            entity: Entity instance to put
        """
        # Build PUT query
        var_name = entity.__class__.__name__.lower()[:1]
        parts = [f"${var_name} isa {entity._type}"]
        
        # Add attributes
        for field_name in entity.__dataclass_fields__.keys():
            value = getattr(entity, field_name)
            if value is not None:
                # Convert snake_case to kebab-case for TypeDB
                db_attr_name = field_name.replace('_', '-')
                parts.append(f'has {db_attr_name} {entity._escape_value(value)}')
        
        query = f"put {', '.join(parts)};"
        
        self.client.execute_query(
            database=self.database,
            query=query,
            transaction_type=TransactionType.WRITE
        )
    
    def fetch_one(
        self,
        entity_type: Type[T],
        filters: Dict[str, Any]
    ) -> Optional[T]:
        """Fetch a single entity by filters.
        
        Args:
            entity_type: Entity class to fetch
            filters: Attribute constraints
            
        Returns:
            Entity instance or None if not found
        """
        var_name = entity_type.__name__.lower()[:1]
        
        # Build match query using QueryBuilder
        qb = QueryBuilder()
        qb.match()
        qb.variable(var_name, entity_type._type)
        
        # Add filter constraints
        for attr, value in filters.items():
            qb.variables[var_name].has(attr, value)
        
        qb.fetch([var_name])
        
        query = qb.get_tql()
        
        result = self.client.execute_query(
            database=self.database,
            query=query,
            transaction_type=TransactionType.READ
        )
        
        # Parse result and return entity
        return self._parse_entity(result, entity_type)
    
    def fetch_all(
        self,
        entity_type: Type[T],
        filters: Optional[Dict[str, Any]] = None
    ) -> List[T]:
        """Fetch all entities matching filters.
        
        Args:
            entity_type: Entity class to fetch
            filters: Optional attribute constraints
            
        Returns:
            List of entity instances
        """
        var_name = entity_type.__name__.lower()[:1]
        
        # Build match query using QueryBuilder
        qb = QueryBuilder()
        qb.match()
        qb.variable(var_name, entity_type._type)
        
        # Add filter constraints
        if filters:
            for attr, value in filters.items():
                qb.variables[var_name].has(attr, value)
        
        qb.fetch([var_name])
        
        query = qb.get_tql()
        
        result = self.client.execute_query(
            database=self.database,
            query=query,
            transaction_type=TransactionType.READ
        )
        
        # Parse results and return list
        return self._parse_entities(result, entity_type)
    
    def exists(self, entity_type: Type[T], key_value: Any) -> bool:
        """Check if entity exists by key.
        
        Args:
            entity_type: Entity class
            key_value: Key attribute value
            
        Returns:
            True if entity exists
        """
        var_name = entity_type.__name__.lower()[:1]
        key_attr = entity_type._key_attr
        
        query = f'match ${var_name} isa {entity_type._type}, has {key_attr} {self._escape_value(key_value)};'
        
        result = self.client.execute_query(
            database=self.database,
            query=query,
            transaction_type=TransactionType.READ
        )
        
        return len(result.get("answers", [])) > 0
    
    def delete(self, entity: Entity) -> None:
        """Delete an entity.
        
        Args:
            entity: Entity instance to delete
        """
        query = entity.to_match_query().replace("match", "match") + " delete $e;"
        
        self.client.execute_query(
            database=self.database,
            query=query,
            transaction_type=TransactionType.WRITE
        )
    
    def insert_relation(self, relation: Relation) -> None:
        """Insert a relation.
        
        Args:
            relation: Relation instance
        """
        # For relations, we need to reference existing entities
        # This would use a more complex query builder
        pass
    
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
    
    def _parse_entity(
        self,
        result: Dict[str, Any],
        entity_type: Type[T]
    ) -> Optional[T]:
        """Parse a single entity from query result."""
        answers = result.get("answers", [])
        if not answers:
            return None
        
        # Extract entity data from first answer
        # Implementation depends on TypeDB HTTP API response format
        # This is a placeholder for now
        return None
    
    def _parse_entities(
        self,
        result: Dict[str, Any],
        entity_type: Type[T]
    ) -> List[T]:
        """Parse multiple entities from query result."""
        answers = result.get("answers", [])
        entities = []
        
        for answer in answers:
            # Extract entity data
            # Implementation depends on TypeDB HTTP API response format
            # This is a placeholder for now
            pass
        
        return entities
