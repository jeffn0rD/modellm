"""TypeDB v3 Client Library - Query Patterns

Pre-built query patterns for common TypeDB queries.
"""

from typing import Dict, Any

from .client import TypeDBClient, TransactionType
from .query_builder import QueryBuilder


class QueryPattern:
    """Base class for predefined query patterns."""
    
    def __init__(self, client: TypeDBClient, database: str):
        self.client = client
        self.database = database
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the query pattern with given parameters."""
        raise NotImplementedError


class MessagesByAction(QueryPattern):
    """Pattern: Get sequence of messages related to an action."""
    
    def execute(self, action_id: str) -> Dict[str, Any]:
        """Get messages related to a specific action.
        
        Args:
            action_id: Action ID (e.g., "ACT1")
            
        Returns:
            Dict with messages and their order
        """
        query = (QueryBuilder()
            .match()
            .variable("action", "action", {"action-id": action_id})
            .variable("message", "message")
            .variable("aggregate", "message-aggregate")
            .relation("messaging")
                .role("producer", "$action")
                .role("message", "$message")
            .relation("membership")
                .role("member-of", "$aggregate")
                .role("member", "$message")
            .order_by("message", "order")
            .fetch(["message", "aggregate"])
            .build()
        )
        
        return self.client.execute_query(
            database=self.database,
            query=query,
            transaction_type=TransactionType.READ
        )


class ConceptsByAnchor(QueryPattern):
    """Pattern: Get concepts anchored to a text block."""
    
    def execute(self, anchor_id: str) -> Dict[str, Any]:
        """Get concepts affected by a text block.
        
        Args:
            anchor_id: Text block anchor ID (e.g., "AN1")
            
        Returns:
            Dict with concepts
        """
        query = (QueryBuilder()
            .match()
            .variable("anchor", "text-block", {"anchor-id": anchor_id})
            .variable("concept", "concept")
            .relation("anchoring")
                .role("anchor", "$anchor")
                .role("concept", "$concept")
            .fetch(["concept"])
            .build()
        )
        
        return self.client.execute_query(
            database=self.database,
            query=query,
            transaction_type=TransactionType.READ
        )


class ConceptsByRequirement(QueryPattern):
    """Pattern: Get concepts needed for a requirement."""
    
    def execute(self, requirement_id: str) -> Dict[str, Any]:
        """Get concepts and messages needed for a requirement.
        
        Args:
            requirement_id: Requirement ID (e.g., "REQ-1")
            
        Returns:
            Dict with concepts and messages
        """
        query = (QueryBuilder()
            .match()
            .variable("req", "requirement", {"requirement-id": requirement_id})
            .variable("concept", "concept")
            .variable("message", "message")
            .relation("requiring")
                .role("required-by", "$req")
                .role("conceptualized-as", "$concept")
            .relation("requiring")
                .role("required-by", "$req")
                .role("conceptualized-as", "$message")
            .fetch(["concept", "message"])
            .build()
        )
        
        return self.client.execute_query(
            database=self.database,
            query=query,
            transaction_type=TransactionType.READ
        )


class MessagesByProducer(QueryPattern):
    """Pattern: Get messages produced by an actor."""
    
    def execute(self, actor_id: str) -> Dict[str, Any]:
        """Get messages produced by a specific actor.
        
        Args:
            actor_id: Actor ID (e.g., "A1")
            
        Returns:
            Dict with messages
        """
        query = (QueryBuilder()
            .match()
            .variable("actor", "actor", {"actor-id": actor_id})
            .variable("message", "message")
            .relation("messaging")
                .role("producer", "$actor")
                .role("message", "$message")
            .fetch(["message"])
            .build()
        )
        
        return self.client.execute_query(
            database=self.database,
            query=query,
            transaction_type=TransactionType.READ
        )


class ActionsByAggregate(QueryPattern):
    """Pattern: Get actions in an action aggregate."""
    
    def execute(self, aggregate_id: str) -> Dict[str, Any]:
        """Get actions in a specific action aggregate.
        
        Args:
            aggregate_id: Action aggregate ID (e.g., "AG1")
            
        Returns:
            Dict with actions
        """
        query = (QueryBuilder()
            .match()
            .variable("agg", "action-aggregate", {"action-agg-id": aggregate_id})
            .variable("action", "action")
            .relation("membership")
                .role("member-of", "$agg")
                .role("member", "$action")
            .order_by("action", "order")
            .fetch(["action"])
            .build()
        )
        
        return self.client.execute_query(
            database=self.database,
            query=query,
            transaction_type=TransactionType.READ
        )


class TextBlocksBySection(QueryPattern):
    """Pattern: Get text blocks in a section."""
    
    def execute(self, section_id: str) -> Dict[str, Any]:
        """Get text blocks belonging to a section.
        
        Args:
            section_id: Section ID (e.g., "S1")
            
        Returns:
            Dict with text blocks
        """
        query = (QueryBuilder()
            .match()
            .variable("section", "spec-section", {"spec-section-id": section_id})
            .variable("textblock", "text-block")
            .relation("outlining")
                .role("section", "$section")
                .role("subsection", "$textblock")
            .order_by("textblock", "order")
            .fetch(["textblock"])
            .build()
        )
        
        return self.client.execute_query(
            database=self.database,
            query=query,
            transaction_type=TransactionType.READ
        )


# Registry for all patterns
QUERY_PATTERNS = {
    "messages_by_action": MessagesByAction,
    "concepts_by_anchor": ConceptsByAnchor,
    "concepts_by_requirement": ConceptsByRequirement,
    "messages_by_producer": MessagesByProducer,
    "actions_by_aggregate": ActionsByAggregate,
    "text_blocks_by_section": TextBlocksBySection,
}
