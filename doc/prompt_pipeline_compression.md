Strategies for Context Compression in Multi-Step Conceptualization Pipelines

1. **Hierarchical Context Injection** (Recommended)

Strategy

Only provide the **immediately relevant** outputs from previous steps, not the entire history.


Implementation for Your Pipeline

**Step C3 (Extract Concepts):**
• Input: Full YAML spec only


**Step C4 (Define Aggregations):**
• Input: Full YAML spec + Concepts.json
• Omit: Detailed reasoning from C3


**Step C5 (Define Messages):**
• Input: **Concepts.json + Aggregations.json only**
• Omit: Full YAML spec (except for critical anchors reference)
• Rationale: Messages are derived from Concepts/Aggregations, not directly from raw spec


**Step C6+ (subsequent steps):**
• Input: Only the **immediate predecessor outputs** + a **summary document**


Example for Step C5 (Compressed):

# Instead of full spec, provide:
anchor_summary:
  AN4: "Create tasks with title, description, due date"
  AN5: "Edit, mark complete/incomplete, delete tasks"
  AN12: "Automatic save without user action"
  # ... only anchors referenced in Concepts/Aggregations

concepts: [full Concepts.json]
aggregations: [full Aggregations.json]


⸻


2. **Anchor-Based Compression**

Strategy

Since anchors are the "evidence trail," create a **compact anchor index** instead of repeating full YAML sections.


Implementation

{
  "anchor_index": {
    "AN4": {
      "text": "Let the user create simple to-do items with at least a title...",
      "type": "capability",
      "section": "2.1 Task Creation and Management"
    },
    "AN5": {
      "text": "Let the user edit tasks, mark them complete/incomplete...",
      "type": "capability",
      "section": "2.1 Task Creation and Management"
    }
  }
}


**Benefits:**
• Reduces YAML verbosity by 70-80%
• Preserves traceability
• Easy to reference in justifications


⸻


3. **Concept Summary Tables**

Strategy

Replace verbose JSON with compact tabular representations for reference.


Implementation

## Concepts Quick Reference

### Actors
| ID  | Label                | Key Role                          |
|-----|----------------------|-----------------------------------|
| A1  | EndUser              | Initiates all user actions        |
| A2  | BrowserApp           | Orchestrates app logic            |
| A3  | LocalStorageEngine   | Manages persistence               |

### Actions (Core)
| ID    | Label              | Description                        | Anchors    |
|-------|--------------------|------------------------------------|------------|
| ACT1  | CreateTask         | Create new task                    | AN4        |
| ACT2  | EditTask           | Modify task properties             | AN5        |
| ACT4  | MarkTaskComplete   | Set task to complete               | AN5        |

### DataEntities (Core)
| ID  | Label            | Description                          | Anchors    |
|-----|------------------|--------------------------------------|------------|
| DE1 | Task             | Individual to-do item                | AN4, AN5   |
| DE2 | Category         | User-defined task grouping           | AN6        |


**Benefits:**
• 50-60% token reduction vs. full JSON
• Still machine-parseable (with simple parser)
• Human-readable for reasoning


⸻


4. **Differential Updates**

Strategy

For iterative refinement, only pass **changes** rather than full documents.


Implementation

{
  "base_version": "concepts_v1.json",
  "changes": {
    "added": [
      {"id": "ACT28", "label": "NewAction", "...": "..."}
    ],
    "modified": [
      {"id": "ACT5", "changes": {"description": "Updated description"}}
    ],
    "removed": ["ACT99"]
  }
}


**Use Case:**
• Step C5 refinement after review
• Iterative concept evolution


⸻


5. **Semantic Compression via Embeddings** (Advanced)

Strategy

For very large specs, use embeddings to retrieve only **relevant sections** per step.


Implementation
1. Pre-process: Embed all YAML anchors
2. At each step: Embed the task description
3. Retrieve top-K most relevant anchors
4. Provide only those anchors as context


**Example:**

# Step C5: Define Messages
query = "Define message interactions between actors for task lifecycle"
relevant_anchors = retrieve_top_k(query, k=20)  # Instead of all 30 anchors


**Benefits:**
• Scales to very large specifications (100+ anchors)
• Maintains relevance
• Reduces noise


⸻


6. **Layered Context Architecture**

Strategy

Organize context into **layers** with decreasing detail, allowing the LLM to "drill down" only when needed.


Implementation

# Layer 1: Executive Summary (always included)
summary:
  purpose: "Browser-based local to-do list"
  core_entities: ["Task", "Category", "ViewPreferences"]
  core_actors: ["EndUser", "BrowserApp", "LocalStorageEngine"]
  architecture: "Local-first, offline, single-user"

# Layer 2: Concept Inventory (always included)
concepts:
  actors: [A1, A2, A3, A4, A5]
  actions: [ACT1-ACT27]
  data_entities: [DE1-DE12]

# Layer 3: Detailed Definitions (reference only, retrieve on-demand)
concept_details:
  A1: {full definition}
  ACT1: {full definition}
  # ...

# Layer 4: Source Evidence (reference only)
anchors:
  AN4: {full text}
  # ...


**Prompt Instruction:**

You have access to:
- Layer 1-2: Full context (provided below)
- Layer 3-4: Reference IDs only; assume you can look up details if needed

Focus on Layer 1-2 for your reasoning. Reference Layer 3-4 IDs in your output.


⸻


7. **Schema-Only References**

Strategy

For well-defined structures (like Concepts.json), provide **schema + count** instead of full content.


Implementation

