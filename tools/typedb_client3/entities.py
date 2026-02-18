"""TypeDB v3 Client Library - Entity and Relation Classes

Defines all entities and relations from the typedb_schema_2.tql file.
These are dataclasses that can be used with EntityManager for CRUD operations.
"""

import uuid
from typing import ClassVar, Optional, Dict, List, Any, Tuple
from dataclasses import dataclass


@dataclass
class Entity:
    """Base class for TypeDB entities with schema metadata."""
    
    _type: ClassVar[str] = ""  # TypeDB entity type name
    _key_attr: ClassVar[Optional[str]] = None  # Primary key attribute
    
    def get_key_value(self) -> Any:
        """Get the value of the key attribute."""
        if not self._key_attr:
            raise ValueError(f"No key attribute defined for {self.__class__.__name__}")
        
        # Find the attribute in the dataclass fields
        for field_name, field in self.__dataclass_fields__.items():
            # Convert field name to TypeDB attribute name (id_label -> id-label)
            db_attr_name = field_name.replace('_', '-')
            if db_attr_name == self._key_attr:
                return getattr(self, field_name)
        
        raise ValueError(f"Key attribute {self._key_attr} not found in entity")
    
    def to_insert_query(self) -> str:
        """Generate INSERT query for this entity.
        
        Returns:
            TypeQL INSERT query string
        """
        var_name = self.__class__.__name__.lower()[:1]  # Single letter variable
        
        parts = [f"${var_name} isa {self._type}"]
        
        # Add attributes
        for field_name in self.__dataclass_fields__.keys():
            value = getattr(self, field_name)
            if value is not None:
                # Convert snake_case to kebab-case for TypeDB
                db_attr_name = field_name.replace('_', '-')
                parts.append(f'has {db_attr_name} {self._escape_value(value)}')
        
        return f"insert {', '.join(parts)};"
    
    def to_match_query(self) -> str:
        """Generate MATCH query to find this entity by key.
        
        Returns:
            TypeQL MATCH query string
        """
        if not self._key_attr:
            raise ValueError(f"No key attribute defined for {self.__class__.__name__}")
        
        key_value = self.get_key_value()
        var_name = self.__class__.__name__.lower()[:1]
        
        return f'match ${var_name} isa {self._type}, has {self._key_attr} {self._escape_value(key_value)};'
    
    def _escape_value(self, value: Any) -> str:
        """Escape a value for TypeQL.
        
        WARNING: This method is deprecated and should only be used for backward
        compatibility. Use to_parameterized_insert_query() instead for security.
        """
        if isinstance(value, str):
            escaped = value.replace('\\', '\\\\').replace('"', '\\"')
            return f'"{escaped}"'
        elif isinstance(value, bool):
            return str(value).lower()
        elif isinstance(value, (int, float)):
            return str(value)
        else:
            raise ValueError(f"Unsupported value type: {type(value)}")

    def _create_parameterized_value(self, value: Any, attribute_name: str) -> Tuple[str, Any]:
        """Create a parameterized placeholder for a value.
        
        This method prevents SQL/TypeQL injection by using parameterized queries
        instead of string escaping.
        
        Args:
            value: The value to parameterize
            attribute_name: The attribute name for the placeholder
            
        Returns:
            Tuple of (placeholder_string, parameter_value)
        """
        if value is None:
            return (None, None)
        
        # Generate unique placeholder using entity type, attribute, and UUID
        unique_suffix = str(uuid.uuid4())[:8]
        placeholder = f"${self._type}_{attribute_name}_{unique_suffix}"
        
        # Return placeholder and the raw value (to be bound by the client)
        return (placeholder, value)

    def to_parameterized_insert_query(self) -> Tuple[str, Dict[str, Any]]:
        """Generate parameterized INSERT query for this entity.
        
        This method is secure against injection attacks as it uses parameterized
        queries instead of string escaping.
        
        Returns:
            Tuple of (query_string, parameters_dict)
            - query_string: TypeQL INSERT query with placeholders
            - parameters_dict: Dictionary mapping placeholders to values
        """
        var_name = self.__class__.__name__.lower()[:1]  # Single letter variable
        parameters: Dict[str, Any] = {}
        
        parts = [f"${var_name} isa {self._type}"]
        
        # Add attributes with parameterized placeholders
        for field_name in self.__dataclass_fields__.keys():
            value = getattr(self, field_name)
            if value is not None:
                # Convert snake_case to kebab-case for TypeDB
                db_attr_name = field_name.replace('_', '-')
                placeholder, param_value = self._create_parameterized_value(value, field_name)
                if placeholder:
                    parts.append(f'has {db_attr_name} {placeholder}')
                    parameters[placeholder] = param_value
        
        query = f"insert {', '.join(parts)};"
        return (query, parameters)
    
    def to_parameterized_match_query(self) -> Tuple[str, Dict[str, Any]]:
        """Generate parameterized MATCH query to find this entity by key.
        
        This method is secure against injection attacks as it uses parameterized
        queries instead of string escaping.
        
        Returns:
            Tuple of (query_string, parameters_dict)
            - query_string: TypeQL MATCH query with placeholders
            - parameters_dict: Dictionary mapping placeholders to values
        """
        if not self._key_attr:
            raise ValueError(f"No key attribute defined for {self.__class__.__name__}")
        
        key_value = self.get_key_value()
        var_name = self.__class__.__name__.lower()[:1]
        
        # Convert key attribute from kebab-case to snake_case for field lookup
        key_field_name = self._key_attr.replace('-', '_')
        
        placeholder, param_value = self._create_parameterized_value(key_value, key_field_name)
        
        parameters = {placeholder: param_value} if placeholder else {}
        
        query = f'match ${var_name} isa {self._type}, has {self._key_attr} {placeholder};'
        
        return (query, parameters)


