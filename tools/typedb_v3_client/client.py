"""TypeDB v3 Client Library - HTTP Client

Implements TypeDB v3 HTTP API client with:
- Authentication (JWT tokens)
- Query execution (read/write transactions)
- Transaction support (multiple operations)
- Database management (create, delete, list)
- Schema loading from TQL files
"""

import json
import requests
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List

from .exceptions import (
    TypeDBConnectionError, TypeDBAuthenticationError,
    TypeDBQueryError, TypeDBServerError, TypeDBValidationError
)


class TransactionType(Enum):
    """Transaction type for TypeDB operations."""
    READ = "read"
    WRITE = "write"


class TypeDBClient:
    """TypeDB v3 HTTP API client with authentication and connection pooling."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 30
    ):
        """Initialize client with connection details.
        
        Args:
            base_url: TypeDB server URL
            username: TypeDB username (optional, for authentication)
            password: TypeDB password (optional, for authentication)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.timeout = timeout
        self._token: Optional[str] = None
        self._session = requests.Session()
        
        # Authenticate if credentials provided
        if username and password:
            self._authenticate()
    
    def _authenticate(self) -> None:
        """Authenticate with TypeDB server and get JWT token."""
        auth_url = f"{self.base_url}/auth/token"
        try:
            response = self._session.post(
                auth_url,
                json={"username": self.username, "password": self.password},
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            self._token = data.get("token")
            if not self._token:
                raise TypeDBAuthenticationError("No token received from auth endpoint")
        except requests.exceptions.RequestException as e:
            raise TypeDBConnectionError(f"Authentication failed: {e}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication token."""
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers
    
    def connect_database(self, database: str) -> bool:
        """Verify database exists and set as current.
        
        Args:
            database: Database name
            
        Returns:
            True if database exists or was created
        """
        if not self.database_exists(database):
            self.create_database(database)
        return True
    
    def list_databases(self) -> List[str]:
        """List all databases on the server.
        
        Returns:
            List of database names
        """
        url = f"{self.base_url}/databases"
        try:
            response = self._session.get(
                url,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            return data.get("databases", [])
        except requests.exceptions.RequestException as e:
            raise TypeDBConnectionError(f"Failed to list databases: {e}")
    
    def create_database(self, database: str) -> None:
        """Create a new database.
        
        Args:
            database: Database name to create
            
        Raises:
            TypeDBServerError: If database already exists or other server error
        """
        url = f"{self.base_url}/databases/{database}"
        try:
            response = self._session.post(
                url,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 409:
                raise TypeDBValidationError(f"Database '{database}' already exists")
            raise TypeDBServerError(f"Failed to create database: {e}")
        except requests.exceptions.RequestException as e:
            raise TypeDBConnectionError(f"Failed to create database: {e}")
    
    def delete_database(self, database: str) -> None:
        """Delete a database.
        
        Args:
            database: Database name to delete
            
        Raises:
            TypeDBServerError: If database doesn't exist or other server error
        """
        url = f"{self.base_url}/databases/{database}"
        try:
            response = self._session.delete(
                url,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise TypeDBValidationError(f"Database '{database}' does not exist")
            raise TypeDBServerError(f"Failed to delete database: {e}")
        except requests.exceptions.RequestException as e:
            raise TypeDBConnectionError(f"Failed to delete database: {e}")
    
    def database_exists(self, database: str) -> bool:
        """Check if database exists.
        
        Args:
            database: Database name
            
        Returns:
            True if database exists
        """
        try:
            databases = self.list_databases()
            return database in databases
        except TypeDBConnectionError:
            return False
    
    def execute_query(
        self,
        database: str,
        query: str,
        transaction_type: TransactionType = TransactionType.READ
    ) -> Dict[str, Any]:
        """Execute a raw TypeQL query.
        
        Args:
            database: Database name
            query: TypeQL query string (should use 'fetch' for TypeDB v3)
            transaction_type: READ or WRITE transaction
            
        Returns:
            Query results as JSON
            
        Raises:
            TypeDBQueryError: If query is invalid
            TypeDBConnectionError: If connection fails
        """
        url = f"{self.base_url}/api/v1/databases/{database}/transaction"
        payload = {
            "transaction_type": transaction_type.value,
            "query": query
        }
        
        try:
            response = self._session.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_msg = f"Query execution failed: {e}"
            try:
                error_data = e.response.json()
                error_msg += f" - {error_data.get('message', '')}"
            except:
                pass
            raise TypeDBQueryError(error_msg, query=query)
        except requests.exceptions.RequestException as e:
            raise TypeDBConnectionError(f"Failed to execute query: {e}")
    
    def execute_transaction(
        self,
        database: str,
        transaction_type: TransactionType,
        operations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute multiple operations in a single transaction.
        
        Args:
            database: Database name
            transaction_type: READ or WRITE
            operations: List of operation dictionaries
            
        Returns:
            Combined results
            
        Example:
            # Execute multiple writes in one transaction
            operations = [
                {"query": "insert $a isa actor, has actor-id \"A1\";"},
                {"query": "insert $a isa actor, has actor-id \"A2\";"},
            ]
            result = client.execute_transaction(
                "specifications", 
                TransactionType.WRITE, 
                operations
            )
        """
        url = f"{self.base_url}/api/v1/databases/{database}/transaction"
        payload = {
            "transaction_type": transaction_type.value,
            "operations": operations
        }
        
        try:
            response = self._session.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=self.timeout * 2  # Longer timeout for transactions
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_msg = f"Transaction execution failed: {e}"
            try:
                error_data = e.response.json()
                error_msg += f" - {error_data.get('message', '')}"
            except:
                pass
            raise TypeDBQueryError(error_msg, details={"operations": operations})
        except requests.exceptions.RequestException as e:
            raise TypeDBConnectionError(f"Failed to execute transaction: {e}")
    
    def execute_queries(
        self,
        database: str,
        *queries: str,
        transaction_type: TransactionType = TransactionType.WRITE
    ) -> List[Dict[str, Any]]:
        """Execute multiple queries in a single transaction.
        
        Args:
            database: Database name
            *queries: Variable number of TypeQL queries
            transaction_type: READ or WRITE
            
        Returns:
            List of results for each query
            
        Example:
            results = client.execute_queries(
                "specifications",
                "insert $a isa actor, has actor-id \"A1\";",
                "insert $a isa actor, has actor-id \"A2\";",
                transaction_type=TransactionType.WRITE
            )
        """
        # Convert positional args to operations list
        operations = [{"query": q} for q in queries]
        return self.execute_transaction(database, transaction_type, operations)
    
    def with_transaction(self, database: str, transaction_type: TransactionType) -> "TransactionContext":
        """Create a transaction context for executing multiple operations.
        
        Args:
            database: Database name
            transaction_type: READ or WRITE
            
        Returns:
            TransactionContext manager
            
        Example:
            with client.with_transaction("specifications", TransactionType.WRITE) as tx:
                tx.execute("insert $a isa actor, has actor-id \"A1\";")
                tx.execute("insert $a isa actor, has actor-id \"A2\";")
                # All operations committed when exiting context
        """
        return TransactionContext(self, database, transaction_type)
    
    def load_schema(self, database: str, schema_path: Path) -> None:
        """Load TypeDB schema from TQL file.
        
        Args:
            database: Database name
            schema_path: Path to .tql schema file
            
        Raises:
            FileNotFoundError: If schema file doesn't exist
            TypeDBQueryError: If schema is invalid
        """
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")
        
        schema_content = schema_path.read_text()
        # Schema loading requires a schema transaction
        url = f"{self.base_url}/api/v1/databases/{database}/transaction"
        payload = {
            "transaction_type": "write",
            "query": schema_content,
            "request_type": "schema"  # Important for schema loading
        }
        
        try:
            response = self._session.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=self.timeout * 2
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            error_msg = f"Schema loading failed: {e}"
            try:
                error_data = e.response.json()
                error_msg += f" - {error_data.get('message', '')}"
            except:
                pass
            raise TypeDBQueryError(error_msg)
        except requests.exceptions.RequestException as e:
            raise TypeDBConnectionError(f"Failed to load schema: {e}")
    
    def clear_database(self, database: str) -> None:
        """Clear all data from database (keep schema).
        
        Args:
            database: Database name
        """
        # TypeDB doesn't have a direct clear operation
        # We delete all concept instances using a query
        query = """
            match $x isa entity; delete $x;
            match $r isa relation; delete $r;
        """
        self.execute_query(database, query, TransactionType.WRITE)
    
    def close(self) -> None:
        """Close all connections and cleanup resources."""
        self._session.close()


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
        transaction_type: TransactionType
    ):
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
    
    def execute_builder(self, builder) -> None:
        """Add a query from a QueryBuilder to the transaction.
        
        Args:
            builder: QueryBuilder or any object with get_tql() method
        """
        if hasattr(builder, 'get_tql'):
            self.operations.append({"query": builder.get_tql()})
        else:
            raise TypeError("Expected object with get_tql() method")
    
    def __enter__(self) -> "TransactionContext":
        """Enter transaction context."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Execute all operations in transaction when exiting context."""
        if self.operations:
            self.client.execute_transaction(
                self.database,
                self.transaction_type,
                self.operations
            )
