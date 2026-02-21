# ModelLM: AI-Driven Application Modeling & Design

Modellm is an AI-driven application modeling and design system that transforms natural language specifications into structured knowledge graphs in TypeDB. Starting with a natural language (NL) specification, the system builds a conceptual model in TypeDB, which is then refined into a design model and finally an implementation model through an iterative approach with feedback from software engineers and stakeholders.

## Overview

The system connects specification requirements to concepts, designs, and implementation, enabling thorough auditing and dependency tracking. It employs a structured reasoning approach using TypeDB's knowledge graph capabilities to model software applications from initial concepts through to implementation details.

### Key Features

- **Natural Language to Knowledge Graph**: Convert NL specifications into structured TypeDB databases
- **Iterative Refinement**: Multi-stage pipeline with stakeholder feedback loops
- **Dependency Tracking**: Comprehensive tracking of relationships between requirements, concepts, and implementations
- **Flexible Pipeline Configuration**: YAML-based configuration for customizable processing workflows
- **Multi-Model Support**: Conceptual → Design → Implementation model progression
- **AI-Driven Reasoning**: LLM-powered context compression and intelligent query generation

## Architecture

### System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   NL Specification  │    │   Prompt Pipeline  │    │   TypeDB Database  │
│     (Markdown)      │───▶│   (Multi-Step)     │───▶│  (Knowledge Graph) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
       │                       │                       │
       ▼                       ▼                       ▼┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│   Stakeholder   │       │   LLM Client    │       │   Query Engine  │
│    Feedback     │◀──────│  (OpenRouter)   │◀──────│  (TypeDB HTTP)  │
└─────────────────┘       └─────────────────┘       └─────────────────┘
```

### Pipeline Stages

1. **Conceptual Model** (`step1` → `stepC3` → `stepC4` → `stepC5` → `stepD1`)
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
  --nl-spec doc/todo_list_spec.md \
  --output-dir yaml/

# Extract concepts
prompt-pipeline run-step stepC3 \
  --input-yaml yaml/spec_1.yaml \
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
prompt-pipeline run-pipeline --input input.txt

# Run specific step
prompt-pipeline run-step --step step1 --input input.txt

# Validate data/files
prompt-pipeline validate --config configuration/pipeline_config.yaml

# Import data to TypeDB
prompt-pipeline import --file data.json --database my_db

# Show configuration
prompt-pipeline config --show
```

### Configuration Options

```bash
# Verbosity levels
prompt-pipeline -v 0  # Quiet
prompt-pipeline -v 1  # Normal (default)
prompt-pipeline -v 2  # Verbose
prompt-pipeline -v 3  # Debug

# Custom configuration
prompt-pipeline --config custom_config.yaml run-pipeline --input spec.md
```

## Pipeline Configuration

The system uses `configuration/pipeline_config.yaml` for step definitions and workflow configuration:

```yaml
# CLI input specifications
cli_inputs:
  - label: nl_spec
    type: md
    prompt: 'Enter your natural language specification:'
    required: true
    default_file: doc/todo_list_nl_spec.md

# Pipeline steps
steps:
  step1:
    name: "NL Specification Processing"
    prompt_file: "prompt_step1_v2.md"
    order: 1
    inputs:
      - label: nl_spec
        type: md
    outputs:
      - file: "spec_1.yaml"
        type: yaml
    validation:
      enabled: true
      schema: "schemas/spec.schema.json"
    persona: systems_architect

  stepC3:
    name: "Concept Extraction"
    prompt_file: "prompt_step_C3.md"
    order: 2
    inputs:
      - label: spec
        type: yaml
    outputs:
      - file: "concepts.json"
        type: json
    compression: hierarchical  # Context compression strategy
```

## Context Compression

The system includes advanced context compression strategies to handle large specifications:

### Available Strategies

