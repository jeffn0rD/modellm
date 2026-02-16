"""TypeDB v3 Client Library - HTTP Client

Implements TypeDB v3 HTTP API client with:
- Authentication (JWT tokens)
- Query execution (read/write transactions)
- Transaction support (multiple operations)
- Database management (create, delete, list)
- Schema loading from TQL files
"""

import base64
import json
import secrets
import time
import requests
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List
from cryptography.fernet import Fernet
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .exceptions import (
    TypeDBConnectionError, TypeDBAuthenticationError,
    TypeDBQueryError, TypeDBServerError, TypeDBValidationError
)


# ============================================================================
# Input Validation Functions
# ============================================================================

import re
from urllib.parse import urlparse


def validate_base_url(url: str) -> str:
    """Validate and normalize the base URL.
    
    Args:
        url: The URL string to validate
        
    Returns:
        Normalized URL string
        
    Raises:
        TypeDBValidationError: If URL is invalid
    """
    if not url:
        raise TypeDBValidationError("Base URL cannot be empty")
    
    # Check for malicious protocol patterns first
    dangerous_patterns = [
        r'javascript:',  # XSS
        r'<script',  # XSS
        r'data:',  # Data URLs
        r'file://',  # File access
        r'ftp://',  # FTP access
        r'dict://',  # Protocol attacks
        r'ldap://',  # Protocol attacks
        r'gopher://',  # Protocol attacks
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, url, re.IGNORECASE):
            raise TypeDBValidationError(f"Invalid URL protocol/pattern: {pattern}")
    
    # Add scheme if missing
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    
    parsed = urlparse(url)
    
    # Validate scheme
    if parsed.scheme not in ('http', 'https'):
        raise TypeDBValidationError(f"Invalid URL scheme: {parsed.scheme}. Must be 'http' or 'https'")
    
    # Validate hostname
    if not parsed.hostname:
        raise TypeDBValidationError("Invalid URL: no hostname specified")
    
    # Check for injection patterns in hostname
    injection_patterns = [
        r'[\x00-\x1f\x7f]',  # Control characters
        r'[<>"\']',  # HTML/script characters
    ]
    for pattern in injection_patterns:
        if re.search(pattern, parsed.hostname):
            raise TypeDBValidationError("Invalid characters in hostname")
    
    # Validate port range (handle potential parsing errors)
    try:
        if parsed.port is not None:
            if parsed.port < 1 or parsed.port > 65535:
                raise TypeDBValidationError(f"Invalid port number: {parsed.port}. Must be between 1 and 65535")
    except ValueError:
        raise TypeDBValidationError("Invalid port format in URL")
    
    # Check path for injection patterns
    if parsed.path:
        path_injection = ['../', '\\x', '<script', 'javascript:', 'onerror=']
        for pattern in path_injection:
            if pattern in parsed.path.lower():
                raise TypeDBValidationError(f"Invalid path pattern: {pattern}")
    
    return url.rstrip('/')


def validate_credentials(username: Optional[str], password: Optional[str]) -> None:
    """Validate username and password credentials.
    
    Args:
        username: The username to validate
        password: The password to validate
        
    Raises:
        TypeDBValidationError: If credentials are invalid
    """
    # If neither is provided, that's ok (anonymous access)
    if username is None and password is None:
        return
    
    # If one is provided without the other, that's invalid
    if username is None or password is None:
        raise TypeDBValidationError("Both username and password must be provided together")
    
    # Validate length
    if len(username) < 1 or len(username) > 128:
        raise TypeDBValidationError("Username must be between 1 and 128 characters")
    
    if len(password) < 1 or len(password) > 128:
        raise TypeDBValidationError("Password must be between 1 and 128 characters")
    
    # Check for TypeQL injection patterns (and general injection attempts)
    injection_patterns = [
        r'union\s+select',  # SQL-style
        r'select\s+.*\s+from',
        r'insert\s+into',
        r'drop\s+table',
        r'delete\s+from',
        r'or\s+.*=.*',  # Logical OR injection
        r'\'.*=.*\'',  # Quote-based injection
        r'--',  # Comment injection (both SQL and TypeQL)
        r'".*";',  # TypeQL command separator
        r'\$.*isa\s+',  # Variable injection
        r'match\s+\$.*;',  # Match injection
        r'/\*.*\*/',  # Block comment
        r'javascript:',  # XSS
        r'<script',  # XSS
        r'onerror=',  # XSS
        r'onload=',  # XSS
        r'`.*`',  # Backtick injection
        r'\|',  # Command pipes
        r';.*;',  # Multiple statements
    ]
    
    combined = (username + password).lower()
    for pattern in injection_patterns:
        if re.search(pattern, combined, re.IGNORECASE):
            raise TypeDBValidationError("Invalid characters in credentials")
    
    # Check for XSS injection patterns
    xss_patterns = [
        r'<script',
        r'javascript:',
        r'onerror=',
        r'onload=',
    ]
    for pattern in xss_patterns:
        if re.search(pattern, combined, re.IGNORECASE):
            raise TypeDBValidationError("Invalid characters in credentials")


