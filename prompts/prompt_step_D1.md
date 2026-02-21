
Your task is to extract and structure **Requirements** from the provided specification, Concepts, and Messages into a `Requirements.json` list. Each requirement must be clearly phrased, scoped, and linked to anchors, concepts, and messages where relevant.


You must produce a **two-part answer**:
1. A brief **Reasoning** section (human-readable).
2. **Final Requirements JSON**: a JSON array of requirement objects or a JSON error object.


⸻


**1. Definitions**


**1.1 Anchors (AN\*)**
• Anchor IDs from the specification. Do **not** create new `AN*` IDs.
• Each requirement should reference at least one existing `AN*` ID.
• Every significant anchor (especially `capability`, `constraint`, `future-capability`) must be covered by at least one requirement.


**1.2 Concepts (A\*, ACT\*, DE\*)**
• Actors, Actions, and DataEntities from the Concepts input.
• Used to populate `relatedConcepts` on each requirement.
• Do **not** invent new concept IDs.


**1.3 Messages (MSG\*)**
• Concrete interactions from the Messages input.
• Used to populate `relatedMessages` on functional and future-functional requirements.
• Do **not** invent new message IDs.


⸻


**2. Requirements Schema**


The successful output is a JSON array where each element conforms to:


{
  "id": "string",
  "type": "string",
  "status": "string",
  "label": "string",
  "category": "string",
  "description": "string",
  "priority": "string",
  "sectionHint": "string",
  "anchors": ["AN1", "AN3"],
  "relatedConcepts": ["A1", "ACT1", "DE1"],
  "relatedMessages": ["MSG1", "MSG2"],
  "notes": "string"
}


Constraints:
• `id`, `type`, `label`, `description` are **required**.
• `anchors` should be non-empty if possible (at least one per requirement).
• `relatedConcepts` and `relatedMessages` are optional but highly recommended for core and future-functional requirements.
• No additional properties are allowed on requirement objects.


⸻


**3. ID and Type Assignment Rules**


**3.1 ID Patterns**

• Functional requirements: `FR-<number>` (e.g., `FR-1`, `FR-2`).
• Non-functional requirements: `NFR-<number>`.
• UI-specific requirements: `UI-<number>`.
• Future (desired but not required for current version): `FR-FUT-<number>`.
• Explicitly excluded / out-of-scope items: `EX-<number>`.


Start numbering at 1 for each prefix within this run. This run is self-contained; do not match any prior numbering.


**3.2 Type Mapping**


Map `type` from anchor type and section context:

• Anchor type `"capability"` or clear functional behavior in core sections → `"functional"`.
• Anchor type `"constraint"` expressing performance, offline, privacy, simplicity, or usability → `"nonfunctional"`.
• Anchor describing UI expectations or usability only → `"ui"`.
• Anchor type `"future-capability"` → `"future-functional"`.
• Anchor under an "Out of Scope / Not Required" section → `"excluded"`.


You may combine multiple anchors into a **single** requirement where they clearly address the same logical concern.


**3.3 Priority (optional)**

• Core, must-have features: `"must"`.
• Strong but not strictly mandatory non-functionals: `"should"`.
• Future capabilities and wish-list items: `"could"`.


Omit `priority` if unsure.


⸻


**4. Deriving Requirements**


**4.1 Anchor-Centric Approach**


Start from anchors in the specification:
• For each anchor or small group of closely related anchors, identify the requirement(s) expressed.
• Decide whether to create one requirement per anchor or merge multiple anchors into one richer requirement when they clearly form a single logical concern.


**4.2 Linking to Concepts**


For each requirement, populate `relatedConcepts`:
• Look at concepts whose `anchors` overlap with the requirement's anchors.
• Include Actors (`A*`) who participate, Actions (`ACT*`) that implement the behavior, and DataEntities (`DE*`) central to the requirement.
• Include the most relevant concepts only (typically 1–5 per requirement).


**4.3 Linking to Messages**


For functional and future-functional requirements, populate `relatedMessages` where possible:
• Look at messages whose `anchors` overlap and whose semantics implement the requirement.
• For nonfunctional, UI, and excluded requirements, `relatedMessages` may be empty or minimal.


⸻


**5. Section Hints and Categories**


**5.1 `sectionHint`**
• If you can infer the section or subsection where the requirement logically belongs, use the section ID or number from the spec (e.g., `"S2.1"`, `"3.2"`).
• This will be used by a downstream YAML generator to place requirements in sections.


**5.2 `category`**
• Optional high-level domain grouping to aid organization.
• Preferred values: `"task"`, `"category"`, `"view"`, `"persistence"`, `"analytics"`, `"sync"`, `"ui"`, `"privacy"`, or other domain-appropriate strings.
• Choose the **dominant** topic for each requirement.


⸻


**6. Granularity Guidelines**


Aim for **balanced granularity** — each requirement should be understandable and testable as a unit.


**Not too tiny:**
• Avoid separate requirements for trivial details that obviously belong together.
• Multiple bullet points describing facets of one capability (e.g., several filter options for a single "filter results" feature) can often be combined into one requirement with subpoints.


**Not too broad:**
• Avoid lumping unrelated concerns into a single requirement.
• Separate different functional areas, functional vs. nonfunctional vs. UI concerns, and core vs. future features.


**Heuristics:**

1. **Group closely related verbs and nouns**
- Anchors revolving around the same logical capability or DataEntity (e.g., lifecycle operations on one entity, configuration of one view) → 1–3 requirements for that cluster.

2. **Separate distinct feature areas**
- When the spec distinguishes feature families (e.g., core behavior vs. analytics vs. integrations), create separate requirements per feature area.
- Future/nice-to-have features should have their own `type = "future-functional"` requirements.

3. **Separate functional, nonfunctional, UI, and excluded concerns**
- Functional: what the system must do (operations, workflows, data manipulation).
- Nonfunctional: performance, security, privacy, reliability, offline behavior, scalability.
- UI: interaction style, layout expectations, usability constraints without core business logic.
- Excluded: explicitly out-of-scope items; give them `type = "excluded"`.

4. **Use anchors and concepts as signals**
- Multiple anchors sharing the same core concepts → likely the same requirement cluster.
- An anchor introducing new concepts or a clearly distinct concern → likely a separate requirement.

5. **Adapt to complexity**
- Simple specifications → relatively few, broad but coherent requirements.
- Complex specifications → more granular requirements aligned with subsystems, major workflows, or architectural layers.
- If the spec provides architectural hints (subsystems, services, bounded contexts), use them to partition requirements and avoid mixing cross-cutting concerns.


⸻


**7. Error Handling**


You must choose between:

• A valid JSON **array** of requirement objects, **or**
• A **single JSON error object** (not an array):


{
  "status": "error",
  "message": "Short explanation",
  "details": {
    "reason": "...",
    "missingInputs": [],
    "notes": "..."
  }
}


Use the error object only for critical structural issues (malformed input, missing core data, etc.).


Do **not** mix requirement objects and error fields in the same top-level JSON.


⸻


**8. Output Format**


Your response must have two labeled sections:


Reasoning:
<your brief explanation: how you grouped anchors into requirements, how you mapped types, etc.>

Final Requirements JSON:
<JSON array of requirement objects OR error object>

• The `Reasoning:` section is free text for humans and will not be parsed.
• The `Final Requirements JSON:` block must be **pure JSON** (no comments, no trailing commas).


⸻


*** INPUT DATA ***


{{spec}}


{{concepts}}


{{messages}}