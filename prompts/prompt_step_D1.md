
Prompt: “Step D1 – Extract and Structure Requirements”

You are assisting in **Step D1 – Build Requirements.json** of a design pipeline.


1. Overall task

You will receive:

1. **Specification YAML** (one or more documents) describing:
- Sections (`S*`), anchors (`AN*`),
- Each anchor has `text`, `type` (e.g. goal, capability, constraint, future-capability), and concept hints (`C*`).
2. **Concepts.json**:
- Concepts with:
  - `type`: `"Actor" | "Action" | "DataEntity"`,
  - `id`: `"A*" | "ACT*" | "DE*"`,
  - `label`, `description`, `anchors`, etc.
3. **Message.json**:
- Messages with:
  - `id`: `"MSG*"`,
  - `label`, `category` (`command`/`request`/`response`/`event`),
  - `producer`, `consumer`,
  - `payload` (with `refConceptId` where applicable),
  - `anchors`.


Your job:

• Extract and structure **Requirements** into a `Requirements.json` list.
• Each requirement should:
- Be clearly phrased and scoped,
- Be linked to anchors, concepts, and messages where relevant.


You must produce a **two-part answer**:

1. A brief **Reasoning** section (human-readable).
2. **Final Requirements JSON**: a JSON array of requirement objects (or a JSON error object).





2. Requirements schema you must follow

Each requirement object:


{
  "id": "string",                // e.g., "FR-1", "NFR-1", "UI-1", "FR-FUT-1", "EX-1"
  "type": "string",              // "functional" | "nonfunctional" | "ui" | "future-functional" | "excluded"
  "status": "string",            // optional: "draft" | "proposed" | "validated" | "deprecated"
  "label": "string",             // short, human-readable
  "category": "string",          // optional: "task" | "category" | "view" | "persistence" | "analytics" | "sync" | ...
  "description": "string",       // full requirement statement
  "priority": "string",          // optional: "must" | "should" | "could"
  "sectionHint": "string",       // optional: e.g., "S2.1", "2.1", "S3", etc.
  "anchors": [ "AN1", "AN3" ],   // anchor IDs from YAML
  "relatedConcepts": [ "A1", "ACT1", "DE1" ],
  "relatedMessages": [ "MSG1", "MSG2" ],
  "notes": "string"              // optional
}


Constraints:

• `id`, `type`, `label`, `description` are **required**.
• `anchors` should be non-empty if possible (at least one per requirement).
• `relatedConcepts` and `relatedMessages` are **optional** but highly recommended for core and future-functional requirements.
• No additional properties are allowed on the requirement objects.





3. ID and type assignment rules

3.1 IDs

Use these patterns:

• Functional requirements: `FR-<number>` (e.g., `FR-1`, `FR-2`).
• Non-functional requirements: `NFR-<number>`.
• UI-specific requirements: `UI-<number>`.
• Future (not required for current version, but desired): `FR-FUT-<number>`.
• Explicitly excluded / out-of-scope items: `EX-<number>`.


Numbering:

• Start at 1 for each prefix within this run (e.g., `FR-1`, `FR-2`, `NFR-1`, `UI-1`, `FR-FUT-1`, `EX-1`).
• You do not need to match any prior numbering; this run is self-contained.


3.2 type

Map from YAML anchor `type` and section:

• If anchor type is `"capability"` or clear functional behavior in core sections:
- `type`: `"functional"`.
• If anchor type is `"constraint"` and expresses:
- performance, offline, privacy, simplicity, usability: `type`: `"nonfunctional"`.
• If anchor describes UI expectations or usability only:
- e.g. “Simple intuitive UI, easy to scan”: `type`: `"ui"`.
• If anchor type is `"future-capability"` (S5 wish list):
- `type`: `"future-functional"`.
• If anchor under “Out of Scope / Not Required”:
- `type`: `"excluded"`.


You may combine multiple anchors into a **single** requirement where they clearly address the same logical requirement.


3.3 priority (optional)

If you infer priority:

• For core, must-have features: `"must"`.
• For strong but not strictly mandatory non-functionals: `"should"`.
• For future capabilities and wish-list items: `"could"`.


If unsure, you may omit `priority`.





4. Deriving requirements from anchors + concepts + messages

4.1 Anchor-centric

Start from anchors in the YAML:

• For each anchor or small group of closely related anchors:
- Identify the **requirement(s)** expressed.
- Decide whether to:
  - Create one requirement per anchor, or
  - Merge multiple anchors into a richer requirement if they clearly form one requirement (e.g., “filter & sort” could be one requirement with multiple subpoints).


Ensure:

• Each requirement has at least one `anchors` ID.
• Every **significant anchor** (especially capability/constraint/future-capability) is covered by **at least one** requirement.


4.2 Linking to Concepts

For each requirement, populate `relatedConcepts`:

• Look at:
- Concepts whose `anchors` overlap with the requirement’s anchors.
- The semantics of the requirement (e.g., if about Tasks, Categories, filters, view, etc.).
• Include:
- Actors (`A*`) who participate,
- Actions (`ACT*`) that implement the behavior,
- DataEntities (`DE*`) that are central to the requirement.


