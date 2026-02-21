
Your task is to reconcile an edited formal markdown specification against a previous YAML requirements model, producing an **updated YAML specification** and a **separate DIFF YAML** summarizing what changed.


The edited markdown is the **authoritative** description of current requirements. The previous YAML provides stable IDs, original client wording, and prior structure.


⸻


**1. Definitions**


**1.1 Pipeline Context**


This is step 3 of a three-step pipeline:
1. Informal client text → initial YAML (sections, text blocks, concepts).
2. YAML → formal markdown specification.
3. Edited formal markdown + previous YAML → **updated YAML + DIFF** ← you are here.


**1.2 Anchors (AN\*)**
• Text blocks identified by globally unique `anchor_id` values (e.g., `AN1`, `AN2`).
• Each anchor represents a single coherent requirement atom.
• Stable IDs must be preserved where meaning remains the same.


**1.3 Concepts (C\*)**
• Candidate domain terms attached to text blocks, identified by globally unique `concept_id` values.
• Stable IDs must be preserved where meaning remains the same.


**1.4 Sections (S\*)**
• Hierarchical groupings identified by globally unique `section_id` values.
• Stable IDs must be preserved where the section still represents the same conceptual area.


**1.5 Text Block Status Values**
• `"unchanged"` – present and essentially the same in meaning and scope.
• `"modified"` – present but substantively edited, clarified, or changed in scope or conditions.
• `"new"` – newly introduced in the edited markdown with no prior analogue.
• `"deleted"` – present in the old YAML but no longer appearing in the edited markdown.


⸻


**2. Reconciliation Rules**


**2.1 Matching Existing Text Blocks**


For each text block in the old YAML, attempt to match it to content in the edited markdown:
• Match primarily on **meaning** (intent, main subject, scope).
• Secondarily consider similar phrasing, terminology, section/heading alignment, and previous `label`, `type`, and `semantic_cues`.


**2.2 When a Clear Match Exists**