@dataclass
class Relation:
    """Base class for TypeDB relations."""
    
    _type: ClassVar[str] = ""  # TypeDB relation type name
    _roles: ClassVar[List[str]] = []  # Role names
    
    def to_insert_query(self, variables: Dict[str, str]) -> str:
        """Generate INSERT query for this relation.
        
        Args:
            variables: Mapping of role names to variable names
            
        Returns:
            TypeQL INSERT query string
        """
        role_parts = []
        for role in self._roles:
            if role in variables:
                role_parts.append(f"{role}: ${variables[role]}")
        
        return f"({', '.join(role_parts)}) isa {self._type};"


# ============================================================================
# Entity Classes from typedb_schema_2.tql
# ============================================================================

@dataclass
class Actor(Entity):
    """Actor entity representing a system component."""
    _type = "actor"
    _key_attr = "actor-id"
    
    actor_id: str
    id_label: str
    description: str
    justification: str


@dataclass
class Action(Entity):
    """Action entity representing a system action."""
    _type = "action"
    _key_attr = "action-id"
    
    action_id: str
    id_label: str
    description: str
    justification: str


@dataclass
class Message(Entity):
    """Message entity for inter-actor communication."""
    _type = "message"
    _key_attr = "message-id"
    
    message_id: str
    id_label: str
    description: str
    justification: str


@dataclass
class DataEntity(Entity):
    """DataEntity entity for domain data."""
    _type = "data-entity"
    _key_attr = "data-entity-id"
    
    data_entity_id: str
    id_label: str
    description: str
    justification: str


@dataclass
class Requirement(Entity):
    """Requirement entity for functional/non-functional requirements."""
    _type = "requirement"
    _key_attr = "requirement-id"
    
    requirement_id: str
    requirement_type: str
    status: str
    priority: str
    id_label: str
    description: str
    justification: str


