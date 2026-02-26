# ModelLM: AI-Driven Application Modeling & Design

ModelLM is an AI-driven application modeling and design system that transforms natural language specifications into structured knowledge graphs in TypeDB. Starting with a natural language (NL) specification, the system builds a conceptual model in TypeDB, which is then refined into a design model and finally an implementation model through an iterative approach with feedback from software engineers and stakeholders.

## Overview

The system connects specification requirements to concepts, designs, and implementation, enabling thorough auditing and dependency tracking. It employs a structured reasoning approach using TypeDB's knowledge graph capabilities to model software applications from initial concepts through to implementation details.

### Key Features

- **Natural Language to Knowledge Graph**: Convert NL specifications into structured TypeDB databases
- **Iterative Refinement**: Multi-stage pipeline with stakeholder feedback loops
- **Dependency Tracking**: Comprehensive tracking of relationships between requirements, concepts, and implementations
- **Flexible Pipeline Configuration**: YAML-based configuration for customizable processing workflows
- **Multi-Model Support**: Conceptual → Design → Implementation model progression
- **AI-Driven Reasoning**: LLM-powered context compression and intelligent query generation
- **Comprehensive Compression Strategies**: Multiple strategies to handle large specifications efficiently
- **Interactive CLI System**: Rich command-line interface with approval workflows and input validation

## Architecture

### System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   NL Specification  │    │   Prompt Pipeline  │    │   TypeDB Database  │
│     (Markdown)      │───▶│   (Multi-Step)     │───▶│  (Knowledge Graph) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
       │                       │                       │
       ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Stakeholder   │    │   LLM Client    │    │   Query Engine  │
│    Feedback     │◀───│  (OpenRouter)   │◀───│  (TypeDB HTTP)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Pipeline Stages

1. **Conceptual Model** (`step1` → `step2` → `step3` → `stepC3` → `stepC4` → `stepC5` → `stepD1`)
   - Extract concepts from NL specification
   - Define aggregations and message flows
   - Identify requirements and constraints

2. **Design Model** ([Future] `stepD2` → `stepD3` → `stepD4`)
   - Architectural patterns and design decisions
   - Interface definitions and system boundaries
   - Technology stack selection

3. **Implementation Model** ([Future] `stepI1` → `stepI2` → `stepI3`)
   - Code generation templates
   - Implementation-specific details
   - Deployment configurations

## Quick Start

### Installation

```bash
# Install from source (includes CLI tools)
pip install -e .

# Or install TypeDB client separately
pip install typedb-client3
```

### Basic Usage

1. **Set up environment variables**:
```bash
export OPENROUTER_API_KEY="sk-or-..."      # For LLM processing
export TYPEDB_URL="http://localhost:8000"  # TypeDB server
export TYPEDB_USERNAME="admin"
export TYPEDB_PASSWORD="password"
```

2. **Run the full pipeline**:
```bash
prompt-pipeline run-pipeline \
  --nl-spec doc/todo_list_spec.md \
  --output-dir pipeline_output/ \
  --import-database my_app \
  --wipe \
  --model-level 1 \
  --verbosity 2
```

3. **Run individual steps**:
```bash
# Generate initial YAML specification
prompt-pipeline run-step step1 \
  --input-file nl_spec:doc/todo_list_nl_spec.md \
  --output-dir yaml/

# Extract concepts
prompt-pipeline run-step stepC3 \
  --input-file spec:yaml/spec_1.yaml \
  --output-dir concepts/

# Import to TypeDB
prompt-pipeline import \
  --file concepts/concepts.json \
  --database my_app
```

## CLI Reference

### Core Commands

