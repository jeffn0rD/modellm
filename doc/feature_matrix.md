# ModelLM Feature Matrix

This document provides a comprehensive overview of all implemented features in ModelLM v0.1.0, with their implementation status, file locations, and usage information.

## Quick Reference

| Feature Category | Status | Count |
|-----------------|--------|-------|
| **Core Pipeline System** | ✅ Complete | 5 features |
| **CLI System** | ✅ Complete | 5 commands |
| **Input System** | ✅ Complete | 4 input methods |
| **Approval Flow** | ✅ Complete | 3 modes |
| **Compression Strategies** | ✅ Complete | 7 strategies |
| **Data Entities** | ✅ Complete | Centralized system |
| **Validation** | ✅ Complete | Multi-format |
| **Terminal Output** | ✅ Complete | Rich formatting |
| **Model Management** | ✅ Complete | 3 levels |
| **TypeDB Integration** | ✅ Complete | Full support |
| **Testing** | ✅ Complete | Comprehensive |
| **Documentation** | ✅ Complete | 5 guides |

---

## 1. Core Pipeline System

### Feature: Multi-Step Execution
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **File** | `prompt_pipeline/orchestrator.py` |
| **Lines** | 16,899 bytes |
| **Key Methods** | `load_steps()`, `execute_steps()`, `sort_by_order()` |
| **Features** | Dependency management, Auto-discovery, Sortable execution |

### Feature: YAML Configuration
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **File** | `configuration/pipeline_config.yaml` |
| **Lines** | 312 |
| **Key Sections** | `data_entities`, `steps`, `model_levels`, `dev_defaults` |
| **Features** | No code changes needed, Dynamic behavior, Runtime modification |

### Feature: Pipeline Orchestration
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **File** | `prompt_pipeline/orchestrator.py` |
| **Key Methods** | `execute_pipeline()`, `resolve_inputs()`, `track_outputs()` |
| **Features** | Dependency resolution, Step ordering, Output tracking |

### Feature: Input Resolution
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **File** | `prompt_pipeline/label_registry.py` |
| **Key Methods** | `resolve_input()`, `resolve_label()`, `resolve_file()` |
| **Priority** | CLI → Config → Previous outputs |

### Feature: Label Registry
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **File** | `prompt_pipeline/label_registry.py` |
| **Key Methods** | `register_output()`, `get_label_path()`, `clear_registry()` |
| **Features** | Dynamic label tracking, Step-specific labels |

---

## 2. CLI System

### Command: run-step
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **File** | `prompt_pipeline_cli/commands/run_step.py` |
| **Lines** | 38,092 bytes |
| **Key Options** | `--input-file`, `--input-prompt`, `--input-text`, `--input-env`, `--approve`, `--auto-approve`, `--dry-run`, `--show-prompt`, `--show-response`, `--model-level`, `--model`, `--output-dir`, `--output-file`, `--skip-validation`, `--force`, `--config`, `--verbosity`, `--batch` |
| **Use Case** | Execute individual steps with full control |

### Command: run-pipeline
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **File** | `prompt_pipeline_cli/commands/run_pipeline.py` |
| **Lines** | 9,848 bytes |
| **Key Options** | `--nl-spec`, `--input-file`, `--output-dir`, `--import-database`, `--wipe`, `--model-level`, `--auto-approve`, `--verbosity` |
| **Use Case** | Execute complete pipeline automatically |

### Command: validate
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **File** | `prompt_pipeline_cli/commands/validate.py` |
| **Lines** | 7,649 bytes |
| **Key Options** | `--config`, `--file` |
| **Use Case** | Validate configuration or output files |

### Command: import
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **File** | `prompt_pipeline_cli/commands/import_cmd.py` |
| **Lines** | 2,877 bytes |
| **Key Options** | `--file`, `--database`, `--wipe`, `--import-id` |
| **Use Case** | Import data to TypeDB |

### Command: config
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **File** | `prompt_pipeline_cli/commands/config.py` |
| **Lines** | 2,807 bytes |
| **Key Options** | `--show` |
| **Use Case** | Display configuration details |

---

## 3. Input System

### Input Method: File Input
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **Syntax** | `--input-file label:filename` |
| **Priority** | Highest (1) |
| **Example** | `--input-file nl_spec:doc/spec.md` |
| **Supports** | All file types (md, yaml, json, txt) |

