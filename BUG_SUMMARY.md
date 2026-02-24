# Bug Summary: --dry-run Does Not Show Prompt Construction

## Current Behavior (BUGGY)

When running:
```bash
prompt-pipeline run-step --nl-spec doc/todo_list_spec_2.yaml --dry-run step1
```

**Output:**
```
[DRY RUN] Would execute step: step1
[DRY RUN] Config: configuration/pipeline_config.yaml
[DRY RUN] Output path: pipeline_output/spec_1.yaml
[DRY RUN] Model level: 2
[DRY RUN] Required inputs: nl_spec
```

**Problem:** The dry-run only shows config metadata. It does NOT:
1. Load the prompt file
2. Show what the prompt file contains
3. Show how inputs are aggregated
4. Show the full generated prompt that would be sent to the LLM

## Expected Behavior

The `--dry-run` option should:
1. Load the prompt file specified in the step config
2. Show the prompt file content
3. Show how inputs are being processed (source: cli, file, label)
4. Display the complete prompt that would be sent to the LLM (preamble + prompt file + inputs)
5. Make NO API calls

## Root Cause

In `prompt_pipeline_cli/commands/run_step.py` lines 134-158:

```python
if dry_run:
    # ... basic config output ...
    return  # <-- Returns BEFORE prompt construction!
```

The dry-run logic returns early, preventing prompt construction from happening.

## Fix Required

The `--dry-run` option should be enhanced to:
1. Build the complete prompt (preamble + prompt file + input variables)
2. Display it to the user
3. NOT make any API calls

## Related Issue

The `--show-both` option is supposed to display the prompt, but:
1. It makes API calls (no way to just see the prompt)
2. The prompt display happens AFTER the API call (for debugging the response)

## Test That Failed

This integration test should exist but doesn't:
```python
def test_dry_run_shows_prompt():
    """Test that --dry-run shows the complete prompt without making API calls."""
    result = subprocess.run([
        "prompt-pipeline", "run-step",
        "--nl-spec", "doc/todo_list_spec_2.yaml",
        "--dry-run",
        "step1"
    ], capture_output=True, text=True)
    
    # Should show prompt file content
    assert "Given the inputs:" in result.stdout
    
    # Should NOT make API calls
    assert "Executing step" not in result.stdout
    assert result.returncode == 0
```

## Security Impact

This bug prevents proper testing of prompt construction, which could lead to:
1. Prompt injection vulnerabilities going undetected
2. SQL injection issues in prompts being missed
3. Malformed prompts being deployed to production

## Priority

**HIGH** - This is a critical testing gap that prevents proper validation of prompt construction.