```bash
# Show help
prompt-pipeline --help

# Run complete pipeline
prompt-pipeline run-pipeline --nl-spec spec.md

# Run specific step with file input
prompt-pipeline run-step step1 --input-file nl_spec:doc/spec.md

# Run step with interactive prompt
prompt-pipeline run-step step1 --input-prompt nl_spec

# Run step with direct text input
prompt-pipeline run-step step1 --input-text nl_spec:"My specification text"

# Run with approval workflow
prompt-pipeline run-step step1 --input-file nl_spec:doc/spec.md --approve

# Run in batch mode (CI/CD)
prompt-pipeline run-step step1 --input-file nl_spec:doc/spec.md --auto-approve

# Validate data/files
prompt-pipeline validate --config configuration/pipeline_config.yaml

# Import data to TypeDB
prompt-pipeline import --file data.json --database my_db

# Show configuration
prompt-pipeline config --show
```

### Input System

The CLI supports multiple input methods with priority resolution:

**1. File Input** (Highest Priority)
```bash
prompt-pipeline run-step step1 --input-file nl_spec:doc/todo_list_nl_spec.md
```

**2. Interactive Prompt**
```bash
prompt-pipeline run-step step1 --input-prompt nl_spec
# Prompts user to enter content interactively
```

**3. Direct Text Input**
```bash
prompt-pipeline run-step step1 --input-text nl_spec:"My specification text"
# Provides content directly on command line
```

**4. Environment Variable**
```bash
prompt-pipeline run-step step1 --input-env nl_spec:SPEC_TEXT
# Reads from environment variable SPEC_TEXT
```

**Input Resolution Priority:**
1. CLI `--input-file` / `--input-prompt` / `--input-text` / `--input-env` (highest)
2. Config `exogenous_inputs` (medium)
3. Previous step outputs in pipeline mode (lowest)
4. Missing required input (error, unless `--force` used)

### Approval Flow

**Interactive Approval:**
```bash
prompt-pipeline run-step step1 --input-file nl_spec:doc/spec.md --approve
# Shows substituted prompt and waits for confirmation
```

**Batch Mode (CI/CD):**
```bash
prompt-pipeline run-step step1 --input-file nl_spec:doc/spec.md --auto-approve
# Skips approval prompt
```

**Dry Run:**
```bash
prompt-pipeline run-step step1 --input-file nl_spec:doc/spec.md --dry-run
# Shows what would happen without executing
```

### Verbosity Levels

```bash
prompt-pipeline -v 0  # Quiet mode
prompt-pipeline -v 1  # Normal mode (default)
prompt-pipeline -v 2  # Verbose mode
prompt-pipeline -v 3  # Debug mode
```

## Pipeline Configuration

The system uses `configuration/pipeline_config.yaml` for step definitions and workflow configuration:

### Data Entities (Centralized Definitions)

```yaml
data_entities:
  nl_spec:
    type: md
    filename: todo_list_nl_spec.md
    description: "Natural language requirements specification in markdown format"

  spec:
    type: yaml
    filename: spec_1.yaml
    description: "A formal software application specification"
    yaml_schema: schemas/spec_yaml_schema.json
    compression_strategies:
      none:
        description: "Complete specification in YAML format"
      anchor_index:
        description: "Compact anchor index for traceability"
      yaml_as_json:
        description: "Complete specification in JSON format"

  concepts:
    type: json
    filename: concepts.json
    description: "Extracted concepts from specification"
    schema: schemas/concepts.schema.json
    compression_strategies:
      none:
        description: "Complete JSON concepts"
      concept_summary:
        description: "Concept summary format (markdown tables)"
```

### Pipeline Steps

```yaml
steps:
  step1:
    name: "step1"
    prompt_file: "prompt_step1_v2.md"
    order: 1
    inputs:
      - label: nl_spec
        source: cli
        compression: none
        color: cyan
    outputs:
      - label: spec
    dependencies: []
    validation:
      enabled: false
    persona: systems_architect

  stepC3:
    name: "stepC3"
    prompt_file: "prompt_step_C3.md"
    order: 4
    inputs:
      - label: spec
        source: label:spec
        compression: hierarchical
        compression_params:
          level: 3  # 1=light, 2=medium, 3=aggressive
        color: magenta
    outputs:
      - label: concepts
    dependencies:
      - step1
    validation:
      enabled: true
    persona: systems_architect

  stepC4:
    name: "stepC4"
    prompt_file: "prompt_step_C4.md"
    order: 5
    inputs:
      - label: spec
        source: label:spec
        compression: anchor_index
        color: cyan
      - label: concepts
        source: label:concepts
        compression: concept_summary
        color: green
    outputs:
      - label: aggregations
    dependencies:
      - stepC3
    validation:
      enabled: true
    persona: software_engineer
```

