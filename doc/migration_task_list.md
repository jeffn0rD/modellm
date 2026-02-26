# ModelLM: Merged Migration & Code Review Task List

**Version:** 2.0  
**Date:** 2026-02-26  
**Scope:** JSON Compression Migration + Code Review Improvements (full)  
**Intended Consumer:** LLM agent performing autonomous implementation  
**Source Review Documents:** `code_review_tasks.md`, `code_review_comprehensive.md`, `doc/json_validator_review_summary.md`, `doc/json_validator_refactor_proposal.md`, `doc/compression_alignment_report.md`, `BUG_SUMMARY.md`, `developer_todo.md`

---

## Overview

This document merges three work streams:

1. **JSON Compression Migration (M-series):** Replace content-dependent compression strategies (`anchor_index`, `concept_summary`, `hierarchical`) for `yaml`/`json` typed data entities with a new `json_compact` strategy using the pipeline `(YAML→)JSON → COMPRESSED → PROMPT`. Markdown/NL entities (`md`, `text`) are **not affected** — they pass through as-is.

2. **Validator & Schema Fixes (CR-01..CR-05):** Fixes identified in `doc/json_validator_review_summary.md`, `doc/json_validator_refactor_proposal.md`, `BUG_SUMMARY.md`, and `developer_todo.md`.

3. **Full Code Review Improvements (CR-06..CR-20):** Security, reliability, testing, refactoring, and performance improvements from `code_review_tasks.md` and `code_review_comprehensive.md`.

**Execution order:** CR tasks that are prerequisites to M tasks are listed first. Within each series, tasks are ordered by priority and dependency.

---

## Key Architectural Decisions (from prior session)

| # | Decision | Resolution |
|---|----------|------------|
| 1 | `compression_params.level` on yaml/json entities using `json_compact` | **Remove** — `json_compact` has its own `compression:` block; `level` is not applicable |
| 2 | Backward compatibility for old strategy names on yaml/json entities | **Migrate directly** — not in production; old strategies removed from yaml/json entities |
| 3 | `message_aggregations` schema | **Add `json_compact`** — use `schemas/messageAggregations.schema.json` (needs array wrapper — see CR-03) |
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

---

### CR-01: Fix JSONValidator Base Class — Use jsonschema Library

**Priority:** High  
**File:** `prompt_pipeline/validation/json_validator.py` — `_validate_schema()` (lines 78–95)

**Description:**  
The `JSONValidator` base class implements custom validation logic instead of using the `jsonschema` library. The `_validate_schema()` method only checks basic type (array vs object) and ignores all schema constraints (required fields, patterns, enums, additionalProperties). Refactor to use `jsonschema.validate()`.

**References:**  
- `doc/json_validator_review_summary.md` — Priority 2  
- `doc/json_validator_refactor_proposal.md` — Section 2

**Dependencies:** None

**Implementation Details:**  
Replace the body of `JSONValidator._validate_schema()`:
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
Add `import jsonschema` at top if not present. Note: `jsonschema>=4.17.0` is already declared in `pyproject.toml`.

**Testing Requirements:**  
- Unit: Valid concepts array passes schema validation  
- Unit: Wrong `type` enum value fails with schema error message  
- Unit: Missing required field fails with schema error message  
- Unit: `schema_path=""` (disabled) still works — no crash  
- Edge cases: `data=None`, empty array `[]`, schema file not found

**Acceptance Criteria:**  
- `jsonschema.validate()` called when `self.schema` is set  
- Schema errors produce meaningful messages  
- All existing passing tests continue to pass

---

### CR-02: Simplify Subclass Validators — Remove Hardcoded Logic

**Priority:** High  
**File:** `prompt_pipeline/validation/json_validator.py` — lines 120–327

**Description:**  
`ConceptsValidator`, `AggregationsValidator`, `MessagesValidator`, and `RequirementsValidator` contain hardcoded ID patterns, required field lists, and enum values that duplicate what is already in the schema files. Since CR-01 makes the base class schema-driven, remove all custom validation logic from subclasses.

**References:**  
- `doc/json_validator_refactor_proposal.md` — Section 3  
- `schemas/concepts.schema.json`, `schemas/aggregations.schema.json`, `schemas/messages.schema.json`, `schemas/requirements.schema.json`

**Dependencies:** CR-01

**Implementation Details:**  
For each subclass: remove hardcoded `VALID_TYPES`, `REQUIRED_FIELDS`, `VALID_CATEGORIES`, regex patterns, and custom `_validate_*()` methods. Each subclass `validate()` should delegate to `super().validate()`. Keep `DEFAULT_SCHEMA_FILE` class attribute. Keep module-level convenience functions (`validate_concepts()`, etc.).

**Testing Requirements:**  
- Unit: Update `tests/test_prompt_pipeline/test_json_validator.py` — replace custom-message assertions with schema-error assertions  
- Unit: Test each validator with invalid enum, missing field, wrong type — all produce schema errors  
- Edge cases: Empty array `[]` passes; null items fail

**Acceptance Criteria:**  
- No hardcoded patterns or field lists in subclasses  
- All validation driven by schema files  
- Tests pass using real schema files

---

### CR-03: Fix messageAggregations Schema — Wrap as Array

**Priority:** High  
**File:** `schemas/messageAggregations.schema.json`

**Description:**  
`schemas/messageAggregations.schema.json` currently defines a single object (`"type": "object"`), but the pipeline output `messageAggregations.json` is an array of such objects. Update the schema to wrap the object definition in an array schema with `items`.

**References:**  
- `doc/json_validator_review_summary.md` — Priority 1  
- `schemas/aggregations.schema.json` (reference pattern — already correct)

**Dependencies:** None

**Implementation Details:**  
Wrap existing `required`, `properties`, `additionalProperties` inside `"items"`:
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
Also update `pipeline_config.yaml`: set `message_aggregations.schema` to `schemas/messageAggregations.schema.json` (currently `schema: null`).

**Testing Requirements:**  
- Unit: Validate `json/messageAggregations.json` against updated schema — passes  
- Unit: Single object (not array) against schema — fails  
- Unit: Array with missing required field — fails

**Acceptance Criteria:**  
- `messageAggregations.schema.json` uses `"type": "array"` at root  
- `pipeline_config.yaml` `message_aggregations.schema` is set  
- `json/messageAggregations.json` validates successfully

---

### CR-04: Fix dry-run to Show Full Prompt Construction

**Priority:** High  
**File:** `prompt_pipeline_cli/commands/run_step.py` — lines 134–158

**Description:**  
The `--dry-run` flag returns early before prompt construction, so it never shows the substituted prompt. Fix it to build the complete prompt (preamble + prompt file + substituted variables) and display it, without making any LLM API calls.

**References:**  
- `BUG_SUMMARY.md` — full description

**Dependencies:** None

**Implementation Details:**  
Instead of early return, continue to: load step config, resolve inputs, build full prompt via `prompt_manager.get_prompt_with_variables()`, display prompt and compression metrics, print `[DRY RUN] No API call will be made`, return without calling `llm_client.call_prompt_async()`. Cleanest approach: pass `dry_run=True` into `StepExecutor.execute_step()` and skip only the LLM call + file write.

**Testing Requirements:**  
- Integration: `test_dry_run_shows_prompt()` — prompt content appears in stdout; no API call markers  
- Integration: `test_dry_run_no_output_file()` — no output file created  
- Integration: `test_dry_run_shows_compression_metrics()` — compression metrics appear when configured  
- Edge cases: Missing input file in dry-run shows error (not silent crash)

**Acceptance Criteria:**  
- `--dry-run` displays full substituted prompt  
- `--dry-run` makes no LLM API calls  
- `--dry-run` creates no output files  
- Existing dry-run tests continue to pass

---

### CR-05: Add `run-step --info` CLI Command

**Priority:** High  
**File:** `prompt_pipeline_cli/commands/run_step.py`

**Description:**  
Add a `--info` flag to `run-step` that outputs the requirements for a given step: inputs (labels, sources, compression), outputs (labels, filenames), prompt file, persona, validation config, model levels. Listed in `developer_todo.md` as the next task.

**References:**  
- `developer_todo.md` — "need a CLI command/switch that outputs the requirements for a given step"  
- `tests/test_prompt_pipeline/test_run_step_info.py` (test file already exists — implement to satisfy it)

**Dependencies:** None

**Implementation Details:**  
Add `--info` Click flag. When set: load step config via `prompt_manager.get_step_config(step_name)`, display all inputs/outputs/prompt file/persona/validation/model levels using `print_header`/`print_info`, return without executing the step.

**Testing Requirements:**  
- Unit/Integration: `test_run_step_info.py` — inputs, outputs, prompt file, compression, no API call  
- Edge cases: Invalid step name with `--info` shows clear error

**Acceptance Criteria:**  
- `prompt-pipeline run-step stepC3 --info` prints step requirements  
- No API call made  
- Tests in `test_run_step_info.py` pass

---

### CR-06: Fix Path Traversal Vulnerability in CLI Input Parsing

**Priority:** Critical (Security)  
**File:** `prompt_pipeline_cli/commands/run_pipeline.py` — `_parse_input_file_option()` (lines 20–50)

**Description:**  
File paths from user input (`--input-file label:filename`) are not validated for path traversal attacks. A user could pass `../../etc/passwd` or similar. This is a security vulnerability.

**References:**  
- `code_review_tasks.md` — Task 1.1  
- `code_review_comprehensive.md` — §5.1 (Insufficient Input Validation)

**Dependencies:** CR-09 (uses `validate_file_path` from shared file utils — implement CR-09 first, or inline the validation here)

**Implementation Details:**  
Add a `validate_file_path()` function (or import from `file_utils.py` once CR-09 is done):
```python
def validate_file_path(filename: str, allowed_base_dir: Path) -> Path:
    """Validate file path is within allowed directory."""
    try:
        path = Path(filename).resolve()
        base_dir = allowed_base_dir.resolve()
        path.relative_to(base_dir)  # raises ValueError if outside
        if '..' in str(path):
            raise ValueError(f"Path '{filename}' contains parent directory references")
        return path
    except ValueError as e:
        raise ValueError(f"Invalid file path '{filename}': {e}")
```
Update `_parse_input_file_option()` to call validation when `allowed_base_dir` is available (use `Path.cwd()` as the base). Apply the same validation in `run_step.py` wherever `--input-file` is parsed.

