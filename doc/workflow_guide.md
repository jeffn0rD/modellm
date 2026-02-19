# Prompt Pipeline Workflow Guide

## Overview

This guide describes the complete workflow for using the prompt pipeline tool to convert natural language specifications into TypeDB databases.

## Workflow Pattern

### Scenario 1: Basic Pipeline (No Revision Cycle)

For specifications that don't require stakeholder review:

```bash
# Set environment variables
export OPENROUTER_API_KEY="sk-or-..."
export TYPEDB_URL="http://localhost:8000"
export TYPEDB_USERNAME="admin"
export TYPEDB_PASSWORD="password"

# Run full pipeline in one command
prompt-pipeline run-pipeline \
  --nl-spec doc/todo_list_spec.md \
  --output-dir pipeline_output/ \
  --import-database todo_app \
  --wipe \
  --model-level 1 \
  --verbosity 2
```

**What happens:**
1. Step 1: NL spec → YAML (`spec_1.yaml`)
2. Skip steps 2-3 (not in batch mode)
3. Step C3: Extract concepts → `concepts.json`
4. Step C4: Define aggregations → `aggregations.json`
5. Step C5: Define messages → `messages.json` + `messageAggregations.json`
6. Step D1: Extract requirements → `requirements.json`
7. Validate all outputs
8. Import to TypeDB database `todo_app`

---

### Scenario 2: Revision Cycle (Stakeholder Review)

For specifications requiring stakeholder review and approval:

#### Step 1: Generate Initial YAML
```bash
prompt-pipeline run-step step1 \
  --nl-spec doc/todo_list_spec.md \
  --output-dir yaml/ \
  --model-level 1
```
**Output:** `yaml/spec_1.yaml`

#### Step 2: Generate Formal Specification
```bash
prompt-pipeline run-step step2 \
  --spec-file yaml/spec_1.yaml \
  --output-dir yaml/ \
  --model-level 1
```
**Output:** `yaml/spec_formal.md`

#### Step 3: Stakeholder Review (Manual)
- Distribute `spec_formal.md` to stakeholders
- Collect feedback and revisions
- Update `spec_formal.md` with stakeholder changes

#### Step 4: Generate Revised Specification
```bash
prompt-pipeline run-step step3 \
  --spec-file yaml/spec_formal.md \
  --output-dir yaml/ \
  --model-level 1
```
**Output:** `yaml/revised_spec.md`

**Note:** This step generates a revised specification with tacit approval (user-provided file).

#### Step 5: Continue with Conceptual Pipeline
```bash
# Extract concepts
prompt-pipeline run-step stepC3 \
  --spec-file yaml/revised_spec.md \
  --output-dir json/ \
  --model-level 1

# Define aggregations
prompt-pipeline run-step stepC4 \
  --spec-file yaml/revised_spec.md \
  --concepts-file json/concepts.json \
  --output-dir json/ \
  --model-level 1

# Define messages
prompt-pipeline run-step stepC5 \
  --spec-file yaml/revised_spec.md \
  --concepts-file json/concepts.json \
  --aggregations-file json/aggregations.json \
  --output-dir json/ \
  --model-level 1

# Extract requirements
prompt-pipeline run-step stepD1 \
  --spec-file yaml/revised_spec.md \
  --concepts-file json/concepts.json \
  --messages-file json/messages.json \
  --output-dir json/ \
  --model-level 1
```

#### Step 6: Import to TypeDB
```bash
prompt-pipeline import json/ \
  --database todo_app \
  --wipe \
  --create
```

---

### Scenario 3: Development Mode (Cheap Models, Less Validation)

For testing and development:

```bash
prompt-pipeline run-pipeline \
  --nl-spec doc/todo_list_spec.md \
  --output-dir dev_output/ \
  --model-level 1 \
  --skip-validation \
  --verbosity 3 \
  --dry-run
```

**Flags:**
- `--model-level 1`: Use cheapest available models
- `--skip-validation`: Continue even if validation fails (warn only)
- `--verbosity 3`: Maximum verbosity (all debug info)
- `--dry-run`: Show what would happen without executing

---

### Scenario 4: Production Mode (Quality Models, Strict Validation)