Reuse the same `anchor_id`, `label`, and `section_id` (even if the section's position or parent has changed). Update or set:

• `text_original`: use the `text` field from the old YAML verbatim (treat it as the original client wording).
• `text_formal`: extract the current authoritative wording from the edited markdown, paraphrased for consistency with the markdown's style without changing meaning.
• `status`:
- `"unchanged"` if meaning and scope are essentially the same, with at most minor rephrasing.
- `"modified"` if scope, conditions, or important details have changed, or the formal text is a significant refinement.
• `change_notes`:
- For `"unchanged"`: may be an empty string or omitted.
- For `"modified"`: brief explanation of what changed (e.g., "Clarified who can create tasks and what fields are required.").


**2.3 When a Text Block No Longer Appears**


Keep the `anchor_id` and `label` in the updated YAML but set:
• `status: "deleted"`.
• `text_original`: retain from the old YAML.
• `text_formal`: leave as `""` or equal to the old `text` for traceability.
• `change_notes`: explain the removal (e.g., "Requirement removed in revised markdown; no longer in scope.").


**2.4 Creating New Text Blocks**


If the edited markdown contains a requirement with no match in the old YAML:
• Assign a new globally unique `anchor_id` continuing the numbering sequence (e.g., if the old highest was `AN17`, next is `AN18`).
• Create a new globally unique `label` matching `/^[A-Z_][a-zA-Z0-9_.]*$/`.
• Place it under the appropriate section corresponding to the markdown heading.
• Set `type` and `semantic_cues` using the same classification rules as step 1 of the pipeline.
• `text_original`: use the closest original client phrase if safely identifiable from the old YAML; otherwise leave as `""`.
• `text_formal`: use the current authoritative wording from the edited markdown.
• `status: "new"`.
• `change_notes`: brief explanation (e.g., "New requirement added in the edited specification regarding task archiving.").


⸻


**3. Concept Reconciliation**


**3.1 Existing Concepts**
• Keep the same `concept_id` and `name` even if the markdown uses slightly different phrasing.
• You may refine `description` slightly to reflect improved understanding, without contradicting the original meaning.


**3.2 New Concepts**
If the edited markdown implies a concept not captured by any existing concept:
• Assign a new globally unique `concept_id` (continuing the sequence).
• Choose a `name` matching `/^[A-Z_][a-zA-Z0-9_.]*$/`.
• Provide a brief `description` aligned with the meaning in the markdown.


**3.3 Concepts on Deleted Text Blocks**
• Keep them associated with their text block in the updated YAML for traceability.
• Note in the DIFF YAML that those concepts are no longer used in any active requirement.


⸻


**4. Section and Hierarchy Reconciliation**


Use the edited markdown's heading structure as the authoritative section hierarchy and order:
• Reuse existing `section_id` values where the section still represents the same conceptual area.
• Create new `section_id` values (next `S<number>`) for sections with no prior analogue.
• Update `section_number` strings to match the new heading numbering (e.g., `"1"`, `"1.1"`, `"2.1.1"`).
• Update `order` to reflect each section's position among its siblings.
• Update `title` to align with the markdown heading text.
• Keep `label` stable unless the section's meaning changed substantially; if updated, ensure global uniqueness.
• Place deleted text blocks within their original sections while preserving their IDs and status.


⸻


**5. Updated YAML Schema**


The updated YAML must use the same top-level structure as the previous YAML, with these changes:

• Update `title`, `description`, and `version` if appropriate (e.g., bump minor version to `"0.2"`).
• Keep `metadata` present; update it to reflect this step if appropriate.
• Align `sections` hierarchy, `section_number`, and `order` with the edited markdown.


Each text block must include at minimum:


- anchor_id: AN<number>
  label: "SOME_LABEL"
  type: "goal" | "capability" | "constraint" | "future-capability" | "other"
  semantic_cues:
    - cue_one
  text_original: >
    <original client wording from old YAML>
  text_formal: >
    <current authoritative wording from edited markdown>
  status: "unchanged" | "modified" | "new" | "deleted"
  change_notes: "..."
  concepts:
    - concept_id: C<number>
      name: "..."
      description: "..."


For backward compatibility with earlier pipeline stages, you may also include a `text` field. If you do, set it equal to `text_original` (preferred) or `text_formal` if no original text is available.


⸻


**6. DIFF YAML Schema**


The DIFF YAML is a concise, separate summary of changes at the anchor and concept level:


diff:
  from_version: "0.1"
  to_version: "0.2"
  anchors:
    - anchor_id: AN3
      change_type: "modified"
      summary: "Clarified task creation fields; added requirement for due date."
    - anchor_id: AN17
      change_type: "new"
      summary: "Introduced requirement for configurable task priorities."
    - anchor_id: AN9
      change_type: "deleted"
      summary: "Removed requirement for legacy export format; no longer in scope."
  concepts:
    - concept_id: C12
      change_type: "unchanged"
    - concept_id: C58
      change_type: "new"
      summary: "New concept for task recurrence pattern."


Include at minimum:
• Short human-readable summaries of all non-trivial changes.
• Entries for new, modified, and deleted anchors.
• Entries for new concepts and concepts no longer used in any active requirement.


You may extend the diff structure for clarity, but keep it concise.


⸻


**7. Classification Rules**

• Mark as `"modified"` if meaning or scope is plausibly changed — not just punctuation or trivial rephrasing.
• Mark as `"unchanged"` if the underlying meaning is preserved even if wording is improved.
• `change_notes` should describe what changed from a requirements perspective (scope, conditions, clarifications), not stylistic differences.


⸻


**8. Output Format**


Produce two YAML documents in this order:

1. The **updated YAML specification**.
2. A separator comment line:
```yaml
# --- DIFF BELOW ---
```
3. The **DIFF YAML**.


Both documents must use 2-space indentation and be syntactically valid YAML. Do not wrap output in code fences.


⸻


*** INPUT DATA ***


{{spec_formal}}


{{spec}}