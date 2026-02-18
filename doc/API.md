# TypeDBClient3 API Documentation

## Overview

The `TypeDBClient3` library provides a Python interface to TypeDB v3's HTTP API. It supports authentication, database management, query execution, schema operations, entity management, query building, and data import.

## Installation

```bash
pip install TypeDBClient3
```

## Quick Start

```python
from typedb_client3 import TypeDBClient, TransactionType

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
from typedb_client3 import TransactionType

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
from typedb_client3 import TypeDBClient, TransactionType
from typedb_client3.exceptions import (
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

---

# Detailed Class Reference

## QueryBuilder

The `QueryBuilder` class provides a fluent interface for building TypeDB v3 queries programmatically.

### Class Methods

#### `QueryBuilder()`

Creates a new QueryBuilder instance.

```python
qb = QueryBuilder()
```

#### `QueryBuilder.match_template()`

Creates a QueryBuilder pre-configured for MATCH queries.

```python
qb = QueryBuilder.match_template()
# Equivalent to QueryBuilder().match()
```

#### `QueryBuilder.insert_template()`

Creates a QueryBuilder pre-configured for INSERT queries.

```python
qb = QueryBuilder.insert_template()
# Equivalent to QueryBuilder().insert()
```

#### `QueryBuilder.put_template()`

Creates a QueryBuilder pre-configured for PUT (idempotent insert) queries.

```python
qb = QueryBuilder.put_template()
```

#### `QueryBuilder.delete_template()`

Creates a QueryBuilder pre-configured for DELETE queries.

```python
qb = QueryBuilder.delete_template()
```

### Instance Methods

#### `.match()`

Set query mode to MATCH (read).

```python
qb = QueryBuilder().match()
```

#### `.insert()`

Set query mode to INSERT (write).

```python
qb = QueryBuilder().insert()
```

#### `.put()`

Set query mode to PUT (idempotent write).

```python
qb = QueryBuilder().put()
```

#### `.delete()`

Set query mode to DELETE (write).

```python
qb = QueryBuilder().delete()
```

#### `.define()`

Set query mode to DEFINE (schema).

```python
qb = QueryBuilder().define()
```

#### `.undefine()`

Set query mode to UNDEFINE (schema).

```python
qb = QueryBuilder().undefine()
```

#### `.redefine()`

Set query mode to REDEFINE (schema).

```python
qb = QueryBuilder().redefine()
```

#### `.variable(name: str, type: str, attributes: dict = None)`

Add a variable to the query.

```python
# Simple variable
qb.variable("x", "actor")

# With attributes
qb.variable("a", "actor", {"actor-id": "A1", "id-label": "User1"})
```

#### `.update_variable(name: str, type: str, attributes: dict)`

Update an existing variable or create a new one.

```python
qb.update_variable("x", "actor", {"actor-id": "A2"})
```

#### `.get_variable(name: str)`

Get a Variable by name.

```python
var = qb.get_variable("x")
```

#### `.clear_variable(name: str)`

Remove a variable from the query.

```python
qb.clear_variable("x")
```

#### `.clear_all_variables()`

Remove all variables from the query.

```python
qb.clear_all_variables()
```

#### `.relation(type: str)`

Add a relation to the query. Returns a `RelationBuilder`.

```python
qb.relation("messaging")  # Returns RelationBuilder
```

#### `.fetch(fields)`

Set the FETCH clause.

```python
# Fetch single variable
qb.fetch(["x"])

# Fetch with nested structure
qb.fetch({"name": "$p.name", "titles": {"a": "$b.title"}})
```

#### `.order_by(variable: str, attribute: str, direction: str = "asc")`

Add ORDER BY clause.

```python
qb.order_by("x", "order")  # ascending
qb.order_by("x", "order", "desc")  # descending
```

#### `.offset(n: int)`

Add OFFSET clause.

```python
qb.offset(10)
```

#### `.limit(n: int)`

Add LIMIT clause.

```python
qb.limit(5)
```

#### `.reduce(variable: str, function: str, group_by: str = None)`

Add REDUCE clause for aggregations.

```python
# Simple count
qb.reduce("$x", "count")

