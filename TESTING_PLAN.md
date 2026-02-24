# Testing Plan: Prompt Construction Without API Calls

## Problem
The current CLI tool makes API calls even when only testing prompt construction. There's no way to:
1. Generate and inspect the prompt without making an LLM API call
2. Test prompt construction logic in integration tests
3. Debug context aggregation issues without network calls

## Required Features

### 1. Add `--dry-run-prompt` CLI Option
Add a new option to `run-step` command that:
- Builds the full prompt (preamble + prompt file + inputs)
- Displays the complete prompt that would be sent to the LLM
- **Stops execution before making any API calls**
- Exits cleanly with success status

**Usage:**
```bash
prompt-pipeline run-step --nl-spec doc/todo_list_spec_2.yaml --dry-run-prompt step1
```

### 2. Add `--dry-run` Enhancement
The existing `--dry-run` option should be enhanced to:
- Show what inputs would be used (with their sources)
- Show the prompt file that would be loaded
- Show the complete prompt that would be generated
- Show the model that would be called
- NOT make any API calls

**Current behavior:**
- Shows config path, output path, model level
- Shows required inputs
- Does NOT show the actual prompt or prompt file

**Expected behavior:**
- Show all of the above PLUS
- Show the prompt file content being used
- Show the full generated prompt (preamble + prompt file + inputs)

### 3. Integration Test Support
The `--dry-run` option should support test assertions:
```bash
# In tests
prompt-pipeline run-step --nl-spec test_spec.yaml --dry-run-prompt step1
# Should exit with code 0 and produce structured output (JSON or YAML)
```

## Implementation Tasks

### Task 1: Enhance `--dry-run` Option
**File:** `prompt_pipeline_cli/commands/run_step.py`

**Changes:**
1. Move the dry-run logic to AFTER prompt construction
2. Add prompt file loading and display
3. Add full prompt generation and display
4. Ensure NO API calls are made

### Task 2: Add Test Infrastructure
**Files:** 
- `tests/test_prompt_construction.py` (new)
- `tests/integration/test_cli_prompt.py` (new)

**Tests to implement:**
1. Test prompt file loading
2. Test prompt variable substitution
3. Test prompt generation with different input sources (cli, file, label)
4. Test `--dry-run` output format

### Task 3: Fix Existing Integration Tests
**File:** `tests/integration/test_run_step.py`

**Change:**
- Update existing tests to use `--dry-run` option
- Add assertions for prompt content
- Ensure tests pass without network access

## CLI Command Examples

### Current Working Command
```bash
prompt-pipeline run-step --nl-spec doc/todo_list_spec_2.yaml --show-both step1
```

### New Test Commands
```bash
# Generate and display prompt without making API call
prompt-pipeline run-step --nl-spec doc/todo_list_spec_2.yaml --dry-run-prompt step1

# Enhanced dry-run showing all details
prompt-pipeline run-step --nl-spec doc/todo_list_spec_2.yaml --dry-run step1

# For testing: capture prompt to file
prompt-pipeline run-step --nl-spec doc/todo_list_spec_2.yaml --dry-run-prompt step1 > prompt_output.txt
```

## Expected Output Format

For `--dry-run-prompt`, the output should be structured:

```yaml
prompt_info:
  step: step1
  prompt_file: prompts/prompt_step1_v2.md
  persona: systems_architect
  model_level: 2
  model: xiaomi/mimo-v2-flash
  
inputs:
  nl_spec:
    source: cli
    type: md
    content_length: 118864
    preview: "We need a simple, browser-based..."
    
generated_prompt:
  preamble_length: 1234
  prompt_file_length: 10949
  input_variables_length: 118864
  total_length: 131047
  
# OR for display purposes, show the actual prompt:
full_prompt: |
  [Preamble section]
  
  [Prompt file content]
  
  [Input content]
```

## Test Assertions

### Unit Tests
```python
def test_prompt_construction_step1():
    """Test that step1 prompt is constructed correctly."""
    prompt_manager = PromptManager("configuration/pipeline_config.yaml")
    step_config = prompt_manager.get_step_config("step1")
    
    # Verify prompt file is loaded
    assert step_config["prompt_file"] == "prompt_step1_v2.md"
    
    # Verify input specification
    inputs = step_config["inputs"]
    assert len(inputs) == 1
    assert inputs[0]["label"] == "nl_spec"
    assert inputs[0]["source"] == "cli"
    
    # Verify prompt can be loaded
    prompt_content = prompt_manager.load_prompt("step1")
    assert len(prompt_content) > 0
```

### Integration Tests
```python
def test_cli_dry_run_prompt():
    """Test CLI dry-run prompt generation."""
    result = subprocess.run([
        "prompt-pipeline", "run-step",
        "--nl-spec", "doc/todo_list_spec_2.yaml",
        "--dry-run-prompt",
        "step1"
    ], capture_output=True, text=True)
    
    # Should not make API calls
    assert "Executing step: step1" not in result.stdout
    assert "PROMPT" in result.stdout
    
    # Verify prompt structure
    assert "You are a systems architect" in result.stdout
    assert "Given the inputs:" in result.stdout
    assert "nl_spec:" in result.stdout
```

## Acceptance Criteria

1. **No Network Calls:** `--dry-run-prompt` or `--dry-run` makes NO API calls
2. **Prompt Display:** Full prompt is shown (preamble + prompt file + inputs)
3. **Test Integration:** Can be used in `pytest` tests without mocking
4. **Exit Code:** Returns exit code 0 on success
5. **Backward Compatibility:** Existing `--show-both` behavior unchanged
6. **Documentation:** CLI help text updated to explain dry-run options

## Next Steps

1. Implement `--dry-run-prompt` option in run_step.py
2. Add prompt generation logic to dry-run mode
3. Create test cases
4. Update existing integration tests
5. Add CLI help documentation
