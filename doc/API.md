# TypeDB v3 Client API Documentation

## Overview

The `typedb_v3_client` library provides a Python interface to TypeDB v3's HTTP API. It supports authentication, database management, query execution, and schema operations.

## Installation

```bash
pip install typedb-v3-client
```

## Quick Start

```python
from typedb_v3_client import TypeDBClient, TransactionType

# Connect to TypeDB
client = TypeDBClient(
    base_url="http://localhost:8000",
    username="admin",
    password="password"
)

# Create database and load schema
client.create_database("my_db")
client.load_schema("my_db", "schema.tql")

# Execute queries
client.execute_query("my_db", 'insert $a isa actor, owns actor-id "A1";', TransactionType.WRITE)

client.close()
```

---

## TypeDBClient

Main client class for interacting with TypeDB v3.

### Constructor

```python
TypeDBClient(
    base_url: str = "http://localhost:8000",
    username: Optional[str] = None,
    password: Optional[str] = None,
    timeout: int = 30,
    operation_timeouts: Optional[Dict[str, int]] = None
)
```

**Parameters:**
- `base_url` (str): TypeDB server URL. Default: `"http://localhost:8000"`
- `username` (Optional[str]): Username for authentication. Default: `None`
- `password` (Optional[str]): Password for authentication. Default: `None`
- `timeout` (int): Default request timeout in seconds. Default: `30`
- `operation_timeouts` (Optional[Dict[str, int]]): Per-operation timeouts. Default: `None`

**Raises:**
- `TypeDBValidationError`: If input parameters are invalid

---

### Database Operations

#### `list_databases()`

```python
def list_databases(self) -> List[str]
```

List all databases on the server.

**Returns:** `List[str]` - List of database names

**Example:**
```python
dbs = client.list_databases()
```

---

#### `database_exists(database: str)`

```python
def database_exists(self, database: str) -> bool
```

Check if a database exists.

**Parameters:**
- `database` (str): Database name

**Returns:** `bool` - True if database exists

---

#### `create_database(database: str)`

```python
def create_database(self, database: str) -> None
```

Create a new database.

**Parameters:**
- `database` (str): Database name to create

**Raises:**
- `TypeDBValidationError`: If database name is invalid or already exists
- `TypeDBServerError`: If server error occurs

---

#### `delete_database(database: str)`

```python
def delete_database(self, database: str) -> None
```

Delete a database.

**Parameters:**
- `database` (str): Database name to delete

**Raises:**
- `TypeDBValidationError`: If database doesn't exist
- `TypeDBServerError`: If server error occurs

---

#### `connect_database(database: str)`

```python
def connect_database(self, database: str) -> bool
```

Verify database exists, create if it doesn't.

**Parameters:**
- `database` (str): Database name

**Returns:** `bool` - True if database exists or was created

---

### Query Execution

#### `execute_query(database: str, query: str, transaction_type: TransactionType = TransactionType.READ)`

```python
def execute_query(
    self,
    database: str,
    query: str,
    transaction_type: TransactionType = TransactionType.READ
) -> Dict[str, Any]
```

Execute a single TypeQL query.

**Parameters:**
- `database` (str): Database name
- `query` (str): TypeQL query string
- `transaction_type` (TransactionType): READ or WRITE

**Returns:** `Dict[str, Any]` - Query results as JSON

**Raises:**
- `TypeDBQueryError`: If query is invalid
- `TypeDBConnectionError`: If connection fails

**Example:**
```python
# Insert data
client.execute_query(
    "my_db",
    'insert $a isa actor, owns actor-id "A1";',
    TransactionType.WRITE
)

# Read data
result = client.execute_query(
    "my_db",
    'match $a isa actor;',
    TransactionType.READ
)
```

---

#### `execute_transaction(database: str, transaction_type: TransactionType, operations: List[Dict[str, Any]])`

```python
def execute_transaction(
    self,
    database: str,
    transaction_type: TransactionType,
    operations: List[Dict[str, Any]]
) -> Dict[str, Any]
```

Execute multiple operations in a single transaction.

**Parameters:**
- `database` (str): Database name
- `transaction_type` (TransactionType): READ or WRITE
- `operations` (List[Dict[str, Any]]): List of operations with "query" key

**Returns:** `Dict[str, Any]` - Combined results

**Example:**
```python
operations = [
    {"query": 'insert $a isa actor, owns actor-id "A1";'},
    {"query": 'insert $b isa actor, owns actor-id "A2";'},
]
result = client.execute_transaction("my_db", TransactionType.WRITE, operations)
```

---

#### `execute_queries(database: str, *queries: str, transaction_type: TransactionType = TransactionType.WRITE)`

```python
def execute_queries(
    self,
    database: str,
    *queries: str,
    transaction_type: TransactionType = TransactionType.WRITE
) -> List[Dict[str, Any]]
```

Execute multiple queries as variadic arguments.

**Parameters:**
- `database` (str): Database name
- `*queries` (str): Variable number of TypeQL queries
- `transaction_type` (TransactionType): READ or WRITE

**Returns:** `List[Dict[str, Any]]` - Results for each query

