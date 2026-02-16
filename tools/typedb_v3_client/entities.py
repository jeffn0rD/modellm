"""TypeDB v3 Client Library - Entity and Relation Classes

Defines all entities and relations from the typedb_schema_2.tql file.
These are dataclasses that can be used with EntityManager for CRUD operations.
"""

from typing import ClassVar, Optional, Dict, List, Any
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