### Model Configuration

```yaml
model_levels:
  step1:
    1: minimax/minimax-m2.5
    2: xiaomi/mimo-v2-flash
    3: moonshotai/kimi-k2-0905
  stepC3:
    1: qwen/qwen-2.5-72b
    2: xiaomi/mimo-v2-flash
    3: moonshotai/kimi-k2-0905
```

## Context Compression

The system includes **7 advanced compression strategies** to handle large specifications efficiently:

### Available Strategies

| Strategy | Compression Ratio | Use Case | Description |
|----------|------------------|----------|-------------|
| `none` / `zero` | 1.0 (no reduction) | Baseline, Step C3 | Returns content as-is without compression |
| `anchor_index` | ~0.2-0.3 (70-80% reduction) | Step C4 | Extracts anchor definitions from YAML spec, creates compact index: `{AN1: "text", AN2: "text"}` |
| `concept_summary` | ~0.4-0.5 (50-60% reduction) | Steps C5, D1 | Converts Concepts.json to markdown tables grouped by entity type (Actors, Actions, DataEntities, Categories) |
| `hierarchical` | ~0.3-0.5 (50-70% reduction) | Step C3 | Multi-layer approach: Layer 1=Executive summary, Layer 2=Concept inventory, Layer 3=Detailed definitions, Layer 4=Source evidence |
| `schema_only` | ~0.1-0.2 (80-90% reduction) | Schema-aware contexts | Provides JSON schema + counts instead of full content |
| `differential` | ~0.05-0.1 (90-95% reduction) | Iterative refinement | Only passes changes: `{added: [...], modified: [...], removed: [...]}` |
| `yaml_as_json` | Similar to full | Data transformation | Converts YAML to JSON format for prompt input |

### Compression Configuration

**Per-Input Compression:**
```yaml
inputs:
  - label: spec
    source: label:spec
    compression: anchor_index  # Compress input before substitution
    compression_params:
      level: 3  # Aggressive compression
    color: cyan  # Highlight in terminal
```

**Compression Settings:**
```yaml
compression:
  strategy: "hierarchical"  # Strategy name
  level: 1  # 1=light, 2=medium, 3=aggressive
  preserve_full: false  # Keep both full and compressed versions
  truncation_length: 4000  # Custom truncation length
```

### Key Features

- **Input-Only Compression**: Outputs are stored in RAW form, compression only applies when constructing prompts
- **Color-Coded Terminal Output**: Different inputs highlighted in different colors (cyan, green, yellow, magenta)
- **Configurable Levels**: Light, medium, and aggressive compression for different use cases
- **Compression Metrics**: Track original length, compressed length, compression ratio, and reduction percentage

## TypeDB Integration

### Entity Model

The system creates a comprehensive entity model including:

**Core Entities:**
- `Actor` - System actors and users
- `Action` - Actions and operations
- `Message` - Messages and communications
- `Concept` - Domain concepts
- `Requirement` - System requirements
- `Constraint` - Design constraints
- `TextBlock` - Specification text segments

**Relations:**
- `Messaging` - Message producer-consumer relationships
- `Anchoring` - Concept-text anchoring
- `Membership` - Entity membership
- `Requiring` - Requirement relationships

### Import Commands

```bash
# Import single file
prompt-pipeline import --file concepts/concepts.json --database my_app

# Import with wipe (clear existing data)
prompt-pipeline import --file concepts/concepts.json --database my_app --wipe

# Import with import ID
prompt-pipeline import --file concepts/concepts.json --database my_app --import-id "v1.0"
```

## Workflows

### Scenario 1: Full Pipeline (Batch Mode)