# With groupby
qb.reduce("$s", "sum", "f")
```

#### `.with_function(func: str)`

Add WITH clause for user-defined functions.

```python
qb.with_function("fun path($start: node) -> { node }: match {}; return { $start };")
```

#### `.build()`

Build and return the final TypeQL query string.

```python
query = qb.build()
```

#### `.get_tql()`

Get the TypeQL query (alias for build() with caching.

```python
tql = qb.get_tql()
```

#### `.clone()`

Create a deep copy of the QueryBuilder.

```python
clone = qb.clone()
```

---

## Variable

Represents a typed variable in a QueryBuilder query.

### Constructor

```python
Variable(name: str)
```

### Methods

#### `.isa(type: str)`

Set the type of the variable.

```python
var = Variable("x")
var.isa("actor")
# Result: "$x isa actor"
```

#### `.has(attribute: str, value)`

Add an attribute to the variable.

```python
var.has("actor-id", "A1")
var.has("name", "John")
var.has("count", 42)
var.has("active", True)
# Result: '$x isa actor, has actor-id "A1", has name "John", has count 42, has active true'
```

#### `.label(name: str)`

Set a label for the variable (TypeDB v3 feature).

```python
var.label("$type_label")
# Result: '$x isa user, label $type_label'
```

### Properties

- `name` - The variable name (without $)
- `type` - The isa type
- `attributes` - Dict of attribute key-value pairs
- `label` - Optional type label

---

## RelationBuilder

Helper for building relations in queries.

### Constructor

```python
RelationBuilder(query_builder: QueryBuilder, relation_type: str)
```

### Methods

#### `.role(role_name: str, variable: str)`

Add a role player to the relation.

```python
rb.role("producer", "$actor")
rb.role("message", "$msg")
```

#### `.links()`

Use the `links` keyword (TypeDB v3).

```python
rb.links()
```

#### `.as_variable(name: str)`

Set the variable name for the relation.

```python
rb.as_variable("m")
```

#### `.end_relation()`

Finish building the relation and return to QueryBuilder.

```python
qb = rb.end_relation()
```

---

## Entity Classes

### Entity (Base Class)

Base class for all entity types.

```python
from typedb_client3.entities import Entity

entity = Entity()
```

**Class Attributes:**
- `_type` - The entity type name (empty string for base class)
- `_key_attr` - The key attribute name

**Methods:**
- `get_key_value()` - Get the key attribute value
- `to_insert_query()` - Generate INSERT query
- `to_match_query()` - Generate MATCH query
- `_escape_value(value)` - Escape value for TypeQL

### Actor

```python
from typedb_client3.entities import Actor

actor = Actor(
    actor_id="A1",
    id_label="User1",
    description="Test actor",
    justification="For testing"
)
```

**Attributes:**
- `actor_id` (key attribute)
- `id_label`
- `description`
- `justification`

### Action

```python
from typedb_client3.entities import Action

action = Action(
    action_id="ACT1",
    id_label="CreateUser",
    description="Creates a user",
    justification="For user management"
)
```

### Message

```python
from typedb_client3.entities import Message

message = Message(
    message_id="MSG1",
    id_label="TestMsg",
    description="A test message",
    justification="For testing"
)
```

### DataEntity

```python
from typedb_client3.entities import DataEntity

data = DataEntity(
    data_entity_id="DATA1",
    id_label="TestData",
    description="Test data"
)
```

### Requirement

```python
from typedb_client3.entities import Requirement

req = Requirement(
    requirement_id="REQ1",
    id_label="TestReq",
    description="A requirement",
    requirement_type="functional",
    status="draft",
    priority="high"
)
```

### ActionAggregate

```python
from typedb_client3.entities import ActionAggregate

agg = ActionAggregate(
    action_agg_id="AGG1",
    id_label="TestAgg"
)
```

### MessageAggregate

```python
from typedb_client3.entities import MessageAggregate

msg_agg = MessageAggregate(
    message_agg_id="MSGAGG1",
    id_label="TestMsgAgg"
)
```

### Constraint

```python
from typedb_client3.entities import Constraint

constraint = Constraint(
    constraint_id="CON1",
    id_label="TestConstraint",
    description="A constraint",
    constraint_type="required"
)
```

### Category

```python
from typedb_client3.entities import Category

category = Category(name="TestCategory")
```

### TextBlock

```python
from typedb_client3.entities import TextBlock

tb = TextBlock(
    anchor_id="AN1",
    id_label="Goal1",
    anchor_type="goal",
    text="This is a goal",
    order=1
)
```

### Concept

```python
from typedb_client3.entities import Concept

