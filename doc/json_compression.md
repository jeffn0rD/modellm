1. Context Summary

1.1 Overall Goal

The overarching goal is to build a **minimal, maintainable JSON→JSON compression tool** in Python that:

• Takes structured JSON (from YAML or other sources).
• Applies **lossless structural compression** (no summarization/truncation yet).
• Outputs:
- A **`schema`** describing the mapping and structure.
- A **`data`** section containing the compact representation.


Subsequently, this was integrated with an existing **YAML configuration** defining **data entities** and their **compression strategies**.


⸻


1.2 Core Design Decisions
1. **Format & Structure**
- Use **JSON** as both input and compressed format.
- The compressed payload has shape:
  ```json
  {
    "schema": { ... },
    "data":   { ... } | [ ... ]
  }
  ```
- `schema` includes:
  - `version` (e.g., `1`).
  - `original_root_type` (`"object"` or `"array"`).
  - `config` (relevant parts of compression config).
  - `fields`: `{ code: logical_path }` mapping.
  - Optional `structure.tabular_arrays`.

2. **Logical Paths**
- Fields identified by **logical paths** (e.g., `user.name`, `anchors[].anchor_id`).
- Arrays use `[]` to indicate per-element paths (e.g., `anchors[].text`).
- Flattening is **conceptual**; the compressed `data` can still be nested, but `schema.fields` always uses full logical paths.

3. **Compression Configuration Model (Python)**
- `CompressionConfig` with:
  - `FilterConfig` (include/exclude paths).
  - `FlattenConfig` (enabled, path_separator).
  - `KeyMappingConfig` (strategy: `identity` or `auto_abbrev`).
  - `TabularConfig` (enabled, `array_paths`).

4. **Core Compression/Decompression Functions**
- Public:
  - `compress_json(data, config) -> {"schema": ..., "data": ...}`
  - `decompress_json(compressed) -> original_like_data`
- Internal helpers (documented scaffolding only was provided):
  - `_collect_logical_fields`
  - `_build_field_code_map`
  - `_encode_data_with_field_codes`
  - `_encode_tabular_arrays`
  - `_build_schema_object`
  - `_decode_data_from_field_codes`
  - `_decode_tabular_arrays`
  - `_reconstruct_nested_structure_from_paths`

5. **Tabular Arrays**
- Certain arrays of objects can be encoded as **2D tables**:
  - Configured via `TabularConfig.array_paths` (e.g., `anchors`, `orders`).
  - `schema.structure.tabular_arrays` records:
    ```json
    "tabular_arrays": {
      "anchors": {
        "fields": ["b", "c"],
        "kind": "object_array"
      }
    }
    ```
  - `data.anchors` becomes `[[v1, v2, ...], [v1', v2', ...]]`.

6. **Key Mapping Strategy**
- `strategy: identity` for debugging/testing (no real compression).
- `strategy: auto_abbrev` for production:
  - Codes like `a`, `b`, ..., `z`, `aa`, `ab`, etc.

7. **Filtering**
- `include_paths`: exact logical paths to keep.
- `exclude_paths`: paths to drop after inclusion.
- Filtering is **lossy** (dropped fields are unrecoverable).


⸻


1.3 YAML Configuration Integration (Final Recommendations)

After reviewing your actual YAML config:


data_entities:
  nl_spec:
    ...
    compression_strategies:
      none: ...
  spec:
    type: yaml
    filename: spec_1.yaml
    yaml_schema: schemas/spec_yaml_schema.json
    compression_strategies:
      none: ...


Final recommendations:

1. **Do NOT change existing structure**; just **extend** it.
2. For each `data_entities.<entity>.compression_strategies.<strategy>`:
- Add:
  - `compression_strategy_type: json_compact`
  - `output_entity: <other data entity label>`
  - `compression:` block mirroring `CompressionConfig`.
3. Define new `data_entities` entries for compressed outputs (e.g., `spec_compact`, `spec_anchors_light`, …) with `type: json`, `filename: ...`, etc.


Example (final pattern):


