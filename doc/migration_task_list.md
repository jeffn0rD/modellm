# ModelLM: Merged Migration & Code Improvement Task List

**Version:** 1.0  
**Date:** 2026-02-26  
**Scope:** JSON Compression Migration + Code Review Improvements  
**Intended Consumer:** LLM agent performing autonomous implementation

---

## Overview

This document merges two work streams:

1. **JSON Compression Migration (M-series):** Replace content-dependent compression strategies (`anchor_index`, `concept_summary`, `hierarchical`) for `yaml`/`json` typed data entities with a new `json_compact` strategy using the pipeline `(YAML→)JSON → COMPRESSED → PROMPT`. Markdown/NL entities (`md`, `text`) are **not affected** — they pass through as-is.

2. **Code Review Improvements (CR-series):** Fixes and refactors identified in code review documents (`json_validator_review_summary.md`, `json_validator_refactor_proposal.md`, `compression_alignment_report.md`, `BUG_SUMMARY.md`).

**Execution order:** CR tasks that are prerequisites to M tasks are listed first. The two streams are otherwise largely independent and can be interleaved.

---

## Key Architectural Decisions (from prior session)

| # | Decision | Resolution |
|---|----------|------------|
| 1 | `compression_params.level` on yaml/json entities using `json_compact` | **Remove** — `json_compact` has its own `compression:` block; `level` is not applicable |
| 2 | Backward compatibility for old strategy names on yaml/json entities | **Migrate directly** — not in production; old strategies removed from yaml/json entities |
| 3 | `message_aggregations` schema | **Add `json_compact`** — use `schemas/messageAggregations.schema.json` (already exists, wraps single object; needs array wrapper — see M-02b) |
| 4 | Tabular config defaults | **Enable tabular** for root-array entities (`concepts`, `aggregations`, `messages`, `message_aggregations`) |
| 5 | `spec_formal` / `revised_spec` (md) | **Unchanged** — md passthrough, no compression migration |
| 6 | Output entity file writing | **In-memory only** — compressed JSON used in prompt; saved JSON entities are uncompressed and schema-validated |

---

## Affected Entities & Steps (Compression Migration Scope)

| Step | Input Label | Entity Type | Old Strategy | New Strategy |
|------|-------------|-------------|--------------|--------------|
| step2 | spec | yaml | anchor_index | minimal_json |
| stepC3 | spec | yaml | hierarchical | minimal_json |
| stepC4 | spec | yaml | anchor_index | minimal_json |
| stepC4 | concepts | json | concept_summary | minimal_json |
| stepC5 | spec | yaml | anchor_index | minimal_json |
| stepC5 | concepts | json | concept_summary | minimal_json |
| stepC5 | aggregations | json | concept_summary | minimal_json |
| stepD1 | spec | yaml | anchor_index | minimal_json |
| stepD1 | concepts | json | concept_summary | minimal_json |
| stepD1 | messages | json | concept_summary | minimal_json |

**Not affected:** `nl_spec` (md/cli), `spec_formal` (md), `revised_spec` (md), `requirements` (json, no compression currently), `message_aggregations` (json, no compression currently — add `minimal_json`).

---

## SECTION 1: Code Review Tasks (CR-series)

These tasks address bugs and structural issues identified in code review. Several are prerequisites for the compression migration.

---

### CR-01: Fix JSONValidator Base Class — Use jsonschema Library

**Description:**  
The `JSONValidator` base class in `prompt_pipeline/validation/json_validator.py` implements custom validation logic instead of using the `jsonschema` library. The `_validate_schema()` method only checks basic type (array vs object) and ignores all schema constraints (required fields, patterns, enums, additionalProperties). Refactor to use `jsonschema.validate()`.

**References:**  
- `doc/json_validator_review_summary.md` — Priority 2  
- `doc/json_validator_refactor_proposal.md` — Section 2  
- `prompt_pipeline/validation/json_validator.py` — lines 78–95 (`_validate_schema`)

**Dependencies:** None

**Implementation Details:**  
1. Verify `jsonschema` is in `pyproject.toml` dependencies (it is already used in `yaml_schema_validator.py` — confirm it's declared).  
2. Replace the body of `JSONValidator._validate_schema()` with:
   ```python
   def _validate_schema(self, data: Any, result: ValidationResult) -> None:
       if not self.schema:
           return
       try:
           jsonschema.validate(instance=data, schema=self.schema)
       except jsonschema.exceptions.ValidationError as e:
           result.add_error(f"Schema validation failed: {e.message}")
           if e.absolute_path:
               path = '.'.join(str(p) for p in e.absolute_path)
               result.add_error(f"  at path: {path}")
   ```
3. Add `import jsonschema` at top of file if not present.
4. The `validate()` method in the base class already calls `_validate_schema` — no change needed there.

**Testing Requirements:**  
- Unit: `tests/test_prompt_pipeline/test_json_validator.py`
  - Test that a valid concepts array passes schema validation
  - Test that an object with wrong `type` enum value fails with a schema error message
  - Test that an object missing a required field fails with a schema error message
  - Test that `schema_path=""` (disabled) still works (no schema loaded, no crash)
- Edge cases: `data=None`, empty array `[]`, schema file not found

**Acceptance Criteria:**  
- `jsonschema.validate()` is called when `self.schema` is set  
- Schema errors produce meaningful error messages  
- All existing passing tests continue to pass

---

### CR-02: Simplify Subclass Validators — Remove Hardcoded Logic

**Description:**  
`ConceptsValidator`, `AggregationsValidator`, `MessagesValidator`, and `RequirementsValidator` contain hardcoded ID patterns, required field lists, and enum values that duplicate what is already in the schema files. Since CR-01 makes the base class schema-driven, remove all custom validation logic from subclasses. Each subclass should only call `super().validate()` and add any post-schema checks that cannot be expressed in JSON Schema.

**References:**  
- `doc/json_validator_refactor_proposal.md` — Section 3  
- `prompt_pipeline/validation/json_validator.py` — lines 120–327  
- `schemas/concepts.schema.json`, `schemas/aggregations.schema.json`, `schemas/messages.schema.json`, `schemas/requirements.schema.json`

**Dependencies:** CR-01

**Implementation Details:**  
For each subclass:
1. Remove hardcoded `VALID_TYPES`, `REQUIRED_FIELDS`, `VALID_CATEGORIES`, regex patterns.
2. Remove custom `_validate_concept()`, `_validate_aggregation()`, `_validate_message()`, `_validate_requirement()` methods.
3. The `validate()` method in each subclass should:
   - Parse JSON (or delegate to base)
   - Check it's an array (base class handles this via schema)
   - Call `super().validate()` which runs schema validation
   - Return the result
4. Keep the `DEFAULT_SCHEMA_FILE` class attribute pointing to the correct schema.
5. Keep the convenience module-level functions (`validate_concepts()`, etc.) intact — they just instantiate the validator.

**Note on `AggregationsValidator`:** The `aggregations.schema.json` already uses array type with `items`. The `messageAggregations.schema.json` currently defines a single object — this is addressed in CR-03.

**Testing Requirements:**  
- Unit: Update `tests/test_prompt_pipeline/test_json_validator.py`
  - Remove tests that rely on custom validation messages (e.g., "must be an array" custom message — replace with schema error message check)
  - Add tests using actual schema files (not `schema_path=""`)
  - Test `ConceptsValidator` with invalid `type` enum → schema error
  - Test `AggregationsValidator` with missing `members` → schema error
  - Test `MessagesValidator` with invalid `category` → schema error
  - Test `RequirementsValidator` with missing `description` → schema error
- Edge cases: Empty array `[]` should pass (schema allows it), null items should fail

**Acceptance Criteria:**  
- No hardcoded patterns or field lists in subclasses  
- All validation driven by schema files  
- Tests pass using real schema files

---

### CR-03: Fix messageAggregations Schema — Wrap as Array

**Description:**  
`schemas/messageAggregations.schema.json` currently defines a single object (`"type": "object"`), but `json/messageAggregations.json` and the pipeline output `messageAggregations.json` are arrays of such objects. Update the schema to wrap the object definition in an array schema with `items`, matching the pattern used by all other entity schemas.

**References:**  
- `doc/json_validator_review_summary.md` — Priority 1  
- `schemas/messageAggregations.schema.json`  
- `schemas/aggregations.schema.json` (reference pattern — already correct array schema)

**Dependencies:** None (can be done independently, but CR-02 depends on it)

**Implementation Details:**  
Current schema root is `{"type": "object", "required": [...], "properties": {...}}`.  
New schema root:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["id", "label", "category", "members", "description", "justification"],
    "properties": { ... }
  }
}
```
Move all existing `required`, `properties`, `additionalProperties` into `items`.

Also update `pipeline_config.yaml`: set `message_aggregations.schema` to `schemas/messageAggregations.schema.json` (currently `schema: null`).

**Testing Requirements:**  
- Unit: Validate `json/messageAggregations.json` against the updated schema — should pass  
- Unit: Validate a single object (not array) against the schema — should fail  
- Unit: Validate an array with a missing required field — should fail

**Acceptance Criteria:**  
- `messageAggregations.schema.json` uses `"type": "array"` at root  
- `pipeline_config.yaml` `message_aggregations.schema` is set  
- `json/messageAggregations.json` validates successfully against the new schema

---

### CR-04: Fix dry-run to Show Full Prompt Construction

**Description:**  
The `--dry-run` flag in `prompt_pipeline_cli/commands/run_step.py` returns early before prompt construction, so it never shows the substituted prompt. Fix it to build the complete prompt (preamble + prompt file + substituted variables) and display it, without making any LLM API calls.

**References:**  
- `BUG_SUMMARY.md` — full description  
- `prompt_pipeline_cli/commands/run_step.py` — lines 134–158 (dry-run early return)  
- `prompt_pipeline/step_executor.py` — `execute_step()` method

**Dependencies:** None

**Implementation Details:**  
1. In `run_step.py`, locate the dry-run early-return block.
2. Instead of returning immediately, continue to:
   - Load step config
   - Resolve inputs (using `_prepare_variables_from_config`)
   - Build the full prompt via `prompt_manager.get_prompt_with_variables()`
   - Display the prompt using `format_prompt()` / `print_header()`
   - Display compression metrics
   - Print `[DRY RUN] No API call will be made`
   - Return without calling `llm_client.call_prompt_async()`
3. The cleanest approach: pass a `dry_run=True` flag into `StepExecutor.execute_step()` and have it skip only the LLM call + file write, but still build and display the prompt.

**Testing Requirements:**  
- Integration: `tests/test_prompt_pipeline/test_cli_dry_run.py`
  - `test_dry_run_shows_prompt()`: Run `--dry-run` on step1 with a test input file; assert prompt content appears in stdout; assert no "Executing step" or API call markers in stdout
  - `test_dry_run_no_output_file()`: Assert no output file is created in dry-run mode
  - `test_dry_run_shows_compression_metrics()`: Assert compression metrics section appears when compression is configured
- Edge cases: Missing input file in dry-run should still show error (not crash silently)

**Acceptance Criteria:**  
- `--dry-run` displays the full substituted prompt  
- `--dry-run` makes no LLM API calls  
- `--dry-run` creates no output files  
- Existing dry-run tests continue to pass

---

### CR-05: Add `run-step --info` CLI Command

**Description:**  
Add a CLI switch `--info` (or sub-command) to `run-step` that outputs the requirements for a given step: inputs (labels, sources, compression), outputs (labels, filenames), prompt file, persona, validation config. This is listed in `developer_todo.md` as the next task.

**References:**  
- `developer_todo.md` — "need a CLI command/switch that outputs the requirements for a given step"  
- `prompt_pipeline_cli/commands/run_step.py`  
- `prompt_pipeline/prompt_manager.py` — `get_step_config()`  
- `tests/test_prompt_pipeline/test_run_step_info.py` (test file already exists — check its content)

**Dependencies:** None

**Implementation Details:**  
1. Add `--info` flag to the `run-step` Click command in `run_step.py`.
2. When `--info` is set:
   - Load step config via `prompt_manager.get_step_config(step_name)`
   - For each input: show label, source, compression strategy, color
   - For each output: show label, filename (from `data_entities`), type, schema
   - Show prompt file path
   - Show persona
   - Show validation enabled/disabled
   - Show model levels for this step
   - Print in a clean, readable format (use `print_header`, `print_info` from `terminal_utils`)
   - Return without executing the step
3. Check `tests/test_prompt_pipeline/test_run_step_info.py` for existing test expectations and implement to satisfy them.

**Testing Requirements:**  
- Unit/Integration: `tests/test_prompt_pipeline/test_run_step_info.py`
  - `test_info_shows_inputs()`: Assert input labels appear in output
  - `test_info_shows_outputs()`: Assert output labels and filenames appear
  - `test_info_shows_prompt_file()`: Assert prompt file name appears
  - `test_info_shows_compression()`: Assert compression strategy names appear
  - `test_info_no_api_call()`: Assert no LLM call is made
- Edge cases: Invalid step name with `--info` should show clear error

**Acceptance Criteria:**  
- `prompt-pipeline run-step stepC3 --info` prints step requirements  
- Output includes: inputs, outputs, prompt file, persona, validation, model levels  
- No API call is made  
- Tests in `test_run_step_info.py` pass

---

## SECTION 2: JSON Compression Migration Tasks (M-series)

---

### M-01: Create Module Structure for json_compression

**Description:**  
Create the Python package directory `prompt_pipeline/compression/json_compression/` with the required module files. This is the home for all new compression code.

**References:**  
- `doc/json_compression.md` — §3.1 Task 1, §4.1  
- `prompt_pipeline/compression/` (existing structure)

**Dependencies:** None

**Implementation Details:**  
Create the following files (initially empty or with stub content):
```
prompt_pipeline/compression/json_compression/
    __init__.py          # Public API exports
    config.py            # CompressionConfig dataclasses
    compressor.py        # Core compression functions + helpers
    decompressor.py      # Core decompression functions + helpers
    yaml_utils.py        # YAML→JSON conversion utility
    strategy.py          # JsonCompactStrategy (CompressionStrategy subclass)
