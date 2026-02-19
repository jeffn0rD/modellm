# Prompt Pipeline Migration Proposal

## Overview

This document provides a comprehensive plan for creating a unified prompt pipeline library and CLI tool that automates the conversion of natural language specifications into TypeDB databases. The pipeline transforms NL specs through multiple stages using LLM-powered prompts with **fully configurable step definitions**.

## Key Innovation: Flexible Step Configuration

**NEW FEATURE:** All steps are now configured in `pipeline_config.yaml` with complete flexibility:

```yaml
steps:
  stepC3:
    name: "stepC3"
    prompt_file: "prompt_step_C3.md"
    order: 4
    output_file: "concepts.json"
    output_type: "json"
    requires_nl_spec: false
    requires_spec_file: true
    dependencies: []
    json_schema: "schemas/concepts_schema.json"
```

**Benefits:**
- ✅ Change step names without code changes
- ✅ Associate any prompt file with any step
- ✅ Customize output file names
- ✅ Add/remove steps dynamically
- ✅ No code modification needed

## Implementation Plan

### Phase 1: Core Library (Tasks 1-6)

#### Task 1: Create LLM Client Module
**File:** `prompt_pipeline/llm_client.py`

**Responsibilities:**
- OpenRouter API integration
- Model selection (3 levels: 1=cheapest, 2=balanced, 3=best)
- Exponential retry with partial state saving
- Rate limiting awareness

**Implementation:**
```python
class OpenRouterClient:
    def __init__(self, api_key: str, default_model: str = "minimax/m2.5"):
        self.api_key = api_key
        self.default_model = default_model
    
    async def call_prompt(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 4000
    ) -> str:
        # API call with retry logic
        ...
```

---

#### Task 2: Create Prompt Manager Module
**File:** `prompt_pipeline/prompt_manager.py`

**Key Innovation:** Loads step configurations dynamically from YAML file.

**Responsibilities:**
- Load prompt templates from files
- Variable substitution (`{{spec_file}}`, `{{concepts_file}}`, etc.)
- Load step configurations from `pipeline_config.yaml`
- Track dependencies between steps

**Step Configuration Management:**
```python
class PromptManager:
    def __init__(self, config_path: str, prompts_dir: str):
        self.steps_config = self._load_config(config_path)
    
    def get_step_config(self, step_name: str) -> Dict[str, Any]:
        """Returns full configuration for a step."""
        return self.steps_config['steps'].get(step_name)
    
    def get_prompt_file(self, step_name: str) -> str:
        """Get prompt filename for step."""
        config = self.get_step_config(step_name)
        return config.get('prompt_file')
    
    def get_output_file(self, step_name: str) -> str:
        """Get output filename for step."""
        config = self.get_step_config(step_name)
        return config.get('output_file')
    
    def get_required_inputs(self, step_name: str) -> List[str]:
        """Determine what inputs a step needs."""
        config = self.get_step_config(step_name)
        inputs = []
        if config.get('requires_nl_spec'):
            inputs.append('nl_spec')
        if config.get('requires_spec_file'):
            inputs.append('spec_file')
        if config.get('requires_concepts_file'):
            inputs.append('concepts_file')
        # ... etc
        return inputs
```

**Sample Configuration:**
```yaml
steps:
  step1:
    name: "step1"
    prompt_file: "prompt_step1_v2.md"
    order: 1
    output_file: "spec_1.yaml"
    output_type: "yaml"
    requires_nl_spec: true
    dependencies: []
    json_schema: null

  stepC3:
    name: "stepC3"
    prompt_file: "prompt_step_C3.md"
    order: 4
    output_file: "concepts.json"
    output_type: "json"
    requires_nl_spec: false
    requires_spec_file: true
    dependencies: []
    json_schema: "schemas/concepts_schema.json"

model_levels:
  step1:
    1: "minimax/m2.5"
    2: "mimo/v2-flash"
    3: "moonshotai/kimi-k2-0905"
```

**Flexibility Examples:**

*Change prompt file:*
```yaml
steps:
  stepC3:
    prompt_file: "my_custom_concepts_prompt.md"
```

*Change output filename:*
```yaml
steps:
  stepC3:
    output_file: "my_concepts_v2.json"
```

*Rename step:*
```yaml
steps:
  extract_concepts:  # New name
    name: "extract_concepts"
    prompt_file: "prompt_step_C3.md"
    # ... etc
```

*Add new step:*
```yaml
steps:
  custom_step:
    name: "custom_step"
    prompt_file: "custom_prompt.md"
    order: 8
    output_file: "custom_output.json"
    output_type: "json"
    requires_nl_spec: false
    requires_spec_file: true
    dependencies: ["stepC3"]
    json_schema: "schemas/custom_schema.json"
```

