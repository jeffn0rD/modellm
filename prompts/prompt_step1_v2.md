
Your task is to transform an informal, executive-style specification into a structured YAML document organized around **sections**, **anchored text blocks**, and **candidate concepts**. This YAML is the first factoring step toward a detailed conceptual model. You are **not** building that model here; you are preparing the raw, well-structured input for it.


⸻


**1. Overall Transformation Goal**


Produce a valid YAML document that:
1. Organizes content into a **hierarchical section structure** (nested sections with explicit order).
2. Identifies **anchored text blocks**: small, logically coherent pieces of text embodying requirements, capabilities, constraints, or important ideas.
3. For each anchored text block, lists **candidate Concept entries** (potential data entities, domain concepts, actions, or other model-relevant notions).
4. Preserves the **exact wording** of the original text inside each text block's `text` field (no paraphrasing there).
5. Adds a short **description** for each concept (which *may* be lightly paraphrased) to clarify its intent.


Anchored text blocks are the **atoms** of the process: they will be used later to derive Actors, Actions, DataEntities, Messages, Requirements, and other domain objects.


⸻


**2. Top-Level YAML Structure**


The output document must conform to this structure:


specification:
  id: SPEC1
  title: "<short descriptive title inferred from the text>"
  version: "0.1"
  description: >
    Short summary of what the specification is about.

  metadata:
    source_style: "informal executive-style requirements"
    intended_use: "stepwise refinement toward formal/domain model"
    anchor_id_pattern: "AN<number>"
    section_numbering: "hierarchical (1, 1.1, 1.2, ...)"
    concept_assignment_rule: >
      An Anchor can be related to more than one Concept, but a Concept should
      be related to only one Anchor.

  sections:
    - section_id: S1
      section_number: "1"
      order: 1
      title: "..."
      label: "..."
      text_blocks:
        - anchor_id: AN1
          label: "..."
          type: "goal"
          semantic_cues:
            - cue_one
            - cue_two
          text: >
            <EXACT excerpt from the input specification>
          concepts:
            - concept_id: C1
              name: "..."
              description: "..."
      sections:
        - section_id: S2
          section_number: "1.1"
          order: 1
          title: "..."
          label: "..."
          text_blocks: []
          sections: []


**Field conventions:**

• `specification.id`: always `"SPEC1"` (format: `/^SPEC\d+$/`).
• `version`: use `"0.1"` unless a version is clearly stated in the input.
• `section_id`: globally unique, format `S<number>` (e.g., `S1`, `S2`, `S3`). Do **not** encode hierarchy into the ID.
• `section_number`: human-readable hierarchical number (e.g., `"1"`, `"1.1"`, `"2.3.1"`). Informational only; downstream tooling may ignore or re-derive it.
• `order`: integer representing position among siblings. Must reflect the logical order of the input document.
• `label`: globally unique across the entire document, matching `/^[A-Z_][a-zA-Z0-9_.]*$/` (e.g., `OVERALL_CONTEXT`, `CORE_CAPABILITIES`, `NON_FUNCTIONAL_CONSTRAINTS`).


⸻


**3. Section Hierarchy and Granularity**


**Hierarchy rules:**
• Use `sections` recursively to model an N-level hierarchy.
• Top-level sections appear in `specification.sections`; each may contain nested `sections:` for subsections.
• Deduce `section_number` from the hierarchy and `order` within each parent.


**Granularity:**
• Use **sections** for thematic grouping: context vs. core features vs. constraints vs. future ideas vs. out-of-scope, etc.
• Use **text blocks** for atomic ideas to be later refined into actors, actions, data, messages, and requirements.
• A section may contain many text blocks, only nested subsections, or both.


**Typical top-level section themes** (adapt as natural for the input):
• Overall Purpose / Context
• Core Capabilities / Functional Requirements
• Non-Functional Expectations / Constraints
• Out of Scope / Not Required
• Future Wish List / Nice-to-Have Features


⸻


**4. Text Blocks (Anchors)**


Each section contains a `text_blocks` list of fine-grained anchored text units.


**A text block represents a single coherent idea:**
• A single requirement, capability, constraint, clearly separable wish-list item, or important context statement.
• Typically corresponds to one bullet item, or a short paragraph or couple of closely related sentences that together define one requirement or idea.
• Should be **narrow**: avoid large blocks containing many distinct requirements. Do not split so aggressively that each minor clause becomes its own block unless clearly separable in meaning.


**Text block structure:**


- anchor_id: AN<number>
  label: "SOME_LABEL"
  type: "goal" | "capability" | "constraint" | "future-capability" | "other"
  semantic_cues:
    - short_cue_one
    - short_cue_two
  text: >
    <EXACT original text excerpt>
  concepts:
    - concept_id: C<number>
      name: "Concept_Name"
      description: "Short explanation."


**Field rules:**
• `anchor_id`: globally unique across the entire document, format `AN<number>` (e.g., `AN1`, `AN2`).
• `label`: globally unique across the entire document, matching `/^[A-Z_][a-zA-Z0-9_.]*$/`.
• `semantic_cues`: 3–6 short tokens in snake_case or kebab-case hinting at the nature of the block (e.g., `task_creation`, `offline_support`, `data_privacy`, `scheduling`, `notifications`).


