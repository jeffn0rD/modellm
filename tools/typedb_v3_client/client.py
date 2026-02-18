"""TypeDB v3 Client Library - HTTP Client

Implements TypeDB v3 HTTP API client with:
- Authentication (JWT tokens)
- Query execution (read/write transactions)
- Transaction support (multiple operations)
- Database management (create, delete, list)
- Schema loading from TQL files
"""

import requests
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .auth import SecureTokenManager
from .exceptions import (
    TypeDBConnectionError, TypeDBAuthenticationError,
    TypeDBQueryError, TypeDBServerError, TypeDBValidationError
)
from .transactions import TransactionContext
from .validation import (
    validate_base_url,
    validate_credentials,
    validate_timeout,
    validate_operation_timeouts,
    create_optimized_session,
    DEFAULT_POOL_CONNECTIONS,
    DEFAULT_POOL_MAXSIZE,
    DEFAULT_MAX_RETRIES,
    DEFAULT_BACKOFF_FACTOR,
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
        timeout: int = 30,
        operation_timeouts: Optional[Dict[str, int]] = None
    ) -> None:
        """Initialize client with connection details.
        
        Args:
            base_url: TypeDB server URL
            username: TypeDB username (optional, for authentication)
            password: TypeDB password (optional, for authentication)
            timeout: Default request timeout in seconds
            operation_timeouts: Optional dict of operation-specific timeouts
            
        Raises:
            TypeDBValidationError: If any input parameters are invalid
        """
        # Validate inputs before using them
        self.base_url = validate_base_url(base_url)
        validate_credentials(username, password)
        self.timeout = validate_timeout(timeout)
        
        # Validate and store operation-specific timeouts
        self._operation_timeouts = validate_operation_timeouts(operation_timeouts or {})
        
        self.username = username
        self.password = password
        
        # Initialize secure token manager
        self._token_manager = SecureTokenManager()
        self._token_encrypted: Optional[str] = None  # Encrypted token for storage
        self._token: Optional[str] = None  # Decrypted token for current session
        self._token_cache_timeout = 30  # minutes
        
        # Create session with connection pooling (using optimized session)
        self._session = create_optimized_session()
        
        # Authenticate if credentials provided
        if username and password:
            self._authenticate()
    
    def _get_timeout_for_operation(self, operation: str) -> int:
        """Get timeout for a specific operation.
        
        Args:
            operation: Operation name (read_operation, write_operation, etc.)
            
        Returns:
            Timeout in seconds for the operation
        """
        return self._operation_timeouts.get(operation, self.timeout)
    
    def _authenticate(self) -> None:
        """Authenticate with TypeDB server and get JWT token."""
        
        auth_url = f"{self.base_url}/v1/signin"
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
            # Encrypt and store the token for potential external storage
            self._token_encrypted = self._token_manager.store_token(self._token)
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
        
        url = f"{self.base_url}/v1/databases"
        try:
            response = self._session.get(
                url,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            # TypeDB v3 returns format like [{"name": "db1"}, {"name": "db2"}]
            # Convert to list of strings
            databases = data.get("databases", [])
            if databases and isinstance(databases[0], dict):
                return [db.get("name") for db in databases if db.get("name") is not None]
            return databases  # fallback to original format
        except requests.exceptions.RequestException as e:
            raise TypeDBConnectionError(f"Failed to list databases: {e}")
    
    def create_database(self, database: str) -> None:
        """Create a new database.
        
        Args:
            database: Database name to create
            
        Raises:
            TypeDBValidationError: If database name is invalid
            TypeDBServerError: If database already exists or other server error
        """
        import requests
        
        url = f"{self.base_url}/v1/databases/{database}"
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
            # Check error message for "already exists"
            error_msg = ""
            try:
                error_data = e.response.json()
                error_msg = error_data.get("message", "").lower()
                print("create_database() *HTTPError*: " . error_msg)
            except Exception:
                pass
            
            # this apparantly never happens
            if "already exists" in error_msg or "exists" in error_msg:
                raise TypeDBValidationError(f"Database '{database}' already exists")
            raise TypeDBServerError(f"Failed to create database: {e}")
        except requests.exceptions.RequestException as e:
            raise TypeDBConnectionError(f"Failed to create database: {e}")
    
    def delete_database(self, database: str) -> None:
        """Delete a database.
        
        Args:
            database: Database name to delete
            
        Raises:
            TypeDBValidationError: If database doesn't exist
            TypeDBServerError: If other server error occurs
        """
        
        url = f"{self.base_url}/v1/databases/{database}"
        try:
            response = self._session.delete(
                url,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            # Check for both 404 and error message
            error_msg = ""
            try:
                error_data = e.response.json()
                error_msg = error_data.get("message", "").lower()
            except Exception:
                pass
            
            if e.response.status_code == 404 or "does not exist" in error_msg or "not found" in error_msg:
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
            # list_databases returns list of strings like ["db1", "db2"]
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
            query: TypeQL query string
            transaction_type: READ or WRITE transaction
            
        Returns:
            Query results as JSON
            
        Raises:
            TypeDBQueryError: If query is invalid
            TypeDBConnectionError: If connection fails
        """
        import requests
        
        # Use POST /v1/query endpoint (one-shot query)
        url = f"{self.base_url}/v1/query"
        
        # Build payload per API spec
        payload: Dict[str, Any] = {
            "databaseName": database,
            "transactionType": transaction_type.value,
            "query": query,
            "commit": True
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
            except Exception:
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
        import requests
        
        # Use POST /v1/query endpoint (one-shot query)
        url = f"{self.base_url}/v1/query"
        
        # Build payload per API spec
        all_queries = [op.get("query", "") for op in operations]
        
        # Combine all queries into one
        payload: Dict[str, Any] = {
            "databaseName": database,
            "transactionType": transaction_type.value,
            "query": " ".join(all_queries),
            "commit": True
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
            except Exception:
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
    
    def with_transaction(
        self, 
        database: str, 
        transaction_type: TransactionType
    ) -> TransactionContext:
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
    
    def load_schema(self, database: str, schema_path) -> None:
        """Load TypeDB schema from TQL file.
        
        Args:
            database: Database name
            schema_path: Path to .tql schema file (str or Path), or schema string
            
        Raises:
            FileNotFoundError: If schema file doesn't exist
            TypeDBQueryError: If schema is invalid
        """
        
        # Check if it's a file path or a schema string
        schema_content: str
        
        # is schema_path a string?
        if isinstance(schema_path, str):
            # Try to treat as file path first
            path = Path(schema_path)
            if path.exists():
                # It's a file
                schema_content = path.read_text()
            elif "\n" in schema_path or "define" in schema_path:
                # It's a schema string
                schema_content = schema_path
            else:
                raise FileNotFoundError(f"Schema file not found: {schema_path}")
            
        elif isinstance(schema_path, Path):
            path = Path(schema_path)
            if path.exists():
                # It's a file
                schema_content = path.read_text()
            else:
                raise FileNotFoundError(f"Schema file not found: {schema_path}")
        else:
            raise TypeDBValidationError("schema_path must be a file path or schema string")
        
        # Use POST /v1/query for schema loading with schema transaction type
        url = f"{self.base_url}/v1/query"
        payload = {
            "databaseName": database,
            "transactionType": "schema",
            "query": schema_content,
            "commit": True
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
            except Exception:
                pass
            raise TypeDBQueryError(error_msg)
        except requests.exceptions.RequestException as e:
            raise TypeDBConnectionError(f"Failed to load schema: {e}")
    
    def get_schema(self, database: str) -> str:
        """Fetch the database schema as TypeQL define string.
        
        Args:
            database: Database name
            
        Returns:
            TypeQL schema string (plain text, not JSON)
            
        Raises:
            TypeDBConnectionError: If connection fails
            TypeDBQueryError: If request fails
        """
        import requests
        
        url = f"{self.base_url}/v1/databases/{database}/schema"
        try:
            response = self._session.get(
                url,
                headers=self._get_headers(),
                timeout=self._get_timeout_for_operation('schema_operation')
            )
            response.raise_for_status()
            # Response is plain text, not JSON
            return response.text
        except requests.exceptions.HTTPError as e:
            error_msg = f"Failed to get schema: {e}"
            try:
                error_data = e.response.json()
                error_msg += f" - {error_data.get('message', '')}"
            except Exception:
                pass
            raise TypeDBQueryError(error_msg)
        except requests.exceptions.RequestException as e:
            raise TypeDBConnectionError(f"Failed to get schema: {e}")
    
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

    def wipe_database(self, database: str, verify: bool = True) -> bool:
        """Wipe all data from database safely (delete in dependency order).
        
        This method deletes all relations first (in dependency order), then deletes
        all entities (in dependency order) to avoid foreign key constraint violations.
        
        Args:
            database: Database name to wipe
            verify: Whether to verify the wipe was complete (default: True)
            
        Returns:
            bool: True if wipe was successful and verified (if verify=True)
            
        Raises:
            TypeDBConnectionError: If connection fails
            TypeDBQueryError: If delete query fails
        """
        # Relation types to delete in dependency order (must delete relations before entities)
        relation_types = [
            "message-payload",
            "constrained-by", 
            "requiring",
            "messaging",
            "membership-seq",
            "membership",
            "anchoring",
            "categorization",
            "outlining",
            "filesystem"
        ]
        
        # Entity types to delete in dependency order
        entity_types = [
            "constraint",
            "message-aggregate",
            "action-aggregate",
            "message",
            "requirement",
            "data-entity",
            "action",
            "actor",
            "category",
            "semantic-cue",
            "concept",
            "text-block",
            "spec-section",
            "spec-document",
            "fs-folder"
        ]
        
        # Delete relations first (in dependency order)
        for rel_type in relation_types:
            try:
                query = f"match $r isa {rel_type}; delete $r;"
                self.execute_query(database, query, TransactionType.WRITE)
            except TypeDBQueryError:
                # Relation type might not exist in schema, continue
                pass
        
        # Delete entities (in dependency order)
        for entity_type in entity_types:
            try:
                query = f"match $x isa {entity_type}; delete $x;"
                self.execute_query(database, query, TransactionType.WRITE)
            except TypeDBQueryError:
                # Entity type might not exist in schema, continue
                pass
        
        # Verify wipe if requested
        if verify:
            return self._verify_wipe(database)
        
        return True
    
    def _verify_wipe(self, database: str) -> bool:
        """Verify that database has been completely wiped.
        
        Checks for any remaining entities and relations in the database.
        
        Args:
            database: Database name to verify
            
        Returns:
            bool: True if database is completely empty
        """
        # Key entity types to check
        entity_types_to_check = [
            "spec-document",
            "spec-section", 
            "text-block",
            "concept",
            "actor",
            "action",
            "data-entity",
            "requirement",
            "constraint",
            "category",
            "semantic-cue",
            "message",
            "action-aggregate",
            "message-aggregate",
            "fs-folder"
        ]
        
        # Key relation types to check
        relation_types_to_check = [
            "outlining",
            "anchoring",
            "categorization",
            "membership",
            "messaging",
            "message-payload",
            "constrained-by",
            "requiring",
            "membership-seq",
            "filesystem"
        ]
        
        remaining: List[str] = []
        
        # Check for remaining entities
        for entity_type in entity_types_to_check:
            try:
                query = f"match $x isa {entity_type}; fetch $x;"
                result = self.execute_query(database, query, TransactionType.READ)
                if result and result.get("answers") and len(result["answers"]) > 0:
                    remaining.append(entity_type)
            except (TypeDBQueryError, TypeDBConnectionError):
                # Schema type might not exist, continue
                pass
        
        # Check for remaining relations
        for rel_type in relation_types_to_check:
            try:
                query = f"match $r isa {rel_type}; fetch $r;"
                result = self.execute_query(database, query, TransactionType.READ)
                if result and result.get("answers") and len(result["answers"]) > 0:
                    remaining.append(rel_type)
            except (TypeDBQueryError, TypeDBConnectionError):
                # Schema type might not exist, continue
                pass
        
        if remaining:
            raise TypeDBQueryError(
                f"Database wipe incomplete! Remaining types: {remaining}",
                query="verification"
            )
        
        return True

    def close(self) -> None:
        """Close all connections and cleanup resources."""
        # Clear sensitive data from memory
        if self._token_manager:
            self._token_manager.clear_memory()
        self._token = None
        self._token_encrypted = None
        self._session.close()
    
    def get_encrypted_token(self) -> Optional[str]:
        """Get the encrypted token for external storage.
        
        Returns:
            Encrypted token string that can be safely stored externally
        """
        return self._token_encrypted
    
    def set_encrypted_token(self, encrypted_token: str) -> None:
        """Set an encrypted token retrieved from external storage.
        
        Args:
            encrypted_token: Previously encrypted token string
        """
        self._token_encrypted = encrypted_token
        # Decrypt and cache the token for use
        self._token = self._token_manager.retrieve_token(encrypted_token)
    
    def get_token_access_log(self) -> List[Dict[str, Any]]:
        """Get the token access audit log.
        
        Returns:
            List of access log entries
        """
        return self._token_manager.get_access_log()
