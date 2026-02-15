# TypeDB Migration Proposal: JSON Concepts Import

## Overview

This document outlines the migration strategy for importing JSON concept files into TypeDB 3 using the `--parse-concepts` flag in the `typedb_import.py` script.

## 1. JSON File Structure Analysis

### 1.1 Concepts JSON File (`concepts.json`)

Contains three types of design concepts:

**Actor Objects:**
```json
{
  "type": "Actor",
  "id": "A1",
  "label": "EndUser",
  "categories": ["core"],
  "description": "A single person using the application...",
  "justification": "Described as a single user...",
  "anchors": ["AN1", "AN2", ...],
  "sourceConceptIds": ["C1", "C5", ...]
}
```

**Action Objects:**
```json
{
  "type": "Action",
  "id": "ACT1",
  "label": "CreateTask",
  "categories": ["core"],
  "description": "Create a new task...",
  "justification": "User needs to create tasks...",
  "anchors": ["AN3", ...],
  "sourceConceptIds": [...]
}
```

**DataEntity Objects:**
```json
{
  "type": "DataEntity",
  "id": "DE16",
  "label": "SearchQuery",
  "categories": ["future"],
  "description": "A free-text expression...",
  "justification": "Search capability specifies...",
  "anchors": ["AN22"],
  "sourceConceptIds": ["C65", "C66", ...]
}
```

### 1.2 Aggregations JSON File (`aggregations.json`)

Contains ActionAggregate objects:
```json
{
  "id": "AG1",
  "label": "TaskLifecycle",
  "category": "lifecycle",
  "members": ["ACT1", "ACT2", "ACT4", "ACT3"],
  "description": "Lifecycle of an individual Task...",
  "justification": "The specification emphasizes...",
  "anchors": ["AN3", "AN6", "AN7"]
}
```

### 1.3 Messages JSON File (`messages.json`)

Contains Message objects:
```json
{
  "id": "MSG1",
  "label": "CreateTaskCommand",
  "category": "command",
  "description": "EndUser requests creation of a new task...",
  "producer": "A1",
  "consumer": "A2",
  "payload": [
    {
      "id": "DE1",
      "label": "Task",
      "refConceptId": "DE1",
      "constraint": "Must include at least a non-empty title...",
      "notes": "Represents the task fields...",
      "isNew": false
    }
  ],
  "constraints": [
    {
      "id": "C-MSG1-1",
      "label": "Task title required on creation",
      "constraint": "TodoApplication must reject...",
      "notes": "",
      "isNew": true
    }
  ],
  "justification": "User needs to create simple to-do items...",
  "anchors": ["AN3"]
}
```

### 1.4 MessageAggregations JSON File (`messageAggregations.json`)

Contains MessageAggregate objects:
```json
{
  "id": "MAG1",
  "label": "TaskLifecycleWorkflow",
  "category": "lifecycle",
  "description": "Workflow covering the lifecycle of a Task...",
  "sequences": [
    [
      {
        "id": "MSG1",
        "label": "CreateTaskCommand",
        "description": "EndUser creates a new task.",
        "isNew": false
      },
      ...
    ]
  ],
  "justification": "Implements AG1 TaskLifecycle by expressing...",
  "anchors": ["AN3", "AN6", "AN7"]
}
```

### 1.5 Requirements JSON File (`requirements.json`)

Contains Requirement objects:
```json
{
  "id": "FR-1",
  "type": "functional",
  "status": "draft",
  "label": "Local single-user browser-based to-do app",
  "category": "category",
  "description": "The system shall operate as a simple...",
  "priority": "must",
  "sectionHint": "1.1",
  "anchors": ["AN1", "AN2"],
  "relatedConcepts": ["A1", "A2", "DE7", "DE22", "DE25"],
  "relatedMessages": [],
  "notes": "Summarizes the overall deployment..."
}
```

---

## 2. TypeDB Schema Mapping

### 2.1 Entity Type Mappings