**Testing Requirements:**  
- Unit: Valid path within cwd → accepted  
- Unit: Path with `../` → `ValueError` raised  
- Unit: Absolute path outside cwd → `ValueError` raised  
- Unit: Normal relative path → accepted  
- Edge cases: Symlinks, Windows-style paths

**Acceptance Criteria:**  
- Path traversal attempts raise `ValueError` with clear message  
- Valid paths continue to work  
- No regression in existing CLI tests

---

### CR-07: Secure API Key Handling in OpenRouterClient

**Priority:** Critical (Security)  
**File:** `prompt_pipeline/llm_client.py` — `OpenRouterClient.__init__()` (lines 50–70)

**Description:**  
The API key is stored as `self.api_key` (public attribute) and could be exposed in error messages, logs, or `repr()` output. Store it as a private attribute and implement `__str__`/`__repr__` that mask it.

**References:**  
- `code_review_tasks.md` — Task 1.2  
- `code_review_comprehensive.md` — §5.1 (API Key Exposure)

**Dependencies:** None

**Implementation Details:**  
1. Change `self.api_key = ...` to `self._api_key = ...` in `__init__`.  
2. Add a read-only property for internal use:
   ```python
   @property
   def api_key(self) -> str:
       """Get API key (for internal use only)."""
       return self._api_key
   ```
3. Implement safe `__str__` and `__repr__`:
   ```python
   def __str__(self) -> str:
       return f"OpenRouterClient(model={self.default_model}, timeout={self.timeout})"
   def __repr__(self) -> str:
       return self.__str__()
   ```
4. Update all internal references from `self.api_key` to `self._api_key` in the request headers construction.

**Testing Requirements:**  
- Unit: `str(client)` does not contain the API key  
- Unit: `repr(client)` does not contain the API key  
- Unit: Client still makes successful API calls (key used internally)  
- Edge cases: `api_key=None` raises `ValueError` with message that does NOT include the key value

**Acceptance Criteria:**  
- API key never appears in `str()`, `repr()`, or log output  
- All internal uses updated to `self._api_key`  
- Existing LLM client tests pass

---

### CR-08: Fix Silent Failures in File Write Operations

**Priority:** Critical (Reliability)  
**File:** `prompt_pipeline/step_executor.py` — `_save_outputs()` (lines 440–500) and inline `output_path.write_text()` calls in `execute_step()`

**Description:**  
File write operations use bare `write_text()` calls with no error handling for disk full, permission denied, or other I/O errors. A failed write silently corrupts the pipeline output. Add a `_write_file_safely()` method with comprehensive error handling and atomic writes.

**References:**  
- `code_review_tasks.md` — Task 1.3  
- `code_review_comprehensive.md` — §2.3 (Silent Failures in File Operations), §3.2 (Unclosed File Handles)

**Dependencies:** CR-09 (can use `write_file_content()` from file_utils once available, or implement inline first)

**Implementation Details:**  
Add to `StepExecutor`:
```python
def _write_file_safely(self, file_path: Path, content: str) -> None:
    """Write content to file with comprehensive error handling and atomic write."""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write: temp file + rename
        temp_path = file_path.with_suffix(file_path.suffix + '.tmp')
        temp_path.write_text(content, encoding='utf-8')
        temp_path.replace(file_path)
    except PermissionError as e:
        raise StepExecutionError(f"Permission denied writing to {file_path}: {e}")
    except OSError as e:
        raise StepExecutionError(f"OS error writing to {file_path}: {e}")
    except Exception as e:
        raise StepExecutionError(f"Unexpected error writing to {file_path}: {e}")
```
Replace all bare `output_path.write_text(...)` calls in `execute_step()` and `_save_outputs()` with `self._write_file_safely(output_path, content)`.

**Testing Requirements:**  
- Unit: Successful write → file exists with correct content  
- Unit: `PermissionError` → `StepExecutionError` raised with clear message  
- Unit: `OSError` (disk full simulation) → `StepExecutionError` raised  
- Unit: Atomic write — temp file cleaned up on success  
- Edge cases: Parent directory does not exist → created automatically

**Acceptance Criteria:**  
- All file writes use `_write_file_safely()`  
- `StepExecutionError` raised (not silent) on write failure  
- Atomic write prevents partial file corruption

---

### CR-09: Create Shared File Utilities Module

**Priority:** High (Code Quality)  
**File:** `prompt_pipeline/file_utils.py` (new file)

**Description:**  
File loading logic is duplicated in `step_executor.py`, `tag_replacement.py`, and other places with slight variations in error handling. Create a shared `file_utils.py` module with `load_file_content()`, `write_file_content()`, and `validate_file_path()` functions. This also provides the path validation needed by CR-06 and the safe write needed by CR-08.

**References:**  
- `code_review_tasks.md` — Task 3.3  
- `code_review_comprehensive.md` — §1.4 (Duplicate File Loading Logic)

**Dependencies:** CR-10 (uses `FileOperationError` from centralized exceptions — implement CR-10 first, or use `StepExecutionError` as interim)

**Implementation Details:**  
Create `prompt_pipeline/file_utils.py` with:
```python
"""Shared file utility functions for prompt pipeline."""
from pathlib import Path
from typing import Optional

def load_file_content(
    file_path: Path,
    encoding: str = "utf-8",
    allow_empty: bool = False,
) -> str:
    """Load content from a file with comprehensive error handling."""
    if not isinstance(file_path, Path):
        file_path = Path(file_path)
    if not file_path.exists():
        raise FileOperationError(f"File not found: {file_path}", file_path=file_path)
    if not file_path.is_file():
        raise FileOperationError(f"Path is not a file: {file_path}", file_path=file_path)
    try:
        content = file_path.read_text(encoding=encoding)
    except PermissionError:
        raise FileOperationError(f"Permission denied: {file_path}", file_path=file_path)
    except UnicodeDecodeError as e:
        raise FileOperationError(f"Encoding error reading {file_path}: {e}", file_path=file_path)
    except Exception as e:
        raise FileOperationError(f"Error reading {file_path}: {e}", file_path=file_path)
    if not allow_empty and not content.strip():
        raise FileOperationError(f"File is empty: {file_path}", file_path=file_path)
    return content

def write_file_content(
    file_path: Path,
    content: str,
    encoding: str = "utf-8",
    create_parents: bool = True,
    atomic: bool = True,
) -> None:
    """Write content to a file with comprehensive error handling."""
    # ... (atomic write via temp file + rename, same pattern as CR-08)

def validate_file_path(
    file_path: Path,
    allowed_base_dir: Optional[Path] = None,
    must_exist: bool = False,
) -> Path:
    """Validate a file path for security and correctness."""
    # ... (path traversal check + allowed_base_dir check)
```
Update `step_executor._load_file_content()` and `tag_replacement._load_file_content()` to use `load_file_content()` from this module.

**Testing Requirements:**  
- Unit: `load_file_content` — file not found, permission denied, empty file, encoding error  
- Unit: `write_file_content` — success, permission denied, OS error, atomic write  
- Unit: `validate_file_path` — path traversal rejected, outside base dir rejected, valid path accepted  
- Integration: `step_executor._load_file_content()` uses the shared utility

**Acceptance Criteria:**  
- `prompt_pipeline/file_utils.py` created with all three functions  
- `step_executor.py` and `tag_replacement.py` updated to use shared utilities  
- No duplicate file loading logic remains

---

### CR-10: Create Centralized Exception Module

**Priority:** High (Code Quality)  
**File:** `prompt_pipeline/exceptions.py` (new file)

**Description:**  
Error handling is inconsistent across the codebase. `StepExecutionError` is defined in `step_executor.py`, `LLMCallError` in `llm_client.py`, and various built-in exceptions are raised elsewhere. Create a centralized `exceptions.py` with a proper hierarchy so all modules import from one place.

**References:**  
- `code_review_tasks.md` — Task 3.1  
- `code_review_comprehensive.md` — §1.3 (Inconsistent Error Handling Patterns)

**Dependencies:** None

**Implementation Details:**  
Create `prompt_pipeline/exceptions.py`:
```python
"""Centralized exception definitions for prompt pipeline."""
from pathlib import Path
from typing import Optional, List

class PromptPipelineError(Exception):
    """Base exception for all prompt pipeline errors."""
    pass

class ConfigurationError(PromptPipelineError):
    """Raised when configuration is invalid or missing."""
    pass

class StepExecutionError(PromptPipelineError):
    """Raised when a step execution fails."""
    def __init__(self, message: str, step_name: Optional[str] = None,
                 errors: Optional[List[str]] = None, warnings: Optional[List[str]] = None):
        super().__init__(message)
        self.step_name = step_name
        self.errors = errors or []
        self.warnings = warnings or []

class ValidationError(PromptPipelineError):
    """Raised when validation fails."""
    def __init__(self, message: str, validation_errors: Optional[List[str]] = None):
        super().__init__(message)
        self.validation_errors = validation_errors or []

class FileOperationError(PromptPipelineError):
    """Raised when file operations fail."""
    def __init__(self, message: str, file_path: Optional[Path] = None):
        super().__init__(message)
        self.file_path = file_path

class LLMClientError(PromptPipelineError):
    """Raised when LLM client operations fail."""
    def __init__(self, message: str, retry_count: int = 0, last_status_code: Optional[int] = None):
        super().__init__(message)
        self.retry_count = retry_count
        self.last_status_code = last_status_code

class CompressionError(PromptPipelineError):
    """Raised when compression operations fail."""
    pass

class InputResolutionError(PromptPipelineError):
    """Raised when input resolution fails."""
    def __init__(self, message: str, label: Optional[str] = None, source: Optional[str] = None):
        super().__init__(message)
        self.label = label
        self.source = source
```
Update imports across codebase:
- `step_executor.py`: import `StepExecutionError` from `exceptions.py` (remove local definition)
- `llm_client.py`: replace `LLMCallError` with `LLMClientError` from `exceptions.py`
- `file_utils.py` (CR-09): import `FileOperationError` from `exceptions.py`

**Testing Requirements:**  
- Unit: Each exception class instantiates correctly with all parameters  
- Unit: All exceptions are subclasses of `PromptPipelineError`  
- Unit: Existing code that catches `StepExecutionError` still works after import change  
- Integration: No import errors after updating all modules

**Acceptance Criteria:**  
- `prompt_pipeline/exceptions.py` created with full hierarchy  
- `StepExecutionError` imported from `exceptions.py` in `step_executor.py`  
- `LLMCallError`/`LLMClientError` unified in `exceptions.py`  
- No duplicate exception class definitions remain

---

### CR-11: Fix Null/None Checks for JSON Extraction