---

#### Task 3: Create Validation Module
**Files:** `prompt_pipeline/validation/yaml_validator.py`, `prompt_pipeline/validation/json_validator.py`

**YAML Validator:**
- Validates Step 1 output structure
- Checks hierarchical IDs (S*, AN*)
- Verifies anchor patterns
- Uses `pyyaml` for parsing

**JSON Validators:**
- concepts.json: Actor/Action/DataEntity IDs
- aggregations.json: AG* IDs and member references
- messages.json: MSG* IDs, producer/consumer
- requirements.json: REQ-* IDs, type/priority

**Schema Validation:**
```python
class JSONValidator:
    def __init__(self, schema_path: str):
        self.schema = self._load_schema(schema_path)
    
    def validate(self, json_content: str) -> ValidationResult:
        # Check structure, required fields, ID patterns
        # Cross-reference validation
        ...
```

---

#### Task 4: Create Step Executor
**File:** `prompt_pipeline/step_executor.py`

**Responsibilities:**
- Execute individual steps
- Load prompt from configured file
- Determine required inputs from step config
- Call LLM
- Validate output
- Save to configured output file

**Integration with Step Config:**
```python
class StepExecutor:
    async def execute_step(self, step_name: str, inputs: Dict[str, Path]) -> Path:
        # Get step configuration
        step_config = self.prompt_manager.get_step_config(step_name)
        
        # Load prompt file
        prompt_file = step_config['prompt_file']
        prompt = self.prompt_manager.load_prompt(prompt_file)
        
        # Prepare variables
        variables = self._prepare_variables(inputs, step_config)
        filled_prompt = self.prompt_manager.substitute_variables(prompt, variables)
        
        # Call LLM
        response = await self.llm_client.call_prompt(
            filled_prompt,
            model=self._get_model(step_name)
        )
        
        # Validate
        output_path = self.output_dir / step_config['output_file']
        if step_config['output_type'] == 'json':
            self._validate_json(response, step_config['json_schema'])
        elif step_config['output_type'] == 'yaml':
            self._validate_yaml(response)
        
        # Save
        output_path.write_text(response)
        return output_path
```

---

#### Task 5: Create Pipeline Orchestrator
**File:** `prompt_pipeline/orchestrator.py`

**Key Innovation:** Executes steps in order based on `order` field in config.

**Responsibilities:**
- Load all step configurations
- Sort by `order` field
- Build execution graph based on dependencies
- Execute steps in sequence
- Manage input/output flow between steps

**Execution Logic:**
```python
class PipelineOrchestrator:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.steps = self._load_steps()
    
    def _load_steps(self) -> List[Dict[str, Any]]:
        """Load and sort steps by order."""
        config = yaml.safe_load(open(self.config_path))
        steps = list(config['steps'].values())
        return sorted(steps, key=lambda s: s['order'])
    
    async def run_pipeline(self, nl_spec_path: Path, output_dir: Path):
        # Track outputs
        outputs = {}
        current_file = nl_spec_path
        
        for step in self.steps:
            step_name = step['name']
            
            # Check if this step should be included
            if step_name in ['step2', 'step3']:
                # Revision steps are manual, skip in auto-pipeline
                continue
            
            # Prepare inputs
            inputs = self._prepare_inputs(step, outputs, current_file)
            
            # Execute step
            result_path = await self.step_executor.execute_step(
                step_name, 
                inputs
            )
            
            # Track output
            outputs[step_name] = result_path
            current_file = result_path
        
        # Import to TypeDB if requested
        if self.import_database:
            await self.import_to_typedb(output_dir)
```

---

#### Task 6: Create CLI Structure
**Files:** `prompt_pipeline_cli/main.py`, `prompt_pipeline_cli/arguments.py`

**Commands:**
```bash
# Individual steps
prompt-pipeline run-step step1 --nl-spec doc/spec.md
prompt-pipeline run-step stepC3 --spec-file yaml/spec_1.yaml
prompt-pipeline run-step stepC4 --spec-file yaml/spec_1.yaml --concepts-dir json/

# Full pipeline (skips revision steps 2-3)
prompt-pipeline run-pipeline --nl-spec doc/spec.md --import-database todo_app

# Validation
prompt-pipeline validate json/ --strict

# Import
prompt-pipeline import json/ --database todo_app --wipe

# Config
prompt-pipeline config show
prompt-pipeline config set steps.stepC3.prompt_file "custom.md"
```

### Phase 2: CLI Implementation (Tasks 7-11)

#### Task 7: run-step Command
- Uses step configuration to load prompt file
- Auto-discovers required inputs from directory
- Example: `--concepts-dir json/` finds `json/concepts.json`