For production runs:

```bash
prompt-pipeline run-pipeline \
  --nl-spec doc/todo_list_spec.md \
  --output-dir prod_output/ \
  --model-level 3 \
  --import-database todo_app \
  --wipe
```

**Flags:**
- `--model-level 3`: Use best available models
- No `--skip-validation`: Fail on validation errors
- Default verbosity: Summary output only

---

## Command Reference

### run-step Command

```bash
prompt-pipeline run-step <step_name> [OPTIONS]
```

**Arguments:**
- `step_name`: Name of the step to run (configured in pipeline_config.yaml)

**Options:**
- `--nl-spec <path>`: Path to NL specification file (required for steps that need it)
- `--spec-file <path>`: Path to input specification file
- `--concepts-file <path>`: Path to concepts.json (required for steps that need it)
- `--aggregations-file <path>`: Path to aggregations.json (required for steps that need it)
- `--messages-file <path>`: Path to messages.json (required for steps that need it)
- `--output-dir <path>`: Output directory (default: `pipeline_output/`)
- `--model-level <1|2|3>`: Model quality level (default: `1`)
- `--model <model_name>`: Specific model name (overrides `--model-level`)
- `--skip-validation`: Skip validation warnings (development mode)
- `--verbosity <0-3>`: Output verbosity level (default: `1`)
- `--dry-run`: Show what would happen without executing
- `--config <path>`: Custom configuration file path

**Auto-discovery of input files:**
- Use `--concepts-dir <path>` to auto-discover `concepts.json` from a directory
- Use `--aggregations-dir <path>` to auto-discover `aggregations.json` from a directory
- Use `--messages-dir <path>` to auto-discover `messages.json` from a directory
- Or use `--output-dir <path>` which will be searched for required files

**Examples:**
```bash
# Step 1: Generate YAML from NL spec
prompt-pipeline run-step step1 --nl-spec doc/spec.md --output-dir yaml/

# Step 2: Generate formal spec
prompt-pipeline run-step step2 --spec-file yaml/spec_1.yaml --output-dir yaml/

# Step 3: Generate revised spec
prompt-pipeline run-step step3 --spec-file yaml/spec_formal.md --output-dir yaml/

# Step C3: Extract concepts
prompt-pipeline run-step stepC3 --spec-file yaml/revised_spec.md --output-dir json/

# Step C4: Define aggregations (auto-discover concepts.json)
prompt-pipeline run-step stepC4 \
  --spec-file yaml/revised_spec.md \
  --concepts-dir json/ \
  --output-dir json/

# Or explicitly specify the file:
prompt-pipeline run-step stepC4 \
  --spec-file yaml/revised_spec.md \
  --concepts-file json/concepts.json \
  --output-dir json/

# Step C5: Define messages (auto-discover from output-dir)
prompt-pipeline run-step stepC5 \
  --spec-file yaml/revised_spec.md \
  --output-dir json/

# Step D1: Extract requirements (auto-discover from output-dir)
prompt-pipeline run-step stepD1 \
  --spec-file yaml/revised_spec.md \
  --output-dir json/
```

---

### run-pipeline Command

```bash
prompt-pipeline run-pipeline [OPTIONS]
```

**Options:**
- `--nl-spec <path>`: Path to NL specification file (required)
- `--output-dir <path>`: Output directory (default: `pipeline_output/`)
- `--model-level <1|2|3>`: Model quality level for all steps (default: `1`)
- `--model <model_name>`: Specific model for all steps (overrides `--model-level`)
- `--skip-validation`: Skip validation warnings (development mode)
- `--verbosity <0-3>`: Output verbosity level (default: `1`)
- `--dry-run`: Show what would happen without executing
- `--config <path>`: Custom configuration file path
- `--import-database <name>`: Automatically import to TypeDB after pipeline
- `--wipe`: Wipe database before import (requires `--import-database`)
- `--create`: Create database if it doesn't exist (requires `--import-database`)

**Notes:**
- Does NOT include steps 2-3 (revision cycle)
- For revision cycle, use individual step commands

