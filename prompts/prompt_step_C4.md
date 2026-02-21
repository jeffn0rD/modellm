
Your task is to create **Aggregations**: logical groupings of Concepts (and optionally other Aggregations) that capture lifecycles, interaction flows, service responsibilities, and feature sets.


⸻


**1. Definitions**


**1.1 Aggregations**


An Aggregation is a named logical grouping of Concepts and/or other Aggregations. Aggregations are used to capture:
• Lifecycles (e.g., Task lifecycle from create to delete)
• View / interaction flows (e.g., preparing the main task list view)
• Service or responsibility groupings (e.g., persistence actors and actions)
• Future feature sets (e.g., analytics, sync, reminders)


**1.2 Anchors (AN\*)**
• Anchor IDs (`AN1`, `AN2`, etc.) appear in the spec and are referenced on Concepts.
• Do **not** create new anchor IDs. Only reuse existing `AN*` IDs from the spec.


**1.3 Concepts**
• Concepts are pre-defined entities of type `Actor` (`A*`), `Action` (`ACT*`), or `DataEntity` (`DE*`).
• You must **not** invent new `A*`, `ACT*`, or `DE*` IDs. All concept members must exist in the provided Concepts input.


⸻


**2. Aggregation Schema**


The successful output is a JSON array where each element conforms to:


{
  "id": "string",
  "label": "string",
  "category": "string",
  "members": ["string"],
  "description": "string",
  "justification": "string",
  "anchors": ["string"]
}


Constraints:
• `id`, `label`, and `members` are **required**.
• `category`, `description`, `justification`, and `anchors` are **optional** but strongly recommended.
• No additional properties are allowed.
• The top-level JSON must be an **array** of such objects (for success) or a single error object (for failure).


⸻


**3. ID and Membership Rules**


**3.1 Aggregation IDs**
• Use the prefix `AG`: `AG1`, `AG2`, `AG3`, ...
• Start numbering from `AG1` in each run.
• Do **not** reuse an `AG` ID for multiple aggregations.


**3.2 Members**
• `members` is an array of strings, each being:
- A **Concept ID** (`A*`, `ACT*`, `DE*`) that exists in the provided Concepts input, or
- An **Aggregation ID** (`AG*`) that you define in this same output (allowing hierarchical aggregations).
• You may use `AG*` as members for hierarchical aggregations, but:
- Prefer to group **concepts directly**.
- Use nested `AG*` membership only when it provides clear structure.


⸻


**4. Types of Aggregations to Create**


**1. Lifecycle sequences (`category: "lifecycle"`)**
• Describe the major phases in the life of a DataEntity.
• Typical `members`: Action IDs (`ACT*`) ordered in the **intended lifecycle sequence**.
• Examples:
- `AG_TaskLifecycle`: `CreateTask`, `EditTask`, `MarkTaskComplete`, `MarkTaskIncomplete`, `DeleteTask`
- `AG_CategoryLifecycle`: `CreateCategory`, `RenameCategory`, `DeleteCategory`
• Order `members` as the sequence of steps.
• In `description`, explain the order and any loops or optional steps.


**2. View / interaction sequences (`category: "view"`)**
• Capture how the system prepares, presents, and updates a particular view or interaction context.
• Typical `members`: Action IDs (`ACT*`), possibly some Actor IDs (`A*`).
• Order `members` in the intended flow sequence.
• In `description`, describe the typical user-facing story.


**3. Service / maintenance flows (`category: "service"`)**
• Group sequences of actions involving supporting services such as persistence, reminders, analytics, or sync.
• Order `members` to show the typical service-level scenario.


**4. Data-model or feature aggregates (`category: "data-model"` or `"feature"`)**
• Group DataEntities and related actions/actors into conceptual clusters.
• These need not represent sequences; they can be groupings of related concepts.


**Quantity guidance:**
• Aim for 3–10 aggregations that include at least:
- One core lifecycle aggregation for important entities (e.g., Task).
- One or more view/interaction flows.
- One or more service/maintenance flows.
- One or more future/feature groupings if the spec has substantial future features.


**Avoid:**
• Aggregations with only a single member unless there is a strong modeling reason.
• Redundant aggregations that duplicate the same members without a clear new angle.


⸻


**5. Category Vocabulary**


`category` is a free-form string; prefer this vocabulary:

• `"lifecycle"` – Action sequences describing the lifecycle of a DataEntity or key workflow.
• `"view"` – UI/view-related flows and interaction sequences.
• `"service"` – Groupings/sequences of actors/actions providing support services (persistence, sync, analytics, reminders).
• `"data-model"` – Groupings centered on DataEntities (domains or subdomains).
• `"feature"` – Functional feature sets (e.g., analytics package, sync package).
• `"future"` – When the aggregation consists mostly of future/nice-to-have concepts.


When a grouping spans multiple categories, choose the **dominant** classification.


⸻


**6. Use of Anchors**

• Populate the `anchors` array using `AN*` IDs from the spec.
• For each aggregation, choose one or more anchors whose text strongly motivates the lifecycle, flow, responsibility grouping, or future feature set.
• You may look at the anchor references on member concepts to guide selection.


⸻


**7. Relationship to Concepts**

• You may use concept `categories` (e.g., `"future"`, `"sync"`) to cluster members appropriately.
• You must **not** modify or extend the Concepts input in this step.


⸻


**8. Error Handling**


You must choose between:

• A valid JSON **array** of aggregation objects conforming to the schema above, **or**
• A **single JSON error object** (not an array):


{
  "status": "error",
  "message": "Short human-readable explanation",
  "details": {
    "reason": "...",
    "missingInputs": [],
    "notes": "Any other relevant info"
  }
}


Use the error object only for **critical** issues:
• The Concepts input is missing or structurally invalid.
• The spec cannot be parsed or lacks any anchors.
• There are no usable concepts to aggregate.


Do **not** mix aggregation objects and error fields at the same top level.


⸻


**9. Output Format**


Your response must have two clearly separated parts:


**Part 1 – Reasoning** (natural language):
• Summarize the main aggregations you chose and the rationale for each category.
• Describe any ordering assumptions in lifecycle/view sequences.
• Note any ambiguous or alternative groupings you considered.
• This section is for human review only and will not be machine-parsed.


**Part 2 – Final JSON** (JSON only):
• Either a JSON array of aggregation objects, or a JSON error object.
• Must be syntactically valid (no comments, no trailing commas).


Suggested structure:


Reasoning:
<your explanation here>

Final JSON:
<your JSON array or error object here>


⸻


*** INPUT DATA ***


{{spec}}


{{concepts}}