def validate_timeout(timeout: Any) -> int:
    """Validate and normalize timeout value.
    
    Args:
        timeout: The timeout value to validate (can be int or float)
        
    Returns:
        Validated timeout as integer
        
    Raises:
        TypeDBValidationError: If timeout is invalid
    """
    # Allow None to use default
    if timeout is None:
        return 30
    
    # Try to convert to int
    try:
        timeout = int(timeout)
    except (ValueError, TypeError):
        raise TypeDBValidationError(f"Timeout must be a number, got {type(timeout).__name__}")
    
    # Validate range
    min_timeout = 1
    max_timeout = 300  # 5 minutes
    
    if timeout < min_timeout:
        raise TypeDBValidationError(f"Timeout must be at least {min_timeout} seconds")
    
    if timeout > max_timeout:
        raise TypeDBValidationError(f"Timeout cannot exceed {max_timeout} seconds")
    
    return timeout


# ============================================================================
# Connection Pooling Configuration
# ============================================================================

# Default connection pool settings
DEFAULT_POOL_CONNECTIONS = 50
DEFAULT_POOL_MAXSIZE = 100
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 0.3
DEFAULT_STATUS_FORCE_LIST = [500, 502, 503, 504]


# ============================================================================
# Operation-Specific Timeout Configuration
# ============================================================================

# Default timeout configuration for different operation types
DEFAULT_TIMEOUTS = {
    'authentication': 10,
    'read_operation': 30,
    'write_operation': 60,
    'schema_operation': 120,
    'transaction': 180,
    'health_check': 5
}

# Timeout validation limits
MIN_TIMEOUT = 1
MAX_TIMEOUT = 300  # 5 minutes


def validate_operation_timeouts(timeouts: Dict[str, int]) -> Dict[str, int]:
    """Validate operation-specific timeouts.
    
    Args:
        timeouts: Dictionary of operation name to timeout in seconds
        
    Returns:
        Validated timeouts dictionary
        
    Raises:
        TypeDBValidationError: If any timeout is invalid
    """
    validated = DEFAULT_TIMEOUTS.copy()
    
    for key, value in timeouts.items():
        if key not in DEFAULT_TIMEOUTS:
            raise TypeDBValidationError(f"Unknown timeout operation: {key}")
        
        try:
            timeout_value = int(value)
        except (ValueError, TypeError):
            raise TypeDBValidationError(f"Timeout must be a number for {key}")
        
        if timeout_value < MIN_TIMEOUT or timeout_value > MAX_TIMEOUT:
            raise TypeDBValidationError(
                f"Timeout for {key} must be between {MIN_TIMEOUT} and {MAX_TIMEOUT} seconds"
            )
        
        validated[key] = timeout_value
    
    return validated


def create_optimized_session(
    pool_connections: int = DEFAULT_POOL_CONNECTIONS,
    pool_maxsize: int = DEFAULT_POOL_MAXSIZE,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    status_forcelist: List[int] = None
) -> requests.Session:
    """Create an optimized requests Session with connection pooling.
    
    Args:
        pool_connections: Number of connection pools to cache
        pool_maxsize: Maximum number of connections per host
        max_retries: Maximum number of retry attempts
        backoff_factor: Exponential backoff factor
        status_forcelist: HTTP status codes to retry on
        
    Returns:
        Configured requests Session with connection pooling
    """
    if status_forcelist is None:
        status_forcelist = DEFAULT_STATUS_FORCE_LIST
    
    # Create retry strategy
    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"]
    )
    
    # Create HTTP adapter with connection pooling
    adapter = HTTPAdapter(
        pool_connections=pool_connections,
        pool_maxsize=pool_maxsize,
        max_retries=retry_strategy
    )
    
    # Create session and mount adapter
    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session