```bash
prompt-pipeline run-pipeline \
  --nl-spec doc/todo_list_spec.md \
  --output-dir pipeline_output/ \
  --import-database todo_app \
  --wipe \
  --model-level 1 \
  --verbosity 2
```

### Scenario 2: Iterative Development with Approval

```bash
# Step 1: Generate initial YAML with approval
prompt-pipeline run-step step1 \
  --input-file nl_spec:doc/todo_list_nl_spec.md \
  --output-dir yaml/ \
  --approve

# Step 2: Generate formal spec
prompt-pipeline run-step step2 \
  --input-file spec:yaml/spec_1.yaml \
  --output-dir yaml/ \
  --approve

# Step 3: User revises spec_formal.md externally, then:
prompt-pipeline run-step step3 \
  --input-file spec_formal:yaml/spec_formal.md \
  --output-dir yaml/ \
  --approve

# Step 4: Extract concepts
prompt-pipeline run-step stepC3 \
  --input-file spec:yaml/revised_spec.md \
  --output-dir concepts/ \
  --approve

# Step 5: Generate aggregations
prompt-pipeline run-step stepC4 \
  --input-file spec:yaml/revised_spec.md \
  --output-dir concepts/ \
  --approve

# Step 6: Generate messages
prompt-pipeline run-step stepC5 \
  --input-file spec:yaml/revised_spec.md \
  --output-dir concepts/ \
  --approve

# Step 7: Generate requirements
prompt-pipeline run-step stepD1 \
  --input-file spec:yaml/revised_spec.md \
  --output-dir requirements/ \
  --approve

# Step 8: Import to TypeDB
prompt-pipeline import \
  --file requirements/requirements.json \
  --database todo_app \
  --wipe
```

### Scenario 3: Interactive Development

```bash
# Use interactive prompts for all inputs
prompt-pipeline run-step step1 --input-prompt nl_spec --approve
```

### Scenario 4: CI/CD Pipeline

```bash
# All inputs from files, no interactive prompts
prompt-pipeline run-pipeline \
  --input-file nl_spec:doc/todo_list_nl_spec.md \
  --auto-approve \
  --verbosity 1
```

## Advanced Features

### Custom Prompt Templates

Create custom prompt templates in the `prompts/` directory:

```markdown
<!-- prompts/prompt_custom.md -->
# Custom Processing Step

## Context
{{ context }}

## Requirements
{{ requirements }}

## Task
Generate structured output based on the above context...
```

### Model Selection

Configure different LLM models for different steps:

```yaml
steps:
  step1:
    model: "openai/gpt-4-turbo-preview"
  stepC3:
    model: "anthropic/claude-3-opus"
    temperature: 0.1
    max_tokens: 4000
```

### Validation Schemas