| JSON Type | TypeDB Entity Type | Key Attribute | Key Field Source |
|-----------|-------------------|---------------|------------------|
| Actor | `actor` | `actor-id` | `id` field (e.g., "A1") |
| Action | `action` | `action-id` | `id` field (e.g., "ACT1") |
| DataEntity | `data-entity` | `data-entity-id` | `id` field (e.g., "DE16") |
| Message | `message` | `message-id` | `id` field (e.g., "MSG1") |
| ActionAggregate | `action-aggregate` | `action-agg-id` | `id` field (e.g., "AG1") |
| MessageAggregate | `message-aggregate` | `message-agg-id` | `id` field (e.g., "MAG1") |
| Category | `category` | `name` | `categories[]` array or `category` field |
| Constraint | `constraint` | `constraint-id` | `id` field (e.g., "C-MSG1-1") |
| Requirement | `design-concept` (abstract) | `id-label` | `id` field (e.g., "FR-1") |

**Note:** Requirement objects don't have a dedicated entity type in the schema. They will be imported as `design-concept` entities with `id-label` as the key.

### 2.2 Attribute Mappings

| JSON Field | TypeDB Attribute | Applicable Entity Types |
|------------|------------------|------------------------|
| `id` | Various (see Key Attributes table above) | Actor, Action, DataEntity, Message, Aggregates |
| `label` | `id-label` | All design-concept subtypes |
| `description` | `description` | All design-concept subtypes |
| `justification` | `justification` | All design-concept subtypes |
| `categories[]` | `categorization` relation | All concepts (via category entities) |
| `category` | `categorization` relation | Aggregates, Messages |
| `anchors[]` | `anchoring` relation | All concepts (via text-block entities) |

### 2.3 Relation Type Mappings

| JSON Field | TypeDB Relation | Source Role | Target Role | Notes |
|------------|-----------------|-------------|-------------|-------|
| `anchors[]` | `anchoring` | `text-block` | `concept` | Requires text-block entities to exist |
| `categories[]` | `categorization` | `category` | `object` | Creates category entities if needed |
| `category` | `categorization` | `category` | `object` | Single category for aggregations/messages |
| `producer` | `messaging` | `producer` | `message` | Links actor to message |
| `consumer` | `messaging` | `consumer` | `message` | Links actor to message |
| `members[]` | `membership` | `member-of` (aggregate) | `member` (action) | Links aggregate to actions |
| `payload[]` | `message-payload` | `message` | `payload` (data-entity) | Links message to data entities |
| `constraints[]` | `constrained-by` | `constraint` | `object` (message) | Links constraints to messages |
| `sequences[]` | Not imported | N/A | N/A | Sequence data not modeled in schema |

---

## 3. TypeQL Query Examples

### 3.1 Actor Entity Creation

**JSON:**
```json
{
  "type": "Actor",
  "id": "A1",
  "label": "EndUser",
  "description": "A single person using the application...",
  "justification": "Described as a single user..."
}
```

**TypeQL:**
```typeql
insert
  $a isa actor,
    has actor-id "A1",
    has id-label "EndUser",
    has description "A single person using the application...",
    has justification "Described as a single user...";
```

### 3.2 Action Entity Creation

**JSON:**
```json
{
  "type": "Action",
  "id": "ACT1",
  "label": "CreateTask",
  "description": "Create a new task...",
  "justification": "User needs to create tasks..."
}
```

**TypeQL:**
```typeql
insert
  $act isa action,
    has action-id "ACT1",
    has id-label "CreateTask",
    has description "Create a new task...",
    has justification "User needs to create tasks...";
```

### 3.3 DataEntity Entity Creation

**JSON:**
```json
{
  "type": "DataEntity",
  "id": "DE16",
  "label": "SearchQuery",
  "categories": ["future"],
  "description": "A free-text expression and optional filters...",
  "justification": "Search capability specifies free-text search...",
  "anchors": ["AN22"]
}
```

**TypeQL:**
```typeql
insert
  $de isa data-entity,
    has data-entity-id "DE16",
    has id-label "SearchQuery",
    has description "A free-text expression and optional filters used to search across task titles and descriptions.",
    has justification "Search capability specifies free-text search across titles and descriptions, possibly with filters like only incomplete.";
```

### 3.4 Category Entity and Categorization Relation

**JSON:**
```json
{
  "categories": ["core", "future"]
}
```

**TypeQL:**
```typeql
# Create category entities (if they don't exist)
insert
  $c1 isa category, has name "core";
insert
  $c2 isa category, has name "future";

# Create categorization relations
match
  $c1 isa category, has name "core";
  $de isa data-entity, has data-entity-id "DE16";
insert categorization(category: $c1, object: $de);

match
  $c2 isa category, has name "future";
  $de isa data-entity, has data-entity-id "DE16";
insert categorization(category: $c2, object: $de);
```