class SecureTokenManager:
    """Secure token manager with Fernet encryption for JWT storage.
    
    This class provides secure storage of JWT tokens using Fernet symmetric
    encryption. Each token encryption uses a unique initialization vector (IV),
    preventing pattern analysis in stored tokens.
    
    Attributes:
        encryption_key: bytes - Fernet encryption key
        cipher: Fernet - Cipher instance for encrypt/decrypt
        token_access_log: List[Dict] - Audit log for token access
    """
    
    def __init__(self):
        """Initialize the secure token manager with a new encryption key."""
        self._encryption_key: bytes = Fernet.generate_key()
        self._cipher = Fernet(self._encryption_key)
        self._token_access_log: List[Dict[str, Any]] = []
        self._token_cache: Optional[str] = None
        self._token_cache_time: Optional[float] = None
        self._token_cache_timeout: float = 300  # 5 minutes default
    
    @property
    def encryption_key(self) -> bytes:
        """Get the encryption key (for storage/external use)."""
        return self._encryption_key
    
    def store_token(self, token: str) -> str:
        """Encrypt and store a JWT token.
        
        Args:
            token: The JWT token string to encrypt
            
        Returns:
            Encrypted token string (safe to store)
        """
        # Generate a random salt for this encryption
        salt = secrets.token_bytes(16)
        
        # Encrypt the token with the salt prepended
        token_bytes = token.encode('utf-8')
        encrypted = self._cipher.encrypt(token_bytes)
        encrypted_with_salt = salt + encrypted
        
        # Encode to base64 for storage (using base64 module)
        encrypted_b64 = base64.b64encode(encrypted_with_salt).decode('utf-8')
        
        # Log the token storage
        self._log_access("store", len(token))
        
        # Cache the decrypted token for performance
        self._token_cache = token
        self._token_cache_time = time.time()
        
        return encrypted_b64
    
    def retrieve_token(self, encrypted_token: str) -> str:
        """Decrypt and retrieve a JWT token.
        
        Args:
            encrypted_token: The encrypted token string
            
        Returns:
            Decrypted JWT token string
        """
        # Check cache first
        if self._token_cache and self._token_cache_time:
            if time.time() - self._token_cache_time < self._token_cache_timeout:
                self._log_access("cache_hit", len(self._token_cache))
                return self._token_cache
        
        # Decode from base64
        try:
            encrypted_bytes = base64.b64decode(encrypted_token.encode('utf-8'))
            salt = encrypted_bytes[:16]
            encrypted = encrypted_bytes[16:]
            
            # Decrypt the token
            decrypted = self._cipher.decrypt(encrypted)
            token = decrypted.decode('utf-8')
            
            # Cache for future use
            self._token_cache = token
            self._token_cache_time = time.time()
            
            self._log_access("retrieve", len(token))
            
            return token
        except Exception as e:
            raise TypeDBAuthenticationError(f"Failed to decrypt token: {e}")
    
    def clear_memory(self) -> None:
        """Clear cached token from memory.
        
        This should be called when the token is no longer needed
        to prevent memory exposure.
        """
        self._token_cache = None
        self._token_cache_time = None
        self._log_access("clear", 0)
    
    def rotate_key(self) -> str:
        """Rotate to a new encryption key.
        
        WARNING: This invalidates all previously encrypted tokens.
        Only use this when the token storage is also being updated.
        
        Returns:
            New encryption key
        """
        self._encryption_key = Fernet.generate_key()
        self._cipher = Fernet(self._encryption_key)
        
        # Clear cached tokens
        self._token_cache = None
        self._token_cache_time = None
        
        self._log_access("rotate", 0)
        
        return self._encryption_key
    
    def _log_access(self, action: str, token_length: int) -> None:
        """Log token access for audit purposes.
        
        Args:
            action: The action performed (store, retrieve, clear, rotate)
            token_length: Length of the token (0 for clear/rotate)
        """
        self._token_access_log.append({
            "action": action,
            "token_length": token_length,
            "timestamp": time.time()
        })
        
        # Keep only last 100 log entries
        if len(self._token_access_log) > 100:
            self._token_access_log = self._token_access_log[-100:]
    
    def get_access_log(self) -> List[Dict[str, Any]]:
        """Get the token access log.
        
        Returns:
            List of access log entries
        """
        return self._token_access_log.copy()


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
    ):
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