data_entities:
  spec:
    type: yaml
    filename: spec_1.yaml
    yaml_schema: schemas/spec_yaml_schema.json
    compression_strategies:
      minimal_json:
        description: >
          Lossless JSON compaction of the YAML spec with short field codes.
        compression_strategy_type: json_compact
        output_entity: spec_compact
        compression:
          filter:
            include_paths: []
            exclude_paths: []
          flatten:
            enabled: false
            path_separator: "."
          key_mapping:
            strategy: auto_abbrev
            min_length: 1
            max_length: 4
          tabular:
            enabled: false
            array_paths: []

  spec_compact:
    type: json
    filename: spec_1_compact.json
    description: "Compacted JSON version of the spec with schema + data."


This refined recommendation supersedes earlier generalized examples and should be considered the **authoritative pattern**.


⸻


2. Implementation Guide

2.1 Data Model Overview

**[2.1.1] CompressionConfig and Sub-Configs**

• **FilterConfig**
- `include_paths: Optional[List[str]]`
- `exclude_paths: Optional[List[str]]`
- Exact logical paths only (for now).

• **FlattenConfig**
- `enabled: bool`
- `path_separator: str` (default `"."`).

• **KeyMappingConfig**
- `strategy: "identity" | "auto_abbrev"`
- `min_length: int`
- `max_length: int`

• **TabularConfig**
- `enabled: bool`
- `array_paths: List[str]` (logical paths to object arrays).

• **CompressionConfig**
- `filter: FilterConfig`
- `flatten: FlattenConfig`
- `key_mapping: KeyMappingConfig`
- `tabular: TabularConfig`


**[2.1.2] Schema Object Structure**

• `schema.version: int` (e.g., `1`)
• `schema.original_root_type: "object" | "array"`
• `schema.config.flatten: { enabled, path_separator }`
• `schema.config.tabular: { enabled, array_paths }`
• `schema.fields: { code: logical_path }`
- Example: `{ "a": "user.name", "b": "anchors[].anchor_id" }`
• Optional `schema.structure.tabular_arrays`:
```json
"tabular_arrays": {
  "anchors": {
    "fields": ["b", "c"],
    "kind": "object_array"
  }
}
```


**[2.1.3] Compressed Data Structure**

• `data` mirrors original root type:
- If original root was a dict: `data` is a dict.
- If original root was a list: `data` is a list.
• Objects use **field codes** as keys.
• Arrays configured as tabular arrays become:
- 2D arrays of values (`[[col1, col2, ...], ...]`).


⸻


2.2 Compression Algorithm

**[2.2.1] High-Level Steps**

1. Determine `original_root_type`.
2. Traverse `data` to:
- Identify candidate logical paths, respecting `flatten` settings.
- Apply `filter` rules to keep/drop paths.
- Identify arrays that match `tabular.array_paths`.
3. Collect all kept logical paths.
4. Build `path_to_code` with `_build_field_code_map`.
5. Encode data:
- Use `_encode_data_with_field_codes` for general nesting.
- Use `_encode_tabular_arrays` for configured tabular arrays.
6. Build `schema` using `_build_schema_object`.
7. Return `{"schema": schema, "data": encoded_data}`.


**[2.2.2] Path Handling**

• Use `path_separator` when composing object paths:
- If `root_path` is empty and key is `user` → `user`.
- If `root_path` is `user` and key is `name` → `user.name`.
• Arrays:
- For tabular arrays, logical paths like `anchors[].anchor_id`.
- For non-tabular arrays, you can either:
  - Reuse `root_path` for elements (simpler).
  - Or track indices (not strictly required for minimal spec).


**[2.2.3] Filtering Semantics**

• If `include_paths` is non-empty:
- Only paths in that list are eligible.
• Then apply `exclude_paths` to drop any matches.
• Filtering is evaluated on **full logical paths**.


⸻


2.3 Decompression Algorithm

**[2.3.1] High-Level Steps**

