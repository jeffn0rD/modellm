# Prompt Pipeline Guide

Comprehensive documentation for the `prompt-pipeline` CLI tool and its underlying components.

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Architecture](#architecture)
5. [Configuration](#configuration)
6. [Pipeline Steps](#pipeline-steps)
7. [CLI Commands](#cli-commands)
8. [Model Selection](#model-selection)
9. [Validation](#validation)
10. [TypeDB Integration](#typedb-integration)
11. [Environment Variables](#environment-variables)
12. [Troubleshooting](#troubleshooting)

---

## Overview

The **Prompt Pipeline** is a flexible CLI tool for transforming natural language (NL) specifications into structured data for TypeDB knowledge graphs. It processes specifications through a series of configurable steps, each using an LLM to perform specific transformations.

### Key Features

- **Modular Step Architecture**: Each transformation step is independent and configurable
- **Multi-Level Model Selection**: Choose from cheap/fast (level 1), balanced (level 2), or best (level 3) models
- **Input/Output Validation**: JSON Schema and YAML validation at each step
- **TypeDB Integration**: Import results directly into TypeDB databases
- **Flexible Configuration**: YAML-based configuration with environment variable substitution
- **Retry & Error Handling**: Automatic retry with exponential backoff, partial state saving on failure

---

## Installation

### Prerequisites

- Python 3.8+
- OpenRouter API key (for LLM calls)

### Install from Source

```bash
# Clone the repository
cd modellm

# Install in editable mode (recommended for development)
pip install -e .

# This automatically registers the `prompt-pipeline` CLI command
```

### Verify Installation

```bash
# Show help
prompt-pipeline --help

# Show version (if available)
prompt-pipeline --version
```

---

## Quick Start

### 1. Set Up Environment Variables

```bash
# Required: OpenRouter API key
export OPENROUTER_API_KEY="your-api-key-here"

# Optional: TypeDB connection (if using import features)
export TYPEDB_URL="http://localhost:8000"
export TYPEDB_USERNAME="admin"
export TYPEDB_PASSWORD="password"
```

### 2. Run the Full Pipeline

```bash
# Process a natural language specification
prompt-pipeline run-pipeline my_spec.txt --output-dir ./output

# With custom model level (1=fast, 2=balanced, 3=best)
prompt-pipeline run-pipeline my_spec.txt --model-level 2
```

### 3. Validate Outputs

```bash
# Validate generated YAML
prompt-pipeline validate output/spec_1.yaml

# Validate generated JSON (auto-detects type)
prompt-pipeline validate output/concepts.json
```

### 4. Import to TypeDB

```bash
# Import pipeline outputs to TypeDB
prompt-pipeline import --file output/requirements.json --database mydb

# With database creation
prompt-pipeline import --file output/requirements.json --database mydb --create
```

---

## Architecture

The prompt pipeline consists of several interconnected modules:

```
┌─────────────────────────────────────────────────────────────────┐
│                        prompt-pipeline CLI                      │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ PromptManager │    │  LLM Client   │    │ StepExecutor  │
└───────────────┘    └───────────────┘    └───────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   Config      │    │ OpenRouter    │    │  Validators   │
│   (YAML)      │    │   API         │    │  (YAML/JSON)  │
└───────────────┘    └───────────────┘    └───────────────┘
                                                      │
                                    ┌─────────────────┴─────────────────┐
                                    ▼                               ▼
                            ┌───────────────┐              ┌───────────────┐
                            │ Pipeline      │              │    TypeDB     │
                            │ Orchestrator  │              │   Integration │
                            └───────────────┘              └───────────────┘
```

### Core Modules

| Module | Purpose |
|--------|---------|
| `prompt_pipeline_cli` | CLI command entry points |
| `prompt_pipeline.prompt_manager` | Load prompts, manage step configs |
| `prompt_pipeline.llm_client` | OpenRouter API wrapper with retry logic |
| `prompt_pipeline.step_executor` | Execute individual pipeline steps |
| `prompt_pipeline.orchestrator` | Coordinate multi-step pipeline execution |
| `prompt_pipeline.typedb_integration` | TypeDB import functionality |
| `prompt_pipeline.validation` | YAML and JSON validators |

---

## Configuration

### Configuration File Location

The pipeline uses `configuration/pipeline_config.yaml` by default. You can override this:

1. **CLI flag**: `--config path/to/config.yaml`
2. **Environment variable**: `PROMPT_PIPELINE_CONFIG=/path/to/config.yaml`
3. **Project local**: `./configuration/pipeline_config.yaml`
4. **User global**: `~/.prompt-pipeline/config.yaml`

### Configuration Structure

```yaml
# ============================================================
# Pipeline Steps Configuration
# ============================================================
steps:
  step1:
    name: "step1"
    prompt_file: "prompt_step1_v2.md"
    order: 1
    output_file: "spec_1.yaml"
    output_type: "yaml"
    requires_nl_spec: true
    dependencies: []

  # ... more steps ...

# ============================================================
# Model Selection by Step and Level
# ============================================================
model_levels:
  step1:
    1: "minimax/m2.5"           # Fast/cheap
    2: "mimo/v2-flash"          # Balanced
    3: "moonshotai/kimi-k2-0905" # Best quality

# ============================================================
# LLM Settings
# ============================================================
llm:
  api_key: "${OPENROUTER_API_KEY}"  # Environment variable
  max_retries: 3
  timeout: 60
  max_tokens: 4000
  rate_limit_delay: 0.5

# ============================================================
# TypeDB Settings
# ============================================================
typedb:
  url: "http://localhost:8000"
  username: "admin"
  password: "password"

# ============================================================
# Validation Settings
# ============================================================
validation:
  strict: true
  auto_fix: false
  max_auto_fix_attempts: 3

# ============================================================
# Output Settings
# ============================================================
output:
  default_verbosity: 1
  colors: true
  save_partial_on_failure: true
```

### Environment Variable Substitution

Configuration values support environment variable substitution using the `${VAR_NAME}` syntax:

```yaml
llm:
  api_key: "${OPENROUTER_API_KEY}"

typedb:
  url: "${TYPEDB_URL}"
  username: "${TYPEDB_USERNAME}"
  password: "${TYPEDB_PASSWORD}"
```

---

## Pipeline Steps

The pipeline consists of multiple steps that transform specifications through different stages:

### Step Overview

| Step | Name | Input | Output | Description |
|------|------|-------|--------|-------------|
| step1 | NL → YAML | NL spec | `spec_1.yaml` | Convert natural language spec to structured YAML |
| step2 | YAML → Formal | `spec_1.yaml` | `spec_formal.md` | Convert to formal specification (revision cycle) |
| step3 | Revision | `spec_formal.md` | `revised_spec.md` | Revision cycle (manual step) |
| stepC3 | Extract Concepts | Formal spec | `concepts.json` | Extract entity concepts |
| stepC4 | Define Aggregations | Concepts | `aggregations.json` | Define action aggregations |
| stepC5 | Define Messages | Concepts + Aggregations | `messages.json` | Define message structures |
| stepD1 | Extract Requirements | Formal spec + Concepts + Messages | `requirements.json` | Extract functional requirements |

### Step Dependencies

```
nl_spec
    │
    ▼
step1 ─────────────► spec_1.yaml
    │                     │
    │                     ▼
    │               step2 ────────────► spec_formal.md
    │                     │                   │
    │                     │                   ▼
    │                     │               step3 ───────────► revised_spec.md
    │                     │                   │
    └─────────────────────┼───────────────────┘
                          │
                          ▼
                    stepC3 ────────────► concepts.json
                          │
                          ▼
                    stepC4 ────────────► aggregations.json
                          │                   │
                          │                   ▼
                          │             stepC5 ────────────► messages.json
                          │                   │                   │
                          │                   └───────────────────┼───────────────────┐
                          │                                       │                   ▼
                          │                                       │             stepD1 ───► requirements.json
                          └───────────────────────────────────────┴───────────────────┘
```

### Running Individual Steps

```bash
# Run step1 with NL spec input
prompt-pipeline run-step step1 --nl-spec my_spec.txt

# Run stepC3 with specification file
prompt-pipeline run-step stepC3 --spec-file output/spec_1.yaml

# Run stepC5 with multiple inputs
prompt-pipeline run-step stepC5 \
  --spec-file output/spec_formal.md \
  --concepts-file output/concepts.json \
  --aggregations-file output/aggregations.json
```

### Automatic Input Discovery

If you don't specify input files, the pipeline will automatically discover them from the output directory:

```bash
# Automatically finds concepts.json, aggregations.json, etc.
prompt-pipeline run-step stepD1 --output-dir ./output
```

---

## CLI Commands

### Global Options

| Option | Description |
|--------|-------------|
| `--config PATH` | Configuration file path (default: `configuration/pipeline_config.yaml`) |
| `-v, --verbosity LEVEL` | Verbosity level: 0=quiet, 1=normal, 2=verbose, 3=debug (default: 1) |

### run-pipeline

Run the full pipeline from a natural language specification.

```bash
prompt-pipeline run-pipeline NL_SPEC_FILE [OPTIONS]
```

**Arguments:**
- `NL_SPEC_FILE`: Path to the natural language specification file

**Options:**
| Option | Description |
|--------|-------------|
| `--output-dir PATH` | Output directory (default: `pipeline_output/`) |
| `--model-level LEVEL` | Model quality level: 1=fast/cheap, 2=balanced, 3=best (default: 1) |
| `--skip-validation` | Skip output validation |
| `--import-database NAME` | Import results to TypeDB database |
| `--wipe` | Wipe database before import |
| `--create` | Create database if it doesn't exist |
| `--dry-run` | Show what would happen without executing |

**Examples:**

```bash
# Basic usage
prompt-pipeline run-pipeline my_spec.txt

# With high-quality model and custom output
prompt-pipeline run-pipeline my_spec.txt --model-level 3 --output-dir ./results

# Import to TypeDB after pipeline
prompt-pipeline run-pipeline my_spec.txt --import-database mydb --create
```

### run-step

Run a single pipeline step.

```bash
prompt-pipeline run-step STEP_NAME [OPTIONS]
```

**Arguments:**
- `STEP_NAME`: Name of the step (e.g., `step1`, `stepC3`, `stepD1`)

**Options:**
| Option | Description |
|--------|-------------|
| `--nl-spec PATH` | NL specification file |
| `--spec-file PATH` | Specification file (YAML/Markdown) |
| `--concepts-file PATH` | Concepts JSON file |
| `--aggregations-file PATH` | Aggregations JSON file |
| `--messages-file PATH` | Messages JSON file |
| `--requirements-file PATH` | Requirements JSON file |
| `--output-dir PATH` | Output directory |
| `--model-level LEVEL` | Model quality level |
| `--model NAME` | Specific model name (overrides --model-level) |
| `--skip-validation` | Skip output validation |
| `--dry-run` | Show what would happen without executing |

**Examples:**

```bash
# Run first step
prompt-pipeline run-step step1 --nl-spec my_spec.txt

# Run concept extraction with specific model
prompt-pipeline run-step stepC3 --spec-file output/spec_formal.md --model-level 3

# Re-run requirements extraction
prompt-pipeline run-step stepD1 \
  --spec-file output/spec_formal.md \
  --concepts-file output/concepts.json \
  --messages-file output/messages.json
```

### validate

Validate pipeline output files against their schemas.

```bash
prompt-pipeline validate FILE [OPTIONS]
```

**Arguments:**
- `FILE`: Path to the file to validate

**Options:**
| Option | Description |
|--------|-------------|
| `--type TYPE` | Validation type: `yaml`, `concepts`, `aggregations`, `messages`, `requirements`, `auto` (default: auto) |
| `--strict` | Fail on warnings as well as errors |

**Examples:**

```bash
# Auto-detect validation type
prompt-pipeline validate output/concepts.json

# Explicit validation type
prompt-pipeline validate output/spec_1.yaml --type yaml

# Strict mode (fail on warnings)
prompt-pipeline validate output/requirements.json --strict
```

### import

Import generated files to TypeDB.

```bash
prompt-pipeline import [OPTIONS]
```

**Options:**
| Option | Description |
|--------|-------------|
| `--file PATH` | File to import (YAML or JSON) |
| `--database NAME` | TypeDB database name |
| `--create` | Create database if it doesn't exist |
| `--wipe` | Wipe database before import |
| `--config PATH` | Configuration file path |

**Examples:**

```bash
# Import requirements to database
prompt-pipeline import --file output/requirements.json --database mydb

# Create database if needed
prompt-pipeline import --file output/requirements.json --database newdb --create

# Wipe and reimport
prompt-pipeline import --file output/requirements.json --database mydb --wipe
```

### config

Show or manage configuration.

```bash
prompt-pipeline config [OPTIONS]
```

**Options:**
| Option | Description |
|--------|-------------|
| `--show` | Display current configuration |
| `--get KEY` | Get specific configuration value |
| `--set KEY VALUE` | Set configuration value (not persisted) |

**Examples:**

```bash
# Show full configuration
prompt-pipeline config --show

# Get specific value
prompt-pipeline config --get defaults.model_level
```

---

## Model Selection

### Model Levels

The pipeline supports three model quality levels:

| Level | Description | Use Case |
|-------|-------------|----------|
| 1 | Fast/Cheap | Development, testing, quick iteration |
| 2 | Balanced | Regular use, production with cost constraints |
| 3 | Best Quality | Production, critical outputs |

### Default Model Mappings

Model selection can be configured per-step in the configuration file:

```yaml
model_levels:
  step1:
    1: "minimax/m2.5"
    2: "mimo/v2-flash"
    3: "moonshotai/kimi-k2-0905"

  stepC3:
    1: "qwen"
    2: "mimo/v2-flash"
    3: "moonshotai/kimi-k2-0905"
```

### Specifying Models

**Via Level:**
```bash
prompt-pipeline run-pipeline spec.txt --model-level 2
```

**Direct Model Name:**
```bash
prompt-pipeline run-step stepC3 --model openai/gpt-4-turbo
```

### Available Models (OpenRouter)

Popular models available through OpenRouter:

| Model | Provider | Strengths |
|-------|----------|-----------|
| `minimax/m2.2` | MiniMax | Fast, cost-effective |
| `minimax/m2.5` | MiniMax | Balanced |
| `mimo/v2-flash` | Mimo | Fast reasoning |
| `moonshotai/kimi-k2-0905` | Moonshot | High quality |
| `openai/gpt-4o` | OpenAI | Best overall |
| `anthropic/claude-3.5-sonnet` | Anthropic | Excellent reasoning |
| `qwen` | Qwen | Open source option |

---

## Validation

### Validation Types

| Type | Schema | Description |
|------|--------|-------------|
| YAML | Custom | Validates specification YAML structure |
| Concepts | `schemas/concepts_schema.json` | Validates extracted concepts |
| Aggregations | `schemas/aggregations_schema.json` | Validates action aggregations |
| Messages | `schemas/messages_schema.json` | Validates message definitions |
| Requirements | `schemas/requirements_schema.json` | Validates functional requirements |

### Validation Rules

**YAML Validation (Step 1):**
- Required fields: `specification.id`, `specification.title`, `specification.sections`
- ID patterns:
  - Anchor: `^AN\d+$`
  - Section: `^S\d+$`
  - Concept: `^C\d+$`

**JSON Validation (Steps C3-C5, D1):**

*Concepts:*
- Required fields: `type`, `id`, `label`, `description`
- ID patterns:
  - Actor: `^A\d+$`
  - Action: `^ACT\d+$`
  - DataEntity: `^DE\d+$`

*Requirements:*
- Required fields: `id`, `type`, `label`, `description`, `priority`
- ID pattern: `^REQ-[a-zA-Z0-9_.]+$`
- Types: `functional`, `nonfunctional`, `ui`, `future-functional`
- Priorities: `must`, `should`, `could`

### Running Validation

```bash
# Validate a specific file
prompt-pipeline validate output/spec_1.yaml --type yaml

# Validate all outputs in directory
for f in output/*; do
  prompt-pipeline validate "$f"
done

# Strict validation (fail on warnings)
prompt-pipeline validate output/requirements.json --strict
```

---

## TypeDB Integration

### Prerequisites

1. Running TypeDB server (default: `http://localhost:8000`)
2. Valid credentials (default: `admin`/`password`)
3. Schema loaded (see `doc/typedb_schema_2.tql`)

### Import Process

```bash
# Import requirements to TypeDB
prompt-pipeline import \
  --file output/requirements.json \
  --database mydb \
  --create
```

### Database Management

```bash
# Create database before import
prompt-pipeline import --file data.json --database newdb --create

# Wipe existing data
prompt-pipeline import --file data.json --database mydb --wipe

# Both create and wipe
prompt-pipeline import --file data.json --database newdb --create --wipe
```

### Environment Configuration

```bash
export TYPEDB_URL="http://localhost:8000"
export TYPEDB_USERNAME="admin"
export TYPEDB_PASSWORD="your-password"
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | Yes | API key for OpenRouter LLM service |
| `TYPEDB_URL` | No* | TypeDB server URL (default: `http://localhost:8000`) |
| `TYPEDB_USERNAME` | No* | TypeDB username (default: `admin`) |
| `TYPEDB_PASSWORD` | No* | TypeDB password (default: `password`) |
| `PROMPT_PIPELINE_CONFIG` | No | Custom configuration file path |

*Only required when using TypeDB import features.

---

## Troubleshooting

### Common Issues

#### 1. "API key not provided"

**Problem:** OpenRouter API key is not set.

**Solution:**
```bash
export OPENROUTER_API_KEY="your-api-key"
```

#### 2. "Step execution failed: Missing required input"

**Problem:** Required input file not specified or not found.

**Solution:**
```bash
# Provide required input explicitly
prompt-pipeline run-step stepC3 --spec-file path/to/spec.yaml
```

#### 3. "Validation failed"

**Problem:** Output doesn't match expected schema.

**Solution:**
```bash
# Run with verbose output to see validation errors
prompt-pipeline -v 2 run-step stepC3 --spec-file spec.yaml

# Skip validation if needed
prompt-pipeline run-step stepC3 --spec-file spec.yaml --skip-validation
```

#### 4. "TypeDB connection failed"

**Problem:** Cannot connect to TypeDB server.

**Solution:**
```bash
# Check TypeDB is running
curl http://localhost:8000

# Verify credentials
export TYPEDB_URL="http://localhost:8000"
export TYPEDB_USERNAME="admin"
export TYPEDB_PASSWORD="password"
```

#### 5. "Model rate limited"

**Problem:** Too many requests to LLM API.

**Solution:**
```bash
# Increase rate limit delay in config
# Or use a different model
prompt-pipeline run-pipeline spec.txt --model-level 1
```

### Debug Mode

Enable debug output for troubleshooting:

```bash
# Maximum verbosity
prompt-pipeline -v 3 run-pipeline spec.txt
```

### Logging

Configure file-based logging in `pipeline_config.yaml`:

```yaml
logging:
  level: "DEBUG"
  file: "pipeline.log"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

---

## Advanced Usage

### Custom Prompts

Create custom prompt files in the `prompts/` directory:

```bash
# Copy existing prompt as template
cp prompts/prompt_step1_v2.md prompts/my_custom_step.md

# Edit the prompt template
# Use {{variable}} syntax for variable substitution

# Update configuration to use your prompt
# In pipeline_config.yaml:
steps:
  custom_step:
    prompt_file: "my_custom_step.md"
    # ... other config
```

### Batch Processing

Process multiple specifications:

```bash
# Process all .txt files in a directory
for spec in specs/*.txt; do
  name=$(basename "$spec" .txt)
  prompt-pipeline run-pipeline "$spec" --output-dir "output/$name"
done
```

### Partial Pipeline Execution

Run only specific steps:

```bash
# Run from stepC3 onwards
prompt-pipeline run-step stepC3 --spec-file output/spec_formal.md

# Run from stepD1 onwards
prompt-pipeline run-step stepD1 \
  --spec-file output/spec_formal.md \
  --concepts-file output/concepts.json \
  --messages-file output/messages.json
```

---

## File Structure

```
modellm/
├── prompt_pipeline/              # Core pipeline modules
│   ├── __init__.py
│   ├── llm_client.py             # OpenRouter API client
│   ├── orchestrator.py           # Pipeline coordination
│   ├── prompt_manager.py         # Prompt loading & config
│   ├── step_executor.py          # Step execution
│   ├── typedb_integration.py     # TypeDB import
│   └── validation/               # Validators
│       ├── __init__.py
│       ├── yaml_validator.py
│       └── json_validators.py
│
├── prompt_pipeline_cli/          # CLI commands
│   ├── commands/
│   │   ├── run_pipeline.py
│   │   ├── run_step.py
│   │   ├── validate.py
│   │   ├── import_cmd.py
│   │   └── config.py
│   └── main.py
│
├── prompts/                      # Prompt templates
│   ├── prompt_step1_v2.md
│   ├── prompt_step2_v2.md
│   └── ...
│
├── configuration/
│   └── pipeline_config.yaml      # Default configuration
│
├── schemas/                      # JSON schemas for validation
│   ├── concepts_schema.json
│   ├── aggregations_schema.json
│   ├── messages_schema.json
│   └── requirements_schema.json
│
└── doc/
    └── prompt_pipeline_guide.md  # This documentation
```

---

## See Also

- [Workflow Guide](workflow_guide.md) - Detailed workflow examples
- [Implementation Guide](../agents/implementation_guide.md) - Technical implementation details
- [TypeDB Schema](typedb_schema_2.tql) - Database schema definition
- [migration_proposal.md](migration_proposal.md) - Original design proposal