concept = Concept(
    concept_id="C1",
    id_label="TestConcept",
    description="A concept"
)
```

### SpecDocument

```python
from typedb_client3.entities import SpecDocument

doc = SpecDocument(
    spec_doc_id="DOC1",
    id_label="TestDoc",
    title="Test Document",
    version="1.0",
    status="draft",
    description="A spec document"
)
```

### SpecSection

```python
from typedb_client3.entities import SpecSection

section = SpecSection(
    spec_section_id="SEC1",
    id_label="TestSection",
    title="Test Section",
    order=1
)
```

---

## Relation Classes

### Relation (Base Class)

Base class for all relation types.

```python
from typedb_client3.entities import Relation

relation = Relation()
```

**Class Attributes:**
- `_type` - The relation type name
- `_roles` - List of role names

### Messaging

```python
from typedb_client3.entities import Messaging, Actor, Message

producer = Actor(actor_id="A1", id_label="P", description="", justification="")
consumer = Actor(actor_id="A2", id_label="C", description="", justification="")
message = Message(message_id="M1", id_label="Msg", description="", justification="")

messaging = Messaging(
    producer=producer,
    consumer=consumer,
    message=message
)
```

**Roles:** `producer`, `consumer`, `message`

### Anchoring

```python
from typedb_client3.entities import Anchoring, TextBlock, Concept

anchor = TextBlock(anchor_id="AN1", id_label="Goal", anchor_type="goal", text="", order=1)
concept = Concept(concept_id="C1", id_label="Test", description="")

anchoring = Anchoring(anchor=anchor, concept=concept)
```

**Roles:** `anchor`, `concept`

### Membership

```python
from typedb_client3.entities import Membership, Actor, Category

member = Actor(actor_id="A1", id_label="Member", description="", justification="")
category = Category(name="TestCategory")

membership = Membership(member_of=category, member=member)
```

**Roles:** `member-of`, `member`

### MembershipSeq

Like Membership but with ordering.

**Roles:** `member-of`, `member`, `order`

### Outlining

```python
from typedb_client3.entities import Outlining, SpecSection

section = SpecSection(spec_section_id="SEC1", id_label="Section", title="", order=1)
subsection = SpecSection(spec_section_id="SEC2", id_label="SubSection", title="", order=2)

outlining = Outlining(section=section, subsection=subsection)
```

**Roles:** `section`, `subsection`

### Categorization

```python
from typedb_client3.entities import Categorization, Category, Concept

category = Category(name="TestCat")
concept = Concept(concept_id="C1", id_label="Test", description="")

categorization = Categorization(category=category, object=concept)
```

**Roles:** `category`, `object`

### Requiring

```python
from typedb_client3.entities import Requiring, Requirement, Concept

req = Requirement(requirement_id="REQ1", id_label="Req", description="")
concept = Concept(concept_id="C1", id_label="Test", description="")

requiring = Requiring(required_by=req, conceptualized_as=concept)
```

**Roles:** `required-by`, `conceptualized-as`, `implemented-by`

### ConstrainedBy

```python
from typedb_client3.entities import ConstrainedBy, Constraint, DataEntity

constraint = Constraint(constraint_id="CON1", id_label="Con", description="")
data = DataEntity(data_entity_id="DATA1", id_label="Data", description="")

constrained = ConstrainedBy(constraint=constraint, object=data)
```

**Roles:** `constraint`, `object`

### MessagePayload

```python
from typedb_client3.entities import MessagePayload, Message, DataEntity

message = Message(message_id="M1", id_label="Msg", description="", justification="")
payload = DataEntity(data_entity_id="DATA1", id_label="Data", description="")

msg_payload = MessagePayload(message=message, payload=payload)
```

**Roles:** `message`, `payload`

### Filesystem

```python
from typedb_client3.entities import Filesystem

# folder and entry can be fs-folder or fs-file entities
filesystem = Filesystem(folder=folder_entity, entry=file_entity)
```

**Roles:** `folder`, `entry`

---

## EntityManager

Manages entity operations with a TypeDB database.

```python
from typedb_client3 import TypeDBClient
from typedb_client3.entity_manager import EntityManager
from typedb_client3.entities import Actor

