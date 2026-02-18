# TypeDBClient3

Python client library for TypeDB v3 HTTP API.

## Installation

```bash
pip install TypeDBClient3
```

Or install from source:

```bash
pip install -e .
```

## Quick Start

```python
from typedb_client3 import TypeDBClient, TransactionType

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
    'insert $a isa actor, has actor-id "A1";',
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
- **Query Builder**: Build TypeDB v3 queries programmatically with type safety
- **Entity Classes**: Type-safe entity and relation definitions
- **Query Patterns**: Pre-built query templates for common operations
- **Query Execution**: One-shot queries for read, write, and schema transactions
- **Transaction Support**: Execute multiple operations in a single transaction
- **Database Management**: Create, delete, list, and check existence of databases
- **Schema Operations**: Load and retrieve database schemas
- **YAML/JSON Importer**: Import data from YAML or JSON files

## Query Builder

Build TypeDB v3 queries programmatically:

```python
from typedb_client3 import QueryBuilder, Variable

# Build a MATCH query
query = (QueryBuilder()
    .match()
    .variable("x", "actor", {"actor-id": "A1"})
    .fetch(["x"])
    .build())
# Result: 'match $x isa actor, has actor-id "A1"; fetch {"x": {$x.*}};'

# Build an INSERT query
query = (QueryBuilder()
    .insert()
    .variable("a", "actor", {
        "actor-id": "A1",
        "id-label": "User1",
        "description": "Test user"
    })
    .build())
# Result: 'insert $a isa actor, has actor-id "A1", has id-label "User1", has description "Test user";'

# Build a relation with links
query = (QueryBuilder()
    .match()
    .variable("p", "actor", {"actor-id": "A1"})
    .variable("m", "message", {"message-id": "MSG1"})
    .relation("messaging")
        .links()
        .role("producer", "$p")
        .role("message", "$m")
    .fetch(["m"])
    .build())
```

## Entity Classes

Type-safe entity definitions:

```python
from typedb_client3.entities import Actor, Action, Message, TextBlock

# Create entities
actor = Actor(
    actor_id="A1",
    id_label="User1",
    description="Test actor",
    justification="For testing"
)

# Generate INSERT query
query = actor.to_insert_query()
# Result: 'insert $a isa actor, has actor-id "A1", has id-label "User1", ...;'

# Create relations
from typedb_client3.entities import Messaging, Message
actor = Actor(actor_id="A1", id_label="Test", description="", justification="")
message = Message(message_id="M1", id_label="Test", description="", justification="")
messaging = Messaging(producer=actor, consumer=actor, message=message)
```

### Available Entity Classes

**Entities:**
- `Actor` - Actor entity with ID, label, description
- `Action` - Action entity
- `Message` - Message entity
- `DataEntity` - Generic data entity
- `Requirement` - Requirement entity
- `ActionAggregate` - Action aggregate entity
- `MessageAggregate` - Message aggregate entity
- `Constraint` - Constraint entity
- `Category` - Category entity
- `TextBlock` - Text block (goal/principle/criteria)
- `Concept` - Concept entity
- `SpecDocument` - Specification document
- `SpecSection` - Specification section

**Relations:**
- `Messaging` - Message producer-consumer relation
- `Anchoring` - Concept anchoring to text block
- `Membership` - Membership relation
- `Outlining` - Section outlining relation
- `Categorization` - Category categorization relation
- `Requiring` - Requirement relation
- `ConstrainedBy` - Constraint relation

## Entity Manager

Manage entities with a dedicated manager:

```python
from typedb_client3 import TypeDBClient
from typedb_client3.entity_manager import EntityManager
from typedb_client3.entities import Actor

client = TypeDBClient(base_url="http://localhost:8000", username="admin", password="password")
em = EntityManager(client, "my_database")

# Insert entity
actor = Actor(actor_id="A1", id_label="User1", description="Test", justification="")
em.insert(actor)

# Put entity (idempotent)
em.put(actor)

# Check if exists
exists = em.exists(Actor, "A1")

# Fetch entities
actor = em.fetch_one(Actor, {"actor-id": "A1"})
actors = em.fetch_all(Actor)

# Delete entity
em.delete(actor)
```

## Query Patterns

Pre-built query templates for common operations:

```python
from typedb_client3.query_patterns import QUERY_PATTERNS, QueryPattern

# Get all available patterns
print(QUERY_PATTERNS.keys())

# Use a pattern
pattern = QueryPattern.get("messages_by_producer")
result = pattern.execute(client, "my_database", actor_id="A1")
```

## Importer

Import data from YAML or JSON files:

```python
from typedb_client3.importer import TypeDBImporter, create_importer

# Create importer
importer = create_importer(
    base_url="http://localhost:8000",
    username="admin",
    password="password"
)

# Import from YAML
importer.import_file("data.yaml", "my_database")

# Import from JSON
importer.import_file("data.json", "my_database")

# Import from string
importer.import_string(yaml_content, "my_database")
```

## API Reference

### TypeDBClient

```python
client = TypeDBClient(
    base_url="http://localhost:8000",  # TypeDB server URL
    username="admin",                  # Username (optional)
    password="password",               # Password (optional)
    timeout=30,                        # Request timeout in seconds
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
    'insert $a isa actor, has actor-id "A1";',
    'insert $b isa actor, has actor-id "A2";',
    transaction_type=TransactionType.WRITE
)

# Execute with transaction context manager
with client.with_transaction("my_database", TransactionType.WRITE) as tx:
    tx.execute('insert $a isa actor, has actor-id "A1";')
```

#### Schema Operations

```python
# Load schema from file
client.load_schema("my_database", "path/to/schema.tql")

# Load schema from string
schema = "define actor sub entity, has actor-id;"
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
from typedb_client3 import TransactionType

TransactionType.READ   # For read queries
TransactionType.WRITE # For write/insert/delete queries
```

### Validation Functions

```python
from typedb_client3.validation import (
    validate_base_url,
    validate_credentials,
    validate_timeout,
    validate_operation_timeouts
)
```

### SecureTokenManager

```python
from typedb_client3 import SecureTokenManager

manager = SecureTokenManager()
encrypted = manager.store_token("jwt_token")
token = manager.retrieve_token(encrypted)
```

### Exceptions

```python
from typedb_client3.exceptions import (
    TypeDBError,
    TypeDBConnectionError,
    TypeDBAuthenticationError,
    TypeDBQueryError,
    TypeDBServerError,
    TypeDBValidationError
)
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
