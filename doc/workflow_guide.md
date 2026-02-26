# Workflow Guide for ModelLM

This guide provides detailed workflows and patterns for using the ModelLM prompt pipeline system.

## Table of Contents

1. [Quick Start Workflows](#quick-start-workflows)
2. [Individual Step Execution](#individual-step-execution)
3. [Full Pipeline Execution](#full-pipeline-execution)
4. [Iterative Development](#iterative-development)
5. [CI/CD Integration](#cicd-integration)
6. [Interactive Development](#interactive-development)
7. [Compression Strategy Selection](#compression-strategy-selection)
8. [Error Handling and Recovery](#error-handling-and-recovery)
9. [Testing and Debugging](#testing-and-debugging)
10. [Advanced Patterns](#advanced-patterns)

---

## Quick Start Workflows

### 1. Basic Single Step

Execute a single step with minimal configuration:

```bash
# Step 1: Generate YAML specification
prompt-pipeline run-step step1 \
  --input-file nl_spec:doc/todo_list_nl_spec.md \
  --output-dir yaml/ \
  --approve
```

### 2. Full Pipeline in One Command

Execute the complete pipeline in batch mode:

```bash
prompt-pipeline run-pipeline \
  --nl-spec doc/todo_list_nl_spec.md \
  --output-dir pipeline_output/ \
  --import-database todo_app \
  --wipe \
  --model-level 1 \
  --verbosity 2
```

### 3. Interactive Development

Start with interactive prompts:

```bash
prompt-pipeline run-step step1 \
  --input-prompt nl_spec \
  --approve
```

---

## Individual Step Execution

### Pattern 1: File Input with Approval

**Use Case:** Development and review

```bash
prompt-pipeline run-step stepC3 \
  --input-file spec:yaml/spec_1.yaml \
  --output-dir concepts/ \
  --approve \
  --show-prompt \
  --show-response
```

**What happens:**
1. Load specification from `yaml/spec_1.yaml`
2. Apply `hierarchical` compression (configured in config)
3. Substitute `{{spec}}` in prompt with compressed content
4. Display substituted prompt (green highlight)
5. Wait for user confirmation (y/n/q/v)
6. Call LLM API with substituted prompt
7. Display LLM response
8. Save response to `concepts/concepts.json`
9. Validate output against schema

### Pattern 2: Multiple Inputs

**Use Case:** Steps requiring multiple data sources

```bash
prompt-pipeline run-step stepC4 \
  --input-file spec:yaml/spec_1.yaml \
  --input-file concepts:concepts/concepts.json \
  --output-dir aggregations/ \
  --approve
```

**What happens:**
1. Load two inputs: `spec` and `concepts`
2. Compress `spec` with `anchor_index` strategy
3. Compress `concepts` with `concept_summary` strategy
4. Display both inputs in different colors (cyan and green)
5. Substitute both in prompt template
6. Execute LLM call with combined context
7. Save response to `aggregations/aggregations.json`

### Pattern 3: Dry Run

**Use Case:** Verify configuration without API calls

```bash
prompt-pipeline run-step stepC3 \
  --input-file spec:yaml/spec_1.yaml \
  --dry-run \
  --approve
```

**Output:**
```
[DRY RUN] Step: stepC3
[DRY RUN] Input: spec -> yaml/spec_1.yaml
[DRY RUN] Compression: hierarchical (level 3)
[DRY RUN] Output: concepts/concepts.json
[DRY RUN] No API call will be made
```

### Pattern 4: Interactive Prompt

**Use Case:** Direct content entry

```bash
prompt-pipeline run-step step1 \
  --input-prompt nl_spec \
  --approve
```

**Interaction:**
```
Enter content for nl_spec (press Ctrl+D when done):
> This is a to-do list application
> - Users can create tasks
> - Tasks have titles and descriptions
> - Users can mark tasks complete
> ^D
Content accepted (150 characters)
Continue? (y/n) [n]: y
```

### Pattern 5: Direct Text Input

**Use Case:** Quick testing with inline content

```bash
prompt-pipeline run-step step1 \
  --input-text nl_spec:"A todo list app where users can add, complete, and delete tasks." \
  --approve
```

---

## Full Pipeline Execution

### Pattern 1: Complete Pipeline with Import

**Use Case:** Production pipeline from spec to TypeDB

```bash
prompt-pipeline run-pipeline \
  --nl-spec doc/todo_list_nl_spec.md \
  --output-dir pipeline_output/ \
  --import-database todo_app \
  --wipe \
  --model-level 1 \
  --verbosity 2
```

**Execution Flow:**
1. **step1**: Generate `spec_1.yaml` from NL spec
2. **step2**: Generate `spec_formal.md` from spec
3. **step3**: Generate `revised_spec.md` from formal spec
4. **stepC3**: Extract `concepts.json` from revised spec
5. **stepC4**: Generate `aggregations.json` from concepts
6. **stepC5**: Generate `messages.json` and `messageAggregations.json`
7. **stepD1**: Generate `requirements.json` from all data
8. **Import**: Load `requirements.json` into TypeDB

**Time Estimate:** 2-5 minutes depending on model level

### Pattern 2: Pipeline with Custom Output Directory

**Use Case:** Organized outputs for different projects

```bash
prompt-pipeline run-pipeline \
  --nl-spec doc/ecommerce_spec.md \
  --output-dir ecommerce_pipeline/ \
  --import-database ecommerce_app \
  --model-level 2
```

**Directory Structure:**
```
ecommerce_pipeline/
├── spec_1.yaml
├── spec_formal.md
├── revised_spec.md
├── concepts.json
├── aggregations.json
├── messages.json
├── messageAggregations.json
└── requirements.json
```

### Pattern 3: Pipeline with Specific Model Level

**Use Case:** Cost control and quality trade-off

```bash
# Level 1 (cheapest, fastest)
prompt-pipeline run-pipeline --model-level 1

# Level 2 (balanced)
prompt-pipeline run-pipeline --model-level 2

# Level 3 (best quality, most expensive)
prompt-pipeline run-pipeline --model-level 3
```

### Pattern 4: Pipeline without Import

**Use Case:** Generate outputs for review before import

```bash
prompt-pipeline run-pipeline \
  --nl-spec doc/todo_list_nl_spec.md \
  --output-dir pipeline_output/ \
  --model-level 1
# Review outputs in pipeline_output/
# Then import manually:
prompt-pipeline import --file pipeline_output/requirements.json --database todo_app --wipe
```

---

## Iterative Development

### Scenario: Specification Revision Cycle

**Step 1:** Generate initial YAML

```bash
prompt-pipeline run-step step1 \
  --input-file nl_spec:doc/todo_list_nl_spec.md \
  --output-dir yaml/ \
  --approve
```

**Step 2:** Generate formal specification

```bash
prompt-pipeline run-step step2 \
  --input-file spec:yaml/spec_1.yaml \
  --output-dir yaml/ \
  --approve
```

**Step 3:** Manual Review and Revision

```bash
# Open the generated spec_formal.md
open yaml/spec_formal.md

# Make revisions as needed
# (User edits the file externally)

# When ready, continue:
```

**Step 4:** Process revised specification

```bash
prompt-pipeline run-step step3 \
  --input-file spec_formal:yaml/spec_formal.md \
  --output-dir yaml/ \
  --approve
```

**Step 5:** Extract concepts from revised spec

```bash
prompt-pipeline run-step stepC3 \
  --input-file spec:yaml/revised_spec.md \
  --output-dir concepts/ \
  --approve
```

**Step 6:** Generate aggregations

```bash
prompt-pipeline run-step stepC4 \
  --input-file spec:yaml/revised_spec.md \
  --input-file concepts:concepts/concepts.json \
  --output-dir concepts/ \
  --approve
```

**Step 7:** Generate message flows

```bash
prompt-pipeline run-step stepC5 \
  --input-file spec:yaml/revised_spec.md \
  --input-file concepts:concepts/concepts.json \
  --input-file aggregations:concepts/aggregations.json \
  --output-dir concepts/ \
  --approve
```

**Step 8:** Generate requirements

```bash
prompt-pipeline run-step stepD1 \
  --input-file spec:yaml/revised_spec.md \
  --input-file concepts:concepts/concepts.json \
  --input-file messages:concepts/messages.json \
  --output-dir requirements/ \
  --approve
```

**Step 9:** Import to TypeDB

```bash
prompt-pipeline import \
  --file requirements/requirements.json \
  --database todo_app \
  --wipe
```

### Pattern: Skipping Revision Steps

**Use Case:** Direct from YAML to concepts

```bash
# Generate YAML
prompt-pipeline run-step step1 \
  --input-file nl_spec:doc/todo_list_nl_spec.md \
  --output-dir yaml/ \
  --approve

# Skip step2 and step3, go directly to concepts
prompt-pipeline run-step stepC3 \
  --input-file spec:yaml/spec_1.yaml \
  --output-dir concepts/ \
  --approve

# Continue with rest of pipeline
prompt-pipeline run-step stepC4 \
  --input-file spec:yaml/spec_1.yaml \
  --input-file concepts:concepts/concepts.json \
  --output-dir concepts/ \
  --approve
```

---

## CI/CD Integration

### Pattern 1: GitHub Actions Workflow

```yaml
# .github/workflows/pipeline.yml
name: ModelLM Pipeline

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  pipeline:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install -e .
    
    - name: Run ModelLM Pipeline
      env:
        OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
        TYPEDB_URL: ${{ secrets.TYPEDB_URL }}
        TYPEDB_USERNAME: ${{ secrets.TYPEDB_USERNAME }}
        TYPEDB_PASSWORD: ${{ secrets.TYPEDB_PASSWORD }}
      run: |
        prompt-pipeline run-pipeline \
          --nl-spec doc/todo_list_nl_spec.md \
          --output-dir pipeline_output/ \
          --import-database todo_app \
          --auto-approve \
          --model-level 1 \
          --verbosity 1
    
    - name: Upload artifacts
      uses: actions/upload-artifact@v2
      with:
        name: pipeline-outputs
        path: pipeline_output/
```

### Pattern 2: Docker Container

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install -e .

# Copy source code
COPY prompt_pipeline/ prompt_pipeline/
COPY prompt_pipeline_cli/ prompt_pipeline_cli/
COPY configuration/ configuration/
COPY prompts/ prompts/
COPY schemas/ schemas/
COPY doc/ doc/

# Copy application code
COPY my_spec.md .

# Set environment variables
ENV OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
ENV TYPEDB_URL=${TYPEDB_URL}
ENV TYPEDB_USERNAME=${TYPEDB_USERNAME}
ENV TYPEDB_PASSWORD=${TYPEDB_PASSWORD}

# Run pipeline
CMD ["prompt-pipeline", "run-pipeline", \
     "--nl-spec", "my_spec.md", \
     "--output-dir", "/output", \
     "--import-database", "my_app", \
     "--auto-approve", \
     "--model-level", "1"]
```

### Pattern 3: Batch Processing Multiple Specs

```bash
# Script: process_all_specs.sh
#!/bin/bash

for spec in specs/*.md; do
    echo "Processing $spec..."
    
    prompt-pipeline run-pipeline \
      --nl-spec "$spec" \
      --output-dir "outputs/$(basename "$spec" .md)/" \
      --import-database "db_$(basename "$spec" .md)" \
      --auto-approve \
      --model-level 1 \
      --verbosity 0
    
    if [ $? -eq 0 ]; then
        echo "✓ Success: $spec"
    else
        echo "✗ Failed: $spec"
    fi
done
```

### Pattern 4: Dry Run in CI

```yaml
# Test configuration without executing
- name: Validate Configuration
  run: |
    prompt-pipeline run-step step1 \
      --input-file nl_spec:doc/todo_list_nl_spec.md \
      --dry-run \
      --auto-approve
```

---

## Interactive Development

### Pattern 1: Step-by-Step Interactive

**Use Case:** Learning the system or debugging

```bash
# Step 1: Interactive NL spec entry
prompt-pipeline run-step step1 \
  --input-prompt nl_spec \
  --approve

# Check output
cat yaml/spec_1.yaml

# Step 2: Generate formal spec
prompt-pipeline run-step step2 \
  --input-file spec:yaml/spec_1.yaml \
  --approve

# Review
cat yaml/spec_formal.md

# Step 3: Continue with user edits...
prompt-pipeline run-step step3 \
  --input-file spec_formal:yaml/spec_formal.md \
  --approve
```

### Pattern 2: Visual Prompt Review

**Use Case:** Understand what the LLM receives

```bash
prompt-pipeline run-step stepC3 \
  --input-file spec:yaml/spec_1.yaml \
  --approve \
  --show-prompt
```

**Output includes:**
```
=== PROMPT (substituted) ===
[System message about persona]

[Input content with {{spec}} replaced]

=== END PROMPT ===

Compression: hierarchical (level 3)
Original size: 15,234 bytes
Compressed: 7,617 bytes (50% reduction)

Continue? (y/n) [n]:
```

### Pattern 3: Response Inspection

**Use Case:** Debug LLM responses

```bash
prompt-pipeline run-step stepC3 \
  --input-file spec:yaml/spec_1.yaml \
  --approve \
  --show-response
```

**Output includes:**
```
[Spinner while waiting for LLM]

=== LLM RESPONSE ===
{
  "concepts": [...],
  "relationships": [...]
}

=== END RESPONSE ===

Response size: 12,456 bytes
Validation: PASSED

Output saved to: concepts/concepts.json
```

### Pattern 4: Verbose Inspection

**Use Case:** Detailed debugging

```bash
prompt-pipeline run-step stepC3 \
  --input-file spec:yaml/spec_1.yaml \
  --approve \
  --show-prompt \
  --show-response \
  --verbosity 3
```

---

## Compression Strategy Selection

### Guide: Choosing the Right Strategy

**Consider these factors:**
1. **Input Size**: Large files need aggressive compression
2. **Information Density**: How much detail is needed
3. **LLM Context Window**: Stay within limits
4. **Step Requirements**: What the LLM needs to do

### Strategy Comparison

| Strategy | Size Reduction | Information Preserved | Best For |
|----------|---------------|----------------------|----------|
| `zero` | 0% | Full content | Step C3 (concept extraction) |
| `anchor_index` | 70-80% | Anchor IDs + text | Step C4 (aggregations) |
| `concept_summary` | 50-60% | Concept tables | Steps C5, D1 |
| `hierarchical` | 50-70% | Multi-layer summary | Step C3 (large specs) |
| `schema_only` | 80-90% | Schema + counts | Schema-aware contexts |
| `differential` | 90-95% | Only changes | Iterative refinement |

### Strategy Usage Examples

**Example 1: Small Spec (10 KB)**
```yaml
inputs:
  - label: spec
    compression: none  # No compression needed
```

**Example 2: Medium Spec (50 KB)**
```yaml
inputs:
  - label: spec
    compression: anchor_index  # Compact but useful
    compression_params:
      level: 2  # Medium compression
```

**Example 3: Large Spec (200 KB)**
```yaml
inputs:
  - label: spec
    compression: hierarchical  # Aggressive but useful
    compression_params:
      level: 3  # Maximum compression
```

**Example 4: Iterative Updates**
```yaml
inputs:
  - label: spec
    compression: differential  # Only changes
    compression_params:
      base_version: "v1.0"  # Compare against
```

### Configuration Examples

**Step C3 (Concept Extraction):**
```yaml
stepC3:
  inputs:
    - label: spec
      source: label:spec
      compression: hierarchical  # Full context needed
      compression_params:
        level: 3
      color: magenta
```

**Step C4 (Aggregations):**
```yaml
stepC4:
  inputs:
    - label: spec
      source: label:spec
      compression: anchor_index  # Compact reference
      color: cyan
    - label: concepts
      source: label:concepts
      compression: concept_summary  # Table format
      color: green
```

---

## Error Handling and Recovery

### Pattern 1: Handling Validation Errors

**Scenario:** Output fails validation

```bash
prompt-pipeline run-step stepC3 \
  --input-file spec:yaml/spec_1.yaml \
  --approve
```

**Error Output:**
```
✗ Validation FAILED
Error: Required field 'concepts' not found
Warning: 'relationships' array is empty

Options:
  - Fix the LLM prompt and retry
  - Use --skip-validation for development
  - Use --force to continue despite warnings
```

**Recovery Options:**
```bash
# Option 1: Skip validation (development)
prompt-pipeline run-step stepC3 \
  --input-file spec:yaml/spec_1.yaml \
  --skip-validation \
  --approve

# Option 2: Force continue (warning only)
prompt-pipeline run-step stepC3 \
  --input-file spec:yaml/spec_1.yaml \
  --force \
  --approve

# Option 3: Fix and retry
# (Modify prompt template or input)
prompt-pipeline run-step stepC3 \
  --input-file spec:yaml/spec_1.yaml \
  --approve
```

### Pattern 2: Handling API Errors

**Scenario:** OpenRouter API fails

```bash
prompt-pipeline run-step step1 \
  --input-file nl_spec:doc/spec.md \
  --approve
```

**Error Output:**
```
✗ API Error: Rate limit exceeded
Retrying in 4 seconds... (attempt 1/3)
Retrying in 8 seconds... (attempt 2/3)
Retrying in 16 seconds... (attempt 3/3)
✗ API Error: Rate limit exceeded (all attempts failed)
```

**Recovery Options:**
```bash
# Option 1: Wait and retry
sleep 60  # Wait for rate limit reset
prompt-pipeline run-step step1 --input-file nl_spec:doc/spec.md --approve

# Option 2: Use different model level
prompt-pipeline run-step step1 \
  --input-file nl_spec:doc/spec.md \
  --model-level 2  # Different model might have different limits
```

### Pattern 3: Handling Missing Inputs

**Scenario:** Input file not found

```bash
prompt-pipeline run-step stepC3 \
  --input-file spec:yaml/nonexistent.yaml \
  --approve
```

**Error Output:**
```
✗ Input Error: File 'yaml/nonexistent.yaml' not found

Available inputs from step1:
  - spec: yaml/spec_1.yaml
  - spec_formal: yaml/spec_formal.md

Did you mean:
  prompt-pipeline run-step stepC3 --input-file spec:yaml/spec_1.yaml
```

**Recovery Options:**
```bash
# Option 1: Run previous step first
prompt-pipeline run-step step1 \
  --input-file nl_spec:doc/todo_list_nl_spec.md \
  --approve

# Option 2: Specify correct file
prompt-pipeline run-step stepC3 \
  --input-file spec:yaml/spec_1.yaml \
  --approve

# Option 3: Check what's available
prompt-pipeline run-step stepC3 \
  --input-file spec:yaml/spec_1.yaml \
  --dry-run
```

### Pattern 4: Dependency Chain Errors

**Scenario:** Running step without dependencies

```bash
prompt-pipeline run-step stepC4 \
  --input-file spec:yaml/spec_1.yaml \
  --approve
```

**Error Output:**
```
✗ Dependency Error: Step 'stepC4' requires 'concepts' input
Required inputs:
  - spec (provided ✓)
  - concepts (missing ✗)

Dependency chain:
  step1 (spec) -> stepC3 (concepts) -> stepC4 (aggregations)

Solution: Run these steps first:
  1. prompt-pipeline run-step stepC3 --input-file spec:yaml/spec_1.yaml
  2. Then run stepC4
```

**Recovery Options:**
```bash
# Option 1: Run full dependency chain
prompt-pipeline run-step stepC3 --input-file spec:yaml/spec_1.yaml --approve
prompt-pipeline run-step stepC4 --input-file spec:yaml/spec_1.yaml --approve

# Option 2: Use run-pipeline (auto-handles dependencies)
prompt-pipeline run-pipeline --nl-spec doc/spec.md --auto-approve
```

---

## Testing and Debugging

### Pattern 1: Unit Testing Individual Steps

**Use Case:** Test step configuration

```bash
# Test step1 configuration
prompt-pipeline run-step step1 \
  --input-file nl_spec:doc/todo_list_nl_spec.md \
  --dry-run \
  --approve

# Test stepC3 with different compression
prompt-pipeline run-step stepC3 \
  --input-file spec:yaml/spec_1.yaml \
  --dry-run \
  --approve

# Test validation
prompt-pipeline validate --config configuration/pipeline_config.yaml
```

### Pattern 2: Visual Debugging

**Use Case:** See what's happening at each stage

```bash
# Enable verbose output
prompt-pipeline run-step stepC3 \
  --input-file spec:yaml/spec_1.yaml \
  --approve \
  --show-prompt \
  --show-response \
  --verbosity 2
```

**Output includes:**
- Input file paths
- Compression strategy and metrics
- Substituted prompt
- LLM response
- Validation results
- Output file location

### Pattern 3: Testing Compression

**Use Case:** Verify compression strategies work

```bash
# Test anchor_index compression
prompt-pipeline run-step stepC4 \
  --input-file spec:yaml/spec_1.yaml \
  --input-file concepts:concepts/concepts.json \
  --dry-run \
  --approve

# Check compression metrics
# (Look for "Original size: X bytes" in output)
```

### Pattern 4: Testing TypeDB Import

**Use Case:** Verify import without full pipeline

```bash
# First generate requirements
prompt-pipeline run-step stepD1 \
  --input-file spec:yaml/spec_1.yaml \
  --input-file concepts:concepts/concepts.json \
  --input-file messages:concepts/messages.json \
  --approve

# Test import
prompt-pipeline import \
  --file requirements/requirements.json \
  --database test_app \
  --wipe
```

### Pattern 5: Integration Testing

**Use Case:** Test full pipeline with test data

```bash
# Create test specification
cat > test_spec.md << EOF
# Test Application

## Goals
- Test goal 1
- Test goal 2

## Capabilities
- Capability A: Does something
- Capability B: Does something else
EOF

# Run full pipeline
prompt-pipeline run-pipeline \
  --nl-spec test_spec.md \
  --output-dir test_output/ \
  --import-database test_app \
  --wipe \
  --auto-approve

# Check results
ls -la test_output/
```

---

## Advanced Patterns

### Pattern 1: Custom Compression Configuration

**Use Case:** Fine-tune compression for specific inputs

```yaml
stepC3:
  inputs:
    - label: spec
      source: label:spec
      compression: hierarchical
      compression_params:
        level: 3
        max_tokens: 3000
        preserve_full: false
      color: magenta
```

### Pattern 2: Multiple Outputs per Step

**Use Case:** Step produces multiple related outputs

```yaml
stepC5:
  outputs:
    - label: messages
    - label: message_aggregations
```

**Usage:**
```bash
prompt-pipeline run-step stepC5 \
  --input-file spec:yaml/spec_1.yaml \
  --input-file concepts:concepts/concepts.json \
  --input-file aggregations:concepts/aggregations.json \
  --output-dir outputs/ \
  --approve
```

**Output files:**
- `outputs/messages.json`
- `outputs/messageAggregations.json`

### Pattern 3: Color-Coded Terminal Output

**Use Case:** Visual differentiation of inputs

```yaml
stepC4:
  inputs:
    - label: spec
      source: label:spec
      compression: anchor_index
      color: cyan  # Primary input
    - label: concepts
      source: label:concepts
      compression: concept_summary
      color: green  # Secondary input
```

**Terminal display:**
```
cyan:   spec -> anchor_index -> [1,234 bytes]
green:  concepts -> concept_summary -> [4,567 bytes]
```

### Pattern 4: Skipping Steps in Pipeline

**Use Case:** Continue from intermediate step

```bash
# Generate requirements starting from existing outputs
prompt-pipeline run-step stepD1 \
  --input-file spec:yaml/spec_1.yaml \
  --input-file concepts:concepts/concepts.json \
  --input-file messages:concepts/messages.json \
  --output-dir requirements/ \
  --approve
```

### Pattern 5: Model Selection Override

**Use Case:** Override model for specific step

```bash
# Use specific model (overrides config)
prompt-pipeline run-step stepC3 \
  --input-file spec:yaml/spec_1.yaml \
  --model anthropic/claude-3-opus \
  --approve
```

### Pattern 6: Batch Processing with Different Specs

**Use Case:** Process multiple specifications

```bash
#!/bin/bash
# process_multiple.sh

SPECS=("todo_app.md" "ecommerce.md" "blog.md")

for spec in "${SPECS[@]}"; do
    echo "Processing: $spec"
    
    prompt-pipeline run-pipeline \
      --nl-spec "specs/$spec" \
      --output-dir "outputs/$(basename "$spec" .md)/" \
      --import-database "db_$(basename "$spec" .md)" \
      --auto-approve \
      --model-level 1 \
      --verbosity 0
    
    if [ $? -eq 0 ]; then
        echo "✓ $spec completed successfully"
    else
        echo "✗ $spec failed"
    fi
done
```

### Pattern 7: Development vs Production Configuration

**Development:**
```bash
prompt-pipeline run-step stepC3 \
  --input-file spec:yaml/spec_1.yaml \
  --skip-validation \
  --model-level 1 \
  --approve \
  --show-prompt
```

**Production:**
```bash
prompt-pipeline run-step stepC3 \
  --input-file spec:yaml/spec_1.yaml \
  --model-level 3 \
  --auto-approve
```

### Pattern 8: Dry Run with Real Configuration

**Use Case:** Test configuration before execution

```bash
# Full pipeline dry run
prompt-pipeline run-pipeline \
  --nl-spec doc/todo_list_nl_spec.md \
  --dry-run \
  --auto-approve

# Individual step dry run with approval
prompt-pipeline run-step stepC3 \
  --input-file spec:yaml/spec_1.yaml \
  --dry-run \
  --approve
```

---

## Common Workflows Summary

### Quick Reference: Which Command to Use?

| Scenario | Command | Key Options |
|----------|---------|-------------|
| First time setup | `run-pipeline` | `--nl-spec`, `--auto-approve` |
| Debug single step | `run-step` | `--approve`, `--show-prompt`, `--show-response` |
| CI/CD pipeline | `run-pipeline` | `--auto-approve`, `--verbosity 1` |
| Testing configuration | `run-step` | `--dry-run`, `--approve` |
| Interactive learning | `run-step` | `--input-prompt`, `--approve` |
| Validate outputs | `validate` | `--config` |
| Import to TypeDB | `import` | `--file`, `--database`, `--wipe` |
| Check configuration | `config` | `--show` |

### Workflow Selection Guide

**Choose `run-pipeline` when:**
- Running complete workflow
- CI/CD automation
- Processing single spec end-to-end
- Don't need intermediate review

**Choose `run-step` when:**
- Developing/debugging specific step
- Need to review intermediate outputs
- Running steps out of order
- Testing new configuration

**Choose `validate` when:**
- Checking configuration syntax
- Validating output files
- Debugging validation errors

**Choose `import` when:**
- Manually importing generated files
- Re-importing after modifications
- Testing import functionality

**Choose `config` when:**
- Reviewing current configuration
- Debugging configuration issues
- Understanding available steps

---

## Troubleshooting Common Issues

### Issue: "Input not found"

**Problem:** Missing required input

**Solution:**
```bash
# Check what inputs are available
prompt-pipeline run-step stepC3 --dry-run --approve

# Run previous step if needed
prompt-pipeline run-step step1 --input-file nl_spec:doc/spec.md --approve
```

### Issue: "Validation failed"

**Problem:** Output doesn't match schema

**Solution:**
```bash
# Check output file
cat output/concepts.json

# Skip validation for development
prompt-pipeline run-step stepC3 \
  --input-file spec:yaml/spec_1.yaml \
  --skip-validation
```

### Issue: "API rate limit"

**Problem:** Too many API calls

**Solution:**
```bash
# Wait and retry
sleep 60

# Use different model level
prompt-pipeline run-step step1 \
  --input-file nl_spec:doc/spec.md \
  --model-level 1  # Cheaper model
```

### Issue: "Compression not working"

**Problem:** Context too large

**Solution:**
```yaml
# Increase compression level
inputs:
  - label: spec
    compression: hierarchical
    compression_params:
      level: 3  # Maximum compression
```

### Issue: "Color output not working"

**Problem:** Terminal doesn't support colors

**Solution:**
```bash
# Colors are optional, system works without them
# Or check terminal settings
export TERM=xterm-256color
```

---

## Best Practices

### 1. Always Use Approval in Development

```bash
# ❌ Bad: Skipping review
prompt-pipeline run-step stepC3 --input-file spec:yaml/spec.yaml

# ✅ Good: Review before execution
prompt-pipeline run-step stepC3 --input-file spec:yaml/spec.yaml --approve
```

### 2. Use Dry Run for Configuration Testing

```bash
# ✅ Test configuration without API calls
prompt-pipeline run-step stepC3 --input-file spec:yaml/spec.yaml --dry-run --approve
```

### 3. Enable Validation in Production

```yaml
# ✅ Production configuration
steps:
  stepC3:
    validation:
      enabled: true  # Always validate
```

### 4. Use Appropriate Compression

```bash
# Small spec: No compression
prompt-pipeline run-step step1 --input-file nl_spec:doc/small.md

# Large spec: Aggressive compression
prompt-pipeline run-step stepC3 --input-file spec:yaml/large.yaml \
  --input-file spec:yaml/large.yaml
```

### 5. Organize Outputs

```bash
# Use descriptive directories
prompt-pipeline run-pipeline \
  --nl-spec doc/ecommerce_v1.md \
  --output-dir output/ecommerce/v1/ \
  --import-database ecommerce_v1
```

### 6. Monitor Progress

```bash
# Use verbose mode for debugging
prompt-pipeline run-step stepC3 --input-file spec:yaml/spec.yaml \
  --verbosity 2 \
  --approve
```

### 7. Test Before Production

```bash
# Test with small spec first
prompt-pipeline run-pipeline \
  --nl-spec doc/test_spec.md \
  --output-dir test_output/ \
  --import-database test_db \
  --auto-approve \
  --verbosity 1
```

---

## Quick Reference Commands

### File Operations

```bash
# Create test spec
cat > test.md << EOF
# Test Application
Goal: Test functionality
EOF

# View output
cat pipeline_output/spec_1.yaml

# Check directory structure
ls -la pipeline_output/
```

### Pipeline Control

```bash
# Run full pipeline
prompt-pipeline run-pipeline --nl-spec doc/spec.md

# Run individual step
prompt-pipeline run-step stepC3 --input-file spec:yaml/spec.yaml --approve

# Validate configuration
prompt-pipeline validate --config configuration/pipeline_config.yaml

# Show configuration
prompt-pipeline config --show

# Import to TypeDB
prompt-pipeline import --file data.json --database my_app --wipe
```

### Testing and Debugging

```bash
# Test without execution
prompt-pipeline run-step stepC3 --input-file spec:yaml/spec.yaml --dry-run

# See what will happen
prompt-pipeline run-step stepC3 --input-file spec:yaml/spec.yaml --approve

# Check output
pytest tests/ -v

# View test coverage
pytest tests/ --cov=prompt_pipeline --cov-report=html
```

---

## Summary

This workflow guide provides comprehensive patterns for using the ModelLM prompt pipeline system. Key takeaways:

1. **Use `run-pipeline` for full workflows** - Automatic dependency handling
2. **Use `run-step` for development** - Control and visibility
3. **Always use `--approve` in development** - Review before execution
4. **Use `--dry-run` for testing** - Verify configuration without execution
5. **Choose compression strategy based on input size** - Balance size vs information
6. **Enable validation in production** - Catch errors early
7. **Use color coding for clarity** - Different inputs, different colors
8. **Test incrementally** - Start with small specs, then scale up

---

**Document Version:** 1.0  
**Last Updated:** 2026-02-26  
**Related Documents:**
- `README.md` - Main documentation
- `doc/IMPLEMENTATION_SUMMARY.md` - Implementation details
- `configuration/pipeline_config.yaml` - Configuration reference
- `agents/implementation_guide.md` - Technical specifications