client = TypeDBClient(base_url="http://localhost:8000", username="admin", password="password")
em = EntityManager(client, "my_database")
```

### Constructor

```python
EntityManager(client: TypeDBClient, database: str)
```

### Methods

#### `.insert(entity: Entity)`

Insert an entity into the database.

```python
actor = Actor(actor_id="A1", id_label="User1", description="Test", justification="")
em.insert(actor)
```

#### `.put(entity: Entity)`

Insert or update an entity (idempotent).

```python
em.put(actor)
```

#### `.exists(entity_class, key_value: str)`

Check if an entity exists.

```python
exists = em.exists(Actor, "A1")
```

#### `.fetch_one(entity_class, attributes: dict)`

Fetch a single entity matching criteria.

```python
actor = em.fetch_one(Actor, {"actor-id": "A1"})
```

#### `.fetch_all(entity_class, attributes: dict = None)`

Fetch all entities matching criteria.

```python
actors = em.fetch_all(Actor, {"id-label": "User%"})
```

#### `.delete(entity: Entity)`

Delete an entity.

```python
em.delete(actor)
```

#### `.insert_relation(relation: Relation)`

Insert a relation (not fully implemented).

```python
em.insert_relation(messaging)
```

#### `._escape_value(value)`

Escape a value for use in queries.

```python
escaped = em._escape_value('test"string')
# Result: '"test\\"string"'
```

---

## Query Patterns

Pre-built query templates for common operations.

```python
from typedb_client3.query_patterns import QUERY_PATTERNS, QueryPattern
```

### QueryPattern Class

```python
# Get a pattern by name
pattern = QueryPattern.get("messages_by_producer")

# Execute the pattern
result = pattern.execute(client, "my_database", actor_id="A1")
```

### Available Patterns

- `messages_by_producer` - Get messages produced by an actor
- `messages_by_action` - Get messages related to an action
- `concepts_by_anchor` - Get concepts anchored to a text block
- `concepts_by_requirement` - Get concepts needed for a requirement
- `text_blocks_by_section` - Get text blocks in a section
- `actions_by_aggregate` - Get actions in an action aggregate

### QUERY_PATTERNS Dictionary

```python
# List all available patterns
print(QUERY_PATTERNS.keys())
# dict_keys(['messages_by_producer', 'messages_by_action', ...])

# Access a pattern
pattern = QUERY_PATTERNS["messages_by_producer"]
```

---

## Importer

Import data from YAML or JSON files into TypeDB.

```python
from typedb_client3.importer import TypeDBImporter, create_importer
```

### TypeDBImporter Class

```python
importer = TypeDBImporter(
    base_url="http://localhost:8000",
    database="my_database",
    username="admin",
    password="password",
    verbose=1
)
```

### Constructor

```python
TypeDBImporter(
    base_url: str = "http://localhost:8000",
    database: str = "specifications",
    username: Optional[str] = None,
    password: Optional[str] = None,
    verbose: int = VerboseLevel.NORMAL,
    auto_connect: bool = True
)
```

### Methods

#### `.connect()`

Connect to TypeDB.

```python
importer.connect()
```

#### `.import_yaml(file_path: Path, force_update: bool = False)`

Import data from a YAML file.

```python
importer.import_yaml(Path("spec.yaml"), force_update=True)
```

#### `.import_json(file_path: Path, force_update: bool = False)`

Import data from a JSON file.

```python
importer.import_json(Path("data.json"), force_update=True)
```

#### `.import_json_directory(dir_path: Path, force_update: bool = False)`

Import all JSON files from a directory.

```python
importer.import_json_directory(Path("./json"), force_update=True)
```

#### `.import_string(content: str, format: str, force_update: bool = False)`

Import data from a string.

```python
importer.import_string(yaml_content, "yaml", force_update=True)
```

### create_importer Factory Function

```python
importer = create_importer(
    base_url="http://localhost:8000",
    database="my_database",
    username="admin",
    password="password"
)
```

### Colors Class

Terminal color codes for output.

```python
from typedb_client3.importer import Colors

print(f"{Colors.RED}Error:{Colors.RESET} Something went wrong")
```

**Available Colors:**
- `RESET`, `RED`, `GREEN`, `YELLOW`, `BLUE`, `MAGENTA`, `CYAN`, `BOLD`, `DIM`

### VerboseLevel Class

Verbosity levels for importer output.

```python
from typedb_client3.importer import VerboseLevel