**Example:**
```bash
prompt-pipeline run-pipeline \
  --nl-spec doc/todo_list_spec.md \
  --output-dir pipeline_output/ \
  --model-level 1 \
  --import-database todo_app \
  --wipe \
  --verbosity 2
```

---

### validate Command

```bash
prompt-pipeline validate <output_dir> [OPTIONS]
```

**Arguments:**
- `output_dir`: Directory containing generated files

**Options:**
- `--strict`: Fail on warnings (otherwise just warns)
- `--report-format <text|json|html>`: Output format (default: `text`)
- `--verbosity <0-3>`: Output verbosity level

**Example:**
```bash
prompt-pipeline validate pipeline_output/ --strict
```

---

### import Command

```bash
prompt-pipeline import <input_dir> [OPTIONS]
```

**Arguments:**
- `input_dir`: Directory containing YAML/JSON files to import

**Options:**
- `--database <name>`: TypeDB database name (required)
- `--wipe`: Wipe database before import
- `--create`: Create database if it doesn't exist
- `--schema <path>`: Schema file path (default: `doc/typedb_schema_2.tql`)
- `--verbosity <0-3>`: Output verbosity level

**Example:**
```bash
prompt-pipeline import pipeline_output/ \
  --database todo_app \
  --wipe \
  --create
```

---

### config Command

```bash
prompt-pipeline config <action> [OPTIONS]
```

**Actions:**
- `show`: Display current configuration
- `set <key> <value>`: Set configuration value
- `reset`: Reset to defaults

**Options:**
- `--config <path>`: Configuration file path

**Examples:**
```bash
# Show current configuration
prompt-pipeline config show

# Set default model level
prompt-pipeline config set default_model_level 2

# Set a specific model for a step
prompt-pipeline config set step_models.stepC3.level1 "minimax/m2.5"
```

---

## Model Level Configuration

### Model Levels

| Level | Quality | Speed | Cost | Use Case |
|-------|---------|-------|------|----------|
| 1 | Cheapest | Fastest | $ | Development, testing |
| 2 | Balanced | Medium | $ | Regular use |
| 3 | Best | Slower | $$ | Production, critical steps |

### Default Model Mapping

**Level 1 (Cheapest):**
- `minimax/m2.5`
- `mimo/v2-flash`
- `moonshotai/kimi-k2-0905`
- `qwen`

**Level 2 (Balanced):**
- To be configured based on quality testing

**Level 3 (Best):**
- To be configured based on quality testing

### Per-Step Model Configuration

In `configuration/pipeline_config.yaml`:

```yaml
model_levels:
  step1:
    1: "minimax/m2.5"
    2: "mimo/v2-flash"
    3: "moonshotai/kimi-k2-0905"
  step2:
    1: "minimax/m2.5"
    2: "mimo/v2-flash"
    3: "moonshotai/kimi-k2-0905"
  step3:
    1: "minimax/m2.5"
    2: "mimo/v2-flash"
    3: "moonshotai/kimi-k2-0905"
  stepC3:
    1: "qwen"
    2: "mimo/v2-flash"
    3: "moonshotai/kimi-k2-0905"
  stepC4:
    1: "minimax/m2.5"
    2: "mimo/v2-flash"
    3: "moonshotai/kimi-k2-0905"
  stepC5:
    1: "qwen"
    2: "mimo/v2-flash"
    3: "moonshotai/kimi-k2-0905"
  stepD1:
    1: "qwen"
    2: "mimo/v2-flash"
    3: "moonshotai/kimi-k2-0905"
```

---

## Validation Strategy

### Production Mode (Default)

**Behavior:** Hard fail on validation errors

**Validation Checks:**
1. **YAML (Step 1):**
   - Parse successful
   - Required fields present
   - Hierarchical structure valid
   - ID patterns correct (AN*, S*)
   - Non-empty text blocks

2. **JSON (Steps C3, C4, C5, D1):**
   - Parse successful
   - Required fields present
   - ID patterns match type
   - Cross-references valid
   - No duplicate IDs

**On Validation Failure:**
- Pipeline stops immediately
- Error message displayed
- Partial outputs saved for debugging

### Development Mode (Using --skip-validation)

**Behavior:** Warn on validation errors, continue