### 3.5 Anchoring Relation (to text-block)

**JSON:**
```json
{
  "anchors": ["AN22"]
}
```

**TypeQL:**
```typeql
match
  $a isa text-block, has anchor-id "AN22";
  $de isa data-entity, has data-entity-id "DE16";
insert anchoring(anchor: $a, concept: $de);
```

### 3.6 Message Entity Creation

**JSON:**
```json
{
  "id": "MSG1",
  "label": "CreateTaskCommand",
  "category": "command",
  "description": "EndUser requests creation of a new task...",
  "justification": "User needs to create simple to-do items...",
  "producer": "A1",
  "consumer": "A2"
}
```

**TypeQL:**
```typeql
insert
  $m isa message,
    has message-id "MSG1",
    has id-label "CreateTaskCommand",
    has description "EndUser requests creation of a new task with required and optional attributes.",
    has justification "User needs to create simple to-do items with at least a title, and optionally a description and due date.";
```

### 3.7 Messaging Relation (producer/consumer)

**JSON:**
```json
{
  "producer": "A1",
  "consumer": "A2"
}
```

**TypeQL:**
```typeql
match
  $producer isa actor, has actor-id "A1";
  $consumer isa actor, has actor-id "A2";
  $m isa message, has message-id "MSG1";
insert messaging(producer: $producer, consumer: $consumer, message: $m);
```

### 3.8 Message-Payload Relation

**JSON:**
```json
{
  "payload": [
    {
      "id": "DE1",
      "label": "Task",
      "refConceptId": "DE1"
    }
  ]
}
```

**TypeQL:**
```typeql
match
  $m isa message, has message-id "MSG1";
  $de isa data-entity, has data-entity-id "DE1";
insert message-payload(message: $m, payload: $de);
```

### 3.9 Constraint Entity and Constrained-By Relation

**JSON:**
```json
{
  "constraints": [
    {
      "id": "C-MSG1-1",
      "label": "Task title required on creation",
      "constraint": "TodoApplication must reject CreateTaskCommand if the provided Task title is empty or whitespace."
    }
  ]
}
```

**TypeQL:**
```typeql
# Create constraint entity
insert
  $c isa constraint,
    has constraint-id "C-MSG1-1",
    has id-label "Task title required on creation",
    has description "TodoApplication must reject CreateTaskCommand if the provided Task title is empty or whitespace.";

# Create constrained-by relation
match
  $c isa constraint, has constraint-id "C-MSG1-1";
  $m isa message, has message-id "MSG1";
insert constrained-by(constraint: $c, object: $m);
```

### 3.10 ActionAggregate Entity and Membership Relation

**JSON:**
```json
{
  "id": "AG1",
  "label": "TaskLifecycle",
  "category": "lifecycle",
  "members": ["ACT1", "ACT2", "ACT4", "ACT3"],
  "description": "Lifecycle of an individual Task...",
  "justification": "The specification emphasizes..."
}
```

**TypeQL:**
```typeql
# Create action-aggregate entity
insert
  $agg isa action-aggregate,
    has action-agg-id "AG1",
    has id-label "TaskLifecycle",
    has description "Lifecycle of an individual Task from creation through updates, completion state changes, and eventual deletion.",
    has justification "The specification emphasizes basic task management: creating tasks, editing them, marking them complete or incomplete, and deleting them as part of the core task lifecycle.";

# Create category entity
insert
  $cat isa category, has name "lifecycle";

# Create categorization relation
match
  $cat isa category, has name "lifecycle";
  $agg isa action-aggregate, has action-agg-id "AG1";
insert categorization(category: $cat, object: $agg);

# Create membership relations for each member
match
  $agg isa action-aggregate, has action-agg-id "AG1";
  $act1 isa action, has action-id "ACT1";
insert membership(member-of: $agg, member: $act1);

match
  $agg isa action-aggregate, has action-agg-id "AG1";
  $act2 isa action, has action-id "ACT2";
insert membership(member-of: $agg, member: $act2);

match
  $agg isa action-aggregate, has action-agg-id "AG1";
  $act4 isa action, has action-id "ACT4";
insert membership(member-of: $agg, member: $act4);

match
  $agg isa action-aggregate, has action-agg-id "AG1";
  $act3 isa action, has action-id "ACT3";
insert membership(member-of: $agg, member: $act3);
```