- **`none`**: No compression, full context
- **`hierarchical`**: Hierarchical concept compression
- **`schema_only`**: Schema-level compression
- **`concept_summary`**: Concept-based summarization
- **`differential`**: Delta-based compression
- **`full`**: Complete context preservation

### Usage

```yaml
steps:
  stepC3:
    compression: hierarchical
    compression_config:
      max_tokens: 4000
      preserve_relations: true
      compression_ratio: 0.7
```

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

### Query Examples

```python
from typedb_client3 import TypeDBClient, QueryBuilder

client = TypeDBClient(base_url="http://localhost:8000")

# Get all concepts related to a requirement
query = '''
match 
  $r isa requirement, has requirement-id "REQ-001";
  (required: $r, requiring: $s) isa requiring;
  (anchored: $c, anchor: $s) isa anchoring;
fetch {"concepts": $c.*};
'''

result = client.execute_query("my_db", query)
```

## Workflows

### Scenario 1: Basic Pipeline (No Revision)

For specifications without stakeholder review:

```bash
prompt-pipeline run-pipeline \
  --nl-spec your_spec.md \
  --output-dir output/ \
  --import-database your_app \
  --wipe
```

### Scenario 2: Iterative Development

With stakeholder feedback and refinement:

```bash
# Step 1: Generate initial YAML
prompt-pipeline run-step step1 -i spec.md -o yaml/

# Step 2: Manual review and approval
# ... Stakeholder reviews spec_1.yaml ...

# Step 3: Extract concepts from approved specification
prompt-pipeline run-step stepC3 -i yaml/spec_1.yaml -o concepts/

# Step 4: Import to TypeDB
prompt-pipeline import -f concepts/concepts.json -d app_db

# Step 5: Continue with design steps...
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

## Future Development Roadmap

### Phase 1: Implementation Model (Current Focus)
- [ ] Code generation from design models
- [ ] Function-by-function constrained implementation
- [ ] Integration with AI coding assistants

### Phase 2: Advanced Reasoning
- [ ] Impact analysis queries
- [ ] Bug tracing and localization
- [ ] Iterative improvement cycles

### Phase 3: Tool Integration
- [ ] Mermaid diagram generation from TypeDB models
- [ ] Nanocoder MCP integration
- [ ] VS Code extension

### Phase 4: Advanced Analytics
- [ ] Dependency analysis and visualization
- [ ] Change impact prediction
- [ ] Automated optimization suggestions

## Development

### Project Structure

```
modellm/
├── prompt_pipeline/           # Core pipeline logic
│   ├── compression/          # Context compression strategies
│   ├── validation/           # JSON/YAML validation
│   └── *.py                  # Core components
├── prompt_pipeline_cli/      # CLI interface
│   └── commands/             # CLI commands
├── prompts/                  # LLM prompt templates
├── schemas/                  # Validation schemas
├── configuration/            # Pipeline configuration
├── typedb_client3/           # TypeDB client library
├── tests/                    # Test suite
└── doc/                      # Documentation
```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test categories
pytest tests/ -m unit        # Unit tests only
pytest tests/ -m integration # Integration tests

# Run with coverage
pytest tests/ --cov=modellm --cov-report=html
```

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make changes with tests
4. Run the test suite: `pytest tests/ -v`
5. Submit a pull request

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

## Learning Resources

### Documentation
- **Workflow Guide**: `doc/workflow_guide.md`
- **API Reference**: `doc/API.md`
- **Implementation Summary**: `doc/IMPLEMENTATION_SUMMARY.md`
- **TypeDB Integration**: `doc/typedb_llm_reasoning.md`

### Examples

The `doc/` directory contains example specifications:
- `todo_list_spec.md` - Complete NL specification example
- `todo_list_spec_2.yaml` - YAML specification format
- Various schema and configuration examples

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
- Check the documentation in `doc/` directory
- Review example specifications
- Run tests to verify installation
- Create an issue in the repository

---

**Modellm** bridges the gap between natural language specifications and structured software modeling, enabling AI-driven software development with full traceability and reasoning capabilities.