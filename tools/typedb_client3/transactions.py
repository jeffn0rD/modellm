"""Transaction support for TypeDB client.

Provides:
- TransactionContext: Context manager for multi-operation transactions
"""

from typing import Any, Dict, List

from .exceptions import TypeDBQueryError


class TransactionContext:
    """Context manager for executing multiple operations in a single transaction.
    
    Example:
        with client.with_transaction("specifications", TransactionType.WRITE) as tx:
            tx.execute("insert $a isa actor, has actor-id \"A1\";")
            tx.execute("insert $a isa actor, has actor-id \"A2\";")
            # All operations committed when exiting context
    """
    
    def __init__(
        self,
        client: "TypeDBClient",
        database: str,
        transaction_type: "TransactionType"
    ) -> None:
        """Initialize transaction context.
        
        Args:
            client: TypeDBClient instance
            database: Database name
            transaction_type: READ or WRITE transaction
        """
        self.client = client
        self.database = database
        self.transaction_type = transaction_type
        self.operations: List[Dict[str, Any]] = []
    
    def execute(self, query: str) -> None:
        """Add a query to the transaction.
        
        Args:
            query: TypeQL query string
        """
        self.operations.append({"query": query})
    
    def execute_builder(self, builder: Any) -> None:
        """Add a query from a QueryBuilder to the transaction.
        
        Args:
            builder: QueryBuilder or any object with get_tql() method
            
        Raises:
            TypeError: If builder doesn't have get_tql() method
        """
        if hasattr(builder, 'get_tql'):
            self.operations.append({"query": builder.get_tql()})
        else:
            raise TypeError("Expected object with get_tql() method")
    
    def __enter__(self) -> "TransactionContext":
        """Enter transaction context."""
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Execute all operations in transaction when exiting context."""
        if self.operations:
            self.client.execute_transaction(
                self.database,
                self.transaction_type,
                self.operations
            )