### 3.11 MessageAggregate Entity

**JSON:**
```json
{
  "id": "MAG1",
  "label": "TaskLifecycleWorkflow",
  "category": "lifecycle",
  "description": "Workflow covering the lifecycle of a Task...",
  "justification": "Implements AG1 TaskLifecycle by expressing..."
}
```

**TypeQL:**
```typeql
insert
  $mag isa message-aggregate,
    has message-agg-id "MAG1",
    has id-label "TaskLifecycleWorkflow",
    has description "Workflow covering the lifecycle of a Task from creation, through edits and completion toggling, to eventual deletion and UI updates.",
    has justification "Implements AG1 TaskLifecycle by expressing user commands and application events for creating, editing, marking complete/incomplete, and deleting tasks.";
```

### 3.12 Requirement Entity

  ** Revision **
    The schema was updated after this proposal was originally created:
    	relation requiring,
		    relates required-by,
		    relates conceptualized-as,
		    relates implemented-by;

    	entity requirement sub design-concept,
		    owns requirement-id @key,
		    owns requirement-type,
		    owns status,
		    owns priority,
		    plays requiring:required-by;
  	
      attribute requirement-id sub artifact-id, value string @regex("^REQ-[a-zA-Z0-9_.]*$");
	    attribute requirement-type value string @values("functional", "nonfunctional", "ui", "future-functional");
	    attribute priority value string @values("must", "should", "could");

  ** Notes:
    - "notes" in the json needs to be migrated to "justification"
    - "label" in the json needs to be a conformant identifier matching other concept json
    - specification below has been modified to account for the changes
    - "id" in the json becomes requirement-id; has new regex format "REQ-n".
    - requirements.json will need to be updated to new spec
    - "relatedConcepts" and "relatedMessages" related with the "requiring" relation (see below)
  **

**JSON:**
```json
{
  "id": "REQ-1",
  "type": "functional",
  "status": "draft",
  "label": "Local_todo_app",
  "category": "category",
  "description": "The system shall operate as a simple, single-user...",
  "priority": "must",
  "sectionHint": "1.1",
  "justification": "Summarizes the overall deployment and single-user context..."
}
```

**TypeQL:**
```typeql
insert
  $req isa requirement,
    has requirement-id "REQ-1",
		has requirement-type "functional",
		has status "draft",
		has priority "must",
    has id-label "Local_todo_app",
    has description "The system shall operate as a simple, single-user to-do list application that runs in a standard desktop or laptop web browser on the user's local machine without relying on external online services or user accounts.",
    has justification "Summarizes the overall deployment and single-user context...";
  
```
**JSON:**
```json
  {
    "anchors": [
      "AN2"
    ],
    "relatedConcepts": [
      "A1",
      "A2",
      "DE1",
      "DE7"
    ],
    "relatedMessages": [
      "MSG31",
      "MSG32"
    ]
  }
```

**TypeQL:**

```typeql
match
  $req isa requirement, has requirement-id "REQ-1";
  $an2 isa text-block, has anchor-id "AN2";
  $a1 isa actor, has actor-id "A1";
  $a2 isa actor, has actor-id "A2";
  $de1 isa data-entity, has data-entity-id "DE1";
  $de7 isa data-entity, has data-entity-id "DE7";
  $msg31 isa message, has message-id "MSG31";
  $msg32 isa message, has message-id "MSG32";
insert 
  anchoring(anchor: $an2, concept: $req);
  requiring(required-by: $req, conceptualized-as: $a1);
  requiring(required-by: $req, conceptualized-as: $a2);
  requiring(required-by: $req, conceptualized-as: $de1);
  requiring(required-by: $req, conceptualized-as: $de7);
  requiring(required-by: $req, conceptualized-as: $msg31);
  requiring(required-by: $req, conceptualized-as: $msg32);
```

---

## 4. Implementation Strategy

### 4.1 Entity Existence Check

Before creating any entity, check if it already exists to avoid duplicates:

```python
def entity_exists(self, entity_type: str, key_attr: str, key_value: str) -> bool:
    """Check if an entity with the given key already exists."""
    query = f'match $x isa {entity_type}, has {key_attr} "{key_value}";'
    result = self.client.execute_read_query(self.database, query)
    return result and len(result.get('answers', [])) > 0
```

