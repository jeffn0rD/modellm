
Your task is to transform a structured YAML requirements model into a human-readable, formally styled **markdown specification** suitable for stakeholder review and approval.


The output must be coherent, well-structured, and present the requirements in a clear and accessible style while preserving the intent and content of the source material.


⸻


**1. Definitions**


**1.1 Sections**
• The YAML organizes content into a recursive hierarchy of sections, each with a `section_number`, `title`, `order`, and optionally nested `sections`.
• Sections define the document structure and must be traversed in `order` sequence.


**1.2 Text Blocks (Anchors)**
• Each section contains `text_blocks`: fine-grained anchored units of content.
• Each text block has a `type`, a `text` field (the source of truth for meaning), and optionally `concepts`.
• Text blocks are the atomic units you will rewrite into polished prose.


**1.3 Text Block Types**
• `"goal"` – overarching objectives or intentions.
• `"capability"` – what the system **shall** or **should** do.
• `"constraint"` – what the system **must** or **must not** do; non-functional requirements.
• `"future-capability"` – future, optional, or nice-to-have capabilities not part of the initial baseline.
• `"other"` – contextual or background information; present neutrally.


**1.4 Concepts**
• Candidate domain terms attached to text blocks.
• Use them as **terminology hints** to keep vocabulary consistent (e.g., "Task", "End User", "Notification") when rewriting text.
• You do not need to list all concepts explicitly, but you may briefly mention or define particularly central ones where it improves clarity.


⸻


**2. Output Structure**


**2.1 Title Block**


Open the document with:


# <specification.title>

_Version <specification.version>_


Follow with a concise introductory paragraph derived from `specification.description`.


**2.2 Section Headings**


Use `section_number` and `title` to form numbered headings:
• Top-level sections → `##`
• First-level subsections → `###`
• Second-level subsections → `####`
• And so on for deeper nesting.


Examples:
• `## 1. Overall Purpose and Context`
• `### 1.1 Primary Users`
• `#### 1.1.1 Some Subtopic`


If `section_number` is missing or inconsistent, derive a reasonable hierarchical numbering from the nesting and `order` fields.


You may write a brief introductory sentence for a section when its theme is clear from its `label` or `text_blocks`.


**2.3 Text Block Rendering**


For each text block, rewrite the `text` into polished, formal requirements prose guided by `type`:

• `"goal"` → describe as overarching objectives or intentions.
• `"capability"` → describe what the system **shall** or **should** do.
• `"constraint"` → describe what the system **must** or **must not** do, or state non-functional requirements.
• `"future-capability"` → describe explicitly as a **future**, **optional**, or **nice-to-have** capability, clearly distinguished from baseline requirements.
• `"other"` → present neutrally as context or background.


The `text` field is the **source of truth for meaning**:
• Preserve the meaning, scope, and intent of the original.
• Do **not** introduce new strong requirements not implied by the original.
• You may:
- Clarify vague language slightly.
- Add brief neutral connective phrases for fluency.
- Break a single informal sentence into multiple clearer sentences, or combine closely related fragments into a polished paragraph.


Where helpful, group related text blocks under small sub-subheadings or bullet lists to improve readability. Do **not** invent new major sections that alter the document structure.


**2.4 Anchor IDs**


Use `anchor_id` values **internally only** if they help structure the markdown (e.g., optional inline references). Generally, do **not** surface anchor IDs, concept IDs, or other internal identifiers to stakeholders. The default is to **omit explicit IDs** from the output.


⸻


**3. Style Guidelines**

• Aim for clarity over brevity, but avoid unnecessary verbosity.
• Use numbered headings mirroring the `section_number` hierarchy.
• Use bullet lists where they improve readability, especially when a section includes multiple related requirements or capabilities.
• Write so the document is self-contained and understandable by non-technical stakeholders.
• Clearly distinguish:
- Current required behavior (baseline capabilities and constraints).
- High-level goals and rationale.
- Future or nice-to-have capabilities.
• Do **not** introduce implementation details or architectural decisions (e.g., specific technologies, frameworks, or architectures) unless they are explicitly or strongly implied by the original text.


⸻


**4. Process**

1. Read `specification.title`, `version`, and `description` and produce a concise, informative title block and introduction.
2. Traverse `specification.sections` recursively in `order` sequence.
3. For each section, generate the heading and optionally a brief introductory sentence.
4. For each section's `text_blocks` in their given order, rewrite the `text` into polished formal prose guided by `type` and informed by `concepts`.
5. Respect the logical organization of the YAML. Do **not** rearrange sections or blocks in ways that change the apparent priority or structure of the original specification.
6. Produce a final markdown document suitable for sharing with stakeholders for review and approval.


⸻


*** INPUT DATA ***


{{spec}}