#### Task 8: run-pipeline Command
- Loads all steps by order
- Excludes revision steps (2-3)
- Builds execution chain automatically

#### Task 9: validate and import Commands
- Validation uses step-configured schemas
- Import uses existing typedb_import logic

#### Task 10: Main Entry Point
- Click-based CLI with command groups
- Registered in pyproject.toml as `prompt-pipeline`

#### Task 11: Config Management
- Load/save pipeline_config.yaml
- Allow dynamic configuration updates

### Phase 3: Configuration & Testing (Tasks 12-18)

#### Task 12-14: Configuration, Integration, Tests
- Default config file with all step definitions
- Integration with TypeDB import
- Comprehensive test suite

#### Task 15-18: Documentation & Future
- Updated implementation guide
- Development utilities
- Future: compression, caching, batch

## Usage Examples

### Example 1: Modify Step Behavior (No Code Changes)

**Before:** Steps use default prompt files

**After:** Custom prompt file for stepC3
```yaml
# In pipeline_config.yaml
steps:
  stepC3:
    prompt_file: "my_concepts_prompt.md"
```

### Example 2: Add Custom Step

```yaml
steps:
  custom_validation:
    name: "custom_validation"
    prompt_file: "validate_schema.md"
    order: 8
    output_file: "validation_report.json"
    output_type: "json"
    requires_nl_spec: false
    requires_spec_file: true
    dependencies: ["stepC3", "stepC5"]
    json_schema: "schemas/validation_schema.json"
```

### Example 3: Rename Steps

```yaml
steps:
  extract_concepts:  # Was stepC3
    name: "extract_concepts"
    prompt_file: "prompt_step_C3.md"
    order: 4
    output_file: "concepts.json"
    # ... etc
```

### Example 4: Change Output Structure

```yaml
steps:
  stepC3:
    output_file: "v2/concepts.json"  # Subdirectory
```

## Configuration File Structure

### Complete pipeline_config.yaml

```yaml
# Flexible Step Configuration
steps:
  step1:
    name: "step1"
    prompt_file: "prompt_step1_v2.md"
    order: 1
    output_file: "spec_1.yaml"
    output_type: "yaml"
    requires_nl_spec: true
    dependencies: []
    json_schema: null

  step2:
    name: "step2"
    prompt_file: "prompt_step2_v2.md"
    order: 2
    output_file: "spec_formal.md"
    output_type: "md"
    requires_nl_spec: false
    requires_spec_file: true
    dependencies: ["step1"]
    json_schema: null

  step3:
    name: "step3"
    prompt_file: "prompt_step3_v2.md"
    order: 3
    output_file: "revised_spec.md"
    output_type: "md"
    requires_nl_spec: false
    requires_spec_file: true
    dependencies: ["step2"]
    json_schema: null

  stepC3:
    name: "stepC3"
    prompt_file: "prompt_step_C3.md"
    order: 4
    output_file: "concepts.json"
    output_type: "json"
    requires_nl_spec: false
    requires_spec_file: true
    dependencies: []
    json_schema: "schemas/concepts_schema.json"

  stepC4:
    name: "stepC4"
    prompt_file: "prompt_step_C4.md"
    order: 5
    output_file: "aggregations.json"
    output_type: "json"
    requires_nl_spec: false
    requires_spec_file: true
    requires_concepts_file: true
    dependencies: ["stepC3"]
    json_schema: "schemas/aggregations_schema.json"

  stepC5:
    name: "stepC5"
    prompt_file: "prompt_step_C5.md"
    order: 6
    output_file: "messages.json"
    output_type: "json"
    output_files:
      - "messages.json"
      - "messageAggregations.json"
    requires_nl_spec: false
    requires_spec_file: true
    requires_concepts_file: true
    requires_aggregations_file: true
    dependencies: ["stepC3", "stepC4"]
    json_schema: "schemas/messages_schema.json"

  stepD1:
    name: "stepD1"
    prompt_file: "prompt_step_D1.md"
    order: 7
    output_file: "requirements.json"
    output_type: "json"
    requires_nl_spec: false
    requires_spec_file: true
    requires_concepts_file: true
    requires_messages_file: true
    dependencies: ["stepC3", "stepC5"]
    json_schema: "schemas/requirements_schema.json"

# Model levels for each step
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
    1: "qwen/qwen3-235b-a22b-2507"
    2: "mimo/v2-flash"
    3: "moonshotai/kimi-k2-0905"
  stepC4:
    1: "minimax/m2.5"
    2: "mimo/v2-flash"
    3: "moonshotai/kimi-k2-0905"
  stepC5:
    1: "qwen/qwen3-235b-a22b-2507"
    2: "mimo/v2-flash"
    3: "moonshotai/kimi-k2-0905"
  stepD1:
    1: "qwen/qwen3-235b-a22b-2507"
    2: "mimo/v2-flash"
    3: "moonshotai/kimi-k2-0905"

# Validation settings
validation:
  strict: true
  auto_fix: false
  max_auto_fix_attempts: 3

# File locations
paths:
  prompts_dir: "prompts"
  default_output_dir: "pipeline_output"
  schema_file: "doc/typedb_schema_2.tql"

# LLM settings
llm:
  api_key: "${OPENROUTER_API_KEY}"
  max_retries: 3
  timeout: 60
  max_tokens: 4000
  rate_limit_delay: 0.5

# TypeDB settings
typedb:
  url: "http://localhost:8000"
  username: "admin"
  password: "password"

# Import settings
import:
  validate_before_import: true
  create_if_missing: false
  wipe_before_import: false

# Command defaults
defaults:
  model_level: 1
  output_dir: "pipeline_output"
  verbosity: 1
  skip_validation: false
```