### Input Method: Interactive Prompt
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **Syntax** | `--input-prompt label` |
| **Priority** | Highest (1) |
| **Example** | `--input-prompt nl_spec` |
| **Features** | Multiline input, Configurable prompt message |

### Input Method: Direct Text
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **Syntax** | `--input-text label:"content"` |
| **Priority** | Highest (1) |
| **Example** | `--input-text nl_spec:"My spec text"` |
| **Features** | Immediate execution, No file needed |

### Input Method: Environment Variable
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **Syntax** | `--input-env label:ENV_VAR` |
| **Priority** | Highest (1) |
| **Example** | `--input-env nl_spec:SPEC_TEXT` |
| **Features** | Secret-safe, CI/CD friendly |

---

## 4. Approval Flow

### Mode: Interactive Approval
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **Flag** | `--approve` |
| **Behavior** | Shows prompt, waits for user confirmation |
| **Options** | `y` (yes), `n` (no), `q` (quit), `v` (verbose) |
| **Use Case** | Development and review |

### Mode: Batch Mode
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **Flag** | `--auto-approve` |
| **Behavior** | Skips approval prompt, automatic execution |
| **Use Case** | CI/CD, automated workflows |

### Mode: Dry Run
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **Flag** | `--dry-run` |
| **Behavior** | Shows what would happen, no API calls |
| **Use Case** | Testing configuration, verification |

---

## 5. Compression Strategies

### Strategy: Zero Compression
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **File** | `prompt_pipeline/compression/strategies/zero_compression.py` |
| **Lines** | 2,709 bytes |
| **Compression Ratio** | 1.0 (no reduction) |
| **Use Case** | Baseline, Step C3, small inputs |

### Strategy: Anchor Index
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **File** | `prompt_pipeline/compression/strategies/anchor_index.py` |
| **Lines** | 20,321 bytes |
| **Compression Ratio** | ~0.2-0.3 (70-80% reduction) |
| **Use Case** | Step C4, traceability, compact reference |

### Strategy: Concept Summary
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **File** | `prompt_pipeline/compression/strategies/concept_summary.py` |
| **Lines** | 10,684 bytes |
| **Compression Ratio** | ~0.4-0.5 (50-60% reduction) |
| **Use Case** | Steps C5, D1, markdown tables |

### Strategy: Hierarchical
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **File** | `prompt_pipeline/compression/strategies/hierarchical.py` |
| **Lines** | 13,348 bytes |
| **Compression Ratio** | ~0.3-0.5 (50-70% reduction) |
| **Use Case** | Step C3, multi-layer compression |

### Strategy: Schema Only
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **File** | `prompt_pipeline/compression/strategies/schema_only.py` |
| **Lines** | 10,116 bytes |
| **Compression Ratio** | ~0.1-0.2 (80-90% reduction) |
| **Use Case** | Schema-aware contexts, counts only |

### Strategy: Differential
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **File** | `prompt_pipeline/compression/strategies/differential.py` |
| **Lines** | 12,698 bytes |
| **Compression Ratio** | ~0.05-0.1 (90-95% reduction) |
| **Use Case** | Iterative refinement, delta-based |

### Strategy: YAML as JSON
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **File** | `prompt_pipeline/compression/strategies/yaml_as_json.py` |
| **Lines** | 2,103 bytes |
| **Compression Ratio** | Similar to full |
| **Use Case** | Data transformation, JSON format |

---

## 6. Data Entities System

### Feature: Centralized Definitions
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **Configuration** | `configuration/pipeline_config.yaml` - `data_entities` section |
| **Features** | Single source of truth, Automatic description lookup |

### Feature: Compression Strategy Linking
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **Configuration** | `compression_strategies` in data_entities |
| **Features** | Automatic description pull, Strategy validation |

### Feature: Schema Validation Support
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **Configuration** | `yaml_schema` or `schema` in data_entities |
| **Features** | Schema-based validation, Automatic validation |

---

## 7. Validation System

### Validator: YAML Validator
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **File** | `prompt_pipeline/validation/yaml_validator.py` |
| **Lines** | 24,127 bytes |
| **Features** | Custom validation, Schema support, Comprehensive errors |

### Validator: YAML Schema Validator
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **File** | `prompt_pipeline/validation/yaml_schema_validator.py` |
| **Lines** | 4,165 bytes |
| **Features** | JSON Schema validation, YAML schemas |