1. Extract `schema` and `data`.
2. Build `code_to_path` from `schema.fields`.
3. Decode non-tabular parts:
- `_decode_data_from_field_codes(data, code_to_path, schema)`.
- Might yield a path-oriented or semi-nested structure.
4. Decode tabular arrays:
- `_decode_tabular_arrays(decoded_data, code_to_path, tabular_metadata)`.
5. If necessary, run `_reconstruct_nested_structure_from_paths` to go from path-based mapping back to nested objects.
6. Ensure root type matches `schema.original_root_type`.


⸻


2.4 YAML Configuration Integration

**[2.4.1] Data Entity Model**

• Each `data_entities.<name>`:
- `type`: `md` | `yaml` | `json` | ...
- `filename`: file path.
- Optional `yaml_schema`: for validation.
- `compression_strategies`: mapping from strategy name to strategy config.


**[2.4.2] Strategy Config Pattern (Final)**


For each strategy under `data_entities.<entity>.compression_strategies`:

• `description: string`
• `compression_strategy_type: json_compact`
• `output_entity: <label of another data entity>`
• `compression:`:
- `filter: { include_paths: [...], exclude_paths: [...] }`
- `flatten: { enabled: bool, path_separator: "." }`
- `key_mapping: { strategy, min_length, max_length }`
- `tabular: { enabled: bool, array_paths: [...] }`


**[2.4.3] Examples**

1. **Minimal JSON Compression for `spec`**  
(Keep everything, short keys; see §1.3.)

2. **Anchors-Only Light View**  
(Filter to anchors/core fields; see §1.3.)

3. **Tabular Anchors**  
(Convert `anchors` to tabular; see §1.3.)


⸻


2.5 Testing Strategy

**[2.5.1] Unit Tests for Core Functions**

• `compress_json` / `decompress_json`:
- Round-trip tests (compress → decompress → original == filtered original).
• `_build_field_code_map`:
- Deterministic code assignment.
• `_encode_tabular_arrays` / `_decode_tabular_arrays`:
- Tabular conversion correctness.
• Filtering behavior:
- Include/exclude precedence.


**[2.5.2] YAML Config Parsing Tests**

• Given a sample `data_entities` YAML:
- Parse and build a `CompressionConfig` for a given entity/strategy.
- Assert that the config matches expectations.


**[2.5.3] Integration Tests**

• End-to-end:
- Given `spec.yaml` and a strategy:
  - Load -> compress -> write `spec_compact.json`.
  - Optionally decompress and compare with original filtered view.


⸻


2.6 Agentic/Automated Workflow Considerations

**[2.6.1] Atomic Functionality**

• Each helper function has a single responsibility, making it **ideal for agent-level tasks**.
• Config parsing vs. compression logic are **separate modules**.


**[2.6.2] Determinism**

• Ensure deterministic:
- Field code ordering (sorted paths or stable traversal).
- Compression outputs for identical inputs and configs.


**[2.6.3] Extensibility**

• Future additions:
- Summarization/truncation as separate strategies or additional config fields.
- Wildcard path support.


⸻


3. Task List (with Section & Line References)

> Note: “line numbers” are approximate relative positions in this guide; use headings + bullets as lookup anchors (e.g., §2.2.1-bullet-3).


3.1 Non-Code Setup & Documentation

Task 1 — Define Project Structure
• **Title:** Define module layout for compression tooling
• **Description:**  
Decide on Python package structure (`compression/`, `tests/`, `config/`) and where to place compression logic vs. YAML integration.
• **References:**  
- §2.1 (data model overview)  
- §2.2 (compression algorithm)
• **Dependencies:**  
- None.


⸻


Task 2 — Document CompressionConfig and Schema Spec
• **Title:** Write developer-facing spec docs for CompressionConfig & schema
• **Description:**  
Create a Markdown doc (e.g., `docs/compression_spec.md`) describing:
- `CompressionConfig` fields and sub-configs.
- `schema` structure and `data` format.
- Logical path notation and tabular arrays.
• **References:**  
- §2.1.1–2.1.3  
- §2.2.1
• **Dependencies:**  
- Task 1 (project structure) for doc location.


⸻


3.2 Tests for Core Compression Helpers (Before Implementation)