**Priority:** High (Reliability)  
**File:** `prompt_pipeline/step_executor.py` — `_extract_json_from_response()` and `_convert_response_if_needed()`

**Description:**  
`_extract_json_from_response()` can return `None` but the `json` output type branch in `_convert_response_if_needed()` only checks `if extracted_json:` and falls through without raising an error when `None` is returned. This causes silent failures where an empty/invalid response is saved as the output file.

**References:**  
- `code_review_tasks.md` — Task 1.4  
- `code_review_comprehensive.md` — §2.1 (Missing Null/None Checks)

**Dependencies:** CR-10 (uses `StepExecutionError` from centralized exceptions)

**Implementation Details:**  
1. Update return type annotation: `def _extract_json_from_response(...) -> Optional[str]:`  
2. In `_convert_response_if_needed()`, for `output_type == 'json'`:
   ```python
   if output_type == 'json':
       extracted_json = self._extract_json_from_response(response, output_label)
       if extracted_json is None:
           raise StepExecutionError(
               f"Failed to extract valid JSON from LLM response for '{output_label}'. "
               f"Response length: {len(response)} chars.",
               errors=["No valid JSON found in LLM response"]
           )
       return extracted_json
   ```
3. Add `self._log(f"Warning: Could not extract JSON from response for '{output_label}'")` before raising.

**Testing Requirements:**  
- Unit: Response with valid JSON → extracted correctly  
- Unit: Response with no JSON → `StepExecutionError` raised  
- Unit: Response with JSON after reasoning text → JSON extracted  
- Unit: `None` return from `_extract_json_from_response` → exception raised in caller  
- Edge cases: Empty response string, response with only whitespace

**Acceptance Criteria:**  
- `_extract_json_from_response` return type is `Optional[str]`  
- All callers handle `None` explicitly  
- `StepExecutionError` raised (not silent) when JSON extraction fails for json-typed outputs

---

### CR-12: Add Unit Tests for StepExecutor

**Priority:** Critical (Testing)  
**File:** `tests/test_prompt_pipeline/test_step_executor.py` (new file)

**Description:**  
`StepExecutor` is the most critical component in the pipeline and has no unit tests. Add comprehensive unit tests covering success paths, error conditions, and edge cases.

**References:**  
- `code_review_tasks.md` — Task 2.1  
- `code_review_comprehensive.md` — §6.1 (Limited Unit Test Coverage)

**Dependencies:** CR-08, CR-11 (tests should verify the fixed behaviors)

**Implementation Details:**  
Create `tests/test_prompt_pipeline/test_step_executor.py`:
```python
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from prompt_pipeline.step_executor import StepExecutor, StepExecutionError

@pytest.mark.unit
class TestStepExecutor:

    @pytest.fixture
    def mock_llm_client(self):
        client = Mock()
        client.call_prompt_async = AsyncMock(return_value='{"result": "test"}')
        return client

    @pytest.fixture
    def mock_prompt_manager(self):
        manager = Mock()
        manager.get_step_config.return_value = {
            "name": "test_step",
            "prompt_file": "test.md",
            "inputs": [{"label": "input1", "source": "cli", "compression": "none"}],
            "outputs": [{"label": "test_output"}],
            "validation": {"enabled": False},
        }
        manager.get_prompt_with_variables.return_value = "Test prompt with input1"
        manager.get_data_entity.return_value = {"filename": "test_output.json", "type": "json"}
        manager.steps_config = {"model_levels": {}}
        return manager

    @pytest.fixture
    def executor(self, mock_llm_client, mock_prompt_manager, tmp_path):
        return StepExecutor(
            llm_client=mock_llm_client,
            prompt_manager=mock_prompt_manager,
            output_dir=tmp_path,
            model_level=1,
            skip_validation=True,
            verbose=False,
        )

    @pytest.mark.asyncio
    async def test_execute_step_success(self, executor, tmp_path):
        """Test successful step execution creates output file."""
        result = await executor.execute_step(
            step_name="test_step",
            cli_inputs={"input1": "test value"},
        )
        assert "test_output" in result
        assert result["test_output"].exists()

    @pytest.mark.asyncio
    async def test_execute_step_missing_input_raises(self, executor):
        """Test step execution with missing required input raises StepExecutionError."""
        with pytest.raises(StepExecutionError, match="Missing required input"):
            await executor.execute_step(step_name="test_step", cli_inputs={})

    @pytest.mark.asyncio
    async def test_execute_step_unknown_step_raises(self, executor, mock_prompt_manager):
        """Test step execution with unknown step name raises StepExecutionError."""
        mock_prompt_manager.get_step_config.return_value = None
        with pytest.raises(StepExecutionError, match="not found in configuration"):
            await executor.execute_step(step_name="nonexistent_step")

    @pytest.mark.asyncio
    async def test_execute_step_llm_failure_propagates(self, executor, mock_llm_client):
        """Test LLM call failure propagates as exception."""
        mock_llm_client.call_prompt_async.side_effect = Exception("LLM API error")
        with pytest.raises(Exception, match="LLM API error"):
            await executor.execute_step(step_name="test_step", cli_inputs={"input1": "v"})

    def test_write_file_safely_success(self, executor, tmp_path):
        """Test safe file write creates file with correct content."""
        path = tmp_path / "test.json"
        executor._write_file_safely(path, '{"key": "value"}')
        assert path.exists()
        assert path.read_text() == '{"key": "value"}'

    def test_write_file_safely_creates_parents(self, executor, tmp_path):
        """Test safe file write creates parent directories."""
        path = tmp_path / "subdir" / "nested" / "test.json"
        executor._write_file_safely(path, "content")
        assert path.exists()

    def test_load_file_content_missing_file_raises(self, executor, tmp_path):
        """Test loading missing file raises StepExecutionError."""
        with pytest.raises(StepExecutionError, match="not found"):
            executor._load_file_content(tmp_path / "nonexistent.yaml", "yaml")

    def test_extract_json_from_response_valid(self, executor):
        """Test JSON extraction from clean JSON response."""
        result = executor._extract_json_from_response('{"key": "value"}', "output")
        assert result == '{"key": "value"}'

    def test_extract_json_from_response_with_preamble(self, executor):
        """Test JSON extraction from response with reasoning preamble."""
        response = "Some reasoning...\n**Part 2 – Final JSON**:\n{&quot;key&quot;: &quot;value&quot;}"
        result = executor._extract_json_from_response(response, "output")
        assert result is not None
        import json
        assert json.loads(result) == {"key": "value"}

    def test_extract_json_from_response_no_json_returns_none(self, executor):
        """Test JSON extraction returns None when no JSON found."""
        result = executor._extract_json_from_response("No JSON here at all.", "output")
        assert result is None

    @pytest.mark.asyncio
    async def test_force_mode_substitutes_empty_for_missing(self, executor, mock_llm_client):
        """Test force mode substitutes empty string for missing inputs."""
        executor.force = True
        # Should not raise even with missing input
        result = await executor.execute_step(step_name="test_step", cli_inputs={})
        assert "test_output" in result
```

**Testing Requirements:**  
- All test cases above pass  
- Add tests for: multiple outputs, compression applied, validation triggered, yaml output conversion  
- Use `@pytest.mark.asyncio` for async tests  
- Use `tmp_path` fixture for file operations

**Acceptance Criteria:**  
- `test_step_executor.py` created with ≥12 test cases  
- All tests pass with `pytest tests/test_prompt_pipeline/test_step_executor.py -v`  
- Tests cover success, error, and edge cases

---

### CR-13: Add Unit Tests for Orchestrator

**Priority:** Critical (Testing)  
**File:** `tests/test_prompt_pipeline/test_orchestrator.py` (new file)

**Description:**  
`PipelineOrchestrator` is a critical component with no unit tests. Add comprehensive unit tests covering pipeline execution, step ordering, dependency resolution, and failure handling.

**References:**  
- `code_review_tasks.md` — Task 2.2  
- `code_review_comprehensive.md` — §6.1

**Dependencies:** CR-12 (establishes test patterns)

**Implementation Details:**  
Create `tests/test_prompt_pipeline/test_orchestrator.py`:
```python
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from prompt_pipeline.orchestrator import PipelineOrchestrator

@pytest.mark.unit
class TestPipelineOrchestrator:

    @pytest.fixture
    def mock_step_executor(self):
        executor = Mock()
        executor.execute_step = AsyncMock(return_value={"output": Path("test.json")})
        return executor

    @pytest.fixture
    def mock_prompt_manager(self):
        manager = Mock()
        manager.get_all_steps.return_value = [
            {"name": "step1", "order": 1, "dependencies": [], "inputs": [], "outputs": [{"label": "spec"}]},
            {"name": "stepC3", "order": 2, "dependencies": ["step1"], "inputs": [], "outputs": [{"label": "concepts"}]},
        ]
        manager.steps_config = {"steps": {}}
        return manager

    @pytest.mark.asyncio
    async def test_steps_executed_in_order(self, mock_step_executor, mock_prompt_manager, tmp_path):
        """Test steps are executed in dependency order."""
        call_order = []
        async def track_calls(step_name, **kwargs):
            call_order.append(step_name)
            return {step_name + "_out": tmp_path / f"{step_name}.json"}
        mock_step_executor.execute_step.side_effect = track_calls
        # ... orchestrator setup and run ...
        assert call_order.index("step1") < call_order.index("stepC3")

    @pytest.mark.asyncio
    async def test_step_failure_stops_pipeline(self, mock_step_executor, mock_prompt_manager, tmp_path):
        """Test that a step failure stops the pipeline."""
        mock_step_executor.execute_step.side_effect = Exception("Step failed")
        # ... orchestrator setup ...
        with pytest.raises(Exception, match="Step failed"):
            pass  # run pipeline

    # Add tests for: label registry updates, skip_steps, output collection
```

**Testing Requirements:**  
- Tests for: step ordering, dependency resolution, step failure propagation, label registry updates, skip_steps functionality  
- Use mocked `StepExecutor` to avoid LLM calls

**Acceptance Criteria:**  
- `test_orchestrator.py` created with ≥8 test cases  
- All tests pass  
- Tests cover ordering, failure, and dependency scenarios

---

### CR-14: Add Pipeline Integration Tests

**Priority:** Critical (Testing)  
**File:** `tests/test_prompt_pipeline/test_pipeline_integration.py` (new file)

**Description:**  
No integration tests exist for end-to-end pipeline execution. Add integration tests that verify the complete pipeline flow using mocked LLM responses, covering file I/O, compression, validation, and output generation.