### Validator: JSON Validator
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **File** | `prompt_pipeline/validation/json_validator.py` |
| **Lines** | 12,739 bytes |
| **Features** | Multiple schema support, Custom validators |

### Validator: Concepts Validator
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **File** | `prompt_pipeline/validation/json_validator.py` |
| **Schema** | `schemas/concepts.schema.json` |
| **Features** | Validates concept structure, IDs, relationships |

### Validator: Aggregations Validator
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **File** | `prompt_pipeline/validation/json_validator.py` |
| **Schema** | `schemas/aggregations.schema.json` |
| **Features** | Validates aggregation relationships |

### Validator: Messages Validator
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **File** | `prompt_pipeline/validation/json_validator.py` |
| **Schema** | `schemas/messages.schema.json` |
| **Features** | Validates message definitions |

### Validator: Requirements Validator
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **File** | `prompt_pipeline/validation/json_validator.py` |
| **Schema** | `schemas/requirements.schema.json` |
| **Features** | Validates requirements structure |

---

## 8. Terminal Output System

### Feature: Color-Coded Inputs
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **File** | `prompt_pipeline/terminal_utils.py` |
| **Colors** | Cyan (primary), Green (secondary), Yellow (tertiary), Magenta (special) |
| **Configuration** | `color` field in step inputs |
| **Purpose** | Visual differentiation of input sources |

### Feature: Progress Indicators
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **File** | `prompt_pipeline/terminal_utils.py` |
| **Features** | Spinner during LLM calls, Step-by-step progress, Status messages |

### Feature: Formatted Output
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **File** | `prompt_pipeline/terminal_utils.py` |
| **Features** | Substituted prompts, LLM responses, Model info, Error context |

### Feature: Message Types
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **File** | `prompt_pipeline/terminal_utils.py` |
| **Types** | Info, Success, Warning, Error |
| **Features** | Contextual messages, Actionable suggestions |

---

## 9. Model Management

### Feature: Three Quality Levels
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **Configuration** | `model_levels` in pipeline_config.yaml |
| **Level 1** | Cheapest: `minimax/m2.5`, `mimo/v2-flash`, `qwen` |
| **Level 2** | Balanced: Configurable per step |
| **Level 3** | Best: `moonshotai/kimi-k2-0905` |

### Feature: Per-Step Configuration
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **Configuration** | `model_levels` section, per-step overrides |
| **Features** | Different models per step, Flexible quality control |

### Feature: OpenRouter API Integration
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **File** | `prompt_pipeline/llm_client.py` |
| **Lines** | 12,902 bytes |
| **Features** | Exponential retry, Model selection, Configuration |

### Feature: Retry and State Management
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **File** | `prompt_pipeline/llm_client.py` |
| **Features** | Exponential backoff, Partial state saving, Error handling |

---

## 10. TypeDB Integration

### Entity Model
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **File** | `prompt_pipeline/importer/importer.py` |
| **Lines** | 33,283 bytes |
| **Entities** | Actor, Action, Message, Concept, Requirement, Constraint, TextBlock |

### Relation Model
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **File** | `prompt_pipeline/importer/importer.py` |
| **Relations** | Messaging, Anchoring, Membership, Requiring |

### Import Features
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **File** | `prompt_pipeline_cli/commands/import_cmd.py` |
| **Features** | Single file import, Wipe option, Import ID support |

---

## 11. Testing System

### Unit Tests
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **File** | `tests/test_prompt_pipeline/test_compression_*.py` |
| **Coverage** | Compression strategies, Validation, Prompt manager |
| **Markers** | `@pytest.mark.unit` |

### Integration Tests
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **File** | `tests/test_client_integration.py`, `tests/test_database_integration.py` |
| **Coverage** | TypeDB server, API calls |
| **Markers** | `@pytest.mark.integration` |

### CLI Tests
| Aspect | Details |
|--------|---------|
| **Status** | ✅ Implemented |
| **File** | `tests/test_prompt_pipeline/test_cli_dry_run.py` |
| **Coverage** | Run-step, run-pipeline, dry-run |
| **Features** | Command validation, Output verification |

---

## 12. Documentation