⸻


**5. Text Block Types**

• `"goal"` – high-level intent, purpose, or objective. Cues: "we need", "the app is for", "so that we can".
• `"capability"` – specific functionality or behavior the system should provide in the current version. Covers creation, editing, viewing, searching, filtering, workflows, etc.
• `"constraint"` – non-functional expectation, limitation, or explicit exclusion. Covers performance, security/privacy, legal, technical limitations, "we are not looking for…".
• `"future-capability"` – wish-list / nice-to-have / explicitly later-phase capability. Cues: "someday", "in the future we might", "v2", "optional later".
• `"other"` – anything important that doesn't fit the above; vague ideas not yet clearly classifiable.


⸻


**6. Text Preservation Rules**


For each `text_blocks[*].text`:


**You may:**
• Remove leading bullet characters (e.g., `-`, `*`, numbers) at the start of a line only, while preserving the remaining text.
• Re-wrap lines to fit YAML formatting.
• Normalize whitespace minimally.


**You must not:**
• Paraphrase, summarize, or reword any part of the text.
• Omit words, add new words, or merge distinct bullets expressing clearly different ideas into a single text block.


Where bullets or paragraphs combine tightly into a single coherent requirement, you may combine them **only if** that remains faithful to the structure and intent. Default to **narrow** text blocks.


⸻


**7. Concepts (Candidate Domain Concepts)**


Each text block contains a `concepts` list of candidate conceptual entities mentioned or implied by that piece of text.


**A concept can be:**
• A noun or noun phrase, or an action (verb acting upon data or the system), aligned with the client's language.
• Something that may later become a DataEntity, Actor, Action, Event, Message payload element, or other domain-relevant object.


**At this stage:**
• Concepts are **labels and brief descriptions only**. Do not design schemas, attributes, or relationships.


**Constraints:**
• A text block may have zero, one, or many concepts.
• A concept must belong to **exactly one** text block. Do not share a `concept_id` across blocks.
• If a similar concept appears in multiple blocks, define a separate `concept_id` each time with similar names if natural (e.g., `Task`, `Task_instance`).


**Concept field rules:**
• `concept_id`: globally unique, format `C<number>`, monotonically increasing across the entire document (e.g., `C1`, `C2`, `C3`).
• `name`: short noun phrase in the client's terms where possible, matching `/^[A-Z_][a-zA-Z0-9_.]*$/` (e.g., `Todo_item`, `Task_priority_level`, `Offline_operation`).
• `description`: short plain-language phrase or sentence. You **may paraphrase and clarify** here. Do not add new requirements; just capture the intuitive meaning.


⸻


**8. Classification Hints for Later Stages**


When assigning `type` and `semantic_cues`, keep later modeling stages in mind:

• Text describing **who** does something → `goal` or `capability` with Actor-like concepts (e.g., `End_user`, `Admin_user`).
• Text describing **what** is being manipulated → `capability` with DataEntity-like concepts.
• Text describing **how** components interact → `capability` or `constraint` with Action-, Message-, or Event-like concepts.
• Text describing **rules and constraints** → `constraint`.
• Text describing **future enhancements** → `future-capability`.


Useful `semantic_cues` examples: `user_authentication`, `role_management`, `data_retention`, `api_integration`, `notification_delivery`, `audit_trail`, `error_handling`, `scheduling`, `data_import_export`, `analytics_reporting`.


⸻


**9. ID and Label Uniqueness Rules**


Across the entire YAML document:
• `section_id` values are **globally unique**: `S1`, `S2`, `S3`, ...
• `anchor_id` values are **globally unique**: `AN1`, `AN2`, `AN3`, ...
• `concept_id` values are **globally unique**: `C1`, `C2`, `C3`, ...
• All `label` fields (sections and text blocks) are **globally unique** and must match `/^[A-Z_][a-zA-Z0-9_.]*$/`.


⸻


**10. Output Style and Format**

• Output **only** valid YAML — no commentary, no explanation, no code fences.
• 2-space indentation throughout.
• Use `>` for multiline strings under `text` and `description` where helpful.
• Use double quotes when necessary for special characters.


⸻


**11. Process to Follow**

1. **Read the entire input** to understand its overall structure and themes.
2. **Identify natural section groupings**: purpose/context, core features, constraints, future ideas, out-of-scope, etc. Build a section hierarchy matching the document's logical flow.
3. **Extract fine-grained text blocks** within each section: one block per bullet or per tightly related sentence/short paragraph. Keep each block narrow and focused.
4. **For each text block**: assign `anchor_id`, create a unique `label`, decide `type`, add 3–6 `semantic_cues`, copy the **exact original wording** into `text`.
5. **Identify candidate concepts**: extract key noun phrases and domain terms. For each, create a `concept_id`, a `name`, and a short `description`.
6. Repeat until the entire specification is covered.
7. **Verify**: all IDs (`S*`, `AN*`, `C*`) are unique and monotonically increasing; all `label` values are globally unique and match the required pattern; the YAML is syntactically valid.


⸻


*** INPUT DATA ***


{{nl_spec}}