**References:**  
- `code_review_tasks.md` — Task 2.3  
- `code_review_comprehensive.md` — §6.1 (Missing Integration Tests)

**Dependencies:** CR-12, CR-13

**Implementation Details:**  
Create `tests/test_prompt_pipeline/test_pipeline_integration.py`:
```python
import pytest
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

@pytest.mark.integration
class TestPipelineIntegration:

    @pytest.fixture
    def sample_nl_spec(self, tmp_path):
        spec = tmp_path / "spec.md"
        spec.write_text("# Test App\n\nGoal: Test the pipeline.\n")
        return spec

    @pytest.fixture
    def mock_llm_response_concepts(self):
        return json.dumps([
            {"type": "Actor", "id": "A1", "label": "User",
             "description": "A test user", "categories": ["core"]}
        ])

    @pytest.mark.asyncio
    async def test_single_step_end_to_end(self, tmp_path, sample_nl_spec):
        """Test single step execution from file input to output file."""
        from prompt_pipeline.step_executor import StepExecutor
        from prompt_pipeline.prompt_manager import PromptManager
        from unittest.mock import Mock, AsyncMock
        # ... setup with mocked LLM, real PromptManager, real config ...
        # ... verify output file created and contains valid JSON ...

    @pytest.mark.asyncio
    async def test_compression_applied_in_prompt(self, tmp_path):
        """Test that compression is applied and prompt contains compressed content."""
        # ... verify compressed JSON appears in the prompt sent to LLM ...

    @pytest.mark.asyncio
    async def test_yaml_input_converted_to_json(self, tmp_path):
        """Test that YAML input is auto-converted to JSON before compression."""
        # ... load a YAML spec file, verify it arrives as JSON in the prompt ...

    @pytest.mark.asyncio
    async def test_output_file_saved_uncompressed(self, tmp_path):
        """Test that output files are saved uncompressed and schema-valid."""
        # ... run step, verify output file is valid JSON matching schema ...
```

**Testing Requirements:**  
- Tests use real `PromptManager` with actual `pipeline_config.yaml`  
- LLM client is mocked (no real API calls)  
- File I/O uses `tmp_path`  
- Tests verify: output file created, content is valid JSON, compression applied in prompt

**Acceptance Criteria:**  
- `test_pipeline_integration.py` created with ≥5 test cases  
- All tests pass without real LLM API key  
- Tests marked `@pytest.mark.integration`

---

### CR-15: Refactor execute_step() — Extract Sub-Methods

**Priority:** High (Code Quality)  
**File:** `prompt_pipeline/step_executor.py` — `execute_step()` (lines 85–250)

**Description:**  
`execute_step()` is ~165 lines and handles multiple responsibilities: input preparation, prompt loading, LLM calls, output processing, and validation. Extract into focused sub-methods to improve testability and maintainability.

**References:**  
- `code_review_tasks.md` — Task 3.2  
- `code_review_comprehensive.md` — §1.2 (Large Method Complexity), §4.4 (Large Classes)

**Dependencies:** CR-08, CR-11, CR-12 (tests must pass before and after refactor)

**Implementation Details:**  
Extract three methods:

1. `_prepare_step_inputs(step_name, step_config, cli_inputs, exogenous_inputs, previous_outputs) -> tuple[Dict, Dict]` — wraps `_prepare_variables_from_config` + force-mode tag filling.

2. `async _call_llm_for_step(step_name, filled_prompt, model, compression_metrics) -> str` — wraps spinner, show_prompt/show_response display, and `llm_client.call_prompt_async()`.

3. `_process_step_outputs(response, step_config) -> Dict[str, Path]` — wraps the output label loop, `_convert_response_if_needed()`, and `_write_file_safely()`.

4. `_validate_step_outputs(output_paths, step_config, step_name) -> None` — wraps the validation loop.

Update `execute_step()` to call these four methods in sequence, reducing it to ~30 lines.

**Testing Requirements:**  
- All existing tests in `test_step_executor.py` (CR-12) continue to pass after refactor  
- Unit: Each extracted method testable in isolation  
- Unit: `_prepare_step_inputs` with missing input → `StepExecutionError`  
- Unit: `_call_llm_for_step` with LLM failure → exception propagates  
- Unit: `_process_step_outputs` with invalid JSON output type → `StepExecutionError`

**Acceptance Criteria:**  
- `execute_step()` reduced to ≤40 lines  
- Four new private methods created  
- All existing tests pass  
- No behavioral change (pure refactor)

---

### CR-16: Add Type Hints to All Public Methods

**Priority:** Medium (Code Quality)  
**Files:** `prompt_pipeline/llm_client.py`, `prompt_pipeline/orchestrator.py`, `prompt_pipeline/label_registry.py`, and any other files with missing return type hints

**Description:**  
Type hints are inconsistently applied. `llm_client.py` and `orchestrator.py` have methods missing return type hints. Add comprehensive type hints to all public methods and run `mypy` to verify.

**References:**  
- `code_review_tasks.md` — Task 3.4  
- `code_review_comprehensive.md` — §1.1 (Inconsistent Type Hints Coverage)

**Dependencies:** CR-10 (exception types needed for `Raises` annotations)

**Implementation Details:**  
1. In `llm_client.py`: add return types to `call_prompt()`, `call_prompt_async()`, `get_model_for_step()`, `_create_session()`, `_build_headers()`.  
2. In `orchestrator.py`: add return types to `run_pipeline()`, `_prepare_inputs()`, `_discover_inputs()`, `_get_previous_outputs()`, `_load_and_sort_steps()`.  
3. In `label_registry.py`: add return types to all public methods.  
4. Add `mypy` to dev dependencies in `pyproject.toml`:
   ```toml
   [project.optional-dependencies]
   dev = [
       ...
       "mypy>=1.0",
   ]
   ```
5. Run `mypy prompt_pipeline prompt_pipeline_cli --ignore-missing-imports` and fix all errors.

**Testing Requirements:**  
- `mypy prompt_pipeline --ignore-missing-imports` exits with 0 errors  
- No runtime errors introduced by type annotations  
- Existing tests continue to pass

**Acceptance Criteria:**  
- All public methods in `llm_client.py`, `orchestrator.py`, `label_registry.py` have return type hints  
- `mypy` passes with no errors on these files  
- `mypy` added to dev dependencies

---

### CR-17: Optimize TagReplacer.replace() — Single-Pass Regex

**Priority:** Medium (Performance)  
**File:** `prompt_pipeline/tag_replacement.py` — `replace()` (lines 185–225)

**Description:**  
`replace()` performs multiple sequential `str.replace()` calls — one per tag — which is O(n×m) where n is prompt length and m is number of tags. Replace with a single-pass `re.sub()` using a callback function.

**References:**  
- `code_review_tasks.md` — Task 4.1  
- `code_review_comprehensive.md` — §3.1 (Inefficient String Operations)

**Dependencies:** None

**Implementation Details:**  
```python
def replace(
    self,
    replacements: Dict[str, Any],
    validate: bool = True,
    default_value: str = ""
) -> str:
    """Replace all tags using single-pass regex substitution."""
    if validate:
        is_valid, missing_tags = self.validate_tags(replacements)
        if not is_valid:
            raise MissingTagError(missing_tags[0])

    def replacer(match: re.Match) -> str:
        tag_name = match.group(1).strip()
        replacement_value = replacements.get(tag_name, default_value)
        return self._resolve_replacement(tag_name, replacement_value)

    return self.TAG_PATTERN.sub(replacer, self.prompt)
```
`TAG_PATTERN` is already compiled as `re.compile(r'\{\{([^}]+)\}\}')` — reuse it directly.

**Testing Requirements:**  
- Unit: All existing `replace()` tests continue to pass  
- Unit: Tags replaced correctly in single pass  
- Unit: Missing tag with `validate=True` → `MissingTagError`  
- Performance: Benchmark with 100 tags in 10KB prompt — single-pass should be ≥2× faster  
- Edge cases: Tag appearing multiple times in prompt → all occurrences replaced

**Acceptance Criteria:**  
- `replace()` uses `TAG_PATTERN.sub(replacer, self.prompt)` instead of loop  
- All existing tests pass  
- No behavioral change for any existing test case

---

### CR-18: Add Connection Pooling to HTTP Client

**Priority:** Medium (Performance)  
**File:** `prompt_pipeline/llm_client.py` — `_create_session()` (lines 80–100) and `__init__()`

**Description:**  
The `HTTPAdapter` is created without connection pool configuration (`pool_connections`, `pool_maxsize`). Under load, this limits throughput. Also add separate connect/read timeout parameters for better control.

**References:**  
- `code_review_tasks.md` — Task 4.2  
- `code_review_comprehensive.md` — §3.2 (No Connection Pooling)

**Dependencies:** CR-07 (clean up `__init__` while adding parameters)

**Implementation Details:**  
1. Add `connect_timeout: int = 10` and `read_timeout: int = 110` parameters to `__init__`.  
2. Update `_create_session()`:
   ```python
   adapter = HTTPAdapter(
       max_retries=retry_strategy,
       pool_connections=10,
       pool_maxsize=20,
       pool_block=False,
   )
   ```
3. Update request calls to use tuple timeout:
   ```python
   response = self.session.post(
       OPENROUTER_API_URL,
       headers=headers,
       json=payload,
       timeout=(self.connect_timeout, self.read_timeout),
   )
   ```

**Testing Requirements:**  
- Unit: `_create_session()` returns session with configured adapter  
- Unit: Request uses tuple timeout `(connect_timeout, read_timeout)`  
- Unit: Default values are `connect_timeout=10`, `read_timeout=110`  
- Integration: Existing LLM client tests pass with new configuration

**Acceptance Criteria:**  
- `HTTPAdapter` configured with `pool_connections=10`, `pool_maxsize=20`  
- Requests use `(connect_timeout, read_timeout)` tuple  
- New parameters have sensible defaults  
- No regression in existing tests

---

### CR-19: Fix Race Condition in LabelRegistry

**Priority:** Medium (Reliability)  
**File:** `prompt_pipeline/label_registry.py` — `register_label()` (lines 71+)

**Description:**  
The `register_label()` method performs a check-then-register pattern that is not atomic. In concurrent scenarios (future parallel step execution), race conditions could corrupt the registry. Add a `threading.Lock` to make all registry operations atomic.

**References:**  
- `code_review_tasks.md` — Task 4.3  
- `code_review_comprehensive.md` — §2.1 (Race Condition in Label Registry)