VerboseLevel.ERROR   # 0 - Only errors
VerboseLevel.NORMAL  # 1 - Summary (default)
VerboseLevel.VERBOSE # 2 - Detailed progress
VerboseLevel.DEBUG   # 3 - All debug info
```

### Logger Class

Custom logger for importer output.

```python
from typedb_client3.importer import Logger

logger = Logger("importer", verbose_level=VerboseLevel.VERBOSE)
logger.info("Import started")
logger.error("Import failed")
```

---

## Validation Functions

### validate_base_url

```python
from typedb_client3.validation import validate_base_url

url = validate_base_url("http://localhost:8000")
# Returns: "http://localhost:8000"

url = validate_base_url("localhost:8000")
# Returns: "http://localhost:8000" (adds scheme)

url = validate_base_url("http://localhost:8000/")
# Returns: "http://localhost:8000" (removes trailing slash)
```

**Raises:** `TypeDBValidationError` for invalid URLs

### validate_credentials

```python
from typedb_client3.validation import validate_credentials

# Valid credentials
validate_credentials("admin", "password")  # OK

# Both None (anonymous access)
validate_credentials(None, None)  # OK

# Invalid combinations raise TypeDBValidationError
validate_credentials("admin", None)  # Error: must be provided together
validate_credentials("", "password")  # Error: empty username
```

### validate_timeout

```python
from typedb_client3.validation import validate_timeout

timeout = validate_timeout(30)      # Returns 30
timeout = validate_timeout("30")    # Converts string to int
timeout = validate_timeout(None)    # Returns default 30

# Invalid values raise TypeDBValidationError
validate_timeout(0)      # Error: must be at least 1 second
validate_timeout(301)    # Error: cannot exceed 300 seconds
validate_timeout("abc")  # Error: must be a number
```

### validate_operation_timeouts

```python
from typedb_client3.validation import validate_operation_timeouts

timeouts = validate_operation_timeouts({
    "read_operation": 60,
    "write_operation": 120
})
# Returns validated dict with defaults for missing keys

timeouts = validate_operation_timeouts({})
# Returns all defaults
```

### create_optimized_session

Create a requests Session with connection pooling.

```python
from typedb_client3.validation import create_optimized_session

session = create_optimized_session()
# Returns requests.Session with:
# - Connection pooling (DEFAULT_POOL_CONNECTIONS = 10)
# - Max pool size (DEFAULT_POOL_MAXSIZE = 10)
# - Retry logic (DEFAULT_MAX_RETRIES = 3)
# - Backoff factor (DEFAULT_BACKOFF_FACTOR = 0.5)
```

---

## Constants

### Connection Pooling Constants

```python
from typedb_client3.validation import (
    DEFAULT_POOL_CONNECTIONS,   # 10
    DEFAULT_POOL_MAXSIZE,       # 10
    DEFAULT_MAX_RETRIES,        # 3
    DEFAULT_BACKOFF_FACTOR      # 0.5
)
```

### TransactionType

```python
from typedb_client3 import TransactionType

TransactionType.READ   # "read"
TransactionType.WRITE  # "write"
```

---

## SecureTokenManager

Manages encrypted JWT token storage.

```python
from typedb_client3 import SecureTokenManager
```

### Constructor

```python
manager = SecureTokenManager()
```

### Methods

#### `.store_token(token: str) -> str`

Encrypt and store a JWT token.

```python
encrypted = manager.store_token("jwt_token_string")
# Returns encrypted token that can be safely stored
```

#### `.retrieve_token(encrypted_token: str) -> str`

Decrypt and retrieve a JWT token.

```python
token = manager.retrieve_token(encrypted_token)
```

**Raises:** `TypeDBAuthenticationError` if decryption fails

#### `.clear_memory()`

Clear cached token from memory.

```python
manager.clear_memory()
```

#### `.get_access_log() -> List[Dict]`

Get audit log of token operations.

```python
log = manager.get_access_log()
# Returns list of {"action": "...", "timestamp": ...}
```

#### `.rotate_key() -> bytes`

Rotate the encryption key (invalidates old tokens).

```python
new_key = manager.rotate_key()
```

### Properties

#### `.encryption_key -> bytes`

Get the current encryption key.

```python
key = manager.encryption_key
```