Task 3 — Tests for `_build_field_code_map`
• **Title:** Implement unit tests for field code mapping
• **Description:**  
Write tests covering:
- `strategy=identity`: path == code.
- `strategy=auto_abbrev`: deterministic code sequences for given path lists.
• **References:**  
- §2.1.1 (KeyMappingConfig)  
- §2.2.1-step-4
• **Dependencies:**  
- Task 1 (test folder layout)  
- Task 2 (spec for behavior).


⸻


Task 4 — Tests for `_collect_logical_fields`
• **Title:** Implement unit tests for logical field collection
• **Description:**  
Tests to verify:
- Correct path generation for objects and arrays.
- Respect of `flatten.enabled`, `path_separator`.
- Correct include/exclude behavior for `FilterConfig`.
• **References:**  
- §2.2.2 (path handling)  
- §2.2.3 (filtering)
• **Dependencies:**  
- Task 1, Task 2.


⸻


Task 5 — Tests for `_encode_data_with_field_codes`
• **Title:** Implement unit tests for encoding with field codes
• **Description:**  
Tests to ensure:
- Object keys replaced by correct codes.
- Nested structures preserved.
- Non-tabular arrays encoded recursively.
• **References:**  
- §2.2.1-step-5 (non-tabular)  
- §2.2.2
• **Dependencies:**  
- Task 3, Task 4.


⸻


Task 6 — Tests for `_encode_tabular_arrays`
• **Title:** Implement unit tests for tabular array encoding
• **Description:**  
Tests covering:
- Correct 2D table output for a given array and `array_paths`.
- Proper `tabular_metadata` structure (`fields`, `kind`).
- Behavior when array contains non-objects (e.g., skip or error).
• **References:**  
- §2.1.2 (`structure.tabular_arrays`)  
- §2.2.1-step-5 (tabular)
• **Dependencies:**  
- Task 3, Task 4.


⸻


Task 7 — Tests for `_build_schema_object`
• **Title:** Implement unit tests for schema construction
• **Description:**  
Validate that:
- `version`, `original_root_type`, and config subsets are correctly set.
- `fields` is inverted mapping of `path_to_code`.
- `tabular_metadata` is injected under `structure.tabular_arrays`.
• **References:**  
- §2.1.2  
- §2.2.1-step-6
• **Dependencies:**  
- Task 3, Task 6.


⸻


Task 8 — Tests for `_decode_tabular_arrays`
• **Title:** Implement unit tests for tabular array decoding
• **Description:**  
Given `data` with tabular arrays and `tabular_metadata`:
- Ensure arrays are reconstructed to arrays of objects.
- Property names derived correctly from logical paths (`id`, `price`, etc.).
• **References:**  
- §2.3.1-step-4  
- §2.1.2 (`tabular_arrays`)
• **Dependencies:**  
- Task 6, Task 7.


⸻


Task 9 — Tests for `_decode_data_from_field_codes` and `_reconstruct_nested_structure_from_paths`
• **Title:** Implement unit tests for decoding and path-based reconstruction
• **Description:**  
Tests to check:
- Field codes are correctly mapped back to logical paths.
- Nested structure reconstructed from path-based mapping.
• **References:**  
- §2.3.1-steps-3 and 5  
- §2.1.3
• **Dependencies:**  
- Task 3, Task 4, Task 7.


⸻


Task 10 — Tests for `compress_json` / `decompress_json` Integration
• **Title:** Implement round-trip tests for compress/decompress
• **Description:**  
End-to-end tests:
- Small examples: objects, arrays, nested, tabular & non-tabular.
- Compare `decompress_json(compress_json(data, config))` with original filtered view.
• **References:**  
- §2.2.1 (compress)  
- §2.3.1 (decompress)
• **Dependencies:**  
- Tasks 3–9.


⸻


3.3 Core Helper Implementation

Task 11 — Implement `_build_field_code_map`
• **Title:** Implement field code mapping logic
• **Description:**  
Implement `identity` and `auto_abbrev` strategies as per tests/spec.
• **References:**  
- §2.1.1 (KeyMappingConfig)  
- §2.2.1-step-4
• **Dependencies:**  
- Task 3.