**Dependencies:** None

**Implementation Details:**  
```python
import threading

class LabelRegistry:
    def __init__(self):
        self._labels: Dict[str, LabelInfo] = {}
        self._step_labels: Dict[str, List[str]] = {}
        self._file_to_label: Dict[Path, str] = {}
        self._validation_errors: List[str] = []
        self._lock = threading.Lock()  # Add lock

    def register_label(self, label, step_name, file_path, file_type, order=0) -> bool:
        with self._lock:  # Wrap entire method body
            # ... existing check-then-register logic unchanged ...
```
Apply `with self._lock:` to all methods that read or write `_labels`, `_step_labels`, `_file_to_label`, or `_validation_errors`.

Update module docstring to note thread safety.

**Testing Requirements:**  
- Unit: Concurrent `register_label()` calls from multiple threads → no corruption  
- Unit: Existing single-threaded tests continue to pass  
- Unit: Lock is acquired and released correctly (no deadlock)  
- Edge cases: Exception inside lock → lock released (context manager guarantees this)

**Acceptance Criteria:**  
- `threading.Lock` added to `LabelRegistry.__init__()`  
- All mutating methods wrapped with `with self._lock:`  
- Module docstring updated to note thread safety  
- All existing tests pass

---

### CR-20: Standardize Docstrings and Add Module-Level Documentation

**Priority:** Low (Maintainability)  
**Files:** Multiple — `prompt_pipeline/step_executor.py`, `prompt_pipeline/orchestrator.py`, `prompt_pipeline/llm_client.py`, `prompt_pipeline/label_registry.py`, `prompt_pipeline/tag_replacement.py`, `prompt_pipeline/query_patterns.py`

**Description:**  
Docstrings use different formats across the codebase. Some modules lack module-level docstrings. Standardize on Google style (already used in most places) and add module-level docstrings to all modules that lack them.

**References:**  
- `code_review_tasks.md` — Tasks 5.1, 5.2, 5.3  
- `code_review_comprehensive.md` — §4.1 (Missing Module-Level Documentation), §4.2 (Inconsistent Naming)

**Dependencies:** None (can be done any time)

**Implementation Details:**  
1. Add `pydocstyle` to dev dependencies in `pyproject.toml`:
   ```toml
   "pydocstyle>=6.0",
   ```
2. Add module-level docstrings to: `orchestrator.py`, `llm_client.py`, `label_registry.py`, `query_patterns.py` (following the pattern in `terminal_utils.py` and `step_executor.py`).  
3. Ensure all public methods have Google-style docstrings with `Args:`, `Returns:`, `Raises:` sections where applicable.  
4. Fix abbreviated variable names where found (e.g., `aggs_path` → `aggregations_path`).  
5. Do **not** rename parameters that are part of public APIs or widely used internally — only rename local variables.

**Testing Requirements:**  
- `pydocstyle prompt_pipeline --convention=google` passes with no errors (or acceptable ignore list)  
- No functional changes — documentation only  
- Existing tests continue to pass

**Acceptance Criteria:**  
- All modules in `prompt_pipeline/` have module-level docstrings  
- All public methods have Google-style docstrings  
- `pydocstyle` passes  
- No functional changes

---

## SECTION 2: JSON Compression Migration Tasks (M-series)

---

### M-01: Create Module Structure for json_compression

**Description:**  
Create the Python package directory `prompt_pipeline/compression/json_compression/` with the required module files.

**References:** `doc/json_compression.md` — §3.1, §4.1

**Dependencies:** None

**Implementation Details:**  
Create:
```
prompt_pipeline/compression/json_compression/
    __init__.py          # Public API exports
    config.py            # CompressionConfig dataclasses
    compressor.py        # Core compression functions + helpers
    decompressor.py      # Core decompression functions + helpers
    yaml_utils.py        # YAML→JSON conversion utility
    strategy.py          # JsonCompactStrategy (CompressionStrategy subclass)
    config_parser.py     # YAML pipeline config parser
```
`__init__.py` exports: `compress_json`, `decompress_json`, `yaml_to_json_dict`, `JsonCompactStrategy`, all config dataclasses.

**Acceptance Criteria:** Package importable without errors; no circular imports.

---

### M-02: Implement CompressionConfig Dataclasses

**Description:**  
Implement `FilterConfig`, `FlattenConfig`, `KeyMappingConfig`, `TabularConfig`, and `CompressionConfig` dataclasses in `config.py`.

**References:** `doc/json_compression.md` — §2.1.1

**Dependencies:** M-01

**Implementation Details:**  
```python
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
Note: This `CompressionConfig` is **separate** from `prompt_pipeline.compression.manager.CompressionConfig`.

**Acceptance Criteria:** All 5 dataclasses importable; default values match spec.

---

### M-03: Implement yaml_to_json_dict Utility

**Description:**  
Implement `yaml_to_json_dict(yaml_content: str) -> Any` in `yaml_utils.py`. Parses YAML and returns a JSON-compatible Python object, round-tripping through JSON to catch non-serializable types.

**References:** `doc/json_compression.md` — §2.4.1; `prompt_pipeline/compression/strategies/yaml_as_json.py` (existing pattern)

**Dependencies:** M-01

**Implementation Details:**  
```python
def yaml_to_json_dict(yaml_content: str) -> Any:
    try:
        data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML: {e}")
    if data is None:
        raise ValueError("YAML content is empty or null")
    # Round-trip through JSON to ensure JSON-compatibility
    json_str = json.dumps(data, default=str)
    return json.loads(json_str)
```

**Testing Requirements:**  
- Valid YAML dict/list → correct Python object  
- Invalid YAML → `ValueError`  
- Empty YAML → `ValueError`  
- YAML with datetime → converted to string

**Acceptance Criteria:** Returns JSON-compatible objects; raises `ValueError` for invalid input.

---

### M-04: Implement `_build_field_code_map`

**Description:**  
Implement `_build_field_code_map(paths, config) -> Dict[str, str]` in `compressor.py`. Maps logical paths to short codes using `identity` or `auto_abbrev` strategy. Output is `{code: path}`.

**References:** `doc/json_compression.md` — §2.1.1, §2.2.1 step 4, §5.2

**Dependencies:** M-01, M-02

**Implementation Details:**  
- `identity`: `{path: path for path in paths}`  
- `auto_abbrev`: generate alphabetic codes `a, b, ..., z, aa, ab, ...` using `itertools.product`  
- Must be deterministic: sort `paths` before assigning codes  
- Raise `ValueError` for unknown strategy

**Testing Requirements:**  
- `identity`: code == path  
- `auto_abbrev` with 3 paths → `["a", "b", "c"]`  
- `auto_abbrev` with 27 paths → includes `"aa"`  
- Deterministic: same paths → same codes  
- Unknown strategy → `ValueError`

**Acceptance Criteria:** Deterministic, unique codes; both strategies work correctly.

---

### M-05: Implement `_collect_logical_fields`

**Description:**  
Implement `_collect_logical_fields(data, config) -> List[str]` in `compressor.py`. Traverses data structure and collects all logical paths, applying filter rules. Returns sorted list.

**References:** `doc/json_compression.md` — §2.2.2, §2.2.3

**Dependencies:** M-01, M-02

**Implementation Details:**  
- Object keys: `"user.name"`, `"address.city"`  
- Root array of objects: `"[].type"`, `"[].id"`  
- Named array of objects: `"anchors[].anchor_id"`  
- Apply `include_paths` first (if non-empty), then `exclude_paths`  
- Return sorted list for determinism

**Testing Requirements:**  
- Flat dict → `["a", "b"]`  
- Nested dict → `["user.name"]`  
- Root array of objects → `["[].id", "[].type"]`  
- `include_paths` filter → only included paths  
- `exclude_paths` filter → excluded paths removed  
- Empty dict/list → `[]`

**Acceptance Criteria:** Correct paths for all data shapes; filter rules applied; output sorted.

---

### M-06: Implement `_encode_data_with_field_codes`

**Description:**  
Implement `_encode_data_with_field_codes(data, path_to_code, prefix, sep) -> Any` in `compressor.py`. Recursively replaces object keys with their short codes.

**References:** `doc/json_compression.md` — §2.2.1 step 5, §5.4

**Dependencies:** M-04, M-05

**Implementation Details:**  
- For dicts: replace each key with `path_to_code.get(path, key)` (fallback to original key)  
- For lists: recurse on each element  
- For scalars: return unchanged  
- `path_to_code` here is `{path: code}` (inverted from `_build_field_code_map` output)

**Testing Requirements:**  
- Flat dict with code map → keys replaced  
- Nested dict → all levels encoded  
- Array of objects → each object's keys encoded  
- Key not in map → original key preserved

**Acceptance Criteria:** All dict keys replaced by codes where mapping exists; nested structures handled.

---

### M-07: Implement `_encode_tabular_arrays`

**Description:**  
Implement `_encode_tabular_arrays(data, path_to_code, config, sep) -> Tuple[Any, Dict]` in `compressor.py`. Converts configured arrays of objects into 2D tables and returns tabular metadata.

**References:** `doc/json_compression.md` — §2.1.2, §2.2.1 step 5, §5.1–5.3

**Dependencies:** M-04, M-05

**Implementation Details:**  
- Handle root array (path `""` or `"[]"` in `config.tabular.array_paths`)  
- Handle named array paths within a dict  
- `tabular_metadata` shape: `{"path_key": {"fields": ["code1", ...], "kind": "object_array"}}`  
- If `tabular.enabled=False` or `array_paths=[]`: return data unchanged, empty metadata

**Testing Requirements:**  
- Root array with `array_paths=[""]` → 2D list + correct metadata  
- Named array path → `data["anchors"]` becomes 2D list  
- `tabular.enabled=False` → data unchanged  
- Metadata `fields` list matches column order in rows

**Acceptance Criteria:** Configured arrays converted to 2D lists; metadata correctly describes structure.

---

### M-08: Implement `_build_schema_object`

**Description:**  
Implement `_build_schema_object(original_root_type, config, path_to_code, tabular_metadata) -> Dict` in `compressor.py`. Constructs the `schema` section of the compressed output.

**References:** `doc/json_compression.md` — §2.1.2, §5.3.1

**Dependencies:** M-04, M-07

**Implementation Details:**  
```python
schema = {
    "version": 1,
    "original_root_type": original_root_type,  # "object" | "array"
    "config": {
        "flatten": {"enabled": ..., "path_separator": ...},
        "tabular": {"enabled": ..., "array_paths": ...},
    },
    "fields": path_to_code,  # {code: path}
}
if tabular_metadata:
    schema["structure"] = {"tabular_arrays": tabular_metadata}