@dataclass
class ActionAggregate(Entity):
    """ActionAggregate entity grouping actions."""
    _type = "action-aggregate"
    _key_attr = "action-agg-id"
    
    action_agg_id: str
    id_label: str
    description: str
    justification: str


@dataclass
class MessageAggregate(Entity):
    """MessageAggregate entity grouping messages."""
    _type = "message-aggregate"
    _key_attr = "message-agg-id"
    
    message_agg_id: str
    id_label: str
    description: str
    justification: str


@dataclass
class Constraint(Entity):
    """Constraint entity for message constraints."""
    _type = "constraint"
    _key_attr = "constraint-id"
    
    constraint_id: str
    id_label: str
    description: str


@dataclass
class Category(Entity):
    """Category entity for categorization."""
    _type = "category"
    _key_attr = "name"
    
    name: str


@dataclass
class TextBlock(Entity):
    """TextBlock entity for anchored text."""
    _type = "text-block"
    _key_attr = "anchor-id"
    
    anchor_id: str
    id_label: str
    anchor_type: str
    text: str
    order: int


@dataclass
class Concept(Entity):
    """Concept entity for candidate concepts."""
    _type = "concept"
    _key_attr = "concept-id"
    
    concept_id: str
    id_label: str
    description: str


@dataclass
class SpecDocument(Entity):
    """SpecDocument entity for specification documents."""
    _type = "spec-document"
    _key_attr = "spec-doc-id"
    
    spec_doc_id: str
    title: str
    version: str
    description: str


@dataclass
class SpecSection(Entity):
    """SpecSection entity for specification sections."""
    _type = "spec-section"
    _key_attr = "spec-section-id"
    
    spec_section_id: str
    title: str
    id_label: str
    order: int


# ============================================================================
# Relation Classes from typedb_schema_2.tql
# ============================================================================

@dataclass
class Messaging(Relation):
    """Messaging relation between Actors and Message."""
    _type = "messaging"
    _roles = ["producer", "consumer", "message"]
    
    producer: Actor
    consumer: Actor
    message: Message


@dataclass
class Anchoring(Relation):
    """Anchoring relation between TextBlock and domain entities."""
    _type = "anchoring"
    _roles = ["anchor", "concept"]
    
    anchor: TextBlock
    concept: Entity  # Can be any design-concept


@dataclass
class Membership(Relation):
    """Membership relation for grouping."""
    _type = "membership"
    _roles = ["member-of", "member"]
    
    member_of: Entity
    member: Entity


@dataclass
class MembershipSeq(Relation):
    """Ordered membership relation."""
    _type = "membership-seq"
    _roles = ["member-of", "member"]
    
    member_of: Entity
    member: Entity
    order: int


@dataclass
class Outlining(Relation):
    """Outlining relation for hierarchical structure."""
    _type = "outlining"
    _roles = ["section", "subsection"]
    
    section: Entity
    subsection: Entity


@dataclass
class Categorization(Relation):
    """Categorization relation."""
    _type = "categorization"
    _roles = ["category", "object"]
    
    category: Category
    object: Entity


@dataclass
class Requiring(Relation):
    """Requiring relation between Requirements and Concepts/Messages."""
    _type = "requiring"
    _roles = ["required-by", "conceptualized-as"]
    
    required_by: Requirement
    conceptualized_as: Entity


@dataclass
class ConstrainedBy(Relation):
    """ConstrainedBy relation."""
    _type = "constrained-by"
    _roles = ["constraint", "object"]
    
    constraint: Constraint
    object: Entity


@dataclass
class MessagePayload(Relation):
    """MessagePayload relation between Message and DataEntity."""
    _type = "message-payload"
    _roles = ["message", "payload"]
    
    message: Message
    payload: DataEntity


@dataclass
class Filesystem(Relation):
    """Filesystem relation for folder/file structure."""
    _type = "filesystem"
    _roles = ["folder", "entry"]
    
    folder: Entity
    entry: Entity
