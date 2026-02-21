
Your task is to extract **Actors**, **Actions**, and **DataEntities** from the specification and output them as JSON according to the `Concepts.json` schema described below.


Do **not** design UI flows, message protocols, or requirements here; those occur in later steps. Focus on a **technology-agnostic domain concept model**.


⸻


**1. Definitions and Criteria**


**1.1 Anchors (AN\*)**
• Each anchor has an ID like `AN1`, `AN2`, etc.
• **Do not create new anchor IDs.** Only use the `AN*` anchor IDs given in the input.
• Every concept should have at least one supporting anchor ID in its `anchors` list.


**1.2 Concept Types**


You must create three kinds of concepts:


**1. Actor** (type = `"Actor"`, IDs: `A1, A2, ...`)
• Represents any active entity that can **initiate actions** or **produce/consume messages**.
• Examples: end users (e.g., `EndUser`), software components (e.g., `BrowserApp`, `LocalStorageEngine`, `SyncService`), external services (if mentioned).
• Criteria:
- The spec describes it as doing something: initiating, responding, processing.
- It plays a meaningful role in the domain-level workflows.


**2. Action** (type = `"Action"`, IDs: `ACT1, ACT2, ...`)
• An atomic operation or capability the system must support.
• Domain-level verbs such as `CreateTask`, `EditTask`, `DeleteTask`, `SetFilterByCategory`, `PersistViewPreferences`.
• Criteria:
- The spec describes a discrete behavior (create, edit, delete, filter, sort, save, sync, etc.).
- Should be **as atomic as reasonable**: not a large feature bundle; small steps that can be composed later.
• Focus on **domain-level** actions, not on concrete UI gestures (`click`, `tap`, etc.).


**3. DataEntity** (type = `"DataEntity"`, IDs: `DE1, DE2, ...`)
• A high-level conceptual "thing" the system stores, manipulates, or transfers.
• Examples: `Task`, `Category`, `ViewPreferences`, `Reminder`, `Tag`, `SavedView`, `AnalyticsSummary`, `SyncConfiguration`.
• Criteria:
- The spec describes it with identity and/or attributes.
- It recurs across multiple operations or matters as a stable object in the domain.
• Prefer **coarsely-grained entities**; detailed attributes/properties will be modeled later.


⸻


**2. Schema You Must Follow (`Concepts.json`)**


The normal successful output is a JSON array where each element conforms to:


{
  "type": "Actor | Action | DataEntity",
  "id": "A<number> | ACT<number> | DE<number>",
  "label": "string",
  "categories": ["string", "..."],
  "description": "string",
  "justification": "string",
  "anchors": ["AN1", "AN2", "..."],
  "sourceConceptIds": ["C1", "C2", "..."]
}


Constraints:
• `categories`, `justification`, `anchors`, and `sourceConceptIds` are **optional**, but:
- Prefer to include `justification` and `anchors` wherever possible.
- `categories` and `sourceConceptIds` can be omitted when not applicable.


⸻


**3. ID and Category Rules**


**3.1 ID Allocation**
• Number Actors as `A1, A2, A3, ...` in a consistent, stable order.
• Number Actions as `ACT1, ACT2, ACT3, ...`.
• Number DataEntities as `DE1, DE2, DE3, ...`.
• You can choose any sensible ordering (e.g., by significance or first appearance), but be consistent within the single run.


**3.2 Categories**


Use `categories` as an **array of strings** drawn from this vocabulary where appropriate:
• `"core"` – Main domain objects and actions unless clearly future-only or excluded.
• `"future"` – Described only in future/nice-to-have features or clearly labeled as "nice-to-have".
• `"persistence"` – Related to data storage, autosave, local data residency, export/import.
• `"sync"` – Related to multi-device synchronization.
• `"excluded"` – Concepts explicitly out-of-scope for the current version.


Mapping rules:
• If anchors are under an "Out of Scope / Not Required" section → include `"excluded"` in `categories`.
• For multi-device sync → include `"sync"`.
• If you are not sure, you may omit `categories` or keep it empty.


⸻


**4. Use of Anchors and C\* Hints**


**4.1 Anchors in `anchors` Field**
• Each entry must be a valid `AN*` ID present in the input.
• You may attach **multiple anchors** when a concept is supported across different parts of the spec.


**4.2 C\* Guidance Concepts in `sourceConceptIds`**
• Treat these as **hints**, not as final concepts:
- You are **not** required to create a 1:1 mapping for each `C*`.
- You may merge, generalize, or ignore them if they don't meet Actor/Action/DataEntity criteria.
- Add the `concept_id` string (e.g., `"C11"`) to `sourceConceptIds` for the resulting concept.
- You may list multiple `sourceConceptIds` for one concept if relevant.


⸻


**5. Inclusion / Exclusion of Concepts**

• **Non-functional** anchors (performance, offline, privacy, usability):
- Generally: do **not** create DataEntities or Actions solely to represent them.
- Exception: if the text clearly implies an active component (e.g., an `OfflineSyncEngine`), you may introduce an Actor or DataEntity for it.
• **Out-of-scope concepts**:
- You may still create concepts to represent them.
- Mark them with `"excluded"` in `categories`.
• **Future concepts**:
- Do create concepts for them if they are meaningful.
- Mark them with `"future"` and any other relevant categories (e.g., `"sync"`).


⸻


**6. Handling Multiple Documents**

• IDs such as `section_id`, `anchor_id` (`AN*`), and `concept_id` (`C*`) are consistent and unique across all documents provided.


⸻


**7. Error Handling**


You must choose between:

• A valid JSON **array** of concept objects conforming to the schema above, **or**
• A **single JSON error object** (not an array):


{
  "status": "error",
  "message": "Short human-readable explanation",
  "details": {
    "...": "Optional machine-readable diagnostics"
  }
}


Use the error object only for **critical** issues:
• The input is structurally invalid or missing required parts.
• Anchors are inconsistent or impossible to interpret.
• You cannot follow the schema without obvious guessing.


Do **not** mix concept objects and error fields in the same top-level JSON structure.


⸻


**8. Output Format**


Your response must have two clearly separated parts:


**Part 1 – Reasoning** (natural language):
• Summarize the main Actors, DataEntities, and Actions you identified.
• Note any notable decisions (generalizations, exclusions, ambiguous points).
• This section is for humans and will not be parsed by machines.


**Part 2 – Final JSON** (JSON only):
• Either a JSON array of concept objects, or a JSON error object.
• Must be syntactically valid (no comments, no trailing commas).


Suggested structure:


Reasoning:
<your explanation here>

Final JSON:
<your JSON array or error object here>


⸻


*** INPUT DATA ***


{{spec}}