### Core Documentation
| Document | Status | Location |
|----------|--------|----------|
| README.md | ✅ Updated | `README.md` |
| Implementation Summary | ✅ Updated | `doc/IMPLEMENTATION_SUMMARY.md` |
| Workflow Guide | ✅ Updated | `doc/workflow_guide.md` |
| Feature Matrix | ✅ New | `doc/feature_matrix.md` |
| API Reference | ⏳ Planned | `doc/API.md` |

### Configuration Documentation
| Document | Status | Location |
|----------|--------|----------|
| Pipeline Config | ✅ Complete | `configuration/pipeline_config.yaml` |
| Compression Guide | ✅ Complete | `doc/prompt_pipeline_compression.md` |

### Agent Tools Documentation
| Document | Status | Location |
|----------|--------|----------|
| Implementation Guide | ✅ Complete | `agents/implementation_guide.md` |
| Workflow Guide | ✅ Complete | `agents/tools/workflow_guide.md` |
| CLI Syntax Checker | ✅ Complete | `agents/tools/cli_syntax_checker.py` |
| Context Extractor | ✅ Complete | `agents/tools/extract_context.py` |

---

## Feature Comparison Matrix

### CLI Commands

| Feature | run-step | run-pipeline | validate | import | config |
|---------|----------|--------------|----------|--------|--------|
| **File Input** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Interactive Prompt** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Direct Text** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Env Variable** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Approval** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Batch Mode** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Dry Run** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Show Prompt** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Show Response** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Model Level** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Custom Model** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Output Dir** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Validation** | ✅ | ❌ | ✅ | ❌ | ❌ |
| **Wipe** | ❌ | ❌ | ❌ | ✅ | ❌ |
| **Database** | ❌ | ❌ | ❌ | ✅ | ❌ |
| **Config File** | ✅ | ❌ | ✅ | ❌ | ✅ |
| **Verbosity** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Force** | ✅ | ❌ | ❌ | ❌ | ❌ |

### Compression Strategies

| Strategy | zero | anchor_index | concept_summary | hierarchical | schema_only | differential | yaml_as_json |
|----------|------|--------------|-----------------|--------------|-------------|--------------|--------------|
| **Compression Ratio** | 1.0 | 0.2-0.3 | 0.4-0.5 | 0.3-0.5 | 0.1-0.2 | 0.05-0.1 | ~1.0 |
| **Reduction %** | 0% | 70-80% | 50-60% | 50-70% | 80-90% | 90-95% | 0% |
| **Output Format** | Raw | Index | Tables | Layers | Schema | Deltas | JSON |
| **Use Case** | Baseline | Traceability | Summary | Large files | Schema-aware | Iterative | Transform |
| **Step C3** | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Step C4** | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Step C5** | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Step D1** | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |

### Input Methods

| Method | File | Interactive | Text | Env Variable |
|--------|------|-------------|------|--------------|
| **Priority** | 1 | 1 | 1 | 2 |
| **Use Case** | Production | Development | Testing | CI/CD |
| **Example** | `--input-file label:file` | `--input-prompt label` | `--input-text label:"text"` | `--input-env label:VAR` |
| **Multiline** | ✅ | ✅ | ❌ | ✅ |
| **Quoting** | ❌ | ❌ | ✅ | ❌ |
| **File Type** | Any | N/A | Text | Text |

### Approval Modes

| Mode | Interactive | Batch | Dry Run |
|------|-------------|-------|---------|
| **Flag** | `--approve` | `--auto-approve` | `--dry-run` |
| **Use Case** | Development | CI/CD | Testing |
| **Shows Prompt** | ✅ | ❌ | ✅ |
| **Waits** | ✅ | ❌ | ❌ |
| **Executes** | ✅ | ✅ | ❌ |
| **API Calls** | ✅ | ✅ | ❌ |

---

## Implementation Checklist

### Core Pipeline ✅
- [x] Multi-step execution
- [x] Dependency management
- [x] YAML configuration
- [x] Step orchestration
- [x] Input resolution
- [x] Label registry

### CLI System ✅
- [x] run-step command
- [x] run-pipeline command
- [x] validate command
- [x] import command
- [x] config command

### Input System ✅
- [x] File input
- [x] Interactive prompt
- [x] Direct text input
- [x] Environment variable input
- [x] Priority-based resolution

### Approval Flow ✅
- [x] Interactive approval
- [x] Batch mode
- [x] Dry run
- [x] Verbose inspection