**Use Cases:**
- Testing pipeline logic
- Debugging LLM responses
- Quick iterations

**Warning:** TypeDB import may fail if outputs are invalid

---

## Error Recovery

### Retry Strategy

**API Errors (Network, Rate Limiting):**
- Retry with exponential backoff
- Default: 3 retries
- Backoff: 1s, 2s, 4s

**Validation Errors:**
- Production: Fail immediately
- Development: Warn and continue (if `--skip-validation`)

**Partial State Saving:**
- On failure after retries, partial outputs are saved
- Location: Output directory with `.partial` extension
- User can resume from last successful step

### Example Error Messages

```
ERROR: Validation failed
  - Line 15: Invalid anchor pattern "AN-1" (should be "AN1")
  - Line 28: Missing required field "description"
  
  Run with --skip-validation to continue (development mode only)
```

```
ERROR: OpenRouter API call failed after 3 retries
  Last error: 429 Too Many Requests
  
  Partial outputs saved to pipeline_output/spec_1.yaml.partial
  You can resume from Step C3 using:
    prompt-pipeline run-step stepC3 --spec-file pipeline_output/spec_1.yaml.partial
```

---

## Output Directory Structure

### Single Step Execution
```
yaml/
├── spec_1.yaml          # Step 1 output
├── spec_formal.md       # Step 2 output (optional)
└── revised_spec.md      # Step 3 output (optional)
```

```
json/
├── concepts.json        # Step C3 output
├── aggregations.json    # Step C4 output
├── messages.json        # Step C5 output
├── messageAggregations.json  # Step C5 output
└── requirements.json    # Step D1 output
```

### Full Pipeline Execution
```
pipeline_output/
├── spec_1.yaml          # Step 1
├── concepts.json        # Step C3
├── aggregations.json    # Step C4
├── messages.json        # Step C5
├── messageAggregations.json  # Step C5
└── requirements.json    # Step D1
```

---

## Git Integration

### Recommended .gitignore

```gitignore
# Output directories
pipeline_output/
yaml/
json/
dev_output/
prod_output/

# Partial outputs
*.partial

# Cache (future)
.cache/

# Temporary files
*.tmp
```

### Committing Generated Files

```bash
# Add all generated files
git add yaml/
git add json/

# Commit with descriptive message
git commit -m "Add generated specification files for todo app

- Generated from NL spec: doc/todo_list_spec.md
- Steps 1, C3, C4, C5, D1 completed
- Models used: level 1 (minimax/m2.5)
- Import: ready for database import"
```

---

## Common Workflows

### Quick Test
```bash
# Test pipeline without import
prompt-pipeline run-pipeline \
  --nl-spec doc/test_spec.md \
  --output-dir test_output/ \
  --model-level 1 \
  --skip-validation \
  --verbosity 3
```

### Production Run
```bash
# Full production pipeline with import
prompt-pipeline run-pipeline \
  --nl-spec doc/production_spec.md \
  --output-dir production_output/ \
  --model-level 3 \
  --import-database prod_app \
  --wipe \
  --create
```

### Debugging
```bash
# Dry run to see what would happen
prompt-pipeline run-pipeline \
  --nl-spec doc/test_spec.md \
  --model-level 1 \
  --dry-run \
  --verbosity 3

# Validate existing outputs
prompt-pipeline validate production_output/ --strict --report-format json
```

---

## Configuration Management

### Default Configuration Location
- Project-local: `./configuration/pipeline_config.yaml`
- User-global: `~/.prompt-pipeline/config.yaml`

### Setting Environment Variables
```bash
# Required
export OPENROUTER_API_KEY="sk-or-..."

# Optional (defaults)
export TYPEDB_URL="http://localhost:8000"
export TYPEDB_USERNAME="admin"
export TYPEDB_PASSWORD="password"

# Optional (overrides)
export PROMPT_PIPELINE_CONFIG="custom_config.yaml"
```

### Flexible Step Configuration

Steps can be customized via `pipeline_config.yaml` without code changes:

**Rename a step:**
```yaml
steps:
  extract_concepts:  # New step name
    name: "extract_concepts"
    prompt_file: "prompt_step_C3.md"  # Keep existing prompt
    order: 4
    output_file: "concepts.json"
    # ... other settings
```

