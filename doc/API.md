# ModelLM API Reference

Comprehensive API documentation for ModelLM v0.1.0

## Table of Contents

1. [LLM Client API](#llm-client-api)
2. [Prompt Manager API](#prompt-manager-api)
3. [Step Executor API](#step-executor-api)
4. [Pipeline Orchestrator API](#pipeline-orchestrator-api)
5. [Compression Manager API](#compression-manager-api)
6. [Validation API](#validation-api)
7. [CLI API](#cli-api)
8. [TypeDB Importer API](#typedb-importer-api)
9. [Terminal Utils API](#terminal-utils-api)
10. [Label Registry API](#label-registry-api)

---

## 1. LLM Client API

### OpenRouterClient

**File:** `prompt_pipeline/llm_client.py`  
**Lines:** 12,902 bytes

#### Initialization

```python
from prompt_pipeline.llm_client import OpenRouterClient

client = OpenRouterClient(
    api_key: str = None,  # Defaults to OPENROUTER_API_KEY env var
    model: str = "openai/gpt-4-turbo-preview",
    max_retries: int = 3,
    base_delay: float = 2.0
)
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | str | None | OpenRouter API key (falls back to env var) |
| `model` | str | "openai/gpt-4-turbo-preview" | Default model to use |
| `max_retries` | int | 3 | Maximum retry attempts |
| `base_delay` | float | 2.0 | Base delay for exponential backoff (seconds) |

#### Methods

##### `call_llm()`

Execute an LLM API call with retry logic.

```python
def call_llm(
    self,
    prompt: str,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    timeout: Optional[int] = None
) -> Dict[str, Any]:
    """
    Execute LLM API call with exponential backoff retry.
    
    Args:
        prompt: The prompt to send to the LLM
        model: Override default model
        temperature: Temperature setting (0.0-1.0)
        max_tokens: Maximum tokens to generate
        timeout: Request timeout in seconds
    
    Returns:
        Dict with 'response' (str) and 'metadata' (Dict)
    
    Raises:
        OpenRouterError: After max retries exhausted
    """
```

**Example:**
```python
from prompt_pipeline.llm_client import OpenRouterClient

client = OpenRouterClient()
result = client.call_llm(
    prompt="Extract concepts from this specification...",
    model="anthropic/claude-3-opus",
    temperature=0.1,
    max_tokens=4000
)

response_text = result['response']
metadata = result['metadata']
print(f"Response: {response_text}")
print(f"Model: {metadata['model']}")
print(f"Tokens used: {metadata['total_tokens']}")
```

##### `get_model_info()`

Get information about available models.

```python
def get_model_info(self, model: str) -> Dict[str, Any]:
    """
    Get information about a specific model.
    
    Args:
        model: Model name (e.g., "openai/gpt-4-turbo-preview")
    
    Returns:
        Dict with model metadata (context length, pricing, etc.)
    """
```

##### `select_model()`

Select model based on level and step.

```python
def select_model(
    self,
    step_name: str,
    model_level: int,
    step_config: Optional[Dict] = None
) -> str:
    """
    Select model based on configuration.
    
    Args:
        step_name: Name of the step
        model_level: Quality level (1, 2, or 3)
        step_config: Step configuration (optional override)
    
    Returns:
        Selected model name
    """
```

**Example:**
```python
model = client.select_model("stepC3", 1)
# Returns: "qwen/qwen-2.5-72b"
```

#### Error Handling

```python
from prompt_pipeline.llm_client import OpenRouterError

try:
    result = client.call_llm(prompt)
except OpenRouterError as e:
    print(f"API Error: {e.message}")
    print(f"Details: {e.details}")
    print(f"Retry count: {e.retry_count}")
```

---

## 2. Prompt Manager API

### PromptManager

**File:** `prompt_pipeline/prompt_manager.py`  
**Lines:** 19,830 bytes

#### Initialization

```python
from prompt_pipeline.prompt_manager import PromptManager

manager = PromptManager(
    config_path: str = "configuration/pipeline_config.yaml"
)
```

#### Methods

##### `get_step_config()`

Get configuration for a specific step.

```python
def get_step_config(
    self,
    step_name: str
) -> Optional[Dict[str, Any]]:
    """
    Get the configuration for a specific step.
    
    Args:
        step_name: Name of the step
    
    Returns:
        Step configuration dictionary or None if not found
    """
```

**Example:**
```python
config = manager.get_step_config("stepC3")
print(config['name'])  # "stepC3"
print(config['prompt_file'])  # "prompt_step_C3.md"
print(config['inputs'])  # List of input configurations
```

##### `get_prompt_with_variables()`

Get prompt with variable substitution.

```python
def get_prompt_with_variables(
    self,
    step_name: str,
    variables: Optional[Dict[str, str]] = None,
    persona: Optional[str] = None
) -> str:
    """
    Get the complete prompt for a step with variables substituted.
    
    Args:
        step_name: Name of the step
        variables: Dictionary of label -> content mappings
        persona: Override persona (optional)
    
    Returns:
        Complete prompt with preamble and substituted variables
    
    Raises:
        ValueError: If step not found or required variables missing
    """
```

**Example:**
```python
manager = PromptManager()

# Prepare variables from step inputs
variables = {
    'spec': "YAML spec content...",
    'concepts': "JSON concepts content..."
}

prompt = manager.get_step_config_with_variables(
    step_name="stepC4",
    variables=variables
)

# prompt now contains:
# [System message with persona]
# [Preamble]
# [Template with {{spec}} and {{concepts}} replaced]
```

##### `generate_preamble()`

Generate system preamble for step.

```python
def generate_preamble(
    self,
    step_name: str,
    persona: Optional[str] = None
) -> str:
    """
    Generate the system message and preamble for a step.
    
    Args:
        step_name: Name of the step
        persona: Override persona from config
    
    Returns:
        Formatted preamble string
    """
```

##### `get_data_entity()`

Get data entity configuration.

```python
def get_data_entity(
    self,
    label: str
) -> Optional[Dict[str, Any]]:
    """
    Get data entity configuration for a label.
    
    Args:
        label: Label name (e.g., "spec", "concepts")
    
    Returns:
        Data entity configuration or None if not found
    """
```

**Example:**
```python
spec_entity = manager.get_data_entity("spec")
print(spec_entity['type'])  # "yaml"
print(spec_entity['filename'])  # "spec_1.yaml"
print(spec_entity['yaml_schema'])  # "schemas/spec_yaml_schema.json"
```

##### `resolve_inputs()`

Resolve inputs for a step.

```python
def resolve_inputs(
    self,
    step_name: str,
    cli_inputs: Optional[Dict[str, str]] = None,
    previous_outputs: Optional[Dict[str, Path]] = None,
    exogenous_inputs: Optional[Dict[str, str]] = None
) -> Dict[str, str]:
    """
    Resolve all inputs for a step.
    
    Args:
        step_name: Name of the step
        cli_inputs: CLI-provided inputs (highest priority)
        previous_outputs: Outputs from previous steps
        exogenous_inputs: Exogenous inputs from config
    
    Returns:
        Dictionary of label -> content mappings
    
    Raises:
        InputError: If required input not found
    """
```

**Resolution Priority:**
1. CLI inputs (highest)
2. Exogenous inputs
3. Previous outputs
4. Missing required input → Error

##### `register_output()`

Register step output for next steps.

```python
def register_output(
    self,
    step_name: str,
    output_file: str,
    output_label: str,
    output_type: str
) -> None:
    """
    Register an output for use by subsequent steps.
    
    Args:
        step_name: Name of the step producing output
        output_file: Path to output file
        output_label: Label to register
        output_type: Type of output (yaml, json, etc.)
    """
```

---

## 3. Step Executor API

### StepExecutor

**File:** `prompt_pipeline/step_executor.py`  
**Lines:** 35,780 bytes

#### Initialization

```python
from prompt_pipeline.step_executor import StepExecutor
from prompt_pipeline.llm_client import OpenRouterClient
from prompt_pipeline.prompt_manager import PromptManager

executor = StepExecutor(
    llm_client=OpenRouterClient(),
    prompt_manager=PromptManager(),
    output_dir=Path("pipeline_output/"),
    model_level=1,
    skip_validation=False,
    verbose=False,
    show_prompt=False,
    show_response=False,
    output_file=None,
    force=False
)
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `llm_client` | OpenRouterClient | Required | LLM client instance |
| `prompt_manager` | PromptManager | Required | Prompt manager instance |
| `output_dir` | Path | Required | Directory for output files |
| `model_level` | int | 1 | Model quality level (1-3) |
| `skip_validation` | bool | False | Skip validation (dev mode) |
| `verbose` | bool | False | Print verbose output |
| `show_prompt` | bool | False | Display substituted prompt |
| `show_response` | bool | False | Display LLM response |
| `output_file` | str | None | Specific output filename |
| `force` | bool | False | Continue despite warnings |

#### Methods

##### `execute_step()`

Execute a single step.

```python
def execute_step(
    self,
    step_name: str,
    cli_inputs: Optional[Dict[str, str]] = None,
    approval_mode: str = "interactive"
) -> Tuple[bool, Optional[List[Path]]]:
    """
    Execute a single pipeline step.
    
    Args:
        step_name: Name of the step to execute
        cli_inputs: CLI-provided inputs
        approval_mode: "interactive", "auto", or "dry-run"
    
    Returns:
        Tuple of (success, list_of_output_paths)
    
    Raises:
        StepExecutionError: If execution fails
    """
```

**Approval Modes:**
- `"interactive"`: Show prompt and wait for confirmation
- `"auto"`: Skip approval, execute automatically
- `"dry-run"`: Show what would happen, don't execute

**Example:**
```python
executor = StepExecutor(llm_client, prompt_manager, Path("output/"))

# Interactive approval
success, outputs = executor.execute_step(
    step_name="stepC3",
    cli_inputs={'spec': 'yaml/spec_1.yaml'},
    approval_mode="interactive"
)

# Auto approval
success, outputs = executor.execute_step(
    step_name="stepC3",
    cli_inputs={'spec': 'yaml/spec_1.yaml'},
    approval_mode="auto"
)

# Dry run
success, outputs = executor.execute_step(
    step_name="stepC3",
    cli_inputs={'spec': 'yaml/spec_1.yaml'},
    approval_mode="dry-run"
)
```

##### `construct_prompt()`

Construct the prompt for a step.

```python
def construct_prompt(
    self,
    step_name: str,
    cli_inputs: Optional[Dict[str, str]] = None
) -> str:
    """
    Construct the complete prompt for a step.
    
    Args:
        step_name: Name of the step
        cli_inputs: CLI-provided inputs
    
    Returns:
        Complete prompt with all substitutions
    """
```

##### `validate_output()`

Validate step output.

```python
def validate_output(
    self,
    output_file: Path,
    step_name: str
) -> ValidationResult:
    """
    Validate the output of a step.
    
    Args:
        output_file: Path to output file
        step_name: Name of the step
    
    Returns:
        ValidationResult with is_valid, errors, warnings
    """
```

**Example:**
```python
result = executor.validate_output(
    output_file=Path("concepts/concepts.json"),
    step_name="stepC3"
)

if result.is_valid:
    print("✓ Validation passed")
else:
    print(f"✗ Validation failed: {result.errors}")
    print(f"Warnings: {result.warnings}")
```

---

## 4. Pipeline Orchestrator API

### PipelineOrchestrator

**File:** `prompt_pipeline/orchestrator.py`  
**Lines:** 16,899 bytes

#### Initialization

```python
from prompt_pipeline.orchestrator import PipelineOrchestrator

orchestrator = PipelineOrchestrator(
    config_path: str = "configuration/pipeline_config.yaml",
    output_dir: Path = Path("pipeline_output/"),
    model_level: int = 1,
    skip_validation: bool = False
)
```

#### Methods

##### `execute_pipeline()`

Execute the full pipeline.

```python
def execute_pipeline(
    self,
    nl_spec_file: Optional[Path] = None,
    cli_inputs: Optional[Dict[str, str]] = None,
    approval_mode: str = "auto",
    import_database: Optional[str] = None,
    wipe: bool = False
) -> Dict[str, Any]:
    """
    Execute the complete pipeline.
    
    Args:
        nl_spec_file: Path to NL spec file (for step1)
        cli_inputs: Additional CLI inputs
        approval_mode: "interactive", "auto", or "dry-run"
        import_database: Database name for TypeDB import
        wipe: Whether to wipe database before import
    
    Returns:
        Dictionary with execution results and metrics
    
    Raises:
        PipelineExecutionError: If pipeline fails
    """
```

**Example:**
```python
orchestrator = PipelineOrchestrator(
    config_path="configuration/pipeline_config.yaml",
    output_dir=Path("pipeline_output/"),
    model_level=1
)

results = orchestrator.execute_pipeline(
    nl_spec_file=Path("doc/todo_list_spec.md"),
    approval_mode="auto",
    import_database="todo_app",
    wipe=True
)

print(f"Steps executed: {results['steps_executed']}")
print(f"Total cost: ${results['total_cost']}")
print(f"Total time: {results['total_time']}s")
```

##### `get_execution_plan()`

Get the execution plan for the pipeline.

```python
def get_execution_plan(
    self,
    start_step: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get the execution plan for the pipeline.
    
    Args:
        start_step: Name of step to start from (optional)
    
    Returns:
        List of step execution plans
    """
```

**Example:**
```python
plan = orchestrator.get_execution_plan()
for step in plan:
    print(f"Step: {step['name']}")
    print(f"  Order: {step['order']}")
    print(f"  Dependencies: {step['dependencies']}")
    print(f"  Inputs: {[inp['label'] for inp in step['inputs']]}")
    print(f"  Outputs: {[out['label'] for out in step['outputs']]}")
```

##### `get_step_dependencies()`

Get dependencies for a step.

```python
def get_step_dependencies(
    self,
    step_name: str
) -> List[str]:
    """
    Get the dependency chain for a step.
    
    Args:
        step_name: Name of the step
    
    Returns:
        List of required step names in execution order
    """
```

---

## 5. Compression Manager API

### CompressionManager

**File:** `prompt_pipeline/compression/manager.py`  
**Lines:** 18,927 bytes

#### Initialization

```python
from prompt_pipeline.compression import CompressionManager, CompressionConfig

manager = CompressionManager()
```

#### Methods

##### `compress()`

Compress content using a strategy.

```python
def compress(
    self,
    content: str,
    strategy: str,
    config: Optional[CompressionConfig] = None
) -> CompressionResult:
    """
    Compress content using the specified strategy.
    
    Args:
        content: Content to compress
        strategy: Strategy name (e.g., "hierarchical", "anchor_index")
        config: Compression configuration
    
    Returns:
        CompressionResult with compressed content and metrics
    """
```

**CompressionConfig:**
```python
config = CompressionConfig(
    strategy="hierarchical",
    level=3,  # 1=light, 2=medium, 3=aggressive
    preserve_full=False,
    truncation_length=4000,
    metadata={"preserve_relations": True}
)
```

**Example:**
```python
from prompt_pipeline.compression import CompressionManager, CompressionConfig

manager = CompressionManager()

# Compress with default config
result = manager.compress(
    content="Large specification content...",
    strategy="hierarchical"
)

print(f"Original: {result.original_length} bytes")
print(f"Compressed: {result.compressed_length} bytes")
print(f"Reduction: {result.reduction_percent:.1f}%")
print(f"Content: {result.content[:500]}...")
```

##### `get_strategy()`

Get a compression strategy by name.

```python
def get_strategy(self, name: str) -> CompressionStrategy:
    """
    Get a compression strategy by name.
    
    Args:
        name: Strategy name
    
    Returns:
        CompressionStrategy instance
    
    Raises:
        ValueError: If strategy not found
    """
```

##### `get_available_strategies()`

List available strategies.

```python
def get_available_strategies(self) -> List[str]:
    """
    Get list of available compression strategy names.
    
    Returns:
        List of strategy names
    """
```

**Example:**
```python
manager = CompressionManager()
strategies = manager.get_available_strategies()
# ['zero', 'anchor_index', 'concept_summary', 'hierarchical', 
#  'schema_only', 'differential', 'yaml_as_json']
```

### CompressionResult

```python
@dataclass
class CompressionResult:
    """Result of a compression operation."""
    
    content: str
    original_length: int
    compressed_length: int
    compression_ratio: float
    strategy: str
    metadata: Optional[Dict[str, Any]] = None
    
    @property
    def reduction_percent(self) -> float:
        """Get reduction percentage."""
        return (1 - self.compression_ratio) * 100
```

---

## 6. Validation API

### YAMLValidator

**File:** `prompt_pipeline/validation/yaml_validator.py`  
**Lines:** 24,127 bytes

#### Methods

##### `validate()`

Validate YAML content.

```python
def validate(
    self,
    content: str,
    schema_path: Optional[Path] = None
) -> ValidationResult:
    """
    Validate YAML content.
    
    Args:
        content: YAML content to validate
        schema_path: Path to JSON schema (optional)
    
    Returns:
        ValidationResult with is_valid, errors, warnings
    """
```

**Example:**
```python
from prompt_pipeline.validation import YAMLValidator

validator = YAMLValidator()

with open("spec_1.yaml") as f:
    yaml_content = f.read()

result = validator.validate(
    content=yaml_content,
    schema_path=Path("schemas/spec_yaml_schema.json")
)

if result.is_valid:
    print("✓ YAML is valid")
else:
    print(f"✗ Errors: {result.errors}")
```

### JSONValidator

**File:** `prompt_pipeline/validation/json_validator.py`  
**Lines:** 12,739 bytes

#### Methods

##### `validate()`

Validate JSON content.

```python
def validate(
    self,
    content: str,
    schema: Optional[Dict[str, Any]] = None,
    schema_path: Optional[Path] = None
) -> ValidationResult:
    """
    Validate JSON content.
    
    Args:
        content: JSON content to validate
        schema: JSON schema as dict (optional)
        schema_path: Path to JSON schema file (optional)
    
    Returns:
        ValidationResult with is_valid, errors, warnings
    """
```

**Example:**
```python
from prompt_pipeline.validation import JSONValidator

validator = JSONValidator()

with open("concepts.json") as f:
    json_content = f.read()

result = validator.validate(
    content=json_content,
    schema_path=Path("schemas/concepts.schema.json")
)
```

##### `validate_concepts()`

Validate concepts JSON.

```python
def validate_concepts(self, json_content: str) -> ValidationResult:
    """Validate concepts.json structure."""
```

##### `validate_aggregations()`

Validate aggregations JSON.

```python
def validate_aggregations(self, json_content: str) -> ValidationResult:
    """Validate aggregations.json structure."""
```

##### `validate_messages()`

Validate messages JSON.

```python
def validate_messages(self, json_content: str) -> ValidationResult:
    """Validate messages.json structure."""
```

##### `validate_requirements()`

Validate requirements JSON.

```python
def validate_requirements(self, json_content: str) -> ValidationResult:
    """Validate requirements.json structure."""
```

### ValidationResult

```python
@dataclass
class ValidationResult:
    """Result of validation operation."""
    
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None
```

---

## 7. CLI API

### CLI Command: run-step

**File:** `prompt_pipeline_cli/commands/run_step.py`

#### Command Syntax

```bash
prompt-pipeline run-step <step_name> [OPTIONS]
```

#### Options

| Option | Type | Description |
|--------|------|-------------|
| `--input-file` | str | Input file (label:filename) |
| `--input-prompt` | str | Interactive prompt for input |
| `--input-text` | str | Direct text input (label:"text") |
| `--input-env` | str | Environment variable input (label:ENV_VAR) |
| `--approve` | flag | Show prompt and wait for confirmation |
| `--auto-approve` | flag | Skip approval prompt |
| `--dry-run` | flag | Show what would happen without executing |
| `--show-prompt` | flag | Display substituted prompt |
| `--show-response` | flag | Display LLM response |
| `--model-level` | int | Model quality level (1-3) |
| `--model` | str | Override model selection |
| `--output-dir` | str | Output directory |
| `--output-file` | str | Specific output filename |
| `--skip-validation` | flag | Skip validation (dev mode) |
| `--force` | flag | Continue despite warnings |
| `--config` | str | Custom configuration file |
| `--verbosity` | int | Verbosity level (0-3) |
| `--batch` | flag | Disable all interactive prompts |

#### Examples

```bash
# Basic execution
prompt-pipeline run-step stepC3 \
  --input-file spec:yaml/spec_1.yaml \
  --approve

# Multiple inputs
prompt-pipeline run-step stepC4 \
  --input-file spec:yaml/spec_1.yaml \
  --input-file concepts:concepts/concepts.json \
  --approve

# Dry run
prompt-pipeline run-step stepC3 \
  --input-file spec:yaml/spec_1.yaml \
  --dry-run

# Interactive prompt
prompt-pipeline run-step step1 \
  --input-prompt nl_spec \
  --approve

# Batch mode
prompt-pipeline run-step stepC3 \
  --input-file spec:yaml/spec_1.yaml \
  --auto-approve

# With verbosity
prompt-pipeline run-step stepC3 \
  --input-file spec:yaml/spec_1.yaml \
  --approve \
  --verbosity 2
```

### CLI Command: run-pipeline

**File:** `prompt_pipeline_cli/commands/run_pipeline.py`

#### Command Syntax

```bash
prompt-pipeline run-pipeline [OPTIONS]
```

#### Options

| Option | Type | Description |
|--------|------|-------------|
| `--nl-spec` | str | Path to NL spec file |
| `--input-file` | str | Input file (label:filename) |
| `--output-dir` | str | Output directory |
| `--import-database` | str | Database name for TypeDB import |
| `--wipe` | flag | Wipe database before import |
| `--model-level` | int | Model quality level (1-3) |
| `--auto-approve` | flag | Skip approval prompts |
| `--verbosity` | int | Verbosity level (0-3) |

#### Examples

```bash
# Basic pipeline
prompt-pipeline run-pipeline \
  --nl-spec doc/todo_list_spec.md

# With import
prompt-pipeline run-pipeline \
  --nl-spec doc/todo_list_spec.md \
  --import-database todo_app \
  --wipe

# Custom output directory
prompt-pipeline run-pipeline \
  --nl-spec doc/todo_list_spec.md \
  --output-dir output/

# With specific model level
prompt-pipeline run-pipeline \
  --nl-spec doc/todo_list_spec.md \
  --model-level 2

# Batch mode
prompt-pipeline run-pipeline \
  --nl-spec doc/todo_list_spec.md \
  --auto-approve
```

### CLI Command: import

**File:** `prompt_pipeline_cli/commands/import_cmd.py`

#### Command Syntax

```bash
prompt-pipeline import [OPTIONS]
```

#### Options

| Option | Type | Description |
|--------|------|-------------|
| `--file` | str | Path to JSON file to import |
| `--database` | str | TypeDB database name |
| `--wipe` | flag | Wipe database before import |
| `--import-id` | str | Import ID for versioning |

#### Examples

```bash
# Basic import
prompt-pipeline import \
  --file requirements/requirements.json \
  --database my_app

# With wipe
prompt-pipeline import \
  --file requirements/requirements.json \
  --database my_app \
  --wipe

# With import ID
prompt-pipeline import \
  --file requirements/requirements.json \
  --database my_app \
  --import-id "v1.0"
```

### CLI Command: validate

**File:** `prompt_pipeline_cli/commands/validate.py`

#### Command Syntax

```bash
prompt-pipeline validate [OPTIONS]
```

#### Options

| Option | Type | Description |
|--------|------|-------------|
| `--config` | str | Path to configuration file |
| `--file` | str | Path to file to validate |

#### Examples

```bash
# Validate configuration
prompt-pipeline validate --config configuration/pipeline_config.yaml

# Validate a file
prompt-pipeline validate --file concepts/concepts.json
```

### CLI Command: config

**File:** `prompt_pipeline_cli/commands/config.py`

#### Command Syntax

```bash
prompt-pipeline config [OPTIONS]
```

#### Options

| Option | Type | Description |
|--------|------|-------------|
| `--show` | flag | Show configuration details |

#### Example

```bash
prompt-pipeline config --show
```

---

## 8. TypeDB Importer API

### TypeDBImporter

**File:** `prompt_pipeline/importer/importer.py`  
**Lines:** 33,283 bytes

#### Initialization

```python
from prompt_pipeline.importer import TypeDBImporter

importer = TypeDBImporter(
    base_url: str = "http://localhost:8000",
    username: str = "admin",
    password: str = "password"
)
```

#### Methods

##### `import_file()`

Import data from a file.

```python
def import_file(
    self,
    file_path: Path,
    database: str,
    wipe: bool = False,
    import_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Import data from a JSON file to TypeDB.
    
    Args:
        file_path: Path to JSON file
        database: Database name
        wipe: Whether to wipe database before import
        import_id: Import ID for versioning
    
    Returns:
        Dict with import metrics (entities, relations, time)
    
    Raises:
        ImportError: If import fails
    """
```

**Example:**
```python
from prompt_pipeline.importer import TypeDBImporter

importer = TypeDBImporter(
    base_url="http://localhost:8000",
    username="admin",
    password="password"
)

metrics = importer.import_file(
    file_path=Path("requirements/requirements.json"),
    database="todo_app",
    wipe=True,
    import_id="v1.0"
)

print(f"Entities created: {metrics['entities_created']}")
print(f"Relations created: {metrics['relations_created']}")
print(f"Import time: {metrics['import_time']}s")
```

#### Entity Model

**Core Entities:**
- `Actor`: System actors and users
- `Action`: Actions and operations
- `Message`: Messages and communications
- `Concept`: Domain concepts
- `Requirement`: System requirements
- `Constraint`: Design constraints
- `TextBlock`: Specification text segments

**Relations:**
- `Messaging`: Message producer-consumer relationships
- `Anchoring`: Concept-text anchoring
- `Membership`: Entity membership
- `Requiring`: Requirement relationships

---

## 9. Terminal Utils API

### Terminal Output Functions

**File:** `prompt_pipeline/terminal_utils.py`  
**Lines:** 7,048 bytes

#### Print Functions

```python
from prompt_pipeline.terminal_utils import (
    print_info,
    print_success,
    print_warning,
    print_error,
    print_header,
    format_step,
    format_model,
    Color
)
```

##### `print_info()`

Print informational message.

```python
def print_info(
    message: str,
    prefix: str = "ℹ"
) -> None:
    """
    Print info message with color.
    
    Args:
        message: Message to print
        prefix: Prefix symbol
    """
```

##### `print_success()`

Print success message.

```python
def print_success(
    message: str,
    prefix: str = "✓"
) -> None:
    """
    Print success message with color.
    
    Args:
        message: Message to print
        prefix: Prefix symbol
    """
```

##### `print_warning()`

Print warning message.

```python
def print_warning(
    message: str,
    prefix: str = "⚠"
) -> None:
    """
    Print warning message with color.
    
    Args:
        message: Message to print
        prefix: Prefix symbol
    """
```

##### `print_error()`

Print error message.

```python
def print_error(
    message: str,
    prefix: str = "✗"
) -> None:
    """
    Print error message with color.
    
    Args:
        message: Message to print
        prefix: Prefix symbol
    """
```

##### `print_header()`

Print formatted header.

```python
def print_header(
    title: str,
    width: int = 60
) -> None:
    """
    Print formatted header.
    
    Args:
        title: Header title
        width: Width of header
    """
```

##### `format_step()`

Format step name for display.

```python
def format_step(step_name: str) -> str:
    """
    Format step name with color.
    
    Args:
        step_name: Step name
    
    Returns:
        Formatted string with color codes
    """
```

##### `format_model()`

Format model name for display.

```python
def format_model(model: str) -> str:
    """
    Format model name with color.
    
    Args:
        model: Model name
    
    Returns:
        Formatted string with color codes
    """
```

#### Spinner Class

```python
from prompt_pipeline.terminal_utils import Spinner

spinner = Spinner(
    message: str = "Processing...",
    interval: float = 0.1
)

with spinner:
    # Long-running operation
    time.sleep(2)
```

**Example:**
```python
from prompt_pipeline.terminal_utils import Spinner
import time

with Spinner("Calling LLM API..."):
    time.sleep(3)  # Simulate API call
# Output: Calling LLM API... ⠋ (spinning animation)
```

#### Color Constants

```python
from prompt_pipeline.terminal_utils import Color

Color.CYAN    # Cyan for primary inputs
Color.GREEN   # Green for secondary inputs
Color.YELLOW  # Yellow for tertiary inputs
Color.MAGENTA # Magenta for special inputs
Color.RED     # Red for errors
Color.BLUE    # Blue for info
Color.WHITE   # White for normal text
```

---

## 10. Label Registry API

### LabelRegistry

**File:** `prompt_pipeline/label_registry.py`  
**Lines:** 13,560 bytes

#### Initialization

```python
from prompt_pipeline.label_registry import LabelRegistry

registry = LabelRegistry()
```

#### Methods

##### `register_output()`

Register a step output.

```python
def register_output(
    self,
    step_name: str,
    label: str,
    file_path: Path,
    file_type: str
) -> None:
    """
    Register an output for use by subsequent steps.
    
    Args:
        step_name: Name of the step producing output
        label: Label to register
        file_path: Path to output file
        file_type: Type of file (yaml, json, etc.)
    """
```

**Example:**
```python
from pathlib import Path

registry = LabelRegistry()

# After stepC3 executes
registry.register_output(
    step_name="stepC3",
    label="concepts",
    file_path=Path("concepts/concepts.json"),
    file_type="json"
)
```

##### `get_label_path()`

Get file path for a label.

```python
def get_label_path(
    self,
    label: str,
    step_name: Optional[str] = None
) -> Optional[Path]:
    """
    Get file path for a label.
    
    Args:
        label: Label name
        step_name: Optional step name for scoping
    
    Returns:
        Path to file or None if not found
    """
```

##### `resolve_label()`

Resolve label to file content.

```python
def resolve_label(
    self,
    label: str,
    step_name: Optional[str] = None
) -> Optional[str]:
    """
    Resolve label to file content.
    
    Args:
        label: Label name
        step_name: Optional step name for scoping
    
    Returns:
        File content as string or None if not found
    """
```

##### `clear_registry()`

Clear the registry.

```python
def clear_registry(self) -> None:
    """
    Clear all registered labels.
    """
```

##### `get_all_labels()`

Get all registered labels.

```python
def get_all_labels(self) -> List[str]:
    """
    Get all registered labels.
    
    Returns:
        List of label names
    """
```

---

## Error Types

### OpenRouterError

```python
class OpenRouterError(Exception):
    """Exception raised for OpenRouter API errors."""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        details: Optional[Dict] = None,
        retry_count: int = 0
    ):
        self.message = message
        self.status_code = status_code
        self.details = details
        self.retry_count = retry_count
        super().__init__(message)
```

### StepExecutionError

```python
class StepExecutionError(Exception):
    """Exception raised when step execution fails."""
    
    def __init__(
        self,
        message: str,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None
    ):
        self.message = message
        self.errors = errors or []
        self.warnings = warnings or []
        super().__init__(message)
```

### InputValidationError

```python
class InputValidationError(Exception):
    """Exception raised for invalid inputs."""
    
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)
```

### ImportError

```python
class ImportError(Exception):
    """Exception raised for TypeDB import errors."""
    
    def __init__(
        self,
        message: str,
        cause: Optional[Exception] = None
    ):
        self.message = message
        self.cause = cause
        super().__init__(message)
```

---

## Quick Reference

### Common Patterns

**Pattern 1: Execute Step with Approval**
```python
executor = StepExecutor(
    llm_client=OpenRouterClient(),
    prompt_manager=PromptManager(),
    output_dir=Path("output/"),
    model_level=1
)

success, outputs = executor.execute_step(
    step_name="stepC3",
    cli_inputs={'spec': 'yaml/spec_1.yaml'},
    approval_mode="interactive"
)
```

**Pattern 2: Full Pipeline**
```python
orchestrator = PipelineOrchestrator(
    config_path="configuration/pipeline_config.yaml",
    output_dir=Path("pipeline_output/"),
    model_level=1
)

results = orchestrator.execute_pipeline(
    nl_spec_file=Path("doc/spec.md"),
    approval_mode="auto",
    import_database="my_app",
    wipe=True
)
```

**Pattern 3: Compression**
```python
from prompt_pipeline.compression import CompressionManager

manager = CompressionManager()
result = manager.compress(
    content="Large content...",
    strategy="hierarchical",
    config=CompressionConfig(level=3)
)
```

**Pattern 4: Validation**
```python
from prompt_pipeline.validation import JSONValidator

validator = JSONValidator()
result = validator.validate(
    content=json_content,
    schema_path=Path("schemas/concepts.schema.json")
)
```

---

## Environment Variables

```bash
# Required
export OPENROUTER_API_KEY="sk-or-..."
export TYPEDB_URL="http://localhost:8000"
export TYPEDB_USERNAME="admin"
export TYPEDB_PASSWORD="password"

# Optional
export MODEL_LEVEL="1"  # Default model level
export VERBOSITY="2"    # Default verbosity
```

---

## Version Information

**Document Version:** 1.0  
**Last Updated:** 2026-02-26  
**Status:** Complete  
**Project:** ModelLM v0.1.0