⸻


Task 12 — Implement `_collect_logical_fields`
• **Title:** Implement logical field collection
• **Description:**  
Implement traversal that:
- Walks data structure.
- Emits logical paths for fields respecting flatten/filter config.
• **References:**  
- §2.2.2, §2.2.3
• **Dependencies:**  
- Task 4.


⸻


Task 13 — Implement `_encode_data_with_field_codes`
• **Title:** Implement encoding of nested objects/arrays with field codes
• **Description:**  
Replace keys with codes using `path_to_code` and recursive traversal.
• **References:**  
- §2.2.1-step-5  
- §2.2.2
• **Dependencies:**  
- Tasks 11, 12, 5 (tests).


⸻


Task 14 — Implement `_encode_tabular_arrays`
• **Title:** Implement tabular encoding logic
• **Description:**  
Implement detection and conversion of specified arrays to 2D lists and return `tabular_metadata`.
• **References:**  
- §2.1.2 (`tabular_arrays`)  
- §2.2.1-step-5
• **Dependencies:**  
- Tasks 11, 12, 6 (tests).


⸻


Task 15 — Implement `_build_schema_object`
• **Title:** Implement schema construction
• **Description:**  
Create `schema` dict from `original_root_type`, config, `path_to_code`, `tabular_metadata`.
• **References:**  
- §2.1.2  
- §2.2.1-step-6
• **Dependencies:**  
- Tasks 11, 14, 7 (tests).


⸻


Task 16 — Implement `_decode_tabular_arrays`
• **Title:** Implement tabular array decoding
• **Description:**  
Use `code_to_path` + `tabular_metadata` to reconstruct arrays of objects from 2D lists.
• **References:**  
- §2.3.1-step-4  
- §2.1.2
• **Dependencies:**  
- Tasks 14, 15, 8 (tests).


⸻


Task 17 — Implement `_decode_data_from_field_codes` and `_reconstruct_nested_structure_from_paths`
• **Title:** Implement decoding and nested reconstruction
• **Description:**  
Map codes back to paths and reconstruct nested JSON using path segments.
• **References:**  
- §2.3.1-steps-3 and 5  
- §2.1.3
• **Dependencies:**  
- Tasks 11, 12, 9 (tests).


⸻


Task 18 — Implement `compress_json` and `decompress_json`
• **Title:** Implement top-level compress/decompress APIs
• **Description:**  
Wire together all helpers in the order described:
- `compress_json`: determine root type, collect paths, build codes, encode data, build schema.
- `decompress_json`: read schema, decode non-tabular, decode tabular, reconstruct nested.
• **References:**  
- §2.2.1  
- §2.3.1
• **Dependencies:**  
- Tasks 11–17, 10 (tests).


⸻


3.4 YAML Configuration Parsing & Integration

Task 19 — Define Python Structures for Strategy Config from YAML
• **Title:** Implement YAML-to-CompressionConfig mapping
• **Description:**  
Provide a function that:
- Takes parsed YAML `data_entities` and a specific entity + strategy name.
- Returns corresponding `CompressionConfig` and `output_entity` label.
• **References:**  
- §2.4.1–2.4.2  
- §1.3
• **Dependencies:**  
- Tasks 1, 2, 11–12 (for config fields understanding).


⸻


Task 20 — Tests for YAML Strategy Config Parsing
• **Title:** Implement tests for YAML strategy parsing
• **Description:**  
Given a sample YAML (with `spec`, `spec_compact`, strategies), assert:
- Correct detection of `compression_strategy_type: json_compact`.
- Correct mapping to `CompressionConfig`.
- Correct `output_entity`.
• **References:**  
- §2.4.2, §1.3
• **Dependencies:**  
- Task 19.


⸻