```

`__init__.py` should export:
```python
from .config import CompressionConfig, FilterConfig, FlattenConfig, KeyMappingConfig, TabularConfig
from .compressor import compress_json
from .decompressor import decompress_json
from .yaml_utils import yaml_to_json_dict
from .strategy import JsonCompactStrategy
```

**Testing Requirements:**  
- Verify `from prompt_pipeline.compression.json_compression import compress_json` works after creation  
- No functional tests at this stage

**Acceptance Criteria:**  
- Package directory exists with all 6 files  
- `__init__.py` exports are importable without errors  
- No circular imports

---

### M-02: Implement CompressionConfig Dataclasses

**Description:**  
Implement the configuration dataclasses in `prompt_pipeline/compression/json_compression/config.py`. These model the compression configuration as described in the implementation guide.

**References:**  
- `doc/json_compression.md` — §2.1.1 (CompressionConfig and Sub-Configs)

**Dependencies:** M-01

**Implementation Details:**  
```python
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class FilterConfig:
    include_paths: List[str] = field(default_factory=list)
    exclude_paths: List[str] = field(default_factory=list)

@dataclass
class FlattenConfig:
    enabled: bool = False
    path_separator: str = "."

@dataclass
class KeyMappingConfig:
    strategy: str = "auto_abbrev"   # "identity" | "auto_abbrev"
    min_length: int = 1
    max_length: int = 4

@dataclass
class TabularConfig:
    enabled: bool = False
    array_paths: List[str] = field(default_factory=list)

@dataclass
class CompressionConfig:
    filter: FilterConfig = field(default_factory=FilterConfig)
    flatten: FlattenConfig = field(default_factory=FlattenConfig)
    key_mapping: KeyMappingConfig = field(default_factory=KeyMappingConfig)
    tabular: TabularConfig = field(default_factory=TabularConfig)
```

Note: This `CompressionConfig` is **separate** from the existing `prompt_pipeline.compression.manager.CompressionConfig`. The new one lives in `json_compression/config.py` and is specific to the json_compact strategy.

**Testing Requirements:**  
- Unit: Instantiate each dataclass with defaults — verify field values  
- Unit: Instantiate with custom values — verify they are stored  
- Edge cases: Empty `include_paths` means "include all"; `strategy` must be `"identity"` or `"auto_abbrev"`

**Acceptance Criteria:**  
- All 5 dataclasses importable from `prompt_pipeline.compression.json_compression.config`  
- Default values match the spec  
- No runtime errors on instantiation

---

### M-03: Implement yaml_to_json_dict Utility

**Description:**  
Implement `yaml_to_json_dict()` in `prompt_pipeline/compression/json_compression/yaml_utils.py`. This function converts a YAML string to a Python dict/list (JSON-compatible), reusing the existing `yaml.safe_load` pattern already present in `YamlAsJsonStrategy` and `YAMLSchemaValidator`.

**References:**  
- `doc/json_compression.md` — §2.4.1 (entity type: yaml)  
- `prompt_pipeline/compression/strategies/yaml_as_json.py` (existing YAML→JSON conversion)  
- `prompt_pipeline/validation/yaml_schema_validator.py` (existing yaml.safe_load usage)

**Dependencies:** M-01

**Implementation Details:**  
```python
import yaml
import json
from typing import Any

def yaml_to_json_dict(yaml_content: str) -> Any:
    """
    Parse a YAML string and return a JSON-compatible Python object.
    
    Args:
        yaml_content: YAML string to parse.
    
    Returns:
        Python dict or list (JSON-compatible).
    
    Raises:
        ValueError: If YAML is invalid or contains non-JSON-serializable types.
    """
    try:
        data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML: {e}")
    
    if data is None:
        raise ValueError("YAML content is empty or null")
    
    # Round-trip through JSON to ensure JSON-compatibility
    # (catches datetime objects, etc.)
    try:
        json_str = json.dumps(data, default=str)
        return json.loads(json_str)
    except (TypeError, ValueError) as e:
        raise ValueError(f"YAML contains non-JSON-serializable data: {e}")
```

**Testing Requirements:**  
- Unit: Valid YAML dict → correct Python dict  
- Unit: Valid YAML list → correct Python list  
- Unit: Invalid YAML → `ValueError` raised  
- Unit: Empty YAML → `ValueError` raised  
- Unit: YAML with datetime → converted to string (via `default=str`)  
- Integration: Output of `yaml_to_json_dict` can be passed directly to `compress_json`

**Acceptance Criteria:**  
- Function importable from `prompt_pipeline.compression.json_compression.yaml_utils`  
- Returns JSON-compatible Python objects  
- Raises `ValueError` for invalid input

---

### M-04: Implement `_build_field_code_map`

**Description:**  
Implement the internal helper `_build_field_code_map(paths, config)` in `prompt_pipeline/compression/json_compression/compressor.py`. This maps logical paths to short codes using either `identity` or `auto_abbrev` strategy.

**References:**  
- `doc/json_compression.md` — §2.1.1 (KeyMappingConfig), §2.2.1 step 4  
- `doc/json_compression.md` — §5.2 (example: `{"a": "[].type", "b": "[].id", ...}`)

**Dependencies:** M-01, M-02

**Implementation Details:**  
```python
from typing import Dict, List
from .config import KeyMappingConfig

def _build_field_code_map(paths: List[str], config: KeyMappingConfig) -> Dict[str, str]:
    """
    Build a mapping from short code -> logical path.
    
    Args:
        paths: Sorted list of logical paths (deterministic ordering required).
        config: KeyMappingConfig specifying strategy.
    
    Returns:
        Dict mapping code -> path (e.g., {"a": "user.name", "b": "user.email"})
    """
    if config.strategy == "identity":
        return {path: path for path in paths}
    
    elif config.strategy == "auto_abbrev":
        # Generate codes: a, b, ..., z, aa, ab, ..., az, ba, ...
        codes = _generate_codes(len(paths), config.min_length, config.max_length)
        return {code: path for code, path in zip(codes, paths)}
    
    else:
        raise ValueError(f"Unknown key mapping strategy: {config.strategy!r}")

def _generate_codes(n: int, min_length: int, max_length: int) -> List[str]:
    """Generate n unique short alphabetic codes."""
    import string
    alphabet = string.ascii_lowercase
    codes = []
    length = min_length
    while len(codes) < n:
        # Generate all codes of current length
        from itertools import product
        for combo in product(alphabet, repeat=length):
            codes.append("".join(combo))
            if len(codes) == n:
                break
        length += 1
        if length > max_length:
            raise ValueError(f"Cannot generate {n} codes within max_length={max_length}")
    return codes[:n]