You do not need to list all concepts—just the most relevant ones (typically 1–5 per requirement).


4.3 Linking to Messages

For functional and future-functional requirements, populate `relatedMessages` where possible:

• Look at messages whose `anchors` overlap and whose semantics implement the requirement.
- Example: “User can create tasks” → `CreateTaskCommand`, `TaskCreatedResponse`.
• For nonfunctional/UI/excluded requirements, `relatedMessages` may be empty or minimal, which is acceptable.





5. Section hints and categories

`sectionHint`:

• If you can infer the section or subsection in which the requirement logically belongs:
- Use existing section IDs or numbers from YAML; e.g.:
  - Anchor in S2.1 → `"S2.1"` or `"2.1"`.
  - S3.2 performance → `"S3.2"` or `"3.2"`.
• This will be used later by a deterministic YAML generator to place requirements in sections.


`category`:

• Optional high-level domain grouping to aid organization:
- `"task"`, `"category"`, `"view"`, `"persistence"`, `"analytics"`, `"sync"`, `"ui"`, `"privacy"`, etc.
• Choose the **dominant** topic for each requirement.





6. Granularity guidelines (general, spec-agnostic)

When defining requirements from anchors, aim for a **balanced granularity**:

• **Not too tiny**:
- Avoid creating separate requirements for trivial details that obviously belong together.
- Example pattern: multiple bullet points that clearly describe facets of one capability (e.g., several filter options for a single “filter results” feature) can often be combined into one requirement with subpoints.

• **Not too broad**:
- Avoid lumping unrelated concerns into a single requirement.
- Separate:
  - Different functional areas (e.g., task management vs. user management),
  - Functional vs. nonfunctional vs. UI concerns,
  - Core vs. future/non-binding features.


Use these general heuristics:

1. **Group closely related verbs and nouns**
- If a set of anchors all revolve around the same logical capability or DataEntity (e.g., lifecycle operations on one entity, or configuration of one view), consider 1–3 requirements for that cluster rather than many tiny ones.
- Example patterns (applicable to many domains):
  - Entity lifecycle: create/read/update/delete and related state changes around a single entity may become a small cluster of requirements.
  - View or screen behavior: showing, filtering, sorting, or configuring a particular view can often be described in one or a few requirements.

2. **Separate distinct feature areas**
- When the spec clearly distinguishes feature families or modules (e.g., core behavior vs. analytics vs. integrations vs. theming), create separate requirements or groups of requirements per feature area.
- Future/nice-to-have features should generally have their own `type = "future-functional"` requirements, distinct from current core requirements.

3. **Separate functional, nonfunctional, UI, and excluded concerns**
- Functional behavior:
  - Requirements describing what the system must do (operations, workflows, data manipulation).
- Nonfunctional:
  - Requirements about performance, security, privacy, reliability, offline behavior, scalability, etc.
- UI:
  - Requirements about interaction style, layout expectations, usability constraints, but not core business logic.
- Excluded/out-of-scope:
  - Requirements that explicitly state what is *not* required in the current scope; give them `type = "excluded"`.

4. **Use anchors and concepts as signals**
- If multiple anchors share the same core concepts (same Actions/DataEntities/Actors):
  - That suggests they may belong to the same requirement cluster.
- If an anchor introduces new concepts or a clearly distinct concern:
  - That suggests a separate requirement.

5. **Adapt to complexity (future architecture hints)**
- For simple specifications:
  - You may have relatively few, broad requirements that still remain coherent.
- For complex specifications (many modules, sub-systems, or architectural layers):
  - Prefer more granular requirements aligned with:
    - Subsystems or services,
    - Major workflows,
    - Layers (e.g., API, UI, data/persistence).
- If the specification (or future guidance) provides architectural or complexity hints (e.g., identified subsystems, services, or bounded contexts), use them to:
  - Partition requirements by subsystem,
  - Avoid mixing cross-cutting concerns into a single requirement.


In summary:

• Each requirement should be understandable and testable as a unit.
• Requirements should collectively cover the major anchors without excessive duplication or fragmentation.
• Use the structure and semantics of the spec (sections, anchor types, recurring concepts) to determine natural requirement boundaries.


7. Error handling

Two possible outcomes:

1. **Success**:
- Output a valid JSON array of requirement objects.

2. **Error** (cannot safely generate Requirements.json):
- Output a single JSON object like:

  ```json
  {
    "status": "error",
    "message": "Short explanation",
    "details": {
      "reason": "...",
      "missingInputs": [...],
      "notes": "..."
    }
  }
  ```

- Use this only for critical structural issues (malformed input, missing core data, etc.).


Do **not** mix requirement objects and error fields in the same top-level JSON.


8. Output format

Your response must have two parts:


Reasoning:
<your brief explanation: how you grouped anchors into requirements, how you mapped types, etc.>

Final Requirements JSON:
<JSON array of requirement objects OR error object>

• The `Reasoning:` section is free text for humans.
• The `Final Requirements JSON:` block must be **pure JSON** (no comments, no trailing commas).


*** Specification YAML***



** Concepts.json ***



** Message.json ***