Task 21 — Implement High-Level “Run Strategy” Function
• **Title:** Implement a driver for running a compression strategy
• **Description:**  
Function that:
- Given an entity label + strategy name:
  - Loads the input file.
  - Parses to JSON (or via YAML if `type: yaml`).
  - Builds `CompressionConfig` from YAML.
  - Calls `compress_json`.
  - Writes output to `output_entity.filename`.
• **References:**  
- §2.4.1–2.4.3  
- §2.2.1
• **Dependencies:**  
- Tasks 18, 19, 20.


⸻


3.5 Documentation & Finalization

Task 22 — Update/Write Usage Documentation
• **Title:** Document CLI/API usage and YAML examples
• **Description:**  
Extend docs:
- How to declare strategies under `data_entities.<entity>.compression_strategies`.
- How to run compression for a given strategy.
- Examples for `spec` / `spec_compact` / `spec_anchors_light`.
• **References:**  
- §1.3  
- §2.4.2–2.4.3
• **Dependencies:**  
- Tasks 18, 21.


⸻


Task 23 — Add Example Configs & Sample Data
• **Title:** Provide sample YAML config and example compressed output
• **Description:**  
Add:
- A synthetic `spec_1.yaml`.
- Matching `config.yaml` with several strategies (minimal_json, anchors_light, anchors_tabular).
- Sample compressed JSON outputs for reference.
• **References:**  
- §2.4.3  
- §2.5.3
• **Dependencies:**  
- Tasks 18, 21, 22.


⸻


4. Implementation Order & Rationale

4.1 Phase 1: Foundations
1. **Task 1 (Project Structure)**  
Needed so tests and implementation have a home.
2. **Task 2 (Spec Docs)**  
Establishes a shared understanding of `CompressionConfig` and `schema`, crucial for consistent implementations and tests.


4.2 Phase 2: Test-First for Core Helpers
1. **Tasks 3–10 (Helper & Integration Tests)**  
- Write tests **before** implementations to:
  - Lock in behavior for `key_mapping`, path collection, encoding, tabular handling, schema building, and full round-trips.
- This supports agentic workflows (agents can implement functions to satisfy fixed tests).


4.3 Phase 3: Core Helpers Implementation
1. **Tasks 11–17 (Helper Implementations)**  
- Implement in dependency order:
  - Start with `_build_field_code_map` (Task 11) since many later helpers rely on it.
  - `_collect_logical_fields` (Task 12) next, as it feeds into compression.
  - `_encode_data_with_field_codes` (Task 13) and `_encode_tabular_arrays` (Task 14) depend on mapping & paths.
  - `_build_schema_object` (Task 15) depends on mapping & tabular metadata.
  - `_decode_tabular_arrays` (Task 16) and `_decode_data_from_field_codes` + `_reconstruct_nested_structure_from_paths` (Task 17) rely on schema & mapping.

2. **Task 18 (Top-Level compress/decompress)**  
- Only after helpers are ready.
- This is the integration layer, so it must be built on stable, tested helpers.


4.4 Phase 4: YAML Integration
1. **Task 19 (YAML-to-Config Mapping)**  
- Requires understanding `CompressionConfig` and the final YAML pattern from §1.3 and §2.4.
2. **Task 20 (YAML Parsing Tests)**  
- Ensure strategies defined in `data_entities` match expected configs.
3. **Task 21 (Run Strategy Driver)**  
- Depends on compression being stable (Task 18) and on YAML parsing (Task 19, 20).


4.5 Phase 5: Documentation & Examples
1. **Task 22 (Usage Documentation)**  
- Build on working compression & strategy-running flow.
2. **Task 23 (Examples & Sample Data)**  
- Provide concrete examples after everything functions correctly, aiding users and future automated agents.


⸻


This ordering ensures that:

• **Core behavior is precisely specified and tested first** (good for agentic coding).
• **Helpers are implemented in a dependency-aware way**.
• **YAML configuration integration focuses on the final, corrected recommendations** from the last exchanges.
• Documentation and examples are updated at the end when the system is stable.


5. Examples
Below is an example of how this JSON would look after compression using the minimal JSON→JSON scheme we discussed.


To keep it concrete and easy to follow, I’ll assume:

• Root type: **array**.
• We treat the root array itself as a **tabular array** (each element is an object with the same fields).
• We keep **all fields** (no filtering).
• We use `auto_abbrev` for key mapping, with simple alphabetical codes.
• We use the final schema shape described in the guide.


⸻


5.1. Original JSON (for reference)

[
  {
    "type": "Actor",
    "id": "A1",
    "label": "EndUser",
    "categories": ["core"],
    "description": "A single person using the application to manage personal to-do tasks on a desktop or laptop browser.",
    "justification": "Described as a single user who wants a lightweight personal task manager and interacts with tasks, categories, filters, sorting, and preferences.",
    "anchors": ["AN1","AN2","AN3","AN4","AN5","AN6","AN7","AN8","AN9"],
    "sourceConceptIds": ["C1","C5","C7","C22"]
  },
  {
    "type": "Actor",
    "id": "A2",
    "label": "TodoApplication",
    "categories": ["core"],
    "description": "The local browser-based to-do list application that stores and manages tasks and user preferences on the user’s machine.",
    "justification": "Described as a browser-based to-do list app that runs locally, stores data locally, and automatically saves changes.",
    "anchors": ["AN1","AN2","AN8","AN9","AN10","AN13"],
    "sourceConceptIds": ["C1","C2","C3","C9","C10","C31","C32","C33","C34","C36","C42"]
  },
  {
    "type": "DataEntity",
    "id": "DE12",
    "label": "RecurrencePattern",
    "categories": ["future"],
    "description": "The schedule pattern for a recurring task, such as daily, weekly, monthly, or a custom pattern.",
    "justification": "Future capability explicitly lists recurrence patterns including daily, weekly, monthly, and custom.",
    "anchors": ["AN19"],
    "sourceConceptIds": ["C58"]
  },
  {
    "type": "DataEntity",
    "id": "DE13",
    "label": "Tag",
    "categories": ["future"],
    "description": "A label attached to tasks, in addition to categories, that supports richer organization and flexible grouping.",
    "justification": "Richer organization includes tags in addition to categories.",
    "anchors": ["AN20"],
    "sourceConceptIds": ["C59"]
  }
]


⸻


5.2. Logical Fields and Codes

We have a homogeneous array at the root; we treat it as a tabular array with the following logical fields (paths):

• `[].type`
• `[].id`
• `[].label`
• `[].categories`
• `[].description`
• `[].justification`
• `[].anchors`
• `[].sourceConceptIds`


Using a simple alphabetical `auto_abbrev` scheme, we might assign:


"fields": {
  "a": "[].type",
  "b": "[].id",
  "c": "[].label",
  "d": "[].categories",
  "e": "[].description",
  "f": "[].justification",
  "g": "[].anchors",
  "h": "[].sourceConceptIds"
}


⸻


5.3. Example Compressed Output

5.3.1 Schema Section