```

**Testing Requirements:**  
- `version` always `1`; `original_root_type` correct  
- `fields` is `path_to_code` dict  
- `structure.tabular_arrays` present only when `tabular_metadata` non-empty

**Acceptance Criteria:** Schema object matches §2.1.2 structure; all required fields present.

---

### M-09: Implement `_decode_tabular_arrays`

**Description:**  
Implement `_decode_tabular_arrays(data, code_to_path, tabular_metadata, sep) -> Any` in `decompressor.py`. Reconstructs arrays of objects from 2D tables using schema metadata.

**References:** `doc/json_compression.md` — §2.3.1 step 4, §2.1.2

**Dependencies:** M-07, M-08

**Implementation Details:**  
- For root array (path `""` or `"[]"`): reconstruct each row `[v1, v2, ...]` into `{key1: v1, key2: v2, ...}` using `code_to_path` to get field names  
- For named array paths: reconstruct within dict  
- Empty `tabular_metadata` → data unchanged

**Testing Requirements:**  
- Root array tabular → reconstructed array of objects with correct keys  
- Named array path → reconstructed correctly  
- Empty metadata → data unchanged  
- Row with fewer values than fields → missing values are `None`

**Acceptance Criteria:** Tabular arrays correctly reconstructed; non-tabular data unchanged.

---

### M-10: Implement `_decode_data_from_field_codes`

**Description:**  
Implement `_decode_data_from_field_codes(data, code_to_path, sep) -> Any` in `decompressor.py`. Recursively replaces short codes back to original field names in non-tabular data.

**References:** `doc/json_compression.md` — §2.3.1 step 3

**Dependencies:** M-06, M-09

**Implementation Details:**  
- For dicts: replace each code key with the last segment of `code_to_path.get(code, code)`  
- For lists: recurse on each element  
- Fallback to original code when not in map

**Testing Requirements:**  
- Dict with code keys → original key names restored  
- Nested dict → all levels decoded  
- Code not in map → original code used as key

**Acceptance Criteria:** All coded keys replaced with original field names; nested structures handled.

---

### M-11: Implement `compress_json` Public API

**Description:**  
Implement `compress_json(data, config) -> Dict[str, Any]` in `compressor.py`. Wires together all helpers in the correct order.

**References:** `doc/json_compression.md` — §2.2.1, §1.2

**Dependencies:** M-04, M-05, M-06, M-07, M-08

**Implementation Details:**  
Pipeline:
1. Determine `original_root_type`
2. `_collect_logical_fields(data, config)` → `paths`
3. `_build_field_code_map(paths, config.key_mapping)` → `path_to_code` (`{code: path}`)
4. Invert to `path_to_code_inv` (`{path: code}`) for encoding
5. `_encode_tabular_arrays(data, path_to_code, config, sep)` → `(encoded_data, tabular_metadata)`
6. If root not fully tabular: `_encode_data_with_field_codes(encoded_data, path_to_code_inv, "", sep)`
7. `_build_schema_object(original_root_type, config, path_to_code, tabular_metadata)` → `schema`
8. Return `{"schema": schema, "data": encoded_data}`

Raise `ValueError` if `data` is not dict or list.

**Testing Requirements:**  
- Returns `{"schema": ..., "data": ...}`  
- `schema.version == 1`; `schema.fields` maps codes to paths  
- `data` uses short codes as keys  
- Non-dict/list input → `ValueError`

**Acceptance Criteria:** Returns correct compressed format for any valid input.

---

### M-12: Implement `decompress_json` Public API

**Description:**  
Implement `decompress_json(compressed) -> Any` in `decompressor.py`. Reconstructs original data from compressed representation.

**References:** `doc/json_compression.md` — §2.3.1

**Dependencies:** M-09, M-10

**Implementation Details:**  
1. Validate input has `"schema"` and `"data"` keys  
2. Build `code_to_path` from `schema["fields"]`  
3. Get `tabular_metadata` from `schema.get("structure", {}).get("tabular_arrays", {})`  
4. `_decode_tabular_arrays(data, code_to_path, tabular_metadata, sep)`  
5. If root not fully tabular: `_decode_data_from_field_codes(decoded, code_to_path, sep)`  
6. Return decoded data

Raise `ValueError` for invalid input format.

**Testing Requirements:**  
- `decompress_json(compress_json(data, config))` == original data (for no-filter config)  
- Invalid input → `ValueError`  
- Tabular compressed data → correctly reconstructed

**Acceptance Criteria:** Decompressed data matches original for lossless configs; raises `ValueError` for invalid input.

---

### M-13: Implement Round-Trip Tests

**Description:**  
Implement comprehensive round-trip tests in `tests/test_prompt_pipeline/test_json_compression.py`.

**References:** `doc/json_compression.md` — §2.5.1, §2.5.3, §5

**Dependencies:** M-11, M-12

**Implementation Details:**  
Test cases:
- Simple dict with `identity` strategy → round-trip exact match  
- Simple dict with `auto_abbrev` → round-trip exact match  
- Array of objects non-tabular → round-trip exact match  
- Array of objects tabular (`array_paths=[""]`) → `data` is 2D list; round-trip exact match  
- Filter `include_paths` → filtered fields absent after decompress  
- Schema structure: `version==1`, `fields` present  
- Determinism: same input → same output twice  
- Test with actual `json/concepts.json` and `json/aggregations.json` data

**Acceptance Criteria:** All round-trip tests pass; determinism test passes; filter test confirms lossy behavior.

---

### M-14: Implement JsonCompactStrategy (CompressionStrategy Subclass)

**Description:**  
Implement `JsonCompactStrategy` in `strategy.py`. Adapts `compress_json`/`decompress_json` to the existing `CompressionStrategy` interface.

**References:** `prompt_pipeline/compression/strategies/base.py`; `doc/json_compression.md` — §2.4.2

**Dependencies:** M-11, M-12

**Implementation Details:**  
- `name = "json_compact"`  
- `compress()`: parse input (YAML via `yaml_to_json_dict` or JSON via `json.loads`), build `CompressionConfig` from `context.extra["compression"]`, call `compress_json()`, serialize result to JSON string  
- `decompress()`: parse compressed JSON string, call `decompress_json()`, serialize back to JSON string  
- `get_supported_content_types()` returns `["yaml", "json"]`  
- `_build_config_from_context()`: reads `context.extra.get("compression", {})` and builds `CompressionConfig`

**Testing Requirements:**  
- `name == "json_compact"`  
- Compress YAML content → valid JSON string with `schema` and `data`  
- Compress JSON content → valid JSON string  
- Decompress → original data recovered  
- `get_supported_content_types()` returns `["yaml", "json"]`

**Acceptance Criteria:** Full `CompressionStrategy` interface implemented; round-trip works.

---

### M-15: Register JsonCompactStrategy in CompressionManager

**Description:**  
Register `JsonCompactStrategy` in `CompressionManager._register_default_strategies()` and update `__init__.py` exports.

**References:** `prompt_pipeline/compression/manager.py`; `prompt_pipeline/compression/__init__.py`

**Dependencies:** M-14

**Implementation Details:**  
1. Add import in `manager.py`: `from prompt_pipeline.compression.json_compression.strategy import JsonCompactStrategy`  
2. Add `JsonCompactStrategy()` to the `strategies` list in `_register_default_strategies()`  
3. Add export in `compression/__init__.py`

**Testing Requirements:**  
- `CompressionManager().list_strategies()` includes `"json_compact"`  
- `CompressionManager().get_strategy("json_compact")` returns `JsonCompactStrategy` instance  
- Existing strategies still registered

**Acceptance Criteria:** `"json_compact"` available in `CompressionManager`; no import errors.

---

### M-16: Implement YAML Config Parser for json_compact Strategy

**Description:**  
Implement `parse_json_compact_strategy_config(entity_config, strategy_name) -> Tuple[Optional[CompressionConfig], Optional[str]]` in `config_parser.py`.

**References:** `doc/json_compression.md` — §2.4.2, §1.3

**Dependencies:** M-02

**Implementation Details:**  
- Read `entity_config["compression_strategies"][strategy_name]`  
- Check `compression_strategy_type == "json_compact"` — return `(None, None)` if not  
- Parse `compression:` sub-block into `CompressionConfig`  
- Return `(config, output_entity_label)`

**Testing Requirements:**  
- Valid `json_compact` config → correct `CompressionConfig` and `output_entity`  
- Non-json_compact strategy → `(None, None)`  
- Missing strategy → `(None, None)`  
- Default values used when sub-config keys absent

**Acceptance Criteria:** Correctly parses all sub-config fields; returns `(None, None)` for non-json_compact.

---

### M-17: Update pipeline_config.yaml — Add json_compact Strategies and Compact Entities

**Description:**  
Update `configuration/pipeline_config.yaml` to add `minimal_json` strategy entries to all affected `data_entities`, add `*_compact` entity definitions, and set `message_aggregations.schema`.

**References:** `doc/json_compression.md` — §1.3, §2.4.2–2.4.3; affected entities table above

**Dependencies:** M-02, CR-03

**Implementation Details:**  
For each affected entity (`spec`, `concepts`, `aggregations`, `messages`, `message_aggregations`), add:
```yaml
minimal_json:
  description: "Lossless JSON compaction with short field codes."
  compression_strategy_type: json_compact
  output_entity: <entity>_compact
  compression:
    filter: {include_paths: [], exclude_paths: []}
    flatten: {enabled: false, path_separator: "."}
    key_mapping: {strategy: auto_abbrev, min_length: 1, max_length: 4}
    tabular: {enabled: false, array_paths: []}  # true + [""] for array entities