```

**Testing Requirements:**  
- Unit: `identity` strategy — code equals path for each entry  
- Unit: `auto_abbrev` with 3 paths → `["a", "b", "c"]`  
- Unit: `auto_abbrev` with 27 paths → codes include `"aa"` after `"z"`  
- Unit: Deterministic — same paths always produce same codes  
- Unit: Unknown strategy → `ValueError`  
- Edge cases: Empty paths list → empty dict; single path → `{"a": path}`

**Acceptance Criteria:**  
- Function produces deterministic, unique codes  
- `identity` strategy: code == path  
- `auto_abbrev` strategy: codes are short alphabetic strings in order  
- All tests pass

---

### M-05: Implement `_collect_logical_fields`

**Description:**  
Implement `_collect_logical_fields(data, config)` in `compressor.py`. This traverses the data structure and collects all logical paths, applying filter rules.

**References:**  
- `doc/json_compression.md` — §2.2.2 (Path Handling), §2.2.3 (Filtering Semantics)

**Dependencies:** M-01, M-02

**Implementation Details:**  
```python
from typing import Any, List, Set
from .config import CompressionConfig

def _collect_logical_fields(data: Any, config: CompressionConfig) -> List[str]:
    """
    Traverse data and collect all logical paths, applying filter rules.
    
    Logical path notation:
    - Object keys: "user.name", "address.city"
    - Array elements: "[].type", "[].id" (for arrays of objects)
    - Root array: paths start with "[]."
    
    Args:
        data: JSON-compatible Python object (dict or list).
        config: CompressionConfig with filter and flatten settings.
    
    Returns:
        Sorted list of unique logical paths that pass filter rules.
    """
    paths: Set[str] = set()
    sep = config.flatten.path_separator
    
    def _traverse(obj: Any, prefix: str) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                path = f"{prefix}{sep}{key}" if prefix else key
                if not isinstance(value, (dict, list)):
                    paths.add(path)
                else:
                    _traverse(value, path)
        elif isinstance(obj, list):
            if obj and isinstance(obj[0], dict):
                # Array of objects — use [] notation
                arr_prefix = f"{prefix}[]" if prefix else "[]"
                # Collect all keys across all items
                for item in obj:
                    if isinstance(item, dict):
                        for key, value in item.items():
                            path = f"{arr_prefix}{sep}{key}"
                            if not isinstance(value, (dict, list)):
                                paths.add(path)
                            else:
                                _traverse(value, f"{arr_prefix}{sep}{key}")
    
    _traverse(data, "")
    
    # Apply filtering
    result = sorted(paths)
    
    include = config.filter.include_paths
    exclude = config.filter.exclude_paths
    
    if include:
        result = [p for p in result if p in include]
    if exclude:
        result = [p for p in result if p not in exclude]
    
    return result
```

**Testing Requirements:**  
- Unit: Flat dict `{"a": 1, "b": 2}` → `["a", "b"]`  
- Unit: Nested dict `{"user": {"name": "x"}}` → `["user.name"]`  
- Unit: Array of objects `[{"id": 1}, {"id": 2}]` → `["[].id"]`  
- Unit: `include_paths=["[].id"]` → only `["[].id"]` returned  
- Unit: `exclude_paths=["[].description"]` → description excluded  
- Unit: Empty `include_paths` → all paths included  
- Edge cases: Empty dict `{}` → `[]`; empty list `[]` → `[]`; mixed-type list

**Acceptance Criteria:**  
- Correct logical paths generated for all data shapes  
- Filter rules applied correctly (include before exclude)  
- Output is sorted (deterministic)

---

### M-06: Implement `_encode_data_with_field_codes`

**Description:**  
Implement `_encode_data_with_field_codes(data, path_to_code, config)` in `compressor.py`. This recursively replaces object keys with their short codes.

**References:**  
- `doc/json_compression.md` — §2.2.1 step 5 (non-tabular), §2.2.2  
- `doc/json_compression.md` — §5.4 (non-tabular example)

**Dependencies:** M-04, M-05

**Implementation Details:**  
```python
from typing import Any, Dict

def _encode_data_with_field_codes(
    data: Any,
    path_to_code: Dict[str, str],
    prefix: str = "",
    sep: str = ".",
) -> Any:
    """
    Recursively encode data by replacing keys with field codes.
    
    Args:
        data: JSON-compatible Python object.
        path_to_code: Mapping from logical path to short code.
        prefix: Current path prefix (for recursion).
        sep: Path separator.
    
    Returns:
        Encoded data with short keys.
    """
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            path = f"{prefix}{sep}{key}" if prefix else key
            code = path_to_code.get(path, key)  # fallback to original key
            if isinstance(value, (dict, list)):
                result[code] = _encode_data_with_field_codes(value, path_to_code, path, sep)
            else:
                result[code] = value
        return result
    
    elif isinstance(data, list):
        return [_encode_data_with_field_codes(item, path_to_code, prefix, sep) for item in data]
    
    else:
        return data
```

**Testing Requirements:**  
- Unit: Flat dict with code map `{"a": "name"}` → `{"a": "Alice"}` from `{"name": "Alice"}`  
- Unit: Nested dict — nested keys also encoded  
- Unit: Array of objects — each object's keys encoded  
- Unit: Key not in code map → original key preserved (fallback)  
- Unit: Values (strings, numbers, arrays of scalars) are not modified

**Acceptance Criteria:**  
- All dict keys replaced by codes where mapping exists  
- Nested structures handled recursively  
- Non-dict/list values passed through unchanged

---

### M-07: Implement `_encode_tabular_arrays`

**Description:**  
Implement `_encode_tabular_arrays(data, path_to_code, config)` in `compressor.py`. This converts configured arrays of objects into 2D tables and returns tabular metadata.

**References:**  
- `doc/json_compression.md` — §2.1.2 (tabular_arrays structure), §2.2.1 step 5 (tabular)  
- `doc/json_compression.md` — §5.1–5.3 (tabular example with root array)

**Dependencies:** M-04, M-05

**Implementation Details:**  
```python
from typing import Any, Dict, List, Tuple

def _encode_tabular_arrays(
    data: Any,
    path_to_code: Dict[str, str],
    config,  # CompressionConfig
    sep: str = ".",
) -> Tuple[Any, Dict[str, Any]]:
    """
    Convert configured array paths to tabular (2D) format.
    
    Returns:
        Tuple of (encoded_data, tabular_metadata)
        tabular_metadata shape: {
            "array_path": {
                "fields": ["code1", "code2", ...],
                "kind": "object_array"
            }
        }
    """
    tabular_metadata = {}
    
    if not config.tabular.enabled or not config.tabular.array_paths:
        return data, tabular_metadata
    
    # Handle root array (path == "" or path == "[]")
    if isinstance(data, list) and ("" in config.tabular.array_paths or "[]" in config.tabular.array_paths):
        path_key = "" if "" in config.tabular.array_paths else "[]"
        # Collect field codes for root array items
        field_codes = [
            code for code, path in sorted(path_to_code.items(), key=lambda x: x[0])
            if path.startswith("[].")
        ]
        field_paths = [path_to_code[code] for code in field_codes]
        
        # Build 2D table
        rows = []
        for item in data:
            if isinstance(item, dict):
                row = []
                for fpath in field_paths:
                    key = fpath[3:]  # strip "[]."
                    row.append(item.get(key))
                rows.append(row)
        
        tabular_metadata[path_key] = {
            "fields": field_codes,
            "kind": "object_array"
        }
        return rows, tabular_metadata
    
    # Handle named array paths within a dict
    if isinstance(data, dict):
        result = dict(data)
        for array_path in config.tabular.array_paths:
            if array_path in result and isinstance(result[array_path], list):
                arr = result[array_path]
                prefix = f"{array_path}[]"
                field_codes = [
                    code for code, path in sorted(path_to_code.items(), key=lambda x: x[0])
                    if path.startswith(f"{prefix}.")
                ]
                field_paths = [path_to_code[code] for code in field_codes]
                
                rows = []
                for item in arr:
                    if isinstance(item, dict):
                        row = [item.get(fpath.split(".")[-1]) for fpath in field_paths]
                        rows.append(row)
                
                result[array_path] = rows
                tabular_metadata[array_path] = {
                    "fields": field_codes,
                    "kind": "object_array"
                }
        return result, tabular_metadata
    
    return data, tabular_metadata
```

**Testing Requirements:**  
- Unit: Root array with `array_paths=[""]` → 2D list + correct metadata  
- Unit: Named array path `"anchors"` in dict → `data["anchors"]` becomes 2D list  
- Unit: `tabular.enabled=False` → data unchanged, empty metadata  
- Unit: Array of non-objects → handled gracefully (skip or pass through)  
- Unit: Metadata `fields` list matches column order in rows

**Acceptance Criteria:**  
- Configured arrays converted to 2D lists  
- `tabular_metadata` correctly describes field codes and kind  
- Non-configured arrays left unchanged

---

### M-08: Implement `_build_schema_object`

**Description:**  
Implement `_build_schema_object(original_root_type, config, path_to_code, tabular_metadata)` in `compressor.py`. This constructs the `schema` section of the compressed output.

**References:**  
- `doc/json_compression.md` — §2.1.2 (Schema Object Structure)  
- `doc/json_compression.md` — §5.3.1 (example schema section)

**Dependencies:** M-04, M-07

**Implementation Details:**  
```python
from typing import Any, Dict