## Workflow Patterns

### Pattern 1: Standard Pipeline
```bash
# Step 1: Generate YAML
prompt-pipeline run-step step1 --nl-spec doc/spec.md --output-dir yaml/

# Steps C3, C4, C5, D1: Auto-discover inputs
prompt-pipeline run-step stepC3 --spec-file yaml/spec_1.yaml --output-dir json/
prompt-pipeline run-step stepC4 --spec-file yaml/spec_1.yaml --output-dir json/
prompt-pipeline run-step stepC5 --spec-file yaml/spec_1.yaml --output-dir json/
prompt-pipeline run-step stepD1 --spec-file yaml/spec_1.yaml --output-dir json/
```

### Pattern 2: Full Pipeline (One Command)
```bash
prompt-pipeline run-pipeline \
  --nl-spec doc/spec.md \
  --import-database todo_app \
  --wipe
```

### Pattern 3: Custom Steps
```bash
# With custom step configuration
prompt-pipeline run-pipeline --nl-spec doc/spec.md --config custom_config.yaml
```

## Implementation Checklist

### Before Starting
- [ ] Review current task status
- [ ] Understand all prompt files
- [ ] Check existing TypeDB import logic
- [ ] Review test structure

### During Implementation
- [ ] Follow TDD (tests first)
- [ ] Use type hints everywhere
- [ ] Add comprehensive docstrings
- [ ] Match existing code style
- [ ] Update tasks as you progress

### After Completion
- [ ] All tests pass (80%+ coverage)
- [ ] Integration tests with TypeDB server
- [ ] Documentation is complete
- [ ] Example usage works end-to-end

## Questions Answered

### ✅ 1. OpenRouter API Access
**Answer:** Yes, use OpenRouter API key from environment.

### ✅ 2. Revision Cycle
**Answer:** Manual user control (steps 2-3 are separate commands, not automatic)

### ✅ 3. Validation Strictness
**Answer:** Fail on errors (default), with `--skip-validation` for dev mode

### ✅ 4. Output Directory
**Answer:** User-specified (`--output-dir`), default `pipeline_output/`

### ✅ 5. Model Configuration
**Answer:** 3 levels with OpenRouter models:
- Level 1: `minimax/m2.5`, `mimo/v2-flash`, `moonshotai/kimi-k2-0905`, `qwen/qwen3-235b-a22b-2507`
- Level 2: TBD (balanced)
- Level 3: TBD (best)

### ✅ 6. TypeDB Import
**Answer:** Automatic with `--import-database` flag

### ✅ 7. Prompt Template Versioning
**Answer:** Git-based (no code changes)

### ✅ 8. Compression Strategy
**Answer:** Deferred (future task)

### ✅ 9. Error Recovery
**Answer:** Retry + partial state saving

### ✅ 10. Development Mode
**Answer:** Yes, via atomic switches (`--skip-validation`, `--model-level 1`, `--dry-run`)

### ✅ 11. FLEXIBLE STEP CONFIGURATION
**Answer:** **MAJOR NEW FEATURE** - All steps configured in YAML, no code changes needed to:
- Change step names
- Associate different prompt files
- Customize output names
- Add/remove steps
- Change execution order

## Summary

This implementation provides a **fully configurable, flexible prompt pipeline** where:
1. All steps are defined in `pipeline_config.yaml`
2. No code changes needed to customize steps
3. Steps can be renamed, added, removed, reordered
4. Prompt files can be swapped per step
5. Output files can be customized
6. Execution order is dynamic based on `order` field

The system is extensible without touching code - perfect for iteration and experimentation!

**Document Version:** 2.0  
**Last Updated:** 2026-02-18  
**Status:** Proposal for implementation  
**Next:** Start Task 1 (LLM Client Module)