**Change prompt file for a step:**
```yaml
steps:
  stepC3:
    name: "stepC3"
    prompt_file: "custom_concepts_prompt.md"  # Changed
    order: 4
    output_file: "concepts.json"
    # ... other settings
```

**Change output file names:**
```yaml
steps:
  stepC3:
    name: "stepC3"
    prompt_file: "prompt_step_C3.md"
    order: 4
    output_file: "my_concepts.json"  # Changed
    output_type: "json"
    # ... other settings
```

**Add custom steps:**
```yaml
steps:
  custom_step:
    name: "custom_step"
    prompt_file: "custom_prompt.md"
    order: 8  # After existing steps
    output_file: "custom_output.json"
    output_type: "json"
    requires_nl_spec: false
    requires_spec_file: true
    dependencies: ["stepC3", "stepC5"]
    json_schema: "schemas/custom_schema.json"
```

**Remove steps from pipeline:**
Simply delete the step entry from the `steps:` section in config.

**Add new prompt files:**
- Add your custom prompt to `prompts/` directory
- Update `steps:` section in `pipeline_config.yaml`
- Add JSON schema to `schemas/` directory (if JSON output)

No code changes required!

---

## Troubleshooting

### Common Issues

**Issue:** API key not found
**Solution:** Set `OPENROUTER_API_KEY` environment variable

**Issue:** Validation fails
**Solution:** 
- Review error messages
- Fix issues in LLM output
- Or use `--skip-validation` for testing (development mode only)

**Issue:** TypeDB connection failed
**Solution:**
- Check `TYPEDB_URL`, `TYPEDB_USERNAME`, `TYPEDB_PASSWORD`
- Ensure TypeDB server is running

**Issue:** Model not found
**Solution:** 
- Check model name in OpenRouter
- Use `--model-level 1` for cheapest available models
- Update configuration file

**Issue:** Insufficient tokens/API quota
**Solution:**
- Use cheaper models (level 1)
- Reduce `max_tokens` in configuration
- Check OpenRouter account balance

---

## Performance Tips

### Cost Optimization
1. Use `--model-level 1` for development
2. Use `--skip-validation` for quick testing (development only)
3. Run full pipeline once, then re-run individual steps for changes

### Time Optimization
1. Run steps in parallel for independent operations
2. Use faster models (level 1) for non-critical steps
3. Cache outputs and re-run only changed steps

### Quality Optimization
1. Use `--model-level 3` for production
2. Always validate with `--strict` before import
3. Review generated outputs before TypeDB import

---

## Future Enhancements

These features are planned for future versions (not in initial implementation):

### 1. Context Compression
Reduce token usage for revision cycles by compressing previous outputs

### 2. Caching
- Cache LLM responses to avoid re-calling for same inputs
- Cache parsed files for faster validation

### 3. Batch Processing
- Process multiple specifications in one run
- Parallel execution for faster processing

### 4. Auto-Fix
- Automatically retry with model to fix validation errors
- Max 2-3 retry attempts

### 5. Web Interface
- GUI for managing specifications and pipeline runs
- Visual representation of pipeline progress

---

## Summary

### Key Points

1. **Workflow Control:** Steps 2-3 are manual, user-controlled
2. **Validation:** Strict by default (fail on errors), development mode optional
3. **Models:** Three tiers (1=cheapest, 2=balanced, 3=best)
4. **Directory Structure:** Fixed `pipeline_output/` or user-specified
5. **Import:** Automatic after pipeline with `--import-database` flag
6. **Error Recovery:** Retry + partial state saving
7. **No Compression:** Deferred to future implementation

### Quick Start Checklist

- [ ] Set `OPENROUTER_API_KEY` environment variable
- [ ] Install with `pip install -e ".[dev]"`
- [ ] Create NL specification file
- [ ] Run basic pipeline or follow revision workflow
- [ ] Validate outputs
- [ ] Import to TypeDB (if applicable)
- [ ] Commit to git

---

**Document Version:** 1.0  
**Last Updated:** 2026-02-18  
**Status:** Reference guide for implementation