def _build_schema_object(
    original_root_type: str,
    config,  # CompressionConfig
    path_to_code: Dict[str, str],
    tabular_metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build the schema section of the compressed output.
    
    Returns:
        Schema dict with version, original_root_type, config, fields, structure.
    """
    schema = {
        "version": 1,
        "original_root_type": original_root_type,
        "config": {
            "flatten": {
                "enabled": config.flatten.enabled,
                "path_separator": config.flatten.path_separator,
            },
            "tabular": {
                "enabled": config.tabular.enabled,
                "array_paths": config.tabular.array_paths,
            },
        },
        "fields": path_to_code,  # {code: path}
    }
    
    if tabular_metadata:
        schema["structure"] = {
            "tabular_arrays": tabular_metadata
        }
    
    return schema
```

**Testing Requirements:**  
- Unit: `version` is always `1`  
- Unit: `original_root_type` is `"object"` or `"array"`  
- Unit: `fields` is the `path_to_code` dict  
- Unit: `structure.tabular_arrays` present only when `tabular_metadata` is non-empty  
- Unit: Config values correctly reflected in `schema.config`

**Acceptance Criteria:**  
- Schema object matches the structure defined in §2.1.2  
- All required fields present  
- `structure` key only present when tabular arrays exist

---

### M-09: Implement `_decode_tabular_arrays`

**Description:**  
Implement `_decode_tabular_arrays(data, code_to_path, tabular_metadata)` in `decompressor.py`. This reconstructs arrays of objects from 2D tables using the schema metadata.

**References:**  
- `doc/json_compression.md` — §2.3.1 step 4  
- `doc/json_compression.md` — §2.1.2 (tabular_arrays)

**Dependencies:** M-07, M-08

**Implementation Details:**  
```python
from typing import Any, Dict

def _decode_tabular_arrays(
    data: Any,
    code_to_path: Dict[str, str],
    tabular_metadata: Dict[str, Any],
    sep: str = ".",
) -> Any:
    """
    Reconstruct arrays of objects from 2D tabular format.
    
    Args:
        data: Encoded data (may contain 2D lists for tabular arrays).
        code_to_path: Mapping from code to logical path.
        tabular_metadata: From schema.structure.tabular_arrays.
        sep: Path separator.
    
    Returns:
        Data with tabular arrays reconstructed to arrays of objects.
    """
    if not tabular_metadata:
        return data
    
    # Handle root array (path_key == "" or "[]")
    if ("" in tabular_metadata or "[]" in tabular_metadata) and isinstance(data, list):
        path_key = "" if "" in tabular_metadata else "[]"
        meta = tabular_metadata[path_key]
        field_codes = meta["fields"]
        
        result = []
        for row in data:
            if isinstance(row, list):
                obj = {}
                for code, value in zip(field_codes, row):
                    path = code_to_path.get(code, code)
                    # Extract leaf key from path (e.g., "[].name" -> "name")
                    key = path.split(sep)[-1].lstrip("[]").lstrip(sep)
                    obj[key] = value
                result.append(obj)
            else:
                result.append(row)
        return result
    
    # Handle named array paths within a dict
    if isinstance(data, dict):
        result = dict(data)
        for array_path, meta in tabular_metadata.items():
            if array_path in result and isinstance(result[array_path], list):
                field_codes = meta["fields"]
                reconstructed = []
                for row in result[array_path]:
                    if isinstance(row, list):
                        obj = {}
                        for code, value in zip(field_codes, row):
                            path = code_to_path.get(code, code)
                            key = path.split(sep)[-1]
                            obj[key] = value
                        reconstructed.append(obj)
                result[array_path] = reconstructed
        return result
    
    return data
```

**Testing Requirements:**  
- Unit: Root array tabular → reconstructed array of objects with correct keys  
- Unit: Named array path → reconstructed correctly  
- Unit: Empty tabular_metadata → data unchanged  
- Unit: Row with fewer values than fields → missing values are `None`

**Acceptance Criteria:**  
- Tabular arrays correctly reconstructed to arrays of objects  
- Field names derived from `code_to_path` mapping  
- Non-tabular data unchanged

---

### M-10: Implement `_decode_data_from_field_codes`

**Description:**  
Implement `_decode_data_from_field_codes(data, code_to_path, sep)` in `decompressor.py`. This recursively replaces short codes back to original field names in non-tabular data.

**References:**  
- `doc/json_compression.md` — §2.3.1 step 3

**Dependencies:** M-06, M-09

**Implementation Details:**  
```python
from typing import Any, Dict

def _decode_data_from_field_codes(
    data: Any,
    code_to_path: Dict[str, str],
    sep: str = ".",
) -> Any:
    """
    Recursively replace field codes with original field names.
    
    For non-tabular data, codes are the keys in dicts.
    The code_to_path gives us the full logical path; we use the
    last segment as the reconstructed key name.
    
    Args:
        data: Encoded data with short keys.
        code_to_path: Mapping from code to logical path.
        sep: Path separator.
    
    Returns:
        Data with original field names restored.
    """
    if isinstance(data, dict):
        result = {}
        for code, value in data.items():
            path = code_to_path.get(code, code)
            # Use last segment of path as key
            key = path.split(sep)[-1]
            if isinstance(value, (dict, list)):
                result[key] = _decode_data_from_field_codes(value, code_to_path, sep)
            else:
                result[key] = value
        return result
    
    elif isinstance(data, list):
        return [_decode_data_from_field_codes(item, code_to_path, sep) for item in data]
    
    else:
        return data
```

**Testing Requirements:**  
- Unit: Dict with code keys → original key names restored  
- Unit: Nested dict → all levels decoded  
- Unit: Code not in map → original code used as key (fallback)  
- Unit: Array of encoded objects → each object decoded

**Acceptance Criteria:**  
- All coded keys replaced with original field names  
- Nested structures handled recursively  
- Fallback to original code when not in map

---

### M-11: Implement `compress_json` Public API

**Description:**  
Implement the public `compress_json(data, config)` function in `compressor.py`. This wires together all helpers in the correct order as described in §2.2.1.

**References:**  
- `doc/json_compression.md` — §2.2.1 (High-Level Steps)  
- `doc/json_compression.md` — §1.2 (output format: `{"schema": ..., "data": ...}`)

**Dependencies:** M-04, M-05, M-06, M-07, M-08

**Implementation Details:**  
```python
from typing import Any, Dict
from .config import CompressionConfig

def compress_json(data: Any, config: CompressionConfig) -> Dict[str, Any]:
    """
    Compress JSON-compatible data using the json_compact scheme.
    
    Pipeline:
    1. Determine original_root_type
    2. Collect logical paths (with filtering)
    3. Build path_to_code map
    4. Encode tabular arrays (if configured)
    5. Encode remaining data with field codes
    6. Build schema object
    7. Return {"schema": schema, "data": encoded_data}
    
    Args:
        data: JSON-compatible Python object (dict or list).
        config: CompressionConfig controlling compression behavior.
    
    Returns:
        Dict with "schema" and "data" keys.
    
    Raises:
        ValueError: If data is not a dict or list.
    """
    if not isinstance(data, (dict, list)):
        raise ValueError(f"compress_json expects dict or list, got {type(data).__name__}")
    
    original_root_type = "array" if isinstance(data, list) else "object"
    sep = config.flatten.path_separator
    
    # Step 1: Collect logical paths
    paths = _collect_logical_fields(data, config)
    
    # Step 2: Build code map (code -> path)
    path_to_code = _build_field_code_map(paths, config.key_mapping)
    # Invert for encoding: path -> code
    path_to_code_inv = {v: k for k, v in path_to_code.items()}
    
    # Step 3: Encode tabular arrays
    encoded_data, tabular_metadata = _encode_tabular_arrays(
        data, path_to_code, config, sep
    )
    
    # Step 4: Encode remaining data with field codes (non-tabular parts)
    # If root was converted to tabular, skip non-tabular encoding of root
    if not (isinstance(data, list) and ("" in config.tabular.array_paths or "[]" in config.tabular.array_paths)):
        encoded_data = _encode_data_with_field_codes(encoded_data, path_to_code_inv, "", sep)
    
    # Step 5: Build schema
    schema = _build_schema_object(original_root_type, config, path_to_code, tabular_metadata)
    
    return {"schema": schema, "data": encoded_data}
```

**Testing Requirements:**  
- Unit: Simple dict → compressed output has `schema` and `data` keys  
- Unit: `schema.version == 1`  
- Unit: `schema.original_root_type` correct  
- Unit: `schema.fields` maps codes to paths  
- Unit: `data` uses short codes as keys  
- Unit: Non-dict/list input → `ValueError`

**Acceptance Criteria:**  
- Returns `{"schema": ..., "data": ...}` for any valid input  
- Schema and data are consistent  
- All helper functions called in correct order

---

### M-12: Implement `decompress_json` Public API

**Description:**  
Implement the public `decompress_json(compressed)` function in `decompressor.py`. This reconstructs the original data from the compressed representation.

**References:**  
- `doc/json_compression.md` — §2.3.1 (High-Level Steps)

**Dependencies:** M-09, M-10

**Implementation Details:**  
```python
from typing import Any, Dict

def decompress_json(compressed: Dict[str, Any]) -> Any:
    """
    Decompress a json_compact compressed object back to original-like data.
    
    Note: If filtering was applied during compression, filtered fields
    are NOT recoverable (lossy filtering).
    
    Args:
        compressed: Dict with "schema" and "data" keys (output of compress_json).
    
    Returns:
        Reconstructed Python object (dict or list).
    
    Raises:
        ValueError: If compressed format is invalid.
    """
    if not isinstance(compressed, dict) or "schema" not in compressed or "data" not in compressed:
        raise ValueError("Invalid compressed format: expected {'schema': ..., 'data': ...}")
    
    schema = compressed["schema"]
    data = compressed["data"]
    
    # Build code_to_path from schema.fields
    code_to_path: Dict[str, str] = schema.get("fields", {})
    sep = schema.get("config", {}).get("flatten", {}).get("path_separator", ".")
    
    # Get tabular metadata
    tabular_metadata = schema.get("structure", {}).get("tabular_arrays", {})
    
    # Step 1: Decode tabular arrays
    decoded = _decode_tabular_arrays(data, code_to_path, tabular_metadata, sep)
    
    # Step 2: Decode field codes in non-tabular parts
    # If root was tabular, skip non-tabular decoding of root
    if not tabular_metadata or ("" not in tabular_metadata and "[]" not in tabular_metadata):
        decoded = _decode_data_from_field_codes(decoded, code_to_path, sep)
    
    return decoded
```

**Testing Requirements:**  
- Unit: `decompress_json(compress_json(data, config))` ≈ original data (for no-filter config)  
- Unit: Invalid input (missing `schema` key) → `ValueError`  
- Unit: Invalid input (not a dict) → `ValueError`  
- Unit: Tabular compressed data → correctly reconstructed

**Acceptance Criteria:**  
- Decompressed data matches original for lossless configs  
- Raises `ValueError` for invalid input  
- Works for both object and array root types

---

### M-13: Implement Round-Trip Tests

**Description:**  
Implement comprehensive round-trip tests for `compress_json` / `decompress_json` in `tests/test_prompt_pipeline/test_json_compression.py`.

**References:**  
- `doc/json_compression.md` — §2.5.1, §2.5.3  
- `doc/json_compression.md` — §5 (examples)

**Dependencies:** M-11, M-12

**Implementation Details:**  
Create `tests/test_prompt_pipeline/test_json_compression.py` with:

```python
import pytest
from prompt_pipeline.compression.json_compression import compress_json, decompress_json
from prompt_pipeline.compression.json_compression.config import (
    CompressionConfig, FilterConfig, FlattenConfig, KeyMappingConfig, TabularConfig
)

# Use the example data from doc/json_compression.md §5.1
SAMPLE_CONCEPTS = [
    {"type": "Actor", "id": "A1", "label": "EndUser", "categories": ["core"],
     "description": "A single person...", "justification": "...",
     "anchors": ["AN1", "AN2"], "sourceConceptIds": ["C1"]},
    {"type": "DataEntity", "id": "DE12", "label": "RecurrencePattern",
     "categories": ["future"], "description": "...", "justification": "...",
     "anchors": ["AN19"], "sourceConceptIds": ["C58"]},
]

class TestRoundTrip:
    def test_simple_dict_identity(self):
        data = {"name": "Alice", "age": 30}
        config = CompressionConfig(key_mapping=KeyMappingConfig(strategy="identity"))
        compressed = compress_json(data, config)
        result = decompress_json(compressed)
        assert result == data
    
    def test_simple_dict_auto_abbrev(self):
        data = {"name": "Alice", "age": 30}
        config = CompressionConfig()
        compressed = compress_json(data, config)
        result = decompress_json(compressed)
        assert result == data
    
    def test_array_of_objects_non_tabular(self):
        config = CompressionConfig()
        compressed = compress_json(SAMPLE_CONCEPTS, config)
        result = decompress_json(compressed)
        assert result == SAMPLE_CONCEPTS
    
    def test_array_of_objects_tabular(self):
        config = CompressionConfig(
            tabular=TabularConfig(enabled=True, array_paths=[""])
        )
        compressed = compress_json(SAMPLE_CONCEPTS, config)
        assert isinstance(compressed["data"], list)
        assert isinstance(compressed["data"][0], list)  # 2D table
        result = decompress_json(compressed)
        assert result == SAMPLE_CONCEPTS
    
    def test_filter_include_paths(self):
        data = {"id": "A1", "label": "User", "description": "long text"}
        config = CompressionConfig(
            filter=FilterConfig(include_paths=["id", "label"])
        )
        compressed = compress_json(data, config)
        result = decompress_json(compressed)
        assert "id" in result
        assert "label" in result
        assert "description" not in result  # filtered out
    
    def test_schema_structure(self):
        data = {"x": 1}
        config = CompressionConfig()
        compressed = compress_json(data, config)
        assert "schema" in compressed
        assert "data" in compressed
        assert compressed["schema"]["version"] == 1
        assert "fields" in compressed["schema"]
    
    def test_deterministic(self):
        data = {"b": 2, "a": 1, "c": 3}
        config = CompressionConfig()
        c1 = compress_json(data, config)
        c2 = compress_json(data, config)
        assert c1 == c2
```

**Testing Requirements:**  
- All test cases above pass  
- Test with actual `json/concepts.json` data (load from file)  
- Test with actual `json/aggregations.json` data

**Acceptance Criteria:**  
- All round-trip tests pass  
- Determinism test passes  
- Filter test confirms lossy behavior

---

### M-14: Implement JsonCompactStrategy (CompressionStrategy Subclass)

**Description:**  
Implement `JsonCompactStrategy` in `prompt_pipeline/compression/json_compression/strategy.py`. This adapts the new `compress_json`/`decompress_json` functions to the existing `CompressionStrategy` interface so it can be registered in `CompressionManager`.

**References:**  
- `prompt_pipeline/compression/strategies/base.py` — `CompressionStrategy` interface  
- `prompt_pipeline/compression/manager.py` — `_register_default_strategies()`  
- `doc/json_compression.md` — §2.4.2 (strategy config pattern)

**Dependencies:** M-11, M-12

**Implementation Details:**  
```python
import json
from typing import Any, Dict, Optional
from prompt_pipeline.compression.strategies.base import (
    CompressionStrategy, CompressionContext, CompressionResult, create_compression_result
)
from .config import CompressionConfig, FilterConfig, FlattenConfig, KeyMappingConfig, TabularConfig
from .compressor import compress_json
from .decompressor import decompress_json
from .yaml_utils import yaml_to_json_dict

class JsonCompactStrategy(CompressionStrategy):
    """
    JSON compact compression strategy.
    
    Converts YAML/JSON data to a compressed JSON representation with:
    - Short field codes (auto_abbrev)
    - Optional tabular encoding for arrays of objects
    - Optional field filtering
    
    The compressed output is a JSON string: {"schema": ..., "data": ...}
    """
    
    @property
    def name(self) -> str:
        return "json_compact"
    
    @property
    def description(self) -> str:
        return "Lossless JSON compaction with short field codes and optional tabular encoding"
    
    def compress(self, content: str, context: CompressionContext) -> CompressionResult:
        """
        Compress YAML or JSON content.
        
        Args:
            content: YAML or JSON string.
            context: CompressionContext; context.extra may contain json_compact config dict.
        
        Returns:
            CompressionResult with compressed JSON string as content.
        """
        # Parse input based on content type
        if context.content_type == "yaml":
            data = yaml_to_json_dict(content)
        else:
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON content: {e}")
        
        # Build CompressionConfig from context.extra
        config = self._build_config_from_context(context)
        
        # Compress
        compressed = compress_json(data, config)
        
        # Serialize to JSON string
        compressed_str = json.dumps(compressed, ensure_ascii=False)
        
        return create_compression_result(
            content=compressed_str,
            original_content=content,
            strategy_name=self.name,
            metadata={"original_root_type": compressed["schema"]["original_root_type"]},
        )
    
    def decompress(self, compressed: str, context: CompressionContext) -> str:
        """Decompress a json_compact compressed string back to JSON."""
        compressed_dict = json.loads(compressed)
        data = decompress_json(compressed_dict)
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    def get_compression_ratio(self) -> float:
        return 0.4  # Typical ratio
    
    def get_supported_content_types(self) -> list:
        return ["yaml", "json"]
    
    def _build_config_from_context(self, context: CompressionContext) -> CompressionConfig:
        """Build CompressionConfig from context.extra dict."""
        extra = context.extra or {}
        compression_cfg = extra.get("compression", {})
        
        filter_cfg = FilterConfig(
            include_paths=compression_cfg.get("filter", {}).get("include_paths", []),
            exclude_paths=compression_cfg.get("filter", {}).get("exclude_paths", []),
        )
        flatten_cfg = FlattenConfig(
            enabled=compression_cfg.get("flatten", {}).get("enabled", False),
            path_separator=compression_cfg.get("flatten", {}).get("path_separator", "."),
        )
        key_mapping_cfg = KeyMappingConfig(
            strategy=compression_cfg.get("key_mapping", {}).get("strategy", "auto_abbrev"),
            min_length=compression_cfg.get("key_mapping", {}).get("min_length", 1),
            max_length=compression_cfg.get("key_mapping", {}).get("max_length", 4),
        )
        tabular_cfg = TabularConfig(
            enabled=compression_cfg.get("tabular", {}).get("enabled", False),
            array_paths=compression_cfg.get("tabular", {}).get("array_paths", []),
        )
        
        return CompressionConfig(
            filter=filter_cfg,
            flatten=flatten_cfg,
            key_mapping=key_mapping_cfg,
            tabular=tabular_cfg,
        )
```

**Testing Requirements:**  
- Unit: `JsonCompactStrategy().name == "json_compact"`  
- Unit: Compress YAML content → valid JSON string output  
- Unit: Compress JSON content → valid JSON string output  
- Unit: Decompress → original data recovered  
- Unit: `get_supported_content_types()` returns `["yaml", "json"]`  
- Integration: Strategy can be registered in `CompressionManager` without error

**Acceptance Criteria:**  
- Strategy implements full `CompressionStrategy` interface  
- Works with both `yaml` and `json` content types  
- Round-trip compress/decompress works

---

### M-15: Register JsonCompactStrategy in CompressionManager

**Description:**  
Register `JsonCompactStrategy` in `CompressionManager._register_default_strategies()` so it is available by name `"json_compact"` throughout the pipeline.

**References:**  
- `prompt_pipeline/compression/manager.py` — `_register_default_strategies()`  
- `prompt_pipeline/compression/__init__.py` — exports

**Dependencies:** M-14

**Implementation Details:**  
1. In `prompt_pipeline/compression/manager.py`, add import:
   ```python
   from prompt_pipeline.compression.json_compression.strategy import JsonCompactStrategy
   ```
2. In `_register_default_strategies()`, add:
   ```python
   JsonCompactStrategy(),
   ```
   to the `strategies` list.
3. In `prompt_pipeline/compression/__init__.py`, add export:
   ```python
   from prompt_pipeline.compression.json_compression.strategy import JsonCompactStrategy
   ```
   and add `"JsonCompactStrategy"` to `__all__`.

**Testing Requirements:**  
- Unit: `CompressionManager().list_strategies()` includes `"json_compact"`  
- Unit: `CompressionManager().get_strategy("json_compact")` returns `JsonCompactStrategy` instance  
- Unit: `CompressionManager().compress(yaml_content, CompressionConfig(strategy="json_compact"), context)` works

**Acceptance Criteria:**  
- `"json_compact"` available in `CompressionManager`  
- No import errors  
- Existing strategies still registered

---

### M-16: Implement YAML Config Parser for json_compact Strategy

**Description:**  
Implement `parse_json_compact_strategy_config(entity_config, strategy_name)` in a new file `prompt_pipeline/compression/json_compression/config_parser.py`. This reads a `data_entities` entry from the pipeline config YAML and returns a `CompressionConfig` and `output_entity` label.

**References:**  
- `doc/json_compression.md` — §2.4.2 (Strategy Config Pattern), §1.3 (authoritative YAML pattern)  
- `configuration/pipeline_config.yaml` — `data_entities` structure

**Dependencies:** M-02

**Implementation Details:**  
```python
from typing import Optional, Tuple
from .config import CompressionConfig, FilterConfig, FlattenConfig, KeyMappingConfig, TabularConfig

def parse_json_compact_strategy_config(
    entity_config: dict,
    strategy_name: str,
) -> Tuple[Optional[CompressionConfig], Optional[str]]:
    """
    Parse a data_entity's compression strategy config into a CompressionConfig.
    
    Args:
        entity_config: The data_entity dict from pipeline_config.yaml.
        strategy_name: The strategy name key under compression_strategies.
    
    Returns:
        Tuple of (CompressionConfig, output_entity_label).
        Returns (None, None) if strategy not found or not json_compact type.
    """
    strategies = entity_config.get("compression_strategies", {})
    strategy_cfg = strategies.get(strategy_name)
    
    if not strategy_cfg:
        return None, None
    
    if strategy_cfg.get("compression_strategy_type") != "json_compact":
        return None, None
    
    output_entity = strategy_cfg.get("output_entity")
    compression = strategy_cfg.get("compression", {})
    
    filter_cfg = FilterConfig(
        include_paths=compression.get("filter", {}).get("include_paths", []),
        exclude_paths=compression.get("filter", {}).get("exclude_paths", []),
    )
    flatten_cfg = FlattenConfig(
        enabled=compression.get("flatten", {}).get("enabled", False),
        path_separator=compression.get("flatten", {}).get("path_separator", "."),
    )
    key_mapping_cfg = KeyMappingConfig(
        strategy=compression.get("key_mapping", {}).get("strategy", "auto_abbrev"),
        min_length=compression.get("key_mapping", {}).get("min_length", 1),
        max_length=compression.get("key_mapping", {}).get("max_length", 4),
    )
    tabular_cfg = TabularConfig(
        enabled=compression.get("tabular", {}).get("enabled", False),
        array_paths=compression.get("tabular", {}).get("array_paths", []),
    )
    
    config = CompressionConfig(
        filter=filter_cfg,
        flatten=flatten_cfg,
        key_mapping=key_mapping_cfg,
        tabular=tabular_cfg,
    )
    
    return config, output_entity
```

**Testing Requirements:**  
- Unit: Valid `json_compact` strategy config → correct `CompressionConfig` returned  
- Unit: Strategy with `compression_strategy_type != "json_compact"` → `(None, None)`  
- Unit: Missing strategy name → `(None, None)`  
- Unit: `output_entity` correctly extracted  
- Unit: Default values used when sub-config keys absent

**Acceptance Criteria:**  
- Function correctly parses all sub-config fields  
- Returns `(None, None)` for non-json_compact strategies  
- Default values match spec

---

### M-17: Update pipeline_config.yaml — Add json_compact Strategies and Compact Entities

**Description:**  
Update `configuration/pipeline_config.yaml` to:
1. Add `minimal_json` compression strategy entries (with `compression_strategy_type: json_compact`) to all affected `data_entities` (`spec`, `concepts`, `aggregations`, `messages`, `message_aggregations`).
2. Add new `*_compact` data entity entries for each compressed output.
3. Remove `compression_params.level` from step inputs that will use `json_compact`.
4. Set `message_aggregations.schema` to `schemas/messageAggregations.schema.json`.

**References:**  
- `doc/json_compression.md` — §1.3 (authoritative YAML pattern), §2.4.2–2.4.3  
- `configuration/pipeline_config.yaml` — current structure  
- Affected entities table at top of this document

**Dependencies:** M-02, CR-03

**Implementation Details:**  

For each affected entity, add a `minimal_json` strategy. Example for `spec`:
```yaml
spec:
  type: yaml
  filename: spec_1.yaml
  yaml_schema: schemas/spec_yaml_schema.json
  compression_strategies:
    none:
      description: "..."
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
    # Keep old strategies for now (will be removed in M-21)
    anchor_index:
      description: "..."
    ...
```

For `concepts`, `aggregations`, `messages` (root-array entities), enable tabular:
```yaml
        tabular:
          enabled: true
          array_paths: [""]
```

Add compact entity definitions:
```yaml
  spec_compact:
    type: json
    filename: spec_1_compact.json
    description: "Compacted JSON version of the spec with schema + data."

  concepts_compact:
    type: json
    filename: concepts_compact.json
    description: "Compacted JSON version of concepts."

  aggregations_compact:
    type: json
    filename: aggregations_compact.json
    description: "Compacted JSON version of aggregations."

  messages_compact:
    type: json
    filename: messages_compact.json
    description: "Compacted JSON version of messages."

  message_aggregations_compact:
    type: json
    filename: messageAggregations_compact.json
    description: "Compacted JSON version of message aggregations."
```

Also update `message_aggregations`:
```yaml
  message_aggregations:
    type: json
    filename: messageAggregations.json
    schema: schemas/messageAggregations.schema.json   # was null
    compression_strategies:
      none:
        description: "Complete JSON message aggregations"
      minimal_json:
        compression_strategy_type: json_compact
        output_entity: message_aggregations_compact
        compression:
          ...
          tabular:
            enabled: true
            array_paths: [""]
```

**Testing Requirements:**  
- Unit: Load updated `pipeline_config.yaml` with `PromptManager` — no errors  
- Unit: `prompt_manager.get_data_entity("spec_compact")` returns correct entity  
- Unit: `parse_json_compact_strategy_config(spec_entity, "minimal_json")` returns valid config  
- Integration: Dry-run of step2 with `minimal_json` compression — no errors

**Acceptance Criteria:**  
- All affected entities have `minimal_json` strategy defined  
- All `*_compact` entities defined  
- `message_aggregations.schema` set  
- Config loads without errors

---

### M-18: Update StepExecutor._load_file_content — YAML→JSON Auto-Conversion

**Description:**  
Update `StepExecutor._load_file_content()` in `prompt_pipeline/step_executor.py` to automatically convert YAML content to JSON when the entity type is `yaml`. This ensures the compression pipeline always receives JSON-compatible data.

**References:**  
- `prompt_pipeline/step_executor.py` — `_load_file_content()` method  
- `doc/json_compression.md` — §2.4.1 (entity type: yaml → convert before compression)  
- `prompt_pipeline/compression/json_compression/yaml_utils.py` — `yaml_to_json_dict()`

**Dependencies:** M-03

**Implementation Details:**  
The current `_load_file_content()` simply reads the file as text. Add an optional `entity_type` parameter and auto-convert when `entity_type == "yaml"`:

```python
def _load_file_content(self, file_path: Path, input_type: str) -> str:
    """Load content from a file, auto-converting YAML to JSON if needed."""
    if not isinstance(file_path, Path):
        file_path = Path(file_path)
    
    if not file_path.exists():
        raise StepExecutionError(f"Input file not found: {file_path}")
    
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        raise StepExecutionError(f"Failed to read input file {file_path}: {e}")
    
    # Auto-convert YAML to JSON for yaml-typed entities
    if input_type == "yaml":
        try:
            from prompt_pipeline.compression.json_compression.yaml_utils import yaml_to_json_dict
            import json
            data = yaml_to_json_dict(content)
            content = json.dumps(data, ensure_ascii=False)
        except ValueError as e:
            raise StepExecutionError(f"Failed to convert YAML to JSON for {file_path}: {e}")
    
    return content
```

**Note:** The `input_type` parameter is already passed to `_load_file_content` in `_resolve_input_content`. Verify the call sites pass the correct type.

**Testing Requirements:**  
- Unit: YAML file with `input_type="yaml"` → returns JSON string  
- Unit: JSON file with `input_type="json"` → returns JSON string unchanged  
- Unit: MD file with `input_type="md"` → returns raw text unchanged  
- Unit: Invalid YAML with `input_type="yaml"` → `StepExecutionError` raised  
- Integration: `_prepare_variables_from_config` with a yaml entity → content is JSON string

**Acceptance Criteria:**  
- YAML entities auto-converted to JSON before compression  
- Non-YAML entities unchanged  
- Error handling for invalid YAML

---

### M-19: Update StepExecutor._apply_compression — Route json_compact

**Description:**  
Update `StepExecutor._apply_compression()` to handle `json_compact` strategy routing. When the compression strategy name is `"minimal_json"` (or any strategy whose `compression_strategy_type` is `json_compact`), resolve the actual strategy config from `data_entities` and pass it to `JsonCompactStrategy` via `context.extra`.

**References:**  
- `prompt_pipeline/step_executor.py` — `_apply_compression()` method  
- `prompt_pipeline/compression/json_compression/config_parser.py` — `parse_json_compact_strategy_config()`  
- `doc/json_compression.md` — §2.4.2

**Dependencies:** M-15, M-16, M-18

**Implementation Details:**  
In `_apply_compression()`, after the existing `"full"/"none"` check, add handling for `json_compact`:

```python
def _apply_compression(self, content, compression, input_type, label=None, compression_params=None):
    # ... existing none/full check ...
    
    # Check if this is a json_compact strategy
    # Look up the entity's strategy config to get compression_strategy_type
    data_entity = self.prompt_manager.get_data_entity(label) if label else None
    strategy_type = None
    json_compact_config = None
    
    if data_entity:
        strategies = data_entity.get("compression_strategies", {})
        strategy_cfg = strategies.get(compression, {})
        strategy_type = strategy_cfg.get("compression_strategy_type")
        if strategy_type == "json_compact":
            json_compact_config = strategy_cfg.get("compression", {})
    
    if strategy_type == "json_compact":
        try:
            manager = CompressionManager()
            config = CompressionConfig(strategy="json_compact", level=1)
            context = {
                "content_type": input_type,
                "label": label or "input",
                "extra": {"compression": json_compact_config or {}}
            }
            result = manager.compress(content, config, context)
            return result.content, {
                "original_length": result.original_length,
                "compressed_length": result.compressed_length,
                "compression_ratio": result.compression_ratio,
                "strategy": "json_compact",
            }
        except Exception as e:
            self._log(f"json_compact compression failed: {e}, using full content")
            return content, {"original_length": len(content), "compressed_length": len(content),
                             "compression_ratio": 1.0, "strategy": "none", "error": str(e)}
    
    # ... existing CompressionManager routing for other strategies ...
```

**Testing Requirements:**  
- Unit: `_apply_compression(yaml_json_content, "minimal_json", "yaml", "spec")` → compressed JSON string  
- Unit: `_apply_compression(json_content, "minimal_json", "json", "concepts")` → compressed JSON string  
- Unit: Unknown strategy → falls through to existing CompressionManager  
- Integration: Full step execution with `minimal_json` compression → prompt contains compressed JSON

**Acceptance Criteria:**  
- `minimal_json` strategy correctly routed to `JsonCompactStrategy`  
- Compression config read from `data_entities` in pipeline config  
- Fallback to full content on error (with logging)

---

### M-20: Update Step Inputs in pipeline_config.yaml — Switch to minimal_json

**Description:**  
Update all affected step inputs in `configuration/pipeline_config.yaml` to use `compression: minimal_json` instead of the old strategy names. Remove `compression_params.level` from these inputs.

**References:**  
- `configuration/pipeline_config.yaml` — `steps` section  
- Affected entities table at top of this document

**Dependencies:** M-17, M-19

**Implementation Details:**  
For each affected step input, change:
```yaml
# BEFORE (step2, spec input):
- label: spec
  source: label:spec
  compression: anchor_index
  color: green

# AFTER:
- label: spec
  source: label:spec
  compression: minimal_json
  color: green
```

Apply to all rows in the affected entities table:
- `step2`: spec → `minimal_json`
- `stepC3`: spec → `minimal_json` (remove `compression_params.level: 3`)
- `stepC4`: spec → `minimal_json`, concepts → `minimal_json`
- `stepC5`: spec → `minimal_json`, concepts → `minimal_json`, aggregations → `minimal_json`
- `stepD1`: spec → `minimal_json`, concepts → `minimal_json`, messages → `minimal_json`

**Testing Requirements:**  
- Integration: Load updated config → no errors  
- Integration: Dry-run of each affected step → no errors  
- Integration: `_apply_compression` called with `"minimal_json"` for each affected input

**Acceptance Criteria:**  
- All affected step inputs use `compression: minimal_json`  
- No `compression_params.level` on json_compact inputs  
- Config loads and validates without errors

---

### M-21: Update StepExecutor._prepare_variables_from_config — Entity Type Resolution

**Description:**  
Ensure `_prepare_variables_from_config()` correctly resolves the entity type (`yaml`, `json`, `md`) from `data_entities` when calling `_load_file_content()` and `_apply_compression()`. Currently `input_type` comes from the step input config's `type` field, but it should fall back to the `data_entities` type when not explicitly set.

**References:**  
- `prompt_pipeline/step_executor.py` — `_prepare_variables_from_config()`, `_resolve_input_content()`  
- `configuration/pipeline_config.yaml` — step inputs do not always have `type` field

**Dependencies:** M-18, M-19

**Implementation Details:**  
In `_prepare_variables_from_config()`, when resolving `input_type`:
```python
# Current: input_type = input_spec.get("type", "text")
# New: fall back to data_entity type
label = input_spec.get("label")
input_type = input_spec.get("type")
if not input_type and label:
    data_entity = self.prompt_manager.get_data_entity(label)
    if data_entity:
        input_type = data_entity.get("type", "text")
input_type = input_type or "text"
```

This ensures YAML entities are correctly identified as `"yaml"` for auto-conversion in `_load_file_content()`.

**Testing Requirements:**  
- Unit: Input spec without `type` field, entity is `yaml` → `input_type` resolved as `"yaml"`  
- Unit: Input spec without `type` field, entity is `json` → `input_type` resolved as `"json"`  
- Unit: Input spec with explicit `type` → explicit type used (not overridden)  
- Integration: `spec` entity (yaml) loaded and converted to JSON correctly

**Acceptance Criteria:**  
- Entity type correctly resolved from `data_entities` when not in step input config  
- YAML entities auto-converted before compression  
- No regression for existing steps

---

### M-22: Remove Old Compression Strategies from yaml/json Entities in Config

**Description:**  
Remove the old content-dependent compression strategy entries (`anchor_index`, `concept_summary`, `hierarchical`, `yaml_as_json`) from `yaml` and `json` typed `data_entities` in `pipeline_config.yaml`. These are replaced by `minimal_json`. Keep `none` strategy on all entities.

**References:**  
- `configuration/pipeline_config.yaml` — `data_entities` compression_strategies  
- Affected entities: `spec`, `concepts`, `aggregations`, `messages`, `message_aggregations`

**Dependencies:** M-20 (step inputs already updated)

**Implementation Details:**  
For each affected entity, remove old strategy entries:
- `spec`: remove `anchor_index`, `schema_only`, `yaml_as_json`, `heirachical` (note: typo in current config)
- `concepts`: remove `concept_summary`
- `aggregations`: remove `concept_summary`
- `messages`: remove `concept_summary`
- Keep `none` on all entities
- Keep `minimal_json` (added in M-17)

**Note:** The old strategy Python files (`anchor_index.py`, `concept_summary.py`, `hierarchical.py`, `yaml_as_json.py`) are **not deleted** at this stage — they may still be used by `nl_spec` (md) or other non-yaml/json entities. Only the config entries are removed.

**Testing Requirements:**  
- Unit: Load updated config → no errors  
- Unit: `get_data_entity("spec")["compression_strategies"]` only has `none` and `minimal_json`  
- Integration: Dry-run all steps → no errors

**Acceptance Criteria:**  
- Old strategy names removed from yaml/json entity configs  
- `none` and `minimal_json` remain  
- No step references old strategy names for yaml/json entities

---

### M-23: Add Tests for YAML Config Parsing of json_compact

**Description:**  
Add tests for `parse_json_compact_strategy_config()` and the full config loading pipeline in `tests/test_prompt_pipeline/test_json_compression_config.py`.

**References:**  
- `prompt_pipeline/compression/json_compression/config_parser.py`  
- `doc/json_compression.md` — §2.5.2

**Dependencies:** M-16, M-17

**Implementation Details:**  
```python
# tests/test_prompt_pipeline/test_json_compression_config.py

import pytest
from prompt_pipeline.compression.json_compression.config_parser import parse_json_compact_strategy_config
from prompt_pipeline.compression.json_compression.config import CompressionConfig

SAMPLE_ENTITY_CONFIG = {
    "type": "yaml",
    "filename": "spec_1.yaml",
    "compression_strategies": {
        "minimal_json": {
            "description": "Lossless JSON compaction",
            "compression_strategy_type": "json_compact",
            "output_entity": "spec_compact",
            "compression": {
                "filter": {"include_paths": [], "exclude_paths": []},
                "flatten": {"enabled": False, "path_separator": "."},
                "key_mapping": {"strategy": "auto_abbrev", "min_length": 1, "max_length": 4},
                "tabular": {"enabled": False, "array_paths": []},
            }
        },
        "none": {"description": "No compression"}
    }
}

class TestParseJsonCompactConfig:
    def test_valid_config_returns_compression_config(self):
        config, output_entity = parse_json_compact_strategy_config(
            SAMPLE_ENTITY_CONFIG, "minimal_json"
        )
        assert isinstance(config, CompressionConfig)
        assert output_entity == "spec_compact"
    
    def test_non_json_compact_returns_none(self):
        config, output_entity = parse_json_compact_strategy_config(
            SAMPLE_ENTITY_CONFIG, "none"
        )
        assert config is None
        assert output_entity is None
    
    def test_missing_strategy_returns_none(self):
        config, output_entity = parse_json_compact_strategy_config(
            SAMPLE_ENTITY_CONFIG, "nonexistent"
        )
        assert config is None
        assert output_entity is None
    
    def test_key_mapping_strategy_parsed(self):
        config, _ = parse_json_compact_strategy_config(SAMPLE_ENTITY_CONFIG, "minimal_json")
        assert config.key_mapping.strategy == "auto_abbrev"
    
    def test_tabular_config_parsed(self):
        entity = dict(SAMPLE_ENTITY_CONFIG)
        entity["compression_strategies"]["minimal_json"]["compression"]["tabular"] = {
            "enabled": True, "array_paths": [""]
        }
        config, _ = parse_json_compact_strategy_config(entity, "minimal_json")
        assert config.tabular.enabled is True
        assert config.tabular.array_paths == [""]
```

**Testing Requirements:**  
- All test cases above pass  
- Test with actual `pipeline_config.yaml` loaded via `PromptManager`

**Acceptance Criteria:**  
- All tests pass  
- Config parser correctly handles all sub-config fields

---

### M-24: Integration Test — Full Step Execution with json_compact

**Description:**  
Add integration tests that verify the full step execution pipeline with `json_compact` compression, from file loading through prompt construction (dry-run, no LLM call).

**References:**  
- `tests/test_prompt_pipeline/test_cli_dry_run.py`  
- `prompt_pipeline/step_executor.py`

**Dependencies:** M-19, M-20, M-21, CR-04

**Implementation Details:**  
Create `tests/test_prompt_pipeline/test_json_compression_integration.py`:

```python
import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

class TestJsonCompactIntegration:
    
    def test_spec_entity_loaded_as_json(self, tmp_path):
        """YAML spec entity is auto-converted to JSON before compression."""
        from prompt_pipeline.step_executor import StepExecutor
        from prompt_pipeline.prompt_manager import PromptManager
        # Use test fixtures
        spec_file = Path("tests/fixtures/valid_spec.yaml")
        # ... setup executor with mock LLM client ...
        # ... call _load_file_content with input_type="yaml" ...
        # ... assert result is valid JSON string ...
    
    def test_minimal_json_compression_applied(self, tmp_path):
        """minimal_json compression produces compressed JSON in prompt."""
        # ... setup executor ...
        # ... call _apply_compression with "minimal_json" strategy ...
        # ... assert result is valid JSON with "schema" and "data" keys ...
    
    def test_concepts_tabular_compression(self, tmp_path):
        """concepts entity with tabular=True produces 2D table in compressed output."""
        import json
        from prompt_pipeline.compression.json_compression import compress_json
        from prompt_pipeline.compression.json_compression.config import (
            CompressionConfig, TabularConfig
        )
        data = [{"id": "C1", "label": "Foo"}, {"id": "C2", "label": "Bar"}]
        config = CompressionConfig(tabular=TabularConfig(enabled=True, array_paths=[""]))
        compressed = compress_json(data, config)
        assert isinstance(compressed["data"], list)
        assert isinstance(compressed["data"][0], list)  # tabular rows
```

**Testing Requirements:**  
- All test cases above pass  
- No LLM API calls made (mock client)  
- Test with actual fixture files

**Acceptance Criteria:**  
- Integration tests pass  
- YAML→JSON conversion verified end-to-end  
- Tabular compression verified for array entities

---

### M-25: Documentation Updates

**Description:**  
Update project documentation to reflect the new `json_compact` compression strategy and the migration from old strategies.

**References:**  
- `README.md` — Compression Strategies table  
- `doc/IMPLEMENTATION_SUMMARY.md` — Compression Strategies section  
- `doc/json_compression.md` — already exists as implementation guide

**Dependencies:** M-20, M-22

**Implementation Details:**  
1. **`README.md`**: Update the compression strategies table to add `json_compact` row and mark old yaml/json strategies as deprecated/removed.
2. **`doc/IMPLEMENTATION_SUMMARY.md`**: Update compression strategies section to describe `json_compact`.
3. **`configuration/pipeline_config.yaml`**: Add inline comments explaining the `minimal_json` strategy pattern.
4. **`doc/IMPLEMENTATION_SUMMARY.md`**: Update "Known Limitations" to remove "No compression for structured data" if present.

**Testing Requirements:**  
- No code tests — documentation review only  
- Verify all strategy names in docs match actual implementation

**Acceptance Criteria:**  
- `json_compact` documented in README  
- Old strategy names for yaml/json entities noted as removed  
- Config comments explain the pattern

---

## SECTION 3: Dependency Graph

```
CR-01 ──────────────────────────────────────────────────────────────────────────────┐
CR-02 (depends: CR-01) ─────────────────────────────────────────────────────────────┤
CR-03 ──────────────────────────────────────────────────────────────────────────────┤
CR-04 ──────────────────────────────────────────────────────────────────────────────┤
CR-05 ──────────────────────────────────────────────────────────────────────────────┘

M-01 ──────────────────────────────────────────────────────────────────────────────┐
M-02 (depends: M-01) ──────────────────────────────────────────────────────────────┤
M-03 (depends: M-01) ──────────────────────────────────────────────────────────────┤
M-04 (depends: M-01, M-02) ────────────────────────────────────────────────────────┤
M-05 (depends: M-01, M-02) ────────────────────────────────────────────────────────┤
M-06 (depends: M-04, M-05) ────────────────────────────────────────────────────────┤
M-07 (depends: M-04, M-05) ────────────────────────────────────────────────────────┤
M-08 (depends: M-04, M-07) ────────────────────────────────────────────────────────┤
M-09 (depends: M-07, M-08) ────────────────────────────────────────────────────────┤
M-10 (depends: M-06, M-09) ────────────────────────────────────────────────────────┤
M-11 (depends: M-04..M-08) ────────────────────────────────────────────────────────┤
M-12 (depends: M-09, M-10) ────────────────────────────────────────────────────────┤
M-13 (depends: M-11, M-12) ────────────────────────────────────────────────────────┤
M-14 (depends: M-11, M-12) ────────────────────────────────────────────────────────┤
M-15 (depends: M-14) ──────────────────────────────────────────────────────────────┤
M-16 (depends: M-02) ──────────────────────────────────────────────────────────────┤
M-17 (depends: M-02, CR-03) ───────────────────────────────────────────────────────┤
M-18 (depends: M-03) ──────────────────────────────────────────────────────────────┤
M-19 (depends: M-15, M-16, M-18) ──────────────────────────────────────────────────┤
M-20 (depends: M-17, M-19) ────────────────────────────────────────────────────────┤
M-21 (depends: M-18, M-19) ────────────────────────────────────────────────────────┤
M-22 (depends: M-20) ──────────────────────────────────────────────────────────────┤
M-23 (depends: M-16, M-17) ────────────────────────────────────────────────────────┤
M-24 (depends: M-19, M-20, M-21, CR-04) ───────────────────────────────────────────┤
M-25 (depends: M-20, M-22) ────────────────────────────────────────────────────────┘
```

---

## SECTION 4: Recommended Execution Order

### Phase 1: Code Review Fixes (Independent, High Value)
1. **CR-03** — Fix messageAggregations schema (no dependencies, unblocks M-17)
2. **CR-01** — Fix JSONValidator base class (no dependencies)
3. **CR-02** — Simplify subclass validators (depends: CR-01)
4. **CR-04** — Fix dry-run prompt display (no dependencies, needed for M-24)
5. **CR-05** — Add `--info` CLI flag (no dependencies)

### Phase 2: Module Foundation
6. **M-01** — Create module structure
7. **M-02** — Implement config dataclasses
8. **M-03** — Implement yaml_to_json_dict

### Phase 3: Core Compression Helpers
9. **M-04** — `_build_field_code_map`
10. **M-05** — `_collect_logical_fields`
11. **M-06** — `_encode_data_with_field_codes`
12. **M-07** — `_encode_tabular_arrays`
13. **M-08** — `_build_schema_object`

### Phase 4: Core Decompression Helpers
14. **M-09** — `_decode_tabular_arrays`
15. **M-10** — `_decode_data_from_field_codes`

### Phase 5: Public API + Tests
16. **M-11** — `compress_json`
17. **M-12** — `decompress_json`
18. **M-13** — Round-trip tests

### Phase 6: Strategy Integration
19. **M-14** — `JsonCompactStrategy`
20. **M-15** — Register in CompressionManager
21. **M-16** — YAML config parser

### Phase 7: Pipeline Integration
22. **M-17** — Update pipeline_config.yaml (add strategies + compact entities)
23. **M-18** — StepExecutor YAML→JSON auto-conversion
24. **M-19** — StepExecutor _apply_compression routing
25. **M-21** — Entity type resolution in _prepare_variables_from_config
26. **M-20** — Switch step inputs to minimal_json
27. **M-23** — Config parsing tests

### Phase 8: Cleanup + Final Tests
28. **M-22** — Remove old strategies from yaml/json entity configs
29. **M-24** — Integration tests
30. **M-25** — Documentation updates

---

## SECTION 5: Ambiguities & Notes for Implementer

1. **`_encode_data_with_field_codes` vs tabular interaction:** When tabular encoding is applied to the root array, the non-tabular encoding step should be skipped for the root. The `compress_json` implementation in M-11 handles this with a conditional check. Verify this logic is correct for nested tabular arrays within a dict.

2. **Path notation for nested arrays:** The current `_collect_logical_fields` spec uses `[].field` for root arrays and `parent[].field` for nested arrays. Ensure `_encode_tabular_arrays` and `_decode_tabular_arrays` use consistent notation.

3. **`message_aggregations` tabular:** The `messageAggregations.json` is an array of objects (each with `id`, `label`, `category`, `members`, etc.). Tabular encoding is appropriate. The `members` field is itself an array — tabular encoding will store it as a nested array value within each row, which is fine.

4. **`spec` entity tabular:** The `spec` entity is a complex nested YAML object (not a flat array). Tabular encoding should be **disabled** for `spec` (`tabular.enabled: false`). Only root-array entities (`concepts`, `aggregations`, `messages`, `message_aggregations`) should use tabular.

5. **`_collect_logical_fields` for deeply nested spec:** The spec YAML has deeply nested structures (sections → text_blocks → anchors). The current `_collect_logical_fields` implementation collects leaf paths. For the spec, this may produce a very large number of paths. Consider whether `include_paths` filtering should be used for spec compression, or whether the default (include all) is acceptable.

6. **Existing `yaml_as_json` strategy:** The existing `YamlAsJsonStrategy` does YAML→JSON conversion without compression. After this migration, it is no longer needed for yaml/json entities. It is kept in the codebase for now (M-22 only removes config entries, not Python files). A future cleanup task can remove the Python files.

7. **`jsonschema` dependency:** Already used in `yaml_schema_validator.py`. Verify it is declared in `pyproject.toml` under `dependencies` (not just dev dependencies).

---

## SECTION 6: Files Modified Summary

| File | Tasks | Change Type |
|------|-------|-------------|
| `prompt_pipeline/compression/json_compression/__init__.py` | M-01 | Create |
| `prompt_pipeline/compression/json_compression/config.py` | M-02 | Create |
| `prompt_pipeline/compression/json_compression/yaml_utils.py` | M-03 | Create |
| `prompt_pipeline/compression/json_compression/compressor.py` | M-04..M-08, M-11 | Create |
| `prompt_pipeline/compression/json_compression/decompressor.py` | M-09, M-10, M-12 | Create |
| `prompt_pipeline/compression/json_compression/strategy.py` | M-14 | Create |
| `prompt_pipeline/compression/json_compression/config_parser.py` | M-16 | Create |
| `prompt_pipeline/compression/manager.py` | M-15 | Modify |
| `prompt_pipeline/compression/__init__.py` | M-15 | Modify |
| `prompt_pipeline/step_executor.py` | M-18, M-19, M-21 | Modify |
| `configuration/pipeline_config.yaml` | M-17, M-20, M-22 | Modify |
| `schemas/messageAggregations.schema.json` | CR-03 | Modify |
| `prompt_pipeline/validation/json_validator.py` | CR-01, CR-02 | Modify |
| `prompt_pipeline_cli/commands/run_step.py` | CR-04, CR-05 | Modify |
| `tests/test_prompt_pipeline/test_json_compression.py` | M-13 | Create |
| `tests/test_prompt_pipeline/test_json_compression_config.py` | M-23 | Create |
| `tests/test_prompt_pipeline/test_json_compression_integration.py` | M-24 | Create |
| `tests/test_prompt_pipeline/test_json_validator.py` | CR-01, CR-02 | Modify |
| `tests/test_prompt_pipeline/test_cli_dry_run.py` | CR-04 | Modify |
| `tests/test_prompt_pipeline/test_run_step_info.py` | CR-05 | Modify |
| `README.md` | M-25 | Modify |
| `doc/IMPLEMENTATION_SUMMARY.md` | M-25 | Modify |

---

*Document generated: 2026-02-26*  
*Based on: `doc/json_compression.md`, `doc/json_validator_review_summary.md`, `doc/json_validator_refactor_proposal.md`, `doc/compression_alignment_report.md`, `BUG_SUMMARY.md`, `developer_todo.md`, `configuration/pipeline_config.yaml`, `prompt_pipeline/step_executor.py`, `prompt_pipeline/compression/manager.py`*