Define JSON schemas for output validation:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "concepts": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": {"type": "string"},
          "label": {"type": "string"},
          "description": {"type": "string"}
        },
        "required": ["id", "label"]
      }
    }
  },
  "required": ["concepts"]
}
```

### Terminal Output Formatting

The system provides rich terminal output with:
- **Color-coded inputs**: Different colors for different input sources
- **Step progress indicators**: Spinner and status messages
- **Formatted prompts**: Clear display of substituted prompts
- **Response formatting**: Structured display of LLM responses
- **Error reporting**: Detailed error messages with context

## Configuration Options

### CLI Options

**Input Options:**
- `--input-file label:filename` - Provide content from a file
- `--input-prompt label` - Prompt user for content interactively
- `--input-text label:"content"` - Provide content directly
- `--input-env label:ENV_VAR` - Read from environment variable

**Execution Options:**
- `--approve` - Show prompt and wait for confirmation
- `--auto-approve` - Skip approval for batch mode
- `--dry-run` - Show what would happen without executing
- `--show-prompt` - Display the substituted prompt
- `--show-response` - Display the LLM response

**Model Options:**
- `--model-level 1|2|3` - Select model quality level
- `--model <model_name>` - Override model selection

**Output Options:**
- `--output-dir <dir>` - Directory for output files (default: `pipeline_output/`)
- `--output-file <file>` - Specific output filename

**Validation Options:**
- `--skip-validation` - Skip validation (development mode)
- `--force` - Continue despite validation warnings

**Other Options:**
- `--config <file>` - Use custom configuration file
- `--verbosity 0|1|2|3` - Verbosity level
- `--batch` - Disable all interactive prompts

## Project Structure

```
modellm/
├── prompt_pipeline/           # Core pipeline logic
│   ├── compression/          # Compression strategies
│   │   ├── strategies/       # 7 compression strategies
│   │   │   ├── anchor_index.py
│   │   │   ├── concept_summary.py
│   │   │   ├── hierarchical.py
│   │   │   ├── schema_only.py
│   │   │   ├── differential.py
│   │   │   ├── yaml_as_json.py
│   │   │   └── zero_compression.py
│   │   └── manager.py        # Compression management
│   ├── validation/           # JSON/YAML validation
│   │   ├── json_validator.py
│   │   ├── yaml_validator.py
│   │   └── yaml_schema_validator.py
│   ├── llm_client.py         # OpenRouter API client
│   ├── prompt_manager.py     # Prompt loading and config
│   ├── step_executor.py      # Individual step execution
│   ├── orchestrator.py       # Pipeline coordination
│   ├── tag_replacement.py    # Template variable substitution
│   └── terminal_utils.py     # Terminal output formatting
├── prompt_pipeline_cli/      # CLI interface
│   ├── commands/             # CLI commands
│   │   ├── run_step.py       # Run single step
│   │   ├── run_pipeline.py   # Run full pipeline
│   │   ├── import_cmd.py     # Import to TypeDB
│   │   ├── validate.py       # Validate outputs
│   │   └── config.py         # Show configuration
│   └── input_validation.py   # Input validation logic
├── configuration/            # Configuration files
│   └── pipeline_config.yaml  # Main pipeline config
├── prompts/                  # LLM prompt templates
│   ├── prompt_step1_v2.md
│   ├── prompt_step2_v2.md
│   ├── prompt_step3_v2.md
│   ├── prompt_step_C3.md
│   ├── prompt_step_C4.md
│   ├── prompt_step_C5.md
│   └── prompt_step_D1.md
├── schemas/                  # Validation schemas
├── typedb_client3/           # TypeDB client library
├── tests/                    # Test suite
├── doc/                      # Documentation
└── agents/                   # AI agent tools and guides
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run unit tests only
pytest tests/ -m unit -v

# Run integration tests only
pytest tests/ -m integration -v

# Run with coverage
pytest tests/ --cov=prompt_pipeline --cov-report=html

# Run specific test file
pytest tests/test_prompt_pipeline/test_compression_anchors.py -v
```

## Development

### Installation for Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run pre-commit checks (if configured)
# pytest tests/ -v
```

### Code Style

- **Type Hints**: All functions include type hints
- **Docstrings**: Comprehensive docstrings for all public APIs
- **PEP 8**: Follow Python style guidelines
- **Testing**: Unit tests and integration tests required

### Adding New Compression Strategy

1. Create new strategy in `prompt_pipeline/compression/strategies/`
2. Inherit from `CompressionStrategy` base class
3. Implement `compress()` and `decompress()` methods
4. Register in `CompressionManager._register_default_strategies()`
5. Add to `data_entities.compression_strategies` in config
6. Write tests in `tests/test_prompt_pipeline/test_compression_*.py`

### Adding New Pipeline Step

1. Create prompt template in `prompts/` directory
2. Add step configuration to `configuration/pipeline_config.yaml`
3. Define inputs and outputs with labels
4. Configure compression strategies
5. Set validation schema if needed
6. Test step individually

## Requirements

- **Python**: 3.8+
- **TypeDB**: Version 3.x (HTTP API)
- **OpenRouter API**: For LLM processing
- **Dependencies**: Listed in `pyproject.toml`

## Environment Setup

