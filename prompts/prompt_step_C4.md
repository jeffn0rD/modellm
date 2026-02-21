
Prompt: “Step C4 – Define Concept Aggregations”

You are assisting in **Step C4 – Define Concept Aggregations** of a conceptualization pipeline.


1. Overall task

You will receive:

1. **Specification YAML**  one or more YAML documents that together describe **a single software specification**, including:
- Hierarchical Sections (`S*`) which contain `text_blocks`, identified with `anchor_id` formatted as (`AN*`), which is refered to here as an `anchor`.
- For each anchor:
  - `text` (natural-language excerpt),
  - `type` (e.g., `goal`, `capability`, `constraint`, `future-capability`),
  - `semantic_cues`,
  - A list of **hint** concepts: `concepts: [{concept_id: Cn, name: "..."}]`.

2. **Concepts.json**:
- A list of Concepts produced in Step C3.
- Each concept has:
  - `type`: `"Actor" | "Action" | "DataEntity"`,
  - `id`: `"A*" | "ACT*" | "DE*"`,
  - `label`, `description`, optional `categories`, `anchors`, `sourceConceptIds`.


Your job is to create **Aggregations**: logical groupings of these concepts (and optionally other aggregations) that capture:

• Lifecycles (e.g., Task lifecycle from create to delete),
• View / interaction flows (e.g., preparing main task list view),
• Service or responsibility groupings (e.g., persistence actors),
• Future feature sets (e.g., analytics, sync, reminders).


You must produce a **two-part answer**:

1. A brief human-readable **Reasoning** section.
2. A **Final JSON** section that is either:
- A JSON **array** of aggregation objects, or
- A JSON **error object** if you cannot safely generate the array.


⸻


2. Aggregation definition and schema

Aggregations are described by the `Aggregation.json` schema:


{
  "id": "string",           // e.g., 'AG1', 'AG2', ...
  "label": "string",
  "category": "string",     // optional, e.g., 'lifecycle', 'view', 'service', 'feature', 'future'
  "members": ["string"],    // IDs of Concepts (A*, ACT*, DE*) or other Aggregations (AG*)
  "description": "string",  // explanation of what this aggregation represents
  "justification": "string",// why these members belong together; link to modeling goals
  "anchors": ["string"]     // optional; Anchor IDs like 'AN3' that motivated this aggregation
}


Constraints:

• Top-level JSON must be an **array** of such objects (for success) or a single error object (for failure).
• For each aggregation object:
- `id`, `label`, `members` are **required**.
- `category`, `description`, `justification`, `anchors` are **optional** but strongly recommended.
• No additional properties are allowed on the objects.


⸻


3. ID and membership rules

3.1 Aggregation IDs
• Use IDs with the prefix `AG`:
- `AG1`, `AG2`, `AG3`, ...
• Start numbering from `AG1` in each run.
• Do **not** reuse an `AG` ID for multiple aggregations.


3.2 Members
• `members` is an array of strings, each string being:
- A **Concept ID** (`A*`, `ACT*`, `DE*`) that exists in the provided `Concepts.json`, or
- An **Aggregation ID** (`AG*`) that you define in this same output (allowing hierarchical aggregations).
• You must **not invent new A*/ACT*/DE* IDs** here.
• You may use AG* as members (hierarchical aggregations), but:
- Prefer to group **concepts directly**.
- Use nested AG* membership only when it provides clear structure (e.g., a high-level aggregation that bundles several lower-level sequences).


⸻


4. Types of aggregations to consider

You should look for natural, meaningful aggregations of **Actions**, **Actors**, and **DataEntities** such as:

1. **Lifecycle sequences (`category: "lifecycle"`)**

- Describe the major phases in the life of a DataEntity.
- Typical `members`: Action IDs (`ACT*`) ordered in the **intended lifecycle sequence**.
- Examples:
  - `AG_TaskLifecycle`: `CreateTask`, `EditTask`, `MarkTaskComplete`, `MarkTaskIncomplete`, `DeleteTask`.
  - `AG_CategoryLifecycle`: `CreateCategory`, `RenameCategory`, `DeleteCategory`.
- When you define a lifecycle aggregation:
  - Order `members` as the sequence of steps.
  - In `description`, clearly explain the order and any loops/optional steps (e.g., some actions repeatable, some mutually exclusive).

2. **View / interaction sequences (`category: "view"`)**

- Capture how the system prepares, presents, and updates a particular view or interaction context.
- Typical `members`: Action IDs (`ACT*`), possibly some Actor IDs (`A*`) if helpful.
- Examples:
  - `AG_MainListViewFlow`: includes actions like loading tasks, loading preferences, applying filters/sorts, rendering/updating the main task list.
