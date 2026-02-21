
Your task is to define **Messages** and **MessageAggregations** derived from the provided Concepts and Aggregations, grounded in the specification.

• **Messages** are concrete interactions between a producer Actor and a consumer Actor.
• **MessageAggregations** are workflows represented as ordered sequences of Messages.


You must produce a **three-part answer**:
1. A brief human-readable **Reasoning** section.
2. **Final Messages JSON**: a valid Messages array or an error object.
3. **Final MessageAggregations JSON**: a valid MessageAggregations array or an error object.


⸻


**1. Definitions**


**1.1 Actors (A\*)**
• Active entities that send or receive messages.
• Only Actor IDs that exist in the provided Concepts input may be used as `producer` or `consumer`.


**1.2 Actions (ACT\*)**
• Domain-level operations. Used to determine what messages are needed within an Aggregation.


**1.3 DataEntities (DE\*)**
• Conceptual data objects. Used as payload references in messages.


**1.4 Aggregations (AG\*)**
• Logical groupings of Concepts with a `category` (e.g., `"lifecycle"`, `"view"`, `"service"`, `"future"`).
• Each Aggregation drives one or more Messages and at least one MessageAggregation.


**1.5 Anchors (AN\*)**
• Anchor IDs from the specification. Do **not** create new `AN*` IDs. Only reuse existing ones.


⸻


**2. Messages Schema and Semantics**


The successful Messages output is a JSON array where each element conforms to:


{
  "id": "MSG<number>",
  "label": "string",
  "category": "string",
  "description": "string",
  "producer": "A*",
  "consumer": "A*",
  "payload": [
    {
      "id": "string",
      "label": "string",
      "refConceptId": "string | null",
      "constraint": "string",
      "notes": "string",
      "isNew": false
    }
  ],
  "constraints": [
    {
      "id": "C-MSGx-1",
      "label": "string",
      "constraint": "string",
      "notes": "string",
      "isNew": true
    }
  ],
  "justification": "string",
  "anchors": ["AN*"]
}


Constraints:
• `id`, `label`, `producer`, `consumer` are **required**.
• Use `MSG1`, `MSG2`, ... sequentially in this run.
• `producer` and `consumer` must reference **existing Actor IDs** from the Concepts input.
• Do **not** invent new `A*`, `ACT*`, `DE*`, or `AN*` IDs.
• `payload`, `constraints`, `justification`, `anchors`, `category` are optional but recommended.


**2.1 Message Categories**

• `"command"` – producer asks consumer to perform a state-changing action.
• `"request"` – producer asks consumer to return data, without direct state change.
• `"response"` – consumer replies to a `"command"` or `"request"` with outcome/data.
• `"event"` – consumer notifies others that something has happened (e.g., autosave done, reminder fired).


You may omit `category` if unclear, but use these where applicable.


**2.2 Payload Modeling**
• Use `payload` to list the **main data elements** carried by the message.
• Prefer referencing existing DataEntities via `refConceptId`.
• When a payload directly represents a DataEntity, use its ID as the payload `id`:
```json
{ "id": "DE1", "label": "Task", "refConceptId": "DE1" }
```
• Use `constraint` to capture key rules about the payload (e.g., "title must be non-empty", "dueDate is optional").
• Use `isNew: true` only if the payload structure is **not** captured by any existing DataEntity and should not be for now.


**2.3 Message Constraints**
• Use `constraints` for:
- Preconditions (e.g., "Category must exist before adding tasks to it").
- Validation rules (e.g., "Filter must reference a valid category ID").
- Behavioral assumptions (e.g., "No network usage; operations remain local").
• Constraint IDs follow the pattern `C-<MSG_ID>-<sequence>`, e.g., `"C-MSG1-1"`.


⸻


**3. MessageAggregations Schema and Semantics**


The successful MessageAggregations output is a JSON array where each element conforms to:


{
  "id": "MAG<number>",
  "label": "string",
  "category": "string",
  "description": "string",
  "sequences": [
    [
      {
        "id": "MSGx",
        "label": "string",
        "description": "string",
        "isNew": false
      }
    ]
  ],
  "justification": "string",
  "anchors": ["AN*"]
}


Constraints:
• `id`, `label`, `sequences` are **required**.
• `category`, `description`, `justification`, `anchors` are recommended.
• `sequences` is an array of alternative paths through the workflow.
- Each path is an ordered array of steps.
- Each step's `id` must reference an existing `MSG*` defined in the Messages output.
- `isNew` should generally be `false`; define all messages in the Messages output rather than as placeholders here.


⸻


**4. Deriving Messages and MessageAggregations from Aggregations**


**4.1 Which Aggregations to Cover**


Prioritize Aggregations with these categories:
• `"lifecycle"` – Task/entity lifecycle workflows.
• `"view"` – View preparation and interaction flows.
• `"service"` – Persistence, reminders, analytics, sync.
• `"future"` or `"feature"` – Major future feature sets worth modeling.


For each such Aggregation, decide whether to model it now. If yes, produce:
• A set of `MSG*` messages implementing the actions in that Aggregation.
• At least one `MAG*` whose sequences describe the workflow using those `MSG*` IDs.


**4.2 Mapping Aggregation Members to Messages**


For each Aggregation's ordered `members` list:
1. Identify relevant **Actions** (`ACT*`) — these indicate what messages are needed.
2. Identify relevant **Actors** (`A*`) — these indicate producer and consumer roles.
3. For each key step, define at minimum:
- A `"command"` or `"request"` message.
- A `"response"` message.
- Optionally an `"event"` message if the spec suggests broadcasts or notifications.


Conceptual example:
• `ACT_CreateTask` →
- `MSG1 CreateTaskCommand` (producer: BrowserUI, consumer: LocalTaskStore)
- `MSG2 TaskCreatedResponse` (producer: LocalTaskStore, consumer: BrowserUI)


**4.3 Building MessageAggregations**


For each Aggregation you cover:
• Create a `MAG*` with a label reflecting the workflow (e.g., `MAG_TaskLifecycleWorkflow`, `MAG_PersistenceWorkflow`).
• Assign `category` consistent with the source Aggregation (e.g., `"lifecycle"`, `"view"`, `"service"`, `"future"`).
• Define one or more `sequences` using the order implied by the Aggregation's members.
• In `description` and `justification`, explain the overall actor/user story and reference the originating Aggregation informally.


**4.4 Anchors**

• Populate `anchors` on both Messages and MessageAggregations using existing `AN*` IDs.
• Choose anchors whose text best motivates:
- The existence of the message (a specific capability or behavior).
- The existence of the workflow (e.g., "task lifecycle", "autosave", "multi-device sync").


⸻


**5. Error Handling**


You must choose between a valid JSON array or a single error object for **each** of the two outputs independently.


Error object format:

{
  "status": "error",
  "message": "Short explanation",
  "details": { "reason": "...", "notes": "..." }
}


Use the error object only for critical issues:
• Concepts or Aggregations input is missing or structurally invalid.
• The spec lacks usable anchors.
• There are no usable Actors to assign as producers/consumers.


Do **not** mix message objects and error fields in the same top-level structure.


⸻


**6. Output Format**


Your response must have three labeled sections:


Reasoning:
<your explanation here>

Final Messages JSON:
<JSON array of messages OR error object>

Final MessageAggregations JSON:
<JSON array of message aggregations OR error object>

• Both JSON blocks must be **pure JSON** (no comments, no trailing commas).
• The Reasoning section is for human readers and will not be parsed.


⸻


*** INPUT DATA ***


{{spec}}


{{concepts}}


{{aggregations}}