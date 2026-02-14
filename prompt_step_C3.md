

Prompt: “Step C3 – Extract Concepts from YAML Specification”

You are assisting in **Step C3 – Extract Concepts** of a conceptualization pipeline.


1. Overall task

You will receive one or more YAML documents that together describe **a single software specification**, including:

• Hierarchical Sections (`S*`) which contain `text_blocks`, identified with `anchor_id` formatted as (`AN*`), which is refered to here as an `anchor`.
• For each anchor:
- `text` (natural-language excerpt),
- `type` (e.g., `goal`, `capability`, `constraint`, `future-capability`),
- `semantic_cues`,
- A list of **hint** concepts: `concepts: [{concept_id: Cn, name: "..."}]`.


Your job is to extract **Concepts**: `Actors`, `Actions`, and `DataEntities` and output them as JSON according to the `Concepts.json` schema described below.


Do **not** design UI flows, message protocols, or requirements here; those occur in later steps. Focus on a **technology-agnostic domain concept model**.


You must produce a **two-part answer**:

1. A brief human-readable **Reasoning** section.
2. A **Final JSON** section which is either:
- A JSON **array** of concept objects conforming to `Concepts.json`, or
- A JSON **error object** if you cannot do so safely.





2. Definitions and criteria

2.1 Anchors (AN*)
• An **Anchor** represents a specific, meaningful excerpt from the original specification.
• Each anchor has an ID like `AN1`, `AN2`, etc., and contains `text`.
• Anchors are used as **evidence** for your Concepts.
• In this step:
- **Do not create new anchor IDs.** Only use the `AN*` anchor IDs given in the YAML.
- Every Concept should have at least one supporting anchor ID in its `anchors` list.


2.2 Concept types

You must create three kinds of concepts:

1. **Actor** (`type = "Actor"`, IDs: `A1`, `A2`, ...)

- Represents any active entity that can **initiate actions** or **produce/consume messages**.
- Examples:
  - End users (e.g., `EndUser`).
  - Software components (e.g., `BrowserApp`, `LocalStorageEngine`, `SyncService`).
  - External services (if mentioned).
- Criteria:
  - The spec describes it as doing something: initiating, responding, processing.
  - It plays a meaningful role in the domain-level workflows.

2. **Action** (`type = "Action"`, IDs: `ACT1`, `ACT2`, ...)

- An **Action** is an atomic operation or capability the system must support.
- Actions are domain-level verbs such as `CreateTask`, `EditTask`, `DeleteTask`, `SetFilterByCategory`, `PersistViewPreferences`.
- Criteria:
  - The spec describes a discrete behavior (create, edit, delete, filter, sort, save, sync, etc.).
  - It should be **as atomic as reasonable**: not a large feature bundle; small steps that can be composed later in aggregations and message flows.
- In this step, focus on **domain-level** actions, not on concrete UI gestures (`click`, `tap`, etc.).

3. **DataEntity** (`type = "DataEntity"`, IDs: `DE1`, `DE2`, ...)

- A **DataEntity** is a high-level conceptual “thing” the system stores, manipulates, or transfers.
- Criteria:
  - The spec describes it with identity and/or attributes (e.g., `Task`, `Category`, `ViewPreferences`, `Reminder`, `Tag`, `SavedView`, `AnalyticsSummary`, `SyncConfiguration`).
  - It recurs across multiple operations or matters as a stable object in the domain.
- Prefer **coarsely-grained entities**; detailed attributes/properties will be modeled later.





3. Schema you must follow (`Concepts.json`)

The **normal successful output** is a JSON array, where each element conforms to:


{
  "type": "Actor | Action | DataEntity",
  "id": "A<number> | ACT<number> | DE<number>",
  "label": "string",
  "categories": ["string", "..."],       // optional; may be omitted or empty
  "description": "string",
  "justification": "string",             // optional but recommended
  "anchors": ["AN1", "AN2", "..."],      // optional but recommended; must be valid existing anchors if present
  "sourceConceptIds": ["C1", "C2", "..."]// optional; concept_id hints from the input YAML that contributed
}


Constraints:

• `type`, `id`, `label`, and `description` are **required**.
• `categories`, `justification`, `anchors`, and `sourceConceptIds` are **optional**, but:
- Prefer to include `justification` and `anchors` wherever possible.
- `categories` and `sourceConceptIds` can be omitted when not applicable.
• `additionalProperties` are **not allowed**: do not add any other keys.





4. ID and category rules

4.1 ID allocation
• In each run:
- Number Actors as `A1, A2, A3, ...` in a consistent, stable order.
- Number Actions as `ACT1, ACT2, ACT3, ...`.
- Number DataEntities as `DE1, DE2, DE3, ...`.
• Do **not** reuse an ID across different types.
• You can choose any sensible ordering (e.g., by significance or first appearance), but be consistent within the single run.


4.2 Categories

Use `categories` as an **array of strings** drawn from this vocabulary where appropriate:

• `"core"` – Central to the initial required behavior.
• `"future"` – Described only in future/nice-to-have features (anchors of `type: "future-capability"` or clearly labeled as “nice-to-have”).
• `"ui"` – Primarily about views or presentation (e.g., main task list view, saved views).
• `"persistence"` – Related to data storage, autosave, local data residency, export/import.
• `"analytics"` – Related to statistics, charts, insights.
• `"sync"` – Related to multi-device synchronization.
• `"nonfunctional"` – Quality attributes that you explicitly decide to model as concepts (rare).
• `"excluded"` – Concepts explicitly out-of-scope for the current version.


Mapping rules:

• If **all** supporting anchors are `type: "future-capability"` → include `"future"` in `categories`.
• If anchors are under an “Out of Scope / Not Required” section → include `"excluded"` in `categories`.
• For local storage, autosave, export/import, etc. → include `"persistence"`.
• For multi-device sync → include `"sync"`.
• For UI views/layouts → include `"ui"`.
• For main domain objects and actions (e.g., Task, Category, CreateTask) → include `"core"` unless clearly future-only or excluded.
• It is allowed to have **multiple** categories, e.g. `["core", "ui"]` or `["future", "sync"]`.
• If you are not sure, you may omit `categories` or keep it empty.





5. Use of anchors and C* hints

5.1 Anchors in `anchors` field
• For each concept, add at least one `anchors` entry **if possible**.
• Each entry must be a valid `AN*` ID present in the YAML.
• Choose anchors whose `text` clearly support the existence of the concept.
• You may attach **multiple anchors** when a concept is supported across different parts of the spec (e.g., `Task` appears in many anchors).


5.2 C* guidance concepts in `sourceConceptIds`
• The input YAML may contain `concepts` with `concept_id: Cn`, `name: "...“` and `description: "...“` under anchors.
• Treat these as **hints**, not as final concepts:
- You are **not** required to create a 1:1 mapping for each `C*`.
- You may merge, generalize, or ignore them if they don’t meet Actor/Action/DataEntity criteria.
• When a `C*` hint **contributes** to a concept you create:
- Add that `concept_id` string (e.g., `"C11"`) to `sourceConceptIds` for the resulting concept.
- You may list multiple sourceConceptIds for one concept if relevant.





6. Inclusion / exclusion of concepts
• Extract **all reasonable** Actors, Actions, and DataEntities that meet the criteria, even if mentioned only once and even if they appear in future or excluded sections.
• **Non-functional** anchors (performance, offline, privacy, usability):
- Generally: do **not** create DataEntities or Actions solely to represent them.
- Exception: if the text clearly implies an active component (e.g., an `OfflineSyncEngine`), you may introduce an Actor or DataEntity for it.
• **Out-of-scope** / excluded features (e.g., multi-user, authentication, collaboration, mobile):
- You may still create concepts to represent them (e.g., `MultiUserSupport`, `AuthenticationFeature`, `CollaborationCapability`).
- Mark them with `"excluded"` in `categories`.
• **Future** features:
- Do create concepts for them (Actors, Actions, DataEntities) if they are meaningful.
- Mark them appropriately with `"future"` and any other relevant categories (`"analytics"`, `"sync"`, etc.).





7. Handling multiple YAML documents
• You may receive multiple YAML documents in the input, but they all belong to **one logical specification**.
• IDs such as `section_id`, `anchor_id` (`AN*`), and `concept_id` (`C*`) are consistent and unique across these documents.
• When collecting anchors or C* hints, treat all documents together as a single pool.





8. Error handling

You must choose between:

1. **Successful concepts extraction**:  
- Output a valid JSON **array** of concept objects conforming to the schema above.

2. **Error output** when you cannot safely generate valid concepts:
- Output a **single JSON object** (not an array) with at least:
  ```json
  {
    "status": "error",
    "message": "Short human-readable explanation",
    "details": {
      "...": "Optional machine-readable diagnostics"
    }
  }
  ```
- Use this only for **critical** issues:
  - The YAML is structurally invalid or missing required parts.
  - Anchors are inconsistent or impossible to interpret.
  - You cannot follow the schema without obvious guessing.


Do **not** mix concept objects and error fields in the same top-level JSON structure.





9. Output format and structure

Your response must have two clearly separated parts:

1. A **Reasoning** section in natural language:
- Summarize:
  - Main Actors you identified.
  - Main DataEntities.
  - Main Actions.
  - Any notable decisions (generalizations, exclusions, ambiguous points).
- This section is for humans and will not be parsed by machines.

2. A **Final JSON** section that contains **only** JSON:
- Either:
  - A JSON array of concept objects, or
  - A JSON error object with `status: "error"`, etc.
- The JSON must be syntactically valid (no comments, no trailing commas).
- Do not wrap it in Markdown code fences in a way that adds non-JSON characters unless your execution environment strips them. If you must use fences, ensure the content inside is pure JSON.


Suggested structure:


Reasoning:
<your explanation here>

Final JSON:
<your JSON array or error object here>

*** YAML INPUT FILE ***