- As with lifecycles:
  - Order `members` in the intended flow sequence.
  - In `description`, describe the typical user-facing story (“On startup, load tasks and view preferences, then apply filters/sorts, then show the main list; repeat filter/sort actions as user interacts.”).

3. **Service / maintenance flows (`category: "service"`)**

- Group sequences of actions involving supporting services such as persistence, reminders, analytics, sync, etc.
- Examples:
  - `AG_PersistenceFlow`: autosave after each mutation, load data on startup, persist preferences.
  - `AG_ReminderSchedulingFlow`, `AG_SyncFlow` (for future features).
- Order `members` to show the typical service-level scenario (e.g., schedule → wait → trigger).

4. **Data-model or feature aggregates (`category: "data-model"` or `"feature"`)**

- Group DataEntities and related actions/actors into conceptual clusters:
  - `AG_CoreTaskDataModel`: `Task`, `Category`, `ViewPreferences`.
  - `AG_AnalyticsFeatureSet`: analytics-related DataEntities and Actions.
  - `AG_SyncFeatureSet`: sync-related actors/actions/entities.
- These need not represent sequences; they can simply be groupings of related concepts.


Quantity guidance:

• Aim for a moderate number of aggregations (e.g., 3–10) that:
- Include at least:
  - One core lifecycle aggregation for important entities (e.g., Task).
  - One or more view/interaction flows (e.g., main list view).
  - One or more service/maintenance flows (e.g., persistence/autosave).
  - One or more future/feature groupings if the spec has substantial future features.


Avoid:

• Aggregations with only a single member unless there is a strong modeling reason.
• Redundant aggregations that duplicate the same members without a clear new angle.


5. Category field for aggregations

`category` is a free-form string, but you should prefer this vocabulary:

• `"lifecycle"` – for action sequences describing the lifecycle of a DataEntity or key workflow.
• `"view"` – for UI/view-related flows and interaction sequences.
• `"service"` – for groupings/sequences of actors/actions providing support services (persistence, sync, analytics, reminders).
• `"data-model"` – for groupings centered on DataEntities (domains or subdomains).
• `"feature"` – for functional feature sets (e.g., analytics package, sync package).
• `"future"` – when the aggregation consists mostly of future/nice-to-have concepts.


You can also use `"future"` in combination with labels like `FutureAnalyticsFlows`, but since `category` is a single string here, choose the **dominant** classification.


6. Use of anchors
• Use the YAML’s anchor IDs (`AN1`, `AN2`, etc.) in the `anchors` array.
• For each aggregation, choose one or more anchors whose `text` strongly motivates:
- The lifecycle or flow being grouped, or
- The responsibility grouping, or
- The future feature set definition.
• You do **not** create new anchors in this step; only reuse existing `AN*` IDs from the spec.


⸻


7. Relationship to Concepts.json
• You are given `Concepts.json`, which already maps Concepts to anchors.
• When forming aggregations, you may:
- Look at the anchor references on the member concepts,
- Look at concept `categories` (e.g., `"future"`, `"sync"`, `"analytics"`) to cluster them appropriately.
• You must **not** modify or extend `Concepts.json` in this step.
• You must **not** invent new concept IDs; all concept members must exist in `Concepts.json`.


⸻


8. Error handling

As with Step C3, there are two possible outcomes:

1. **Successful aggregation extraction**:
- Output a valid JSON **array** of aggregation objects as defined above.

2. **Error output** if you cannot safely create aggregations:
- Output a single JSON object of the form:
  ```json
  {
    "status": "error",
    "message": "Short human-readable explanation",
    "details": {
      "reason": "...",
      "missingInputs": [...],
      "notes": "Any other relevant info"
    }
  }
  ```
- Use this only for critical issues, such as:
  - `Concepts.json` is missing or structurally invalid.
  - The YAML spec cannot be parsed or lacks any anchors.
  - There are no usable concepts to aggregate.


Do not mix aggregation objects and error fields at the same top level.


⸻


9. Output structure (two-part answer)

Your response must have **two clearly separated parts**:

1. **Reasoning:**
- Provide a short explanation of:
  - The main aggregations you chose (by label).
  - The rationale for each category.
  - Any ordering assumptions in lifecycle/view sequences.
  - Any ambiguous or alternative groupings you considered.
- This is for human review only and will not be machine-parsed.

2. **Final JSON:**
- Provide **only JSON**:
  - Either a JSON **array** of aggregations,
  - Or a JSON **error object** following the format above.
- Ensure the JSON is syntactically valid (no comments, no trailing commas).
- If you use Markdown fences, ensure the content inside is pure JSON.


Suggested template:


Reasoning:
<your explanation here>

Final JSON:
<your JSON array or error object here>

*** SPEC YAML ***



{{spec}}

*** CONCEPTS JSON ***











{{concepts}}

