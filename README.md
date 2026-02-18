# typedb-v3-client

Python client library for TypeDB v3 HTTP API.

## Installation

```bash
pip install typedb-v3-client
```

## Quick Start

```python
from typedb_v3_client import TypeDBClient, TransactionType

# Connect to TypeDB server
client = TypeDBClient(
    base_url="http://localhost:8000",
    username="admin",
    password="password"
)

# Create a database
client.create_database("my_database")

# Load schema from file
client.load_schema("my_database", "schema.tql")

# Execute queries
client.execute_query(
    "my_database",
    'insert $a isa actor, owns actor-id "A1";',
    TransactionType.WRITE
)

# Read data
result = client.execute_query(
    "my_database",
    'match $a isa actor;',
    TransactionType.READ
)

# Close connection
client.close()
```

## Features

- **Authentication**: JWT token-based authentication with secure token encryption
- **Connection Pooling**: Optimized HTTP session with connection pooling and retries
- **Query Execution**: One-shot queries for read, write, and schema transactions
- **Transaction Support**: Execute multiple operations in a single transaction
- **Database Management**: Create, delete, list, and check existence of databases
- **Schema Operations**: Load and retrieve database schemas

## API Reference

### TypeDBClient

```python
client = TypeDBClient(
    base_url="http://localhost:8000",  # TypeDB server URL
    username="admin",                  # Username (optional)
    password="password",               # Password (optional)
    timeout=30,                       # Request timeout in seconds
    operation_timeouts={              # Optional per-operation timeouts
        "read_operation": 30,
        "write_operation": 60,
        "schema_operation": 120
    }
)
```

#### Database Operations

```python
# List all databases
databases = client.list_databases()

# Check if database exists
exists = client.database_exists("my_database")

# Create a database
client.create_database("my_database")

# Connect (creates if not exists)
client.connect_database("my_database")

# Delete a database
client.delete_database("my_database")
```

#### Query Execution

```python
# Execute a single query
result = client.execute_query(
    "my_database",
    'match $a isa actor;',
    TransactionType.READ  # or TransactionType.WRITE
)

# Execute multiple queries in one transaction
result = client.execute_queries(
    "my_database",
    'insert $a isa actor, owns actor-id "A1";',
    'insert $b isa actor, owns actor-id "A2";',
    transaction_type=TransactionType.WRITE
)

# Execute with transaction context manager
with client.with_transaction("my_database", TransactionType.WRITE) as tx:
    tx.execute('insert $a isa actor, owns actor-id "A1";')
```

#### Schema Operations

```python
# Load schema from file
client.load_schema("my_database", "path/to/schema.tql")

# Load schema from string
schema = "define actor sub entity, owns actor-id;"
client.load_schema("my_database", schema)

# Get current schema
schema = client.get_schema("my_database")
```

#### Token Management

```python
# Get encrypted token for external storage
encrypted = client.get_encrypted_token()

# Set encrypted token (e.g., from previous session)
client.set_encrypted_token(encrypted)

# Get access log for audit
log = client.get_token_access_log()
```

#### Cleanup

```python
# Close connection and clear sensitive data
client.close()
```

### TransactionType

```python
from typedb_v3_client import TransactionType

TransactionType.READ   # For read queries
TransactionType.WRITE # For write/insert/delete queries
```

### Validation Functions

```python
from typedb_v3_client.validation import (
    validate_base_url,
    validate_credentials,
    validate_timeout,
    validate_operation_timeouts
)
```

### SecureTokenManager

```python
from typedb_v3_client import SecureTokenManager

manager = SecureTokenManager()
encrypted = manager.store_token("jwt_token")
token = manager.retrieve_token(encrypted)
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run unit tests only (no server required)
pytest tests/ -m unit

# Run integration tests (requires live TypeDB server)
pytest tests/ -m integration
```

## Requirements

- Python 3.8+
- requests
- cryptography (for token encryption)
- pytest

## License

MIT