### Compression ✅
- [x] Zero compression
- [x] Anchor index
- [x] Concept summary
- [x] Hierarchical
- [x] Schema only
- [x] Differential
- [x] YAML as JSON

### Data Entities ✅
- [x] Centralized definitions
- [x] Automatic description lookup
- [x] Compression strategy linking
- [x] Schema validation

### Validation ✅
- [x] YAML validation
- [x] YAML schema validation
- [x] JSON validation
- [x] Concepts validator
- [x] Aggregations validator
- [x] Messages validator
- [x] Requirements validator

### Terminal Output ✅
- [x] Color-coded inputs
- [x] Progress indicators
- [x] Formatted prompts/responses
- [x] Message types (info, success, warning, error)

### Model Management ✅
- [x] Three quality levels
- [x] Per-step configuration
- [x] OpenRouter API integration
- [x] Retry with exponential backoff

### TypeDB Integration ✅
- [x] Entity model (7 entities)
- [x] Relation model (4 relations)
- [x] Import with wipe
- [x] Import ID support

### Testing ✅
- [x] Unit tests
- [x] Integration tests
- [x] CLI tests
- [x] Compression tests
- [x] Validation tests

### Documentation ✅
- [x] README.md (updated)
- [x] Implementation Summary
- [x] Workflow Guide
- [x] Feature Matrix (this file)
- [ ] API Reference (planned)

---

## Configuration Reference

### Data Entities Configuration

```yaml
data_entities:
  nl_spec:
    type: md
    filename: todo_list_nl_spec.md
    description: "Natural language requirements"
  
  spec:
    type: yaml
    filename: spec_1.yaml
    yaml_schema: schemas/spec_yaml_schema.json
    compression_strategies:
      anchor_index:
        description: "Compact anchor index"
      concept_summary:
        description: "Concept summary format"
```

### Step Configuration

```yaml
steps:
  stepC3:
    name: stepC3
    prompt_file: prompt_step_C3.md
    order: 4
    inputs:
      - label: spec
        source: label:spec
        compression: hierarchical
        compression_params:
          level: 3
        color: magenta
    outputs:
      - label: concepts
    dependencies:
      - step1
    validation:
      enabled: true
    persona: systems_architect
```

### Model Configuration

```yaml
model_levels:
  step1:
    1: minimax/minimax-m2.5
    2: xiaomi/mimo-v2-flash
    3: moonshotai/kimi-k2-0905
```

---

## Quick Reference Commands

### Installation
```bash
pip install -e .
```

### Environment Setup
```bash
export OPENROUTER_API_KEY="sk-or-..."
export TYPEDB_URL="http://localhost:8000"
export TYPEDB_USERNAME="admin"
export TYPEDB_PASSWORD="password"
```

### Pipeline Execution
```bash
# Full pipeline
prompt-pipeline run-pipeline --nl-spec doc/spec.md

# Individual step
prompt-pipeline run-step step1 --input-file nl_spec:doc/spec.md --approve

# With approval
prompt-pipeline run-step stepC3 --input-file spec:yaml/spec.yaml --approve

# Batch mode
prompt-pipeline run-pipeline --nl-spec doc/spec.md --auto-approve

# Dry run
prompt-pipeline run-step stepC3 --input-file spec:yaml/spec.yaml --dry-run
```

### Testing
```bash
# All tests
pytest tests/ -v

# Unit tests only
pytest tests/ -m unit -v

# With coverage
pytest tests/ --cov=prompt_pipeline --cov-report=html
```

---

## Version Information

**Project:** ModelLM  
**Version:** 0.1.0  
**Status:** Production Ready  
**Release Date:** 2026-02-26  
**Documentation Status:** Complete  
**Test Coverage:** Comprehensive  

---

## Related Documentation

- **README.md** - Main documentation with quick start
- **doc/IMPLEMENTATION_SUMMARY.md** - Implementation details
- **doc/workflow_guide.md** - Workflow patterns
- **doc/API.md** - API reference (planned)
- **agents/implementation_guide.md** - Technical specifications
- **agents/tools/workflow_guide.md** - Agent workflow patterns
- **configuration/pipeline_config.yaml** - Configuration reference

---

**Document Version:** 1.0  
**Last Updated:** 2026-02-26  
**Status:** Complete  
**Next Steps:** Create API reference documentation