{
  "concepts_summary": {
    "schema": "Concept.json (type, id, label, description, categories, anchors, sourceConceptIds)",
    "counts": {
      "actors": 5,
      "actions": 27,
      "data_entities": 12
    },
    "categories": {
      "core": 14,
      "future": 23,
      "ui": 8,
      "persistence": 6
    }
  },
  "full_concepts": "[Available on request - assume you have access to query by ID]"
}


**Prompt Instruction:**

Concepts.json contains 44 concepts (5 actors, 27 actions, 12 data entities).
When you need details about a specific concept, reference it by ID (e.g., "ACT1").
Assume you can look up full definitions as needed.


⸻


8. **Prompt-Level Compression Techniques**

Strategy

Optimize the prompt itself to reduce redundancy.


Techniques

**A. Remove Redundant Examples:**

- Examples:
-   - Actor: EndUser, BrowserApp, LocalStorageEngine
-   - Action: CreateTask, EditTask, DeleteTask
-   - DataEntity: Task, Category, ViewPreferences
+ (Examples omitted - see Concepts.json for full list)


**B. Use Shorthand Notation:**

- "Each concept has type, id, label, description, optional categories, anchors, and sourceConceptIds"
+ "Concept schema: {type, id, label, description, [categories], [anchors], [sourceConceptIds]}"


**C. Reference External Schema:**

- [Full JSON schema definition: 50 lines]
+ "Follow Message.json schema (v1.2) - see schema registry"


⸻


9. **Recommended Hybrid Approach for Your Pipeline**

Step C3 (Extract Concepts)

**Input:**
• Full YAML spec (necessary for initial extraction)


**Output:**
• Concepts.json (full)
• Anchor index (compact)


⸻


Step C4 (Define Aggregations)

**Input:**
• **Anchor index** (not full YAML)
• **Concepts.json** (full)


**Compression:**

# Compact anchor index
anchors:
  AN4: "Create tasks with title, description, due date [capability]"
  AN5: "Edit, mark complete/incomplete, delete tasks [capability]"
  # ... (50-70% smaller than full YAML)

# Full concepts
concepts: [full Concepts.json - 44 items]


**Token Savings:** ~40-50%


⸻


Step C5 (Define Messages)

**Input:**
• **Concept summary table** (not full JSON)
• **Aggregations.json** (full)
• **Anchor index** (compact)


**Compression:**

## Actors (5 total)
A1: EndUser | A2: BrowserApp | A3: LocalStorageEngine | A4: SyncService (future) | A5: SuggestionEngine (future)

## Core Actions (14 total)
ACT1: CreateTask | ACT2: EditTask | ACT3: DeleteTask | ACT4: MarkTaskComplete | ACT5: MarkTaskIncomplete
ACT6: CreateCategory | ACT7: RenameCategory | ACT8: DeleteCategory
ACT9: DisplayTaskList | ACT10: FilterByCompletionStatus | ACT11: FilterByCategory | ACT12: SortTasks
ACT13: SaveViewPreferences | ACT14: AutoSaveData

## Future Actions (13 total)
ACT15-ACT27: [Priority, Reminders, Recurrence, Tags, Views, Export/Import, Search, Analytics, Sync, Suggestions, Theming]

## DataEntities (12 total)
Core: DE1 (Task), DE2 (Category), DE3 (ViewPreferences)
Future: DE4-DE12 [Priority, Reminder, Recurrence, Tag, SavedView, ExportFile, Analytics, SyncConfig, Theme]

## Aggregations (15 total)
AG1: TaskLifecycle [ACT1,2,4,5,3]
AG2: CategoryLifecycle [ACT6,7,8]
AG3: MainListViewFlow [A3,ACT13,10,11,12,9]
AG4: TaskFilteringSortingFlow [ACT10,11,12,13]
AG5: PersistenceFlow [A3,ACT14]
AG6-AG14: Future features
AG15: FutureEnhancementsPackage [AG6-AG14]


**Token Savings:** ~60-70%


⸻


Step C6+ (Future Steps)

**Input:**
• **Messages summary table** (not full JSON)
• **MessageAggregations summary** (not full JSON)
• **Concept/Aggregation references** (IDs only)


⸻


10. **Practical Implementation Checklist**

Immediate Actions (High Impact, Low Effort)
• Create anchor index (replace full YAML in C4+)
• Use concept summary tables (replace full JSON in C5+)
• Remove redundant examples from prompts
• Reference schemas externally instead of inline


Medium-Term Actions (High Impact, Medium Effort)
• Implement layered context architecture
• Build differential update mechanism for iterations
• Create schema-only reference system


Advanced Actions (Medium Impact, High Effort)
• Implement semantic retrieval with embeddings
• Build dynamic context assembly based on step requirements


⸻


11. **Expected Token Reductions**

Step	Original	With Compression	Savings
C3	15K	15K (baseline)	0%
C4	25K	15K	40%
C5	40K	18K	55%
C6+	50K+	20K	60%+

⸻


12. **Quality Safeguards**

To ensure compression doesn't degrade output:

1. **Validation Step:** After each compressed step, validate that all referenced IDs exist
2. **Spot Checks:** Randomly verify 10% of outputs against full-context baseline
3. **Traceability:** Maintain anchor references even in compressed format
4. **Incremental Compression:** Start with 20% compression, measure quality, then increase


⸻


Recommendation

**Start with Hybrid Approach (Steps 1, 2, 3, 6):**
1. Use **anchor index** instead of full YAML (Step 2)
2. Use **concept summary tables** instead of full JSON (Step 3)
3. Implement **layered context** with summary + details (Step 6)
4. Apply **hierarchical context injection** (Step 1)


**Expected Result:**
• 50-60% token reduction in C4-C5
• Maintained output quality
• Improved focus on relevant information
• Faster processing times