1. **Install TypeDB**: [Download TypeDB 3.x](https://vaticle.com/typedb)
2. **Set up OpenRouter**: Get API key from [OpenRouter](https://openrouter.ai/)
3. **Install dependencies**: `pip install -e .`
4. **Configure environment**: Create `.env` file or set environment variables

```bash
# .env file
OPENROUTER_API_KEY=sk-or-...
TYPEDB_URL=http://localhost:8000
TYPEDB_USERNAME=admin
TYPEDB_PASSWORD=password
```

## Documentation

### Core Documentation
- **Workflow Guide**: `doc/workflow_guide.md` - Detailed workflow patterns
- **API Reference**: `doc/API.md` - Complete API documentation
- **Implementation Summary**: `doc/IMPLEMENTATION_SUMMARY.md` - Implementation overview
- **Compression Guide**: `doc/prompt_pipeline_compression.md` - Compression strategies
- **Migration Guide**: `doc/migration_proposal.md` - Migration and planning

### Agent Tools
- **Workflow Guide**: `agents/tools/workflow_guide.md` - Agent workflow patterns
- **CLI Syntax Checker**: `agents/tools/cli_syntax_checker.py` - CLI validation
- **Context Extractor**: `agents/tools/extract_context.py` - Context extraction
- **Implementation Guide**: `agents/implementation_guide.md` - Detailed specifications

### Examples
- **NL Specification**: `doc/todo_list_nl_spec.md` - Example specification
- **YAML Specification**: `doc/todo_list_spec_2.yaml` - Example YAML format

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
- Check the documentation in `doc/` directory
- Review example specifications in `doc/`
- Run tests to verify installation
- Create an issue in the repository

## Feature Summary

### Implemented Features (v0.1.0)

✅ **Core Pipeline System**
- Multi-step execution with dependency management
- YAML-based configuration (no code changes needed)
- Step orchestration and auto-discovery

✅ **CLI System**
- `run-step` - Execute individual steps
- `run-pipeline` - Execute full pipeline
- `validate` - Validate outputs
- `import` - Import to TypeDB
- `config` - Show configuration

✅ **Input System**
- File input (`--input-file`)
- Interactive prompt (`--input-prompt`)
- Direct text input (`--input-text`)
- Environment variable input (`--input-env`)
- Priority-based resolution

✅ **Approval Flow**
- `--approve` - Interactive approval
- `--auto-approve` - Batch mode
- `--dry-run` - Preview mode

✅ **Compression Strategies** (7 strategies)
- `zero` - No compression
- `anchor_index` - Compact anchor index
- `concept_summary` - Markdown tables
- `hierarchical` - Multi-layer compression
- `schema_only` - Schema + counts
- `differential` - Delta-based
- `yaml_as_json` - YAML to JSON

✅ **Data Entities**
- Centralized data artifact definitions
- Automatic description lookup
- Compression strategy linking
- Schema validation

✅ **Validation**
- YAML validation with schema support
- JSON validation (concepts, aggregations, messages, requirements)
- Configurable strictness

✅ **Terminal Output**
- Color-coded inputs
- Progress indicators
- Formatted prompts/responses
- Rich error reporting

✅ **Model Management**
- 3-level model selection
- Per-step model configuration
- OpenRouter API integration
- Exponential retry with partial state saving

✅ **TypeDB Integration**
- Entity model (Actors, Actions, Messages, Concepts, Requirements, Constraints, TextBlocks)
- Relation model (Messaging, Anchoring, Membership, Requiring)
- Import with wipe option
- Import ID support

### Future Features (Roadmap)

🔒 **Advanced Features**
- Caching layer for repeated queries
- Parallel execution for independent steps
- Progress persistence and resume
- Custom compression strategies
- Plugin system for new validators

🔒 **Monitoring & Analytics**
- Execution metrics and timing
- Compression ratio analytics
- Model cost tracking
- Pipeline performance profiling

🔒 **Enterprise Features**
- User authentication
- Role-based access control
- Audit logging
- Multi-tenant support

---

**Project**: ModelLM  
**Version**: 0.1.0  
**Status**: Production Ready  
**Documentation**: https://github.com/your-org/modellm

---

*This documentation was last updated to reflect all implemented features as of 2026-02-26.*
