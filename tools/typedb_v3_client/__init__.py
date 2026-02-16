"""TypeDB v3 Client Library

A Python library for TypeDB v3 operations with support for:
- TypeDB v3 syntax (fetch, put, links, label, reduce, with)
- Query builder with reusable templates
- Transaction support
- Entity/Relation abstractions
- Import utilities for YAML/JSON files
"""

# Version
__version__ = "0.1.0"

# Main exports
from .client import (
    TypeDBClient, TransactionType, TransactionContext,
    SecureTokenManager,
    validate_base_url, validate_credentials, validate_timeout,
    validate_operation_timeouts,
    create_optimized_session,
    DEFAULT_POOL_CONNECTIONS, DEFAULT_POOL_MAXSIZE,
    DEFAULT_MAX_RETRIES, DEFAULT_BACKOFF_FACTOR
)
from .query_builder import QueryBuilder, Variable, RelationBuilder
from .entities import (
    Entity, Relation,
    Actor, Action, Message, DataEntity, Requirement,
    ActionAggregate, MessageAggregate, Constraint, Category,
    TextBlock, Concept, SpecDocument, SpecSection,
    Messaging, Anchoring, Membership, MembershipSeq,
    Outlining, Categorization, Requiring, ConstrainedBy,
    MessagePayload, Filesystem
)
from .exceptions import (
    TypeDBError, TypeDBConnectionError, TypeDBAuthenticationError,
    TypeDBQueryError, TypeDBServerError, TypeDBValidationError
)
from .entity_manager import EntityManager
from .query_patterns import QUERY_PATTERNS, QueryPattern
from .importer import TypeDBImporter, create_importer, Colors, VerboseLevel, Logger

__all__ = [
    # Client
    "TypeDBClient",
    "TransactionType",
    "TransactionContext",
    "SecureTokenManager",
    "validate_base_url",
    "validate_credentials",
    "validate_timeout",
    "validate_operation_timeouts",
    "create_optimized_session",
    "DEFAULT_POOL_CONNECTIONS",
    "DEFAULT_POOL_MAXSIZE",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_BACKOFF_FACTOR",
    
    # Query Builder
    "QueryBuilder",
    "Variable",
    "RelationBuilder",
    
    # Entities
    "Entity",
    "Relation",
    "Actor",
    "Action",
    "Message",
    "DataEntity",
    "Requirement",
    "ActionAggregate",
    "MessageAggregate",
    "Constraint",
    "Category",
    "TextBlock",
    "Concept",
    "SpecDocument",
    "SpecSection",
    
    # Relations
    "Messaging",
    "Anchoring",
    "Membership",
    "MembershipSeq",
    "Outlining",
    "Categorization",
    "Requiring",
    "ConstrainedBy",
    "MessagePayload",
    "Filesystem",
    
    # Entity Manager
    "EntityManager",
    
    # Query Patterns
    "QUERY_PATTERNS",
    "QueryPattern",
    
    # Exceptions
    "TypeDBError",
    "TypeDBConnectionError",
    "TypeDBAuthenticationError",
    "TypeDBQueryError",
    "TypeDBServerError",
    "TypeDBValidationError",
    
    # Importer
    "TypeDBImporter",
    "create_importer",
    "Colors",
    "VerboseLevel",
    "Logger",
]