```
Enable `tabular: {enabled: true, array_paths: [""]}` for `concepts`, `aggregations`, `messages`, `message_aggregations`.  
Add `*_compact` entity definitions (type: json, filename: `*_compact.json`).  
Set `message_aggregations.schema: schemas/messageAggregations.schema.json`.

**Testing Requirements:**  
- Load updated config with `PromptManager` → no errors  
- `get_data_entity("spec_compact")` returns correct entity  
- `parse_json_compact_strategy_config(spec_entity, "minimal_json")` returns valid config

**Acceptance Criteria:** All affected entities have `minimal_json` strategy; all `*_compact` entities defined; config loads without errors.

---

### M-18: Update StepExecutor._load_file_content — YAML→JSON Auto-Conversion

**Description:**  
Update `_load_file_content()` to automatically convert YAML content to JSON when `input_type == "yaml"`.

**References:** `doc/json_compression.md` — §2.4.1; `prompt_pipeline/step_executor.py`

**Dependencies:** M-03

**Implementation Details:**  
After reading file content, if `input_type == "yaml"`:
```python
from prompt_pipeline.compression.json_compression.yaml_utils import yaml_to_json_dict
import json
data = yaml_to_json_dict(content)
content = json.dumps(data, ensure_ascii=False)
```
Raise `StepExecutionError` (wrapping `ValueError`) if YAML conversion fails.

**Testing Requirements:**  
- YAML file with `input_type="yaml"` → returns JSON string  
- JSON file with `input_type="json"` → unchanged  
- MD file with `input_type="md"` → unchanged  
- Invalid YAML → `StepExecutionError`

**Acceptance Criteria:** YAML entities auto-converted to JSON; non-YAML entities unchanged.

---

### M-19: Update StepExecutor._apply_compression — Route json_compact

**Description:**  
Update `_apply_compression()` to detect `json_compact` strategy type from `data_entities` config and route to `JsonCompactStrategy` with the correct config.

**References:** `prompt_pipeline/step_executor.py` — `_apply_compression()`; `doc/json_compression.md` — §2.4.2

**Dependencies:** M-15, M-16, M-18

**Implementation Details:**  
After the existing `"full"/"none"` check, look up the entity's strategy config:
```python
data_entity = self.prompt_manager.get_data_entity(label) if label else None
if data_entity:
    strategy_cfg = data_entity.get("compression_strategies", {}).get(compression, {})
    if strategy_cfg.get("compression_strategy_type") == "json_compact":
        # Route to JsonCompactStrategy via CompressionManager
        json_compact_config = strategy_cfg.get("compression", {})
        manager = CompressionManager()
        config = CompressionConfig(strategy="json_compact", level=1)
        context = {"content_type": input_type, "label": label,
                   "extra": {"compression": json_compact_config}}
        result = manager.compress(content, config, context)
        return result.content, {...metrics...}
```
Fallback to full content on error (with logging).

**Testing Requirements:**  
- `_apply_compression(yaml_json_content, "minimal_json", "yaml", "spec")` → compressed JSON string  
- `_apply_compression(json_content, "minimal_json", "json", "concepts")` → compressed JSON string  
- Unknown strategy → falls through to existing `CompressionManager`  
- Error in compression → fallback to full content with logged warning

**Acceptance Criteria:** `minimal_json` correctly routed to `JsonCompactStrategy`; fallback on error.

---

### M-20: Update Step Inputs in pipeline_config.yaml — Switch to minimal_json

**Description:**  
Update all affected step inputs in `pipeline_config.yaml` to use `compression: minimal_json` and remove `compression_params.level`.

**References:** `configuration/pipeline_config.yaml` — `steps` section; affected entities table above

**Dependencies:** M-17, M-19

**Implementation Details:**  
For each row in the affected entities table, change `compression: <old_strategy>` to `compression: minimal_json` and remove any `compression_params:` block. Affected steps: `step2`, `stepC3`, `stepC4`, `stepC5`, `stepD1`.

**Testing Requirements:**  
- Load updated config → no errors  
- Dry-run of each affected step → no errors  
- `_apply_compression` called with `"minimal_json"` for each affected input

**Acceptance Criteria:** All affected step inputs use `compression: minimal_json`; no `compression_params.level` on json_compact inputs.

---

### M-21: Update StepExecutor._prepare_variables_from_config — Entity Type Resolution

**Description:**  
Ensure `_prepare_variables_from_config()` resolves entity type from `data_entities` when not explicitly set in the step input config.

**References:** `prompt_pipeline/step_executor.py` — `_prepare_variables_from_config()`

**Dependencies:** M-18, M-19

**Implementation Details:**  
```python
label = input_spec.get("label")
input_type = input_spec.get("type")
if not input_type and label:
    data_entity = self.prompt_manager.get_data_entity(label)
    if data_entity:
        input_type = data_entity.get("type", "text")
input_type = input_type or "text"
```

**Testing Requirements:**  
- Input spec without `type`, entity is `yaml` → `input_type` resolved as `"yaml"`  
- Input spec without `type`, entity is `json` → `input_type` resolved as `"json"`  
- Input spec with explicit `type` → explicit type used

**Acceptance Criteria:** Entity type correctly resolved from `data_entities`; YAML entities auto-converted.

---

### M-22: Remove Old Compression Strategies from yaml/json Entities in Config

**Description:**  
Remove old content-dependent compression strategy entries (`anchor_index`, `concept_summary`, `hierarchical`, `yaml_as_json`, `heirachical` [typo]) from `yaml` and `json` typed `data_entities` in `pipeline_config.yaml`. Keep `none` and `minimal_json`.

**References:** `configuration/pipeline_config.yaml` — `data_entities`

**Dependencies:** M-20 (step inputs already updated)

**Implementation Details:**  
For `spec`: remove `anchor_index`, `schema_only`, `yaml_as_json`, `heirachical`.  
For `concepts`, `aggregations`, `messages`: remove `concept_summary`.  
Keep `none` on all entities. Keep `minimal_json`.  
**Note:** Python strategy files are NOT deleted — only config entries removed.

**Testing Requirements:**  
- Load updated config → no errors  
- `get_data_entity("spec")["compression_strategies"]` only has `none` and `minimal_json`  
- Dry-run all steps → no errors

**Acceptance Criteria:** Old strategy names removed from yaml/json entity configs; no step references old strategy names for yaml/json entities.

---

### M-23: Add Tests for YAML Config Parsing of json_compact

**Description:**  
Add tests for `parse_json_compact_strategy_config()` in `tests/test_prompt_pipeline/test_json_compression_config.py`.

**References:** `doc/json_compression.md` — §2.5.2

**Dependencies:** M-16, M-17

**Testing Requirements:**  
- Valid `json_compact` config → correct `CompressionConfig` and `output_entity`  
- Non-json_compact strategy → `(None, None)`  
- Missing strategy → `(None, None)`  
- Key mapping strategy parsed correctly  
- Tabular config with `enabled=True` and `array_paths=[""]` parsed correctly  
- Test with actual `pipeline_config.yaml` loaded via `PromptManager`

**Acceptance Criteria:** All tests pass; config parser handles all sub-config fields.

---

### M-24: Integration Test — Full Step Execution with json_compact

**Description:**  
Add integration tests verifying the full step execution pipeline with `json_compact` compression, from file loading through prompt construction (dry-run, no LLM call).

**References:** `tests/test_prompt_pipeline/test_cli_dry_run.py`

**Dependencies:** M-19, M-20, M-21, CR-04

**Implementation Details:**  
Create `tests/test_prompt_pipeline/test_json_compression_integration.py`:
- `test_spec_entity_loaded_as_json`: YAML spec auto-converted to JSON  
- `test_minimal_json_compression_applied`: compressed JSON appears in prompt  
- `test_concepts_tabular_compression`: concepts with `tabular=True` produces 2D table  
- `test_round_trip_with_actual_fixtures`: use `tests/fixtures/valid_spec.yaml` and `tests/fixtures/test_concepts.json`

**Acceptance Criteria:** All integration tests pass; no LLM API calls; YAML→JSON conversion verified end-to-end.

---

### M-25: Documentation Updates

**Description:**  
Update `README.md` and `doc/IMPLEMENTATION_SUMMARY.md` to reflect the new `json_compact` strategy and migration from old strategies.

**Dependencies:** M-20, M-22

**Implementation Details:**  
1. `README.md`: add `json_compact` row to compression strategies table; note old yaml/json strategies removed.  
2. `doc/IMPLEMENTATION_SUMMARY.md`: update compression strategies section.  
3. `configuration/pipeline_config.yaml`: add inline comments explaining the `minimal_json` pattern.

**Acceptance Criteria:** `json_compact` documented in README; old strategy names for yaml/json entities noted as removed.

---

## SECTION 3: Dependency Graph

```
CR-03 ──────────────────────────────────────────────────────────────────────────────┐
CR-10 ──────────────────────────────────────────────────────────────────────────────┤
CR-09 (depends: CR-10) ─────────────────────────────────────────────────────────────┤
CR-01 ──────────────────────────────────────────────────────────────────────────────┤
CR-02 (depends: CR-01) ─────────────────────────────────────────────────────────────┤
CR-04 ──────────────────────────────────────────────────────────────────────────────┤
CR-05 ──────────────────────────────────────────────────────────────────────────────┤
CR-06 (depends: CR-09) ─────────────────────────────────────────────────────────────┤
CR-07 ──────────────────────────────────────────────────────────────────────────────┤
CR-08 (depends: CR-09) ─────────────────────────────────────────────────────────────┤
CR-11 (depends: CR-10) ─────────────────────────────────────────────────────────────┤
CR-12 (depends: CR-08, CR-11) ──────────────────────────────────────────────────────┤
CR-13 (depends: CR-12) ─────────────────────────────────────────────────────────────┤
CR-14 (depends: CR-12, CR-13) ──────────────────────────────────────────────────────┤
CR-15 (depends: CR-08, CR-11, CR-12) ───────────────────────────────────────────────┤
CR-16 (depends: CR-10) ─────────────────────────────────────────────────────────────┤
CR-17 ──────────────────────────────────────────────────────────────────────────────┤
CR-18 (depends: CR-07) ─────────────────────────────────────────────────────────────┤
CR-19 ──────────────────────────────────────────────────────────────────────────────┤
CR-20 ──────────────────────────────────────────────────────────────────────────────┘

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
M-18 (depends: M-03, CR-08, CR-09) ────────────────────────────────────────────────┤
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

### Phase 1: Security & Reliability Fixes (Highest Priority — Do First)
1. **CR-10** — Centralized exceptions module (no deps; unblocks CR-06, CR-08, CR-09, CR-11)
2. **CR-07** — Secure API key handling (no deps; security critical)
3. **CR-09** — Shared file utilities module (depends: CR-10)
4. **CR-06** — Fix path traversal vulnerability (depends: CR-09)
5. **CR-08** — Fix silent file write failures (depends: CR-09)
6. **CR-11** — Fix null/None checks for JSON extraction (depends: CR-10)

### Phase 2: Validator & Schema Fixes
7. **CR-03** — Fix messageAggregations schema (no deps; unblocks M-17)
8. **CR-01** — Fix JSONValidator base class (no deps)
9. **CR-02** — Simplify subclass validators (depends: CR-01)