{
  "schema": {
    "version": 1,
    "original_root_type": "array",
    "config": {
      "flatten": {
        "enabled": false,
        "path_separator": "."
      },
      "tabular": {
        "enabled": true,
        "array_paths": [""]
      }
    },
    "fields": {
      "a": "[].type",
      "b": "[].id",
      "c": "[].label",
      "d": "[].categories",
      "e": "[].description",
      "f": "[].justification",
      "g": "[].anchors",
      "h": "[].sourceConceptIds"
    },
    "structure": {
      "tabular_arrays": {
        "": {
          "fields": ["a", "b", "c", "d", "e", "f", "g", "h"],
          "kind": "object_array"
        }
      }
    }
  },


Notes:

• `array_paths: [""]` here designates the root array as tabular (you could instead name it something like `"root"` if you wrap).
• The `fields` list under `structure.tabular_arrays[""].fields` defines the column order in the table.


5.3.2 Data Section (Tabular Rows)

Each row is a list of 8 items corresponding to `[a,b,c,d,e,f,g,h]` in order:


  "data": [
    [
      "Actor",
      "A1",
      "EndUser",
      ["core"],
      "A single person using the application to manage personal to-do tasks on a desktop or laptop browser.",
      "Described as a single user who wants a lightweight personal task manager and interacts with tasks, categories, filters, sorting, and preferences.",
      ["AN1","AN2","AN3","AN4","AN5","AN6","AN7","AN8","AN9"],
      ["C1","C5","C7","C22"]
    ],
    [
      "Actor",
      "A2",
      "TodoApplication",
      ["core"],
      "The local browser-based to-do list application that stores and manages tasks and user preferences on the user’s machine.",
      "Described as a browser-based to-do list app that runs locally, stores data locally, and automatically saves changes.",
      ["AN1","AN2","AN8","AN9","AN10","AN13"],
      ["C1","C2","C3","C9","C10","C31","C32","C33","C34","C36","C42"]
    ],
    [
      "DataEntity",
      "DE12",
      "RecurrencePattern",
      ["future"],
      "The schedule pattern for a recurring task, such as daily, weekly, monthly, or a custom pattern.",
      "Future capability explicitly lists recurrence patterns including daily, weekly, monthly, and custom.",
      ["AN19"],
      ["C58"]
    ],
    [
      "DataEntity",
      "DE13",
      "Tag",
      ["future"],
      "A label attached to tasks, in addition to categories, that supports richer organization and flexible grouping.",
      "Richer organization includes tags in addition to categories.",
      ["AN20"],
      ["C59"]
    ]
  ]
}


This entire object (schema + data) is the compressed representation.


⸻


5.4. Alternative: Non-Tabular Compression (Same Data)

If you **don’t** treat the root as a tabular array (i.e., `tabular.enabled=false`), the compressed data would instead look like an array of objects with short keys:


5.4.1 Schema

{
  "schema": {
    "version": 1,
    "original_root_type": "array",
    "config": {
      "flatten": {
        "enabled": false,
        "path_separator": "."
      },
      "tabular": {
        "enabled": false,
        "array_paths": []
      }
    },
    "fields": {
      "a": "[].type",
      "b": "[].id",
      "c": "[].label",
      "d": "[].categories",
      "e": "[].description",
      "f": "[].justification",
      "g": "[].anchors",
      "h": "[].sourceConceptIds"
    }
  },


5.4.2 Data

  "data": [
    {
      "a": "Actor",
      "b": "A1",
      "c": "EndUser",
      "d": ["core"],
      "e": "A single person using the application to manage personal to-do tasks on a desktop or laptop browser.",
      "f": "Described as a single user who wants a lightweight personal task manager and interacts with tasks, categories, filters, sorting, and preferences.",
      "g": ["AN1","AN2","AN3","AN4","AN5","AN6","AN7","AN8","AN9"],
      "h": ["C1","C5","C7","C22"]
    },
    {
      "a": "Actor",
      "b": "A2",
      "c": "TodoApplication",
      "d": ["core"],
      "e": "The local browser-based to-do list application that stores and manages tasks and user preferences on the user’s machine.",
      "f": "Described as a browser-based to-do list app that runs locally, stores data locally, and automatically saves changes.",
      "g": ["AN1","AN2","AN8","AN9","AN10","AN13"],
      "h": ["C1","C2","C3","C9","C10","C31","C32","C33","C34","C36","C42"]
    },
    {
      "a": "DataEntity",
      "b": "DE12",
      "c": "RecurrencePattern",
      "d": ["future"],
      "e": "The schedule pattern for a recurring task, such as daily, weekly, monthly, or a custom pattern.",
      "f": "Future capability explicitly lists recurrence patterns including daily, weekly, monthly, and custom.",
      "g": ["AN19"],
      "h": ["C58"]
    },
    {
      "a": "DataEntity",
      "b": "DE13",
      "c": "Tag",
      "d": ["future"],
      "e": "A label attached to tasks, in addition to categories, that supports richer organization and flexible grouping.",
      "f": "Richer organization includes tags in addition to categories.",
      "g": ["AN20"],
      "h": ["C59"]
    }
  ]
}


This is slightly less compressed than the tabular version but simpler to handle.


⸻