### 4.2 Import Order

To ensure referential integrity, import in this order:

1. **Categories** - Create all category entities first
2. **Constraints** - Create constraint entities (for messages)
3. **Core Concepts** - Create Actor, Action, DataEntity entities
4. **Aggregates** - Create action-aggregate and message-aggregate entities
5. **Messages** - Create message entities
6. **Relations** - Create all relations in order:
   - Categorization (category → concept)
   - Anchoring (text-block → concept)
   - Messaging (producer/consumer → message)
   - Message-payload (message → data-entity)
   - Constrained-by (constraint → message)
   - Membership (aggregate → member)

### 4.3 Special Considerations

1. **Text-Block References**: The `anchors[]` field references text-block entities that must already exist. These are typically created from specification YAML files using the existing `--parse-spec-file` functionality.

2. **Sequence Data**: MessageAggregations contain `sequences[]` data which is not modeled in the current schema. This data will be ignored during import but could be captured in the description field.
  ** Revision **
  - sequences are to be related using the `membership-seq` relation, from schema:
    	relation membership-seq sub membership,
	    	owns order @card(1);
  - is works like `membership` exccept the `order` attribute is set with the sequence order.
  - ordering should be in increments > 1 so that items can be added more easily in future without forcing a re-order.  This should be a setting somewhere (command line switch?)
  
** Revision **
** specification and schema for requirements has been updated, see section 3.12 **
*3. **Requirement Entities**: Requirements don't have a dedicated entity type and will be imported as *generic `design-concept` entities. Additional fields like `type`, `status`, `priority`, `sectionHint`, *`relatedConcepts`, and `relatedMessages` will need to be:
*   - Encoded in the description field, OR
*   - Require schema extension to support them as attributes
**

4. **Category Handling**: Categories are referenced by name and should be created if they don't exist. The same category name can apply to multiple concepts.

5. **Constraint Creation**: Constraints are embedded in message objects and should be extracted and created as separate constraint entities before creating the constrained-by relations.

---

## 5. Command-Line Interface

### 5.1 New Argument

Add `--parse-concepts` argument to the CLI:

```python
parser.add_argument(
    '--parse-concepts',
    type=Path,
    help='Path to JSON concepts file to import (or directory containing multiple JSON files)'
)
```

### 5.2 Usage Examples

```bash
# Import a single JSON file
python typedb_import.py --parse-concepts ./json/concepts.json

# Import all JSON files in a directory
python typedb_import.py --parse-concepts ./json/

# Import with force update
python typedb_import.py --parse-concepts ./json/ --force-update
```

---

## 6. Error Handling

1. **Missing Text-Blocks**: When anchoring relations fail due to missing text-block entities, log a warning but continue processing.

2. **Missing References**: When messaging or membership relations fail due to missing referenced entities, log a warning and continue.

3. **Invalid IDs**: Skip entities with IDs that don't match the expected regex patterns.

4. **Duplicate Relations**: Existing relations should not cause errors - use try/except to silently handle duplicate insertions.

---

## 7. Testing Strategy

1. **Unit Tests**: Test each entity creation function independently.

2. **Integration Tests**: Test the full import flow with sample JSON data.

3. **Validation Tests**: After import, query TypeDB to verify:
   - All entities were created
   - All relations were established
   - No duplicate entities exist
   - Referential integrity is maintained

4. **Performance Tests**: Test with large JSON files (1000+ concepts) to ensure acceptable performance.

---

## 8. Future Enhancements

1. **Requirement Entity Type**: Add a dedicated `requirement` entity type to the schema to properly capture requirement-specific attributes.

2. **Sequence Modeling**: Add support for modeling message sequences in message-aggregates.

3. **Batch Insertions**: Optimize by batching multiple insert operations into single transactions.

4. **Progress Reporting**: Add progress bars for large imports.

5. **Validation Mode**: Add `--validate` flag to check JSON files against schema before import.

---

## Summary

This migration proposal provides a comprehensive mapping from JSON concept files to TypeDB entities and relations, following the existing patterns in `typedb_import.py`. The implementation should:

- Follow TypeDB 3 syntax patterns
- Check for entity existence before creation
- Handle all relation types appropriately
- Provide clear error messages
- Maintain referential integrity
- Be extensible for future enhancements

The proposed approach ensures backward compatibility with existing functionality while adding robust support for importing JSON concept data.