### Phase 3: Testing Infrastructure
10. **CR-12** — Unit tests for StepExecutor (depends: CR-08, CR-11)
11. **CR-13** — Unit tests for Orchestrator (depends: CR-12)
12. **CR-14** — Pipeline integration tests (depends: CR-12, CR-13)

### Phase 4: CLI & UX Fixes
13. **CR-04** — Fix dry-run prompt display (no deps)
14. **CR-05** — Add `--info` CLI flag (no deps)

### Phase 5: Code Quality Refactoring
15. **CR-15** — Refactor `execute_step()` (depends: CR-08, CR-11, CR-12)
16. **CR-16** — Add type hints (depends: CR-10)
17. **CR-17** — Optimize TagReplacer single-pass regex (no deps)
18. **CR-18** — HTTP connection pooling (depends: CR-07)
19. **CR-19** — Fix LabelRegistry race condition (no deps)
20. **CR-20** — Standardize docstrings (no deps)

### Phase 6: json_compression Module Foundation
21. **M-01** — Create module structure
22. **M-02** — Config dataclasses
23. **M-03** — yaml_to_json_dict utility

### Phase 7: Core Compression Helpers
24. **M-04** — `_build_field_code_map`
25. **M-05** — `_collect_logical_fields`
26. **M-06** — `_encode_data_with_field_codes`
27. **M-07** — `_encode_tabular_arrays`
28. **M-08** — `_build_schema_object`

### Phase 8: Core Decompression Helpers
29. **M-09** — `_decode_tabular_arrays`
30. **M-10** — `_decode_data_from_field_codes`

### Phase 9: Public API + Tests
31. **M-11** — `compress_json`
32. **M-12** — `decompress_json`
33. **M-13** — Round-trip tests

### Phase 10: Strategy Integration
34. **M-14** — `JsonCompactStrategy`
35. **M-15** — Register in CompressionManager
36. **M-16** — YAML config parser

### Phase 11: Pipeline Integration
37. **M-17** — Update pipeline_config.yaml (add strategies + compact entities)
38. **M-18** — StepExecutor YAML→JSON auto-conversion
39. **M-19** — StepExecutor `_apply_compression` routing
40. **M-21** — Entity type resolution in `_prepare_variables_from_config`
41. **M-20** — Switch step inputs to `minimal_json`
42. **M-23** — Config parsing tests

### Phase 12: Cleanup + Final Tests + Docs
43. **M-22** — Remove old strategies from yaml/json entity configs
44. **M-24** — Integration tests
45. **M-25** — Documentation updates

---

## SECTION 5: Complete Task Inventory

| ID | Title | Priority | Phase | New in v2.0? |
|----|-------|----------|-------|--------------|
| CR-01 | Fix JSONValidator — use jsonschema | High | 2 | No |
| CR-02 | Simplify subclass validators | High | 2 | No |
| CR-03 | Fix messageAggregations schema | High | 2 | No |
| CR-04 | Fix dry-run prompt display | High | 4 | No |
| CR-05 | Add `--info` CLI flag | High | 4 | No |
| CR-06 | Fix path traversal vulnerability | **Critical** | 1 | **Yes** |
| CR-07 | Secure API key handling | **Critical** | 1 | **Yes** |
| CR-08 | Fix silent file write failures | **Critical** | 1 | **Yes** |
| CR-09 | Shared file utilities module | High | 1 | **Yes** |
| CR-10 | Centralized exception module | High | 1 | **Yes** |
| CR-11 | Fix null/None JSON extraction | High | 1 | **Yes** |
| CR-12 | Unit tests for StepExecutor | **Critical** | 3 | **Yes** |
| CR-13 | Unit tests for Orchestrator | **Critical** | 3 | **Yes** |
| CR-14 | Pipeline integration tests | **Critical** | 3 | **Yes** |
| CR-15 | Refactor execute_step() | High | 5 | **Yes** |
| CR-16 | Add type hints | Medium | 5 | **Yes** |
| CR-17 | Optimize TagReplacer regex | Medium | 5 | **Yes** |
| CR-18 | HTTP connection pooling | Medium | 5 | **Yes** |
| CR-19 | Fix LabelRegistry race condition | Medium | 5 | **Yes** |
| CR-20 | Standardize docstrings | Low | 5 | **Yes** |
| M-01..M-25 | JSON Compression Migration | High | 6–12 | No |

**Total tasks: 45** (20 CR + 25 M)  
**New tasks added in v2.0: 15** (CR-06 through CR-20)

---

## SECTION 6: Files Modified Summary

| File | Tasks | Change Type |
|------|-------|-------------|
| `prompt_pipeline/exceptions.py` | CR-10 | **Create** |
| `prompt_pipeline/file_utils.py` | CR-09 | **Create** |
| `prompt_pipeline/llm_client.py` | CR-07, CR-16, CR-18 | Modify |
| `prompt_pipeline/step_executor.py` | CR-08, CR-11, CR-15, CR-16, M-18, M-19, M-21 | Modify |
| `prompt_pipeline/orchestrator.py` | CR-16 | Modify |
| `prompt_pipeline/label_registry.py` | CR-16, CR-19 | Modify |
| `prompt_pipeline/tag_replacement.py` | CR-09, CR-17 | Modify |
| `prompt_pipeline/validation/json_validator.py` | CR-01, CR-02 | Modify |
| `prompt_pipeline/compression/manager.py` | M-15 | Modify |
| `prompt_pipeline/compression/__init__.py` | M-15 | Modify |
| `prompt_pipeline/compression/json_compression/__init__.py` | M-01 | **Create** |
| `prompt_pipeline/compression/json_compression/config.py` | M-02 | **Create** |
| `prompt_pipeline/compression/json_compression/yaml_utils.py` | M-03 | **Create** |
| `prompt_pipeline/compression/json_compression/compressor.py` | M-04..M-08, M-11 | **Create** |
| `prompt_pipeline/compression/json_compression/decompressor.py` | M-09, M-10, M-12 | **Create** |
| `prompt_pipeline/compression/json_compression/strategy.py` | M-14 | **Create** |
| `prompt_pipeline/compression/json_compression/config_parser.py` | M-16 | **Create** |
| `prompt_pipeline_cli/commands/run_pipeline.py` | CR-06 | Modify |
| `prompt_pipeline_cli/commands/run_step.py` | CR-04, CR-05 | Modify |
| `schemas/messageAggregations.schema.json` | CR-03 | Modify |
| `configuration/pipeline_config.yaml` | CR-03, M-17, M-20, M-22 | Modify |
| `pyproject.toml` | CR-16, CR-20 | Modify |
| `tests/test_prompt_pipeline/test_step_executor.py` | CR-12 | **Create** |
| `tests/test_prompt_pipeline/test_orchestrator.py` | CR-13 | **Create** |
| `tests/test_prompt_pipeline/test_pipeline_integration.py` | CR-14 | **Create** |
| `tests/test_prompt_pipeline/test_json_compression.py` | M-13 | **Create** |
| `tests/test_prompt_pipeline/test_json_compression_config.py` | M-23 | **Create** |
| `tests/test_prompt_pipeline/test_json_compression_integration.py` | M-24 | **Create** |
| `tests/test_prompt_pipeline/test_json_validator.py` | CR-01, CR-02 | Modify |
| `tests/test_prompt_pipeline/test_cli_dry_run.py` | CR-04 | Modify |
| `tests/test_prompt_pipeline/test_run_step_info.py` | CR-05 | Modify |
| `README.md` | M-25 | Modify |
| `doc/IMPLEMENTATION_SUMMARY.md` | M-25 | Modify |

---

## SECTION 7: Ambiguities & Notes for Implementer

1. **`StepExecutionError` migration (CR-10):** The existing `StepExecutionError` class in `step_executor.py` must be replaced by the one in `exceptions.py`. All existing `except StepExecutionError` blocks in tests and CLI code must continue to work — ensure the import path is updated everywhere, not just in `step_executor.py`.

2. **`LLMCallError` vs `LLMClientError` (CR-10):** The existing `LLMCallError` in `llm_client.py` has `retry_count` and `last_status_code` attributes. The new `LLMClientError` in `exceptions.py` must preserve these. Update all `except LLMCallError` blocks to use `LLMClientError`.

3. **CR-09 and CR-08 ordering:** CR-08 can be implemented inline in `step_executor.py` first (as `_write_file_safely()`), then refactored to use `write_file_content()` from CR-09 once that module exists. This avoids a blocking dependency.

4. **Path traversal scope (CR-06):** The `allowed_base_dir` for path validation should be `Path.cwd()` in most cases. However, the pipeline is designed to accept files from anywhere on the filesystem (e.g., `--input-file spec:/data/specs/my_spec.yaml`). Consider making path validation opt-in or configurable rather than strictly enforced, to avoid breaking legitimate use cases. Flag this for user decision if needed.

5. **`_encode_data_with_field_codes` vs tabular interaction (M-11):** When tabular encoding is applied to the root array, the non-tabular encoding step should be skipped for the root. The `compress_json` implementation handles this with a conditional check. Verify this logic is correct for nested tabular arrays within a dict.

6. **`spec` entity tabular:** The `spec` entity is a complex nested YAML object (not a flat array). Tabular encoding should be **disabled** for `spec` (`tabular.enabled: false`). Only root-array entities (`concepts`, `aggregations`, `messages`, `message_aggregations`) should use tabular.

7. **`message_aggregations` tabular:** The `messageAggregations.json` is an array of objects. Tabular encoding is appropriate. The `members` field is itself an array — tabular encoding will store it as a nested array value within each row, which is fine.

8. **Existing `yaml_as_json` strategy:** After this migration, it is no longer needed for yaml/json entities. It is kept in the codebase (M-22 only removes config entries, not Python files). A future cleanup task can remove the Python files.

9. **`jsonschema` dependency (CR-01):** Already declared in `pyproject.toml` as `"jsonschema>=4.17.0"`. No change needed.

10. **Thread safety scope (CR-19):** The current pipeline is sequential (no parallel step execution). The lock is added as a forward-compatibility measure for when parallel execution is implemented. Document this clearly in the code.

---

*Document version: 2.0 — Updated to include full code review tasks from `code_review_tasks.md` and `code_review_comprehensive.md`*  
*Previous version: 1.0 — covered CR-01..CR-05 and M-01..M-25*  
*New in v2.0: CR-06..CR-20 (15 additional tasks)*