**Example:**
```python
results = client.execute_queries(
    "my_db",
    'insert $a isa actor, owns actor-id "A1";',
    'insert $b isa actor, owns actor-id "A2";',
    transaction_type=TransactionType.WRITE
)
```

---

#### `with_transaction(database: str, transaction_type: TransactionType)`

```python
def with_transaction(
    self,
    database: str,
    transaction_type: TransactionType
) -> TransactionContext
```

Create a transaction context manager.

**Parameters:**
- `database` (str): Database name
- `transaction_type` (TransactionType): READ or WRITE

**Returns:** `TransactionContext` - Context manager

**Example:**
```python
with client.with_transaction("my_db", TransactionType.WRITE) as tx:
    tx.execute('insert $a isa actor, owns actor-id "A1";')
    tx.execute('insert $b isa actor, owns actor-id "A2";')
```

---

### Schema Operations

#### `load_schema(database: str, schema_path)`

```python
def load_schema(self, database: str, schema_path) -> None
```

Load TypeDB schema from file or string.

**Parameters:**
- `database` (str): Database name
- `schema_path`: Path to .tql file (str/Path) or schema string

**Raises:**
- `FileNotFoundError`: If schema file doesn't exist
- `TypeDBQueryError`: If schema is invalid

**Example:**
```python
# From file
client.load_schema("my_db", "path/to/schema.tql")

# From string
schema = """
define
actor sub entity, owns actor-id;
"""
client.load_schema("my_db", schema)
```

---

#### `get_schema(database: str)`

```python
def get_schema(self, database: str) -> str
```

Fetch database schema as TypeQL define string.

**Parameters:**
- `database` (str): Database name

**Returns:** `str` - TypeQL schema string

**Raises:**
- `TypeDBConnectionError`: If connection fails
- `TypeDBQueryError`: If request fails

---

### Token Management

#### `get_encrypted_token()`

```python
def get_encrypted_token(self) -> Optional[str]
```

Get encrypted token for external storage.

**Returns:** `Optional[str]` - Encrypted token string

---

#### `set_encrypted_token(encrypted_token: str)`

```python
def set_encrypted_token(self, encrypted_token: str) -> None
```

Set encrypted token from external storage.

**Parameters:**
- `encrypted_token` (str): Previously encrypted token

---

#### `get_token_access_log()`

```python
def get_token_access_log(self) -> List[Dict[str, Any]]
```

Get token access audit log.

**Returns:** `List[Dict[str, Any]]` - Access log entries

---

### Cleanup

#### `close()`

```python
def close(self) -> None
```

Close all connections and clear sensitive data from memory.

---

## TransactionType

Enum for transaction types.

```python
from typedb_v3_client import TransactionType

TransactionType.READ   # For read queries
TransactionType.WRITE # For write/insert/delete queries
```

---

## Validation Functions

### `validate_base_url(url: str)`

Validate and normalize base URL.

**Parameters:**
- `url` (str): URL to validate

**Returns:** `str` - Normalized URL

**Raises:** `TypeDBValidationError` - If URL is invalid

---

### `validate_credentials(username: Optional[str], password: Optional[str])`

Validate username and password.

**Parameters:**
- `username` (Optional[str]): Username
- `password` (Optional[str]): Password

**Raises:** `TypeDBValidationError` - If credentials are invalid

---

### `validate_timeout(timeout: Any)`

Validate timeout value.

**Parameters:**
- `timeout`: Timeout value to validate

**Returns:** `int` - Validated timeout

**Raises:** `TypeDBValidationError` - If timeout is invalid

---

### `validate_operation_timeouts(timeouts: Dict[str, int])`

Validate operation-specific timeouts.

**Parameters:**
- `timeouts` (Dict[str, int]): Operation name to timeout mapping

**Returns:** `Dict[str, int]` - Validated timeouts

---

## SecureTokenManager

Class for secure JWT token storage with Fernet encryption.

### `store_token(token: str)`

Encrypt and store a JWT token.

**Parameters:**
- `token` (str): JWT token string

**Returns:** `str` - Encrypted token

---

### `retrieve_token(encrypted_token: str)`

Decrypt and retrieve a JWT token.

**Parameters:**
- `encrypted_token` (str): Encrypted token

**Returns:** `str` - Decrypted token

**Raises:** `TypeDBAuthenticationError` - If decryption fails

---

### `clear_memory()`

Clear cached token from memory.

---

## Exceptions

- `TypeDBConnectionError` - Connection-related errors
- `TypeDBAuthenticationError` - Authentication failures
- `TypeDBQueryError` - Query execution errors
- `TypeDBServerError` - Server-side errors
- `TypeDBValidationError` - Input validation errors

---

## Error Handling Example

```python
from typedb_v3_client import TypeDBClient, TransactionType
from typedb_v3_client.exceptions import (
    TypeDBConnectionError,
    TypeDBQueryError,
    TypeDBValidationError
)

try:
    client = TypeDBClient("http://localhost:8000", "admin", "password")
    client.execute_query("my_db", "invalid query", TransactionType.READ)
except TypeDBValidationError as e:
    print(f"Validation error: {e}")
except TypeDBQueryError as e:
    print(f"Query error: {e}")
except TypeDBConnectionError as e:
    print(f"Connection error: {e}")
finally:
    client.close()
```
