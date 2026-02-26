"""Run Step CLI Command - Updated with Generic Input Options."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import click

from prompt_pipeline.llm_client import OpenRouterClient
from prompt_pipeline.orchestrator import PipelineOrchestrator
from prompt_pipeline.prompt_manager import PromptManager
from prompt_pipeline.step_executor import StepExecutor
from prompt_pipeline.step_executor_dry_run import construct_prompt_without_api_call, DryRunResult
from prompt_pipeline.terminal_utils import (
    print_success,
    print_warning,
    print_error,
    print_info,
    print_header,
    print_section,
    format_step,
    Color,
)
from prompt_pipeline_cli.input_validation import InputTypeValidator, InputValidationError


def _analyze_step_dependencies(
    prompt_manager: PromptManager,
    step_name: str,
    nl_spec: Optional[str] = None,
) -> Dict[str, any]:
    """
    Analyze step dependencies and suggest solutions.
    
    Args:
        prompt_manager: PromptManager instance
        step_name: Name of the step to run
        nl_spec: Path to NL spec file if provided
    
    Returns:
        Dictionary with dependency analysis
    """
    step_config = prompt_manager.get_step_config(step_name)
    if not step_config:
        return {"error": f"Step '{step_name}' not found"}
    
    # Get all steps from config
    steps_config = prompt_manager.steps_config.get("steps", {})
    
    # Map labels to producing steps
    label_to_step = {}
    for step_name_key, config in steps_config.items():
        outputs = config.get("outputs", [])
        for output in outputs:
            label = output.get("label")
            if label:
                label_to_step[label] = step_name_key
    
    # Find which labels this step needs
    inputs_config = step_config.get("inputs", [])
    dependencies = []
    missing_inputs = []
    
    for input_spec in inputs_config:
        label = input_spec.get("label")
        source = input_spec.get("source", "")
        
        if source.startswith("label:"):
            ref_label = source[6:]
            producing_step = label_to_step.get(ref_label)
            if producing_step:
                dependencies.append({
                    "label": ref_label,
                    "producing_step": producing_step,
                    "input_type": input_spec.get("type", "unknown"),
                })
    
    # Suggest the full pipeline to run
    dependency_chain = []
    if dependencies:
        # Get unique steps in order
        unique_steps = []
        for dep in dependencies:
            if dep["producing_step"] not in unique_steps:
                unique_steps.append(dep["producing_step"])
        
        # Sort by order
        step_configs = {name: steps_config[name] for name in unique_steps if name in steps_config}
        sorted_steps = sorted(
            step_configs.items(),
            key=lambda x: x[1].get("order", 999)
        )
        
        dependency_chain = [step for step, _ in sorted_steps]
    
    return {
        "step_name": step_name,
        "dependencies": dependencies,
        "dependency_chain": dependency_chain,
        "nl_spec_required": any(
            inp.get("source") == "cli" and inp.get("label") == "nl_spec"
            for inp in inputs_config
        ),
    }


def _get_step_info(
    prompt_manager: PromptManager,
    step_name: str,
) -> Optional[Dict[str, any]]:
    """
    Gather all information about a step from configuration.
    
    Args:
        prompt_manager: PromptManager instance
        step_name: Name of the step
    
    Returns:
        Dictionary with all step information including:
        - step_name
        - configuration (name, order, persona, prompt_file)
        - inputs (label, source, type, compression, color, data_entity)
        - outputs (label, type, data_entity)
        - model_levels
        - validation
        - dependencies
    """
    # Get step configuration
    step_config = prompt_manager.get_step_config(step_name)
    if not step_config:
        return None
    
    # Get step configuration details
    configuration = {
        "name": step_name,
        "order": step_config.get("order"),
        "persona": step_config.get("persona"),
        "prompt_file": step_config.get("prompt_file"),
    }
    
    # Get inputs with data_entity details
    inputs = []
    inputs_config = step_config.get("inputs", [])
    for input_spec in inputs_config:
        input_info = {
            "label": input_spec.get("label"),
            "source": input_spec.get("source"),
            "type": input_spec.get("type"),
            "compression": input_spec.get("compression", "none"),
        }
        
        # Get compression params if present
        if input_spec.get("compression_params"):
            input_info["compression_params"] = input_spec.get("compression_params")
        
        # Get color if present
        if input_spec.get("color"):
            input_info["color"] = input_spec.get("color")
        
        # Get data_entity details
        label = input_spec.get("label")
        data_entity = prompt_manager.get_data_entity(label)
        if data_entity:
            input_info["data_entity"] = {
                "filename": data_entity.get("filename"),
                "description": data_entity.get("description"),
                "schema": data_entity.get("yaml_schema"),
            }
        
        inputs.append(input_info)
    
    # Get outputs with data_entity details
    outputs = []
    outputs_config = step_config.get("outputs", [])
    for output_spec in outputs_config:
        output_info = {
            "label": output_spec.get("label"),
            "type": output_spec.get("type"),
        }
        
        # Get data_entity details
        label = output_spec.get("label")
        data_entity = prompt_manager.get_data_entity(label)
        if data_entity:
            output_info["data_entity"] = {
                "filename": data_entity.get("filename"),
                "description": data_entity.get("description"),
                "schema": data_entity.get("yaml_schema"),
            }
        
        outputs.append(output_info)
    
    # Get model levels
    model_levels = step_config.get("model_levels", {})
    
    # Get validation config
    validation = step_config.get("validation", {})
    
    # Get dependencies (labels that this step depends on)
    dependencies = []
    for input_spec in inputs_config:
        source = input_spec.get("source", "")
        if source.startswith("label:"):
            dependencies.append(source[6:])
    
    return {
        "step_name": step_name,
        "configuration": configuration,
        "inputs": inputs,
        "outputs": outputs,
        "model_levels": model_levels,
        "validation": validation,
        "dependencies": dependencies,
    }


def display_step_info(
    info: Dict[str, any],
    verbose: bool = False,
    as_json: bool = False,
) -> None:
    """
    Display step information in formatted output.
    
    Args:
        info: Step information dictionary
        verbose: Whether to show detailed explanations
        as_json: Whether to output as JSON
    """
    if as_json:
        import json
        print(json.dumps(info, indent=2))
        return
    
    # Display sections
    print_header(f"STEP INFORMATION: {info['step_name']}", Color.CYAN)
    
    # Step Configuration
    print_section("Step Configuration")
    for key, value in info['configuration'].items():
        if value is not None:
            print_info(f"  {key.replace('_', ' ').title()}: {value}")
    
    # Input Requirements
    _display_input_requirements(info['inputs'])
    
    # Output Definitions
    _display_output_definitions(info['outputs'])
    
    # Configuration Settings
    _display_configuration_settings(info)
    
    # CLI Switches
    print_section("Applicable CLI Switches")
    _display_cli_switches()
    
    # Example Commands
    print_section("Example Commands")
    _display_example_commands(info['step_name'])
    
    # Dependencies
    if info.get('dependencies'):
        print_section("Dependency Analysis")
        _display_dependency_analysis(info['step_name'], info['dependencies'])
    
    # Verbose Mode
    if verbose:
        print_section("Detailed Explanations")
        _display_verbose_explanations(info)


def _display_input_requirements(inputs: List[Dict]) -> None:
    """Display input requirements section."""
    print_section("Input Requirements")
    for i, input_info in enumerate(inputs, 1):
        print_info(f"\nInput #{i}:")
        print_info(f"  Label: {input_info['label']}")
        print_info(f"  Source: {input_info['source']}")
        print_info(f"  Type: {input_info['type']}")
        print_info(f"  Compression: {input_info['compression']}")
        
        if input_info.get('compression_params'):
            for key, value in input_info['compression_params'].items():
                print_info(f"    {key}: {value}")
        
        if input_info.get('color'):
            print_info(f"  Color: {input_info['color']}")
        
        if input_info.get('data_entity'):
            print_info(f"  Data Entity:")
            de = input_info['data_entity']
            print_info(f"    Filename: {de.get('filename')}")
            print_info(f"    Description: {de.get('description')}")
            if de.get('schema'):
                print_info(f"    Schema: {de.get('schema')}")


def _display_output_definitions(outputs: List[Dict]) -> None:
    """Display output definitions section."""
    print_section("Output Definitions")
    for i, output_info in enumerate(outputs, 1):
        print_info(f"\nOutput #{i}:")
        print_info(f"  Label: {output_info['label']}")
        print_info(f"  Type: {output_info['type']}")
        
        if output_info.get('data_entity'):
            de = output_info['data_entity']
            print_info(f"  Description: {de.get('description')}")
            if de.get('schema'):
                print_info(f"  Schema: {de.get('schema')}")
            print_info(f"  Filename: {de.get('filename')}")


def _display_configuration_settings(info: Dict[str, any]) -> None:
    """Display configuration settings section."""
    print_section("Configuration Settings")
    
    if info.get('model_levels'):
        print_info("\nModel Levels:")
        for level, model in sorted(info['model_levels'].items(), key=lambda x: int(x[0])):
            level_desc = {1: "fast/cheap", 2: "balanced", 3: "best"}.get(int(level), "unknown")
            print_info(f"  Level {level} ({level_desc}): {model}")
    
    if info.get('validation'):
        validation = info['validation']
        print_info("\nValidation:")
        print_info(f"  Enabled: {validation.get('enabled', False)}")
        if validation.get('schema'):
            print_info(f"  Schema: {validation.get('schema')}")
    
    if info.get('dependencies'):
        print_info("\nDependencies:")
        print_info(f"  Required steps: {', '.join(info['dependencies'])}")


def _display_cli_switches() -> None:
    """Display applicable CLI switches section."""
    switch_categories = {
        "Required Inputs": [
            ("--input-file label:filename", "Provide input from file"),
            ("--input-prompt label", "Prompt user to enter content"),
            ("--input-text label:\"value\"", "Provide content directly"),
        ],
        "Execution Control": [
            ("--dry-run", "Show what would happen without executing"),
            ("--dry-run-prompt", "Display the full prompt without API calls"),
            ("--approve", "Show prompt and wait for confirmation"),
            ("--auto-approve", "Skip approval prompt (CI/CD)"),
            ("--force", "Continue with missing inputs (substitute empty)"),
        ],
        "Output Control": [
            ("--output-dir PATH", "Output directory (default: pipeline_output/)"),
            ("--output-file PATH", "Override output file path"),
            ("--show-prompt", "Display prompt sent to LLM"),
            ("--show-response", "Display response from LLM"),
            ("--show-both", "Display both prompt and response"),
        ],
        "Model Control": [
            ("--model-level 1|2|3", "Model quality level"),
            ("--model NAME", "Specific model (overrides --model-level)"),
        ],
        "Info Mode": [
            ("--info", "Display step information"),
            ("--info-verbose", "Show detailed explanations"),
            ("--info-json", "Output as JSON"),
            ("--info-steps steps", "Show info for multiple steps"),
        ],
        "Other": [
            ("--skip-validation", "Skip output validation"),
            ("--batch", "Run in batch mode (no interactive prompts)"),
            ("--help", "Show this help message"),
        ],
    }
    
    for category, switches in switch_categories.items():
        print_info(f"\n{category}:")
        for flag, desc in switches:
            # Align columns for readability
            print_info(f"  {flag:40} {desc}")


def _display_example_commands(step_name: str) -> None:
    """Display example commands section."""
    examples = [
        f"prompt-pipeline run-step {step_name} --input-file nl_spec:doc/todo_list_nl_spec.md",
        f"prompt-pipeline run-step {step_name} --input-file nl_spec:doc/todo_list_nl_spec.md --approve",
        f"prompt-pipeline run-step {step_name} --input-file nl_spec:doc/todo_list_nl_spec.md --dry-run-prompt",
        f"prompt-pipeline run-step {step_name} --input-file nl_spec:doc/todo_list_nl_spec.md --auto-approve",
        f"prompt-pipeline run-step {step_name} --info",
        f"prompt-pipeline run-step {step_name} --info --info-verbose",
    ]
    
    for example in examples:
        print_info(f"\n  {example}")


def _display_dependency_analysis(step_name: str, dependencies: List[str]) -> None:
    """Display dependency analysis section."""
    print_info("\nThis step depends on:")
    for dep in dependencies:
        print_info(f"  - Previous step output: {dep}")
    
    print_info("\nTo run this step, you must first run:")
    for dep in dependencies:
        print_info(f"  1. prompt-pipeline run-step <step_name> --input-file {dep}:<filename>")
    
    print_info("\nOr run the full pipeline:")
    print_info(f"  prompt-pipeline run-pipeline --input-file nl_spec:doc/todo_list_nl_spec.md")


def _display_verbose_explanations(info: Dict[str, any]) -> None:
    """Display detailed explanations for verbose mode."""
    # Compression strategies explanations
    print_info("\nCOMPRESSION STRATEGIES:")
    
    if info.get('inputs'):
        for input_info in info['inputs']:
            compression = input_info.get('compression')
            if compression and compression != 'none':
                print_info(f"\n  {compression}:")
                if compression == 'hierarchical':
                    print_info("    Creates a hierarchical representation that preserves")
                    print_info("    the original structure while reducing context size.")
                    print_info("    Layers: Executive summary, concept inventory,")
                    print_info("    detailed definitions, source evidence.")
                    print_info("    Compression ratio: ~0.3-0.5 (50-70% reduction)")
                elif compression == 'anchor_index':
                    print_info("    Extract anchor definitions from YAML spec.")
                    print_info("    Create compact index: {AN1: \"text\", AN2: \"text\"}")
                    print_info("    Compression ratio: ~0.2-0.3 (70-80% reduction)")
                elif compression == 'concept_summary':
                    print_info("    Convert Concepts.json to markdown tables.")
                    print_info("    Group by: Actors, Actions, DataEntities, Categories")
                    print_info("    Compression ratio: ~0.4-0.5 (50-60% reduction)")
                elif compression == 'yaml_as_json':
                    print_info("    Converts YAML to JSON format for prompt input.")
    
    # Input source explanations
    print_info("\nINPUT SOURCES:")
    
    if info.get('inputs'):
        for input_info in info['inputs']:
            source = input_info.get('source', '')
            label = input_info.get('label', '')
            
            if source.startswith('label:'):
                print_info(f"\n  {label} (from previous step):")
                print_info("    This input comes from the output of a previous step.")
                print_info("    Priority: High (automatic in full pipeline mode)")
                print_info(f"    Manual override: --input-file {label}:custom_file.yaml")
            elif source == 'cli':
                print_info(f"\n  {label} (interactive):")
                print_info("    This input is provided interactively by the user.")
                print_info("    Priority: CLI inputs override config")
                print_info(f"    Manual override: --input-prompt {label} or --input-file {label}:file.md")
    
    # Model level explanations
    print_info("\nMODEL LEVELS:")
    
    if info.get('model_levels'):
        print_info("\n  Level 1 (fast/cheap):")
        print_info("    Optimized for speed and cost. Use for initial development.")
        
        print_info("\n  Level 2 (balanced):")
        print_info("    Good balance of quality and performance. Use for regular execution.")
        
        print_info("\n  Level 3 (best):")
        print_info("    Highest quality output. Use for final production.")
    
    # Switch explanations
    print_info("\nSWITCH EXPLANATIONS:")
    
    print_info("\n  --dry-run:")
    print_info("    Performs all prompt construction and validation without")
    print_info("    making API calls. Useful for verifying inputs and debugging.")
    
    print_info("\n  --dry-run-prompt:")
    print_info("    Like --dry-run, but also displays the full prompt that would")
    print_info("    be sent to the LLM. Essential for debugging prompt templates.")
    
    print_info("\n  --approve:")
    print_info("    Shows the fully substituted prompt and waits for user")
    print_info("    confirmation before executing the LLM call.")
    
    print_info("\n  --auto-approve:")
    print_info("    Skips the approval prompt entirely. Use for CI/CD pipelines")
    print_info("    and automated workflows.")
    
    print_info("\n  --force:")
    print_info("    Continues execution even if required inputs are missing.")
    print_info("    WARNING: Missing inputs are substituted with empty strings!")


def handle_info(
    ctx: click.Context,
    step_name: str,
    info_verbose: bool,
    info_json: bool,
    info_steps: str,
) -> None:
    """
    Handle the --info flag to display step information.
    
    Args:
        ctx: Click context
        step_name: Name of the step
        info_verbose: Whether to show verbose explanations
        info_json: Whether to output as JSON
        info_steps: Comma-separated list of additional steps
    """
    config_path = ctx.obj.get("config", "configuration/pipeline_config.yaml")
    
    # Initialize prompt manager
    try:
        prompt_manager = PromptManager(config_path)
    except Exception as e:
        raise click.ClickException(f"Failed to load configuration: {e}")
    
    # Determine steps to show
    steps_to_show = [step_name]
    
    if info_steps:
        additional_steps = [s.strip() for s in info_steps.split(",") if s.strip()]
        steps_to_show.extend(additional_steps)
    
    # Display info for each step
    for step_name_to_show in steps_to_show:
        try:
            step_info = _get_step_info(prompt_manager, step_name_to_show)
            
            if step_info is None:
                raise click.ClickException(f"Step '{step_name_to_show}' not found")
            
            display_step_info(
                step_info,
                verbose=info_verbose,
                as_json=info_json,
            )
            
            if not info_json and step_name_to_show != steps_to_show[-1]:
                print()  # Blank line between steps
                
        except Exception as e:
            raise click.ClickException(f"Failed to get info for step '{step_name_to_show}': {e}")


def _parse_input_file_option(value: str) -> Tuple[str, str]:
    """
    Parse --input-file value in format label:filename.
    
    Args:
        value: Input in format "label:filename"
    
    Returns:
        Tuple of (label, filename)
    
    Raises:
        click.ClickException: If format is invalid
    """
    if ":" not in value:
        raise click.ClickException(
            f"Invalid --input-file format: '{value}'. "
            "Expected format: label:filename"
        )
    
    parts = value.split(":", 1)
    label = parts[0].strip()
    filename = parts[1].strip()
    
    if not label or not filename:
        raise click.ClickException(
            f"Invalid --input-file format: '{value}'. "
            "Both label and filename must be non-empty."
        )
    
    return label, filename


def _parse_input_text_option(value: str) -> Tuple[str, str]:
    """
    Parse --input-text value in format label:"content".
    
    Args:
        value: Input in format 'label:"content"' or label:content
    
    Returns:
        Tuple of (label, content)
    
    Raises:
        click.ClickException: If format is invalid
    """
    if ":" not in value:
        raise click.ClickException(
            f"Invalid --input-text format: '{value}'. "
            "Expected format: label:content or label:\"content with spaces\""
        )
    
    parts = value.split(":", 1)
    label = parts[0].strip()
    content = parts[1].strip()
    
    # Remove surrounding quotes if present
    if (content.startswith('"') and content.endswith('"')) or \
       (content.startswith("'") and content.endswith("'")):
        content = content[1:-1]
    
    if not label:
        raise click.ClickException(
            f"Invalid --input-text format: '{value}'. "
            "Label must be non-empty."
        )
    
    return label, content


def _parse_input_prompt_option(value: str) -> str:
    """
    Parse --input-prompt value (just the label).
    
    Args:
        value: Input label
    
    Returns:
        Label string
    
    Raises:
        click.ClickException: If format is invalid
    """
    if not value:
        raise click.ClickException(
            "Invalid --input-prompt format: label cannot be empty"
        )
    
    return value.strip()


def _collect_inputs_from_cli(
    ctx: click.Context,
    step_name: str,
    config_path: str,
    input_file_options: List[str],
    input_prompt_options: List[str],
    input_text_options: List[str],
) -> Tuple[Dict[str, str], Dict[str, Path], Dict[str, Any]]:
    """
    Collect and process all CLI inputs.
    
    Args:
        ctx: Click context
        step_name: Name of the step
        config_path: Path to configuration file
        input_file_options: List of --input-file values
        input_prompt_options: List of --input-prompt values
        input_text_options: List of --input-text values
    
    Returns:
        Tuple of (cli_inputs, exogenous_inputs, input_metadata)
    
    Raises:
        click.ClickException: If input parsing fails
    """
    cli_inputs = {}
    exogenous_inputs = {}
    input_metadata = {}
    
    prompt_manager = PromptManager(config_path)
    step_config = prompt_manager.get_step_config(step_name)
    
    if not step_config:
        raise click.ClickException(f"Step '{step_name}' not found in configuration")
    
    # Get expected inputs from step config
    inputs_config = step_config.get("inputs", [])
    expected_inputs = {inp.get("label"): inp for inp in inputs_config}
    
    # Process --input-file options
    for option_value in input_file_options:
        label, filename = _parse_input_file_option(option_value)
        
        # Check if label is expected
        if label not in expected_inputs:
            available_labels = ", ".join(expected_inputs.keys())
            print_warning(
                f"Warning: Label '{label}' is not expected for step '{step_name}'. "
                f"Available labels: {available_labels}"
            )
        
        # Get expected type for validation
        # First check if the input config has a type field
        expected_type = expected_inputs.get(label, {}).get("type")
        
        # If no type in input config, check data_entities
        if not expected_type:
            data_entity = prompt_manager.get_data_entity(label)
            if data_entity:
                expected_type = data_entity.get("type", "text")
            else:
                expected_type = "text"
        
        # Validate file
        try:
            InputTypeValidator.validate_input_type(
                label=label,
                expected_type=expected_type,
                source="file",
                content_or_path=filename,
            )
        except InputValidationError as e:
            raise click.ClickException(str(e))
        
        # Determine if this should be CLI input or exogenous input
        input_config = expected_inputs.get(label, {})
        source = input_config.get("source", "file")
        
        if source == "cli":
            # Read file content for CLI source
            try:
                content = Path(filename).read_text(encoding="utf-8")
                cli_inputs[label] = content
                input_metadata[label] = {
                    "source": "file",
                    "path": filename,
                    "type": expected_type,
                }
            except Exception as e:
                raise click.ClickException(f"Failed to read input file {filename}: {e}")
        else:
            # Treat as exogenous input (file path)
            exogenous_inputs[label] = Path(filename)
            input_metadata[label] = {
                "source": "file",
                "path": filename,
                "type": expected_type,
            }
    
    # Process --input-prompt options
    for option_value in input_prompt_options:
        label = _parse_input_prompt_option(option_value)
        
        # Check if label is expected
        if label not in expected_inputs:
            available_labels = ", ".join(expected_inputs.keys())
            print_warning(
                f"Warning: Label '{label}' is not expected for step '{step_name}'. "
                f"Available labels: {available_labels}"
            )
        
        # Get expected type
        expected_type = expected_inputs.get(label, {}).get("type")
        
        # If no type in input config, check data_entities
        if not expected_type:
            data_entity = prompt_manager.get_data_entity(label)
            if data_entity:
                expected_type = data_entity.get("type", "text")
            else:
                expected_type = "text"
        
        # Get prompt message from cli_inputs config
        cli_input_config = prompt_manager.get_cli_input_config(label)
        prompt_message = cli_input_config.get("prompt", f"Enter content for {label}:")
        
        # Prompt user for input
        print_info(f"\n{prompt_message}")
        print_info("(Press Ctrl+D on Unix/Linux or Ctrl+Z then Enter on Windows to finish)")
        
        try:
            # Read multiline input
            lines = []
            while True:
                try:
                    line = input("> ")
                    lines.append(line)
                except EOFError:
                    break
                except KeyboardInterrupt:
                    raise click.ClickException("Input cancelled by user")
            
            content = "\n".join(lines).strip()
            
            if not content:
                # Check for default value
                default_value = cli_input_config.get("default_value")
                if default_value:
                    content = default_value
                    print_info(f"Using default value: {default_value}")
                else:
                    raise click.ClickException(
                        f"No content provided for label '{label}'. "
                        f"This input is required."
                    )
            
            # Validate content
            try:
                InputTypeValidator.validate_input_type(
                    label=label,
                    expected_type=expected_type,
                    source="prompt",
                    content_or_path=content,
                )
            except InputValidationError as e:
                raise click.ClickException(str(e))
            
            cli_inputs[label] = content
            input_metadata[label] = {
                "source": "prompt",
                "type": expected_type,
            }
            
        except Exception as e:
            raise click.ClickException(f"Failed to get prompt input: {e}")
    
    # Process --input-text options
    for option_value in input_text_options:
        label, content = _parse_input_text_option(option_value)
        
        # Check if label is expected
        if label not in expected_inputs:
            available_labels = ", ".join(expected_inputs.keys())
            print_warning(
                f"Warning: Label '{label}' is not expected for step '{step_name}'. "
                f"Available labels: {available_labels}"
            )
        
        # Get expected type
        expected_type = expected_inputs.get(label, {}).get("type")
        
        # If no type in input config, check data_entities
        if not expected_type:
            data_entity = prompt_manager.get_data_entity(label)
            if data_entity:
                expected_type = data_entity.get("type", "text")
            else:
                expected_type = "text"
        
        # Validate content
        try:
            InputTypeValidator.validate_input_type(
                label=label,
                expected_type=expected_type,
                source="text",
                content_or_path=content,
            )
        except InputValidationError as e:
            raise click.ClickException(str(e))
        
        cli_inputs[label] = content
        input_metadata[label] = {
            "source": "text",
            "type": expected_type,
        }
    
    return cli_inputs, exogenous_inputs, input_metadata


def _collect_config_inputs(
    prompt_manager: PromptManager,
    step_name: str,
    cli_inputs: Dict[str, str],
    exogenous_inputs: Dict[str, Path],
    output_dir: Path,
    force: bool = False,
) -> Tuple[Dict[str, str], Dict[str, Path]]:
    """
    Collect inputs from configuration (exogenous_inputs and previous outputs).
    
    Args:
        prompt_manager: PromptManager instance
        step_name: Name of the step
        cli_inputs: CLI inputs already collected from CLI
        exogenous_inputs: Exogenous inputs already collected from CLI
        output_dir: Output directory for discovering previous outputs
        force: If True, continue even if inputs are missing
    
    Returns:
        Tuple of (cli_inputs, exogenous_inputs)
    
    Raises:
        click.ClickException: If required inputs are missing
    """
    step_config = prompt_manager.get_step_config(step_name)
    if not step_config:
        raise click.ClickException(f"Step '{step_name}' not found in configuration")
    
    inputs_config = step_config.get("inputs", [])
    
    # Process each input from config
    for input_spec in inputs_config:
        label = input_spec.get("label")
        source = input_spec.get("source", "")
        input_type = input_spec.get("type", "text")
        
        # Skip if already provided via CLI
        if label in cli_inputs or label in exogenous_inputs:
            continue
        
        # Handle file source from config
        if source == "file":
            # Try to find file in exogenous_inputs from config
            config_exogenous = prompt_manager.steps_config.get("exogenous_inputs", [])
            for exo in config_exogenous:
                if exo.get("label") == label:
                    file_path = Path(exo.get("file"))
                    if file_path.exists():
                        exogenous_inputs[label] = file_path
                    elif not force:
                        raise click.ClickException(
                            f"File not found for label '{label}': {file_path}"
                        )
                    break
        
        # Handle label source (previous step output)
        elif source.startswith("label:"):
            ref_label = source[6:]
            # Try to discover from output directory
            data_entity = prompt_manager.get_data_entity(ref_label)
            if data_entity:
                filename = data_entity.get("filename")
                if filename:
                    check_file = output_dir / filename
                    if check_file.exists():
                        exogenous_inputs[label] = check_file
                    elif not force:
                        # This is handled by orchestrator in full pipeline mode
                        pass
    
    # Check for required inputs from CLI (source:cli)
    required_cli_inputs = []
    for input_spec in inputs_config:
        source = input_spec.get("source", "")
        label = input_spec.get("label")
        
        if source == "cli":
            # For CLI source, check both cli_inputs (from prompt/text) and exogenous_inputs (from file)
            if label not in cli_inputs and label not in exogenous_inputs:
                required_cli_inputs.append(label)
    
    # Check if required CLI inputs are provided
    if required_cli_inputs and not force:
        missing = ", ".join(required_cli_inputs)
        raise click.ClickException(
            f"Missing required CLI inputs for step '{step_name}': {missing}\n"
            f"Please provide using --input-file, --input-prompt, or --input-text"
        )
    
    return cli_inputs, exogenous_inputs


def _display_compression_info(dry_run_result: DryRunResult) -> None:
    """
    Display compression information for the prompt.
    
    Args:
        dry_run_result: Result from dry-run prompt construction
    """
    if not dry_run_result.compression_metrics:
        return
    
    print_info("\n" + "=" * 80)
    print_info("COMPRESSION INFO")
    print_info("=" * 80)
    
    total_original = 0
    total_compressed = 0
    
    for label, metrics in dry_run_result.compression_metrics.items():
        original = metrics.get("original_length", 0)
        compressed = metrics.get("compressed_length", 0)
        strategy = metrics.get("strategy", "unknown")
        
        if original > 0:
            ratio = compressed / original
            reduction = (1 - ratio) * 100
            
            print_info(f"\nInput '{label}':")
            print_info(f"  Strategy: {strategy}")
            print_info(f"  Original: {original} chars")
            print_info(f"  Compressed: {compressed} chars")
            print_info(f"  Reduction: {reduction:.1f}%")
            
            total_original += original
            total_compressed += compressed
    
    if total_original > 0:
        overall_ratio = total_compressed / total_original
        overall_reduction = (1 - overall_ratio) * 100
        
        print_info(f"\nOverall:")
        print_info(f"  Total original: {total_original} chars")
        print_info(f"  Total compressed: {total_compressed} chars")
        print_info(f"  Overall reduction: {overall_reduction:.1f}%")
        print_info("=" * 80)


def _show_approval_prompt(
    dry_run_result: DryRunResult,
    step_name: str,
    input_metadata: Dict[str, Any],
) -> bool:
    """
    Show the approval prompt and get user confirmation.
    
    Args:
        dry_run_result: Result from dry-run prompt construction
        step_name: Name of the step being executed
        input_metadata: Metadata about input sources
    
    Returns:
        True if user approves, False otherwise
    
    Raises:
        click.ClickException: If user cancels or quits
    """
    # Show the prompt header
    print_header("=== PROMPT (substituted) ===", Color.CYAN)
    
    # Display the full prompt
    try:
        click.echo(dry_run_result.full_prompt)
    except UnicodeEncodeError:
        # Fallback for encoding issues
        try:
            terminal_encoding = sys.stdout.encoding or 'utf-8'
            safe_bytes = dry_run_result.full_prompt.encode(terminal_encoding, errors='replace')
            sys.stdout.buffer.write(safe_bytes)
            sys.stdout.buffer.write(b'\n')
            sys.stdout.flush()
        except Exception:
            click.echo("[Prompt contains characters that cannot be displayed]")
    
    print_header("=== END PROMPT ===", Color.CYAN)
    
    # Show compression info
    _display_compression_info(dry_run_result)
    
    # Show prompt metadata
    print_info(f"\nStep: {step_name} (#{dry_run_result.step_number})")
    print_info(f"Persona: {dry_run_result.persona}")
    print_info(f"Prompt file: {dry_run_result.prompt_file}")
    print_info(f"Total prompt length: {len(dry_run_result.full_prompt)} characters")
    
    # Show input sources
    if input_metadata:
        print_info(f"\nInput sources:")
        for label, meta in input_metadata.items():
            source_type = meta.get("source", "unknown")
            input_type = meta.get("type", "unknown")
            print_info(f"  {label}: {source_type} ({input_type})")
            if "path" in meta:
                print_info(f"    path: {meta['path']}")
    
    # Interactive approval prompt
    while True:
        try:
            click.echo("")  # Blank line for spacing
            response = click.prompt(
                "Continue? (y/n/q/v)",
                default="n",
                show_default=True,
                type=str,
            ).strip().lower()
            
            if response in ('y', 'yes'):
                return True
            elif response in ('n', 'no'):
                print_warning("Execution cancelled by user")
                return False
            elif response in ('q', 'quit'):
                print_warning("Quitting")
                raise click.ClickException("User quit")
            elif response in ('v', 'verbose'):
                # Show verbose details
                print_info("\n" + "=" * 80)
                print_info("VERBOSE DETAILS")
                print_info("=" * 80)
                print_info(f"\nStep configuration:")
                print_info(f"  Step name: {dry_run_result.step_name}")
                print_info(f"  Prompt file: {dry_run_result.prompt_file}")
                print_info(f"  Persona: {dry_run_result.persona}")
                print_info(f"  Step number: {dry_run_result.step_number}")
                
                print_info(f"\nCLI inputs:")
                if dry_run_result.cli_inputs:
                    for label, content in dry_run_result.cli_inputs.items():
                        preview = content[:100] + "..." if len(content) > 100 else content
                        print_info(f"  {label}: {preview}")
                else:
                    print_info("  None")
                
                print_info(f"\nFile inputs:")
                if dry_run_result.exogenous_inputs:
                    for label, path in dry_run_result.exogenous_inputs.items():
                        print_info(f"  {label}: {path}")
                else:
                    print_info("  None")
                
                print_info(f"\nPrevious outputs:")
                if dry_run_result.previous_outputs:
                    for label, path in dry_run_result.previous_outputs.items():
                        print_info(f"  {label}: {path}")
                else:
                    print_info("  None")
                
                print_info("=" * 80)
                continue  # Show prompt again
            else:
                print_warning("Invalid response. Please enter y, n, q, or v")
                
        except KeyboardInterrupt:
            print_warning("\n\nExecution cancelled by user")
            return False
        except click.Abort:
            print_warning("\n\nExecution cancelled by user")
            return False


@click.command()
@click.argument("step_name")
@click.option(
    "--input-file",
    type=str,
    multiple=True,
    help="Input from file (format: label:filename). "
         "Overrides config exogenous_inputs.",
)
@click.option(
    "--input-prompt",
    type=str,
    multiple=True,
    help="Input from interactive prompt (format: label). "
         "Prompts user to enter content.",
)
@click.option(
    "--input-text",
    type=str,
    multiple=True,
    help="Input from command line (format: label:value). "
         "Provide content directly.",
)
@click.option(
    "--output-dir",
    type=click.Path(),
    default="pipeline_output/",
    help="Output directory",
)
@click.option(
    "--output-file",
    type=click.Path(),
    help="Output file path (overrides config file setting)",
)
@click.option(
    "--model-level",
    type=int,
    default=1,
    help="Model quality level (1=fast/cheap, 2=balanced, 3=best)",
)
@click.option(
    "--model",
    type=str,
    help="Specific model name (overrides --model-level)",
)
@click.option(
    "--skip-validation",
    is_flag=True,
    help="Skip output validation",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would happen without executing (displays prompt construction)",
)
@click.option(
    "--dry-run-prompt",
    is_flag=True,
    help="Generate and display the full prompt without making API calls",
)
@click.option(
    "--show-prompt",
    is_flag=True,
    help="Display the prompt sent to LLM (after API call)",
)
@click.option(
    "--show-response",
    is_flag=True,
    help="Display the response from LLM (requires API call)",
)
@click.option(
    "--show-both",
    is_flag=True,
    help="Display both prompt and response (requires API call)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Continue even if inputs are missing (substitute empty strings)",
)
@click.option(
    "--batch",
    is_flag=True,
    help="Run in batch mode (no interactive prompts)",
)
@click.option(
    "--approve",
    is_flag=True,
    help="Show substituted prompt and wait for user confirmation before executing",
)
@click.option(
    "--auto-approve",
    is_flag=True,
    help="Skip approval prompt (useful for CI/CD or batch processing)",
)
@click.option(
    "--info",
    is_flag=True,
    help="Display step information (inputs, outputs, configuration, switches)",
)
@click.option(
    "--info-verbose",
    is_flag=True,
    help="Show detailed explanations with --info",
)
@click.option(
    "--info-json",
    is_flag=True,
    help="Output step info as JSON for programmatic use",
)
@click.option(
    "--info-steps",
    type=str,
    help="Comma-separated list of steps to show info for (with --info)",
)
@click.pass_context
def run_step(
    ctx,
    step_name,
    input_file,
    input_prompt,
    input_text,
    output_dir,
    output_file,
    model_level,
    model,
    skip_validation,
    dry_run,
    dry_run_prompt,
    show_prompt,
    show_response,
    show_both,
    force,
    batch,
    approve,
    auto_approve,
    info,
    info_verbose,
    info_json,
    info_steps,
):
    """Run a single pipeline step.

    STEP_NAME: Name of the step to execute (e.g., step1, stepC3)
    """
    config_path = ctx.obj.get("config", "configuration/pipeline_config.yaml")
    verbosity = ctx.obj.get("verbosity", 1)
    verbose = verbosity > 1

    # Handle --info flag
    if info:
        return handle_info(ctx, step_name, info_verbose, info_json, info_steps)

    # Validate info flags are not used without --info
    if info_verbose or info_json or info_steps:
        raise click.ClickException(
            "--info-verbose, --info-json, and --info-steps can only be used with --info"
        )

    # Check for interactive inputs in batch mode
    if batch and input_prompt:
        raise click.ClickException(
            "Cannot use --input-prompt in batch mode. "
            "Use --input-file or --input-text instead."
        )

    # Initialize components
    # API key will be read from OPENROUTER_API_KEY environment variable
    llm_client = OpenRouterClient(api_key=None)
    prompt_manager = PromptManager(config_path)
    
    # Determine what to show
    show_both = show_both or (show_prompt and show_response)

    executor = StepExecutor(
        llm_client=llm_client,
        prompt_manager=prompt_manager,
        output_dir=Path(output_dir),
        model_level=model_level,
        skip_validation=skip_validation,
        verbose=verbose,
        show_prompt=show_prompt or show_both,
        show_response=show_response or show_both,
        output_file=output_file,
        force=force,
    )

    orchestrator = PipelineOrchestrator(
        config_path=config_path,
        llm_client=llm_client,
        prompt_manager=prompt_manager,
        step_executor=executor,
        output_dir=Path(output_dir),
        verbose=verbose,
    )

    # Get step config to check requirements
    step_config = prompt_manager.get_step_config(step_name)
    if not step_config:
        raise click.ClickException(f"Step '{step_name}' not found in configuration")

    # Collect inputs from CLI
    try:
        cli_inputs, exogenous_inputs, input_metadata = _collect_inputs_from_cli(
            ctx=ctx,
            step_name=step_name,
            config_path=config_path,
            input_file_options=input_file,
            input_prompt_options=input_prompt,
            input_text_options=input_text,
        )
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(f"Failed to parse CLI inputs: {e}")

    # Collect inputs from config
    try:
        cli_inputs, exogenous_inputs = _collect_config_inputs(
            prompt_manager=prompt_manager,
            step_name=step_name,
            cli_inputs=cli_inputs,
            exogenous_inputs=exogenous_inputs,
            output_dir=Path(output_dir),
            force=force,
        )
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(f"Failed to collect config inputs: {e}")

    # Handle approval logic (must be before dry-run to avoid double processing)
    # Skip approval if using --dry-run (dry-run doesn't need approval)
    if (approve or auto_approve) and not dry_run and not dry_run_prompt:
        # Check for conflicting flags
        if auto_approve and approve:
            raise click.ClickException(
                "Cannot use --approve and --auto-approve together. "
                "Use --approve for interactive approval or --auto-approve for CI/CD."
            )
        
        # Build the prompt for approval check
        try:
            approval_dry_run_result = construct_prompt_without_api_call(
                step_name=step_name,
                cli_inputs=cli_inputs,
                exogenous_inputs=exogenous_inputs,
                previous_outputs={},
                prompt_manager=prompt_manager,
                force=force,
            )
        except ValueError as e:
            error_msg = str(e)
            if "Missing required input" in error_msg or "Previous step output" in error_msg:
                # Analyze dependencies
                deps = _analyze_step_dependencies(prompt_manager, step_name, None)
                
                if deps.get("dependency_chain"):
                    error_msg += "\n\n" + "=" * 80 + "\n"
                    error_msg += "DEPENDENCY ANALYSIS\n"
                    error_msg += "=" * 80 + "\n\n"
                    error_msg += f"Step '{step_name}' has dependencies on previous steps.\n"
                    error_msg += "\n"
                    error_msg += "RECOMMENDED COMMAND (run in order):\n"
                    error_msg += "-" * 80 + "\n"
                    
                    # Build the dependency chain command
                    error_msg += "# First, run the dependency chain:\n"
                    for dep_step in deps["dependency_chain"]:
                        error_msg += f"prompt-pipeline run-step {dep_step} --input-file nl_spec:doc/todo_list_nl_spec.md\n"
                    
                    error_msg += "\n" + f"prompt-pipeline run-step {step_name} --input-file nl_spec:doc/todo_list_nl_spec.md" + "\n"
                    error_msg += "\n"
                    error_msg += "Or run all steps at once:\n"
                    error_msg += "prompt-pipeline run-pipeline --input-file nl_spec:doc/todo_list_nl_spec.md\n"
                    error_msg += "=" * 80 + "\n\n"
            
            raise click.ClickException(f"Failed to build prompt for approval: {error_msg}")
        
        # Show approval prompt unless auto-approved
        if approve:
            should_proceed = _show_approval_prompt(
                dry_run_result=approval_dry_run_result,
                step_name=step_name,
                input_metadata=input_metadata,
            )
            if not should_proceed:
                print_warning("Execution cancelled by user")
                return
        
        # If auto_approve, skip the prompt and continue
        # If approve was used and user approved, continue
        # If neither flag is set, continue without approval (current behavior)

    # Handle dry-run modes
    if dry_run or dry_run_prompt:
        try:
            # Construct the prompt without making API calls
            dry_run_result = construct_prompt_without_api_call(
                step_name=step_name,
                cli_inputs=cli_inputs,
                exogenous_inputs=exogenous_inputs,
                previous_outputs={},
                prompt_manager=prompt_manager,
                force=force,
            )
            
            # Show dry-run information
            if dry_run:
                click.echo(f"[DRY RUN] Would execute step: {step_name}")
                click.echo(f"[DRY RUN] Config: {config_path}")
                click.echo(f"[DRY RUN] Step number: {dry_run_result.step_number}")
                click.echo(f"[DRY RUN] Persona: {dry_run_result.persona}")
                click.echo(f"[DRY RUN] Prompt file: {dry_run_result.prompt_file}")
                click.echo(f"[DRY RUN] Total prompt length: {len(dry_run_result.full_prompt)} characters")
                
                # Show approval status
                if approve or auto_approve:
                    click.echo(f"[DRY RUN] Approval skipped (dry-run mode)")
                
                # Show inputs
                if cli_inputs:
                    click.echo(f"[DRY RUN] CLI inputs: {', '.join(cli_inputs.keys())}")
                if exogenous_inputs:
                    click.echo(f"[DRY RUN] File inputs: {', '.join(exogenous_inputs.keys())}")
                
                # Show input metadata
                if input_metadata:
                    click.echo(f"[DRY RUN] Input sources:")
                    for label, meta in input_metadata.items():
                        source_type = meta.get("source", "unknown")
                        input_type = meta.get("type", "unknown")
                        click.echo(f"    {label}: {source_type} ({input_type})")
                        if "path" in meta:
                            click.echo(f"        path: {meta['path']}")
            
            # Show the prompt
            if dry_run_prompt or dry_run:
                print_header("FULL PROMPT (no API call made)", Color.CYAN)
                
                # Show prompt info
                click.echo(f"Step: {step_name} (#{dry_run_result.step_number})")
                click.echo(f"Persona: {dry_run_result.persona}")
                click.echo(f"Prompt file: {dry_run_result.prompt_file}")
                click.echo(f"Total length: {len(dry_run_result.full_prompt)} characters")
                click.echo("")
                
                # Display the full prompt
                # Handle encoding issues gracefully
                try:
                    # Try to print directly
                    click.echo(dry_run_result.full_prompt)
                except UnicodeEncodeError:
                    # Fallback: replace problematic characters with replacement character
                    try:
                        # Get the terminal encoding
                        import sys
                        terminal_encoding = sys.stdout.encoding or 'utf-8'
                        # Encode with replacement character, keeping the bytes
                        safe_bytes = dry_run_result.full_prompt.encode(terminal_encoding, errors='replace')
                        # Write bytes directly to stdout buffer
                        sys.stdout.buffer.write(safe_bytes)
                        sys.stdout.buffer.write(b'\n')
                        sys.stdout.flush()
                    except Exception:
                        # Ultimate fallback: just show a warning
                        click.echo("[Prompt contains characters that cannot be displayed in current terminal encoding]")
                        click.echo("Use --encoding=utf-8 or redirect output to file to view full prompt")
            
            return
            
        except ValueError as e:
            # Add dependency analysis to the error message
            error_msg = str(e)
            if "Missing required input" in error_msg or "Previous step output" in error_msg:
                # Analyze dependencies
                deps = _analyze_step_dependencies(prompt_manager, step_name, None)
                
                if deps.get("dependency_chain"):
                    error_msg += "\n\n" + "=" * 80 + "\n"
                    error_msg += "DEPENDENCY ANALYSIS\n"
                    error_msg += "=" * 80 + "\n\n"
                    error_msg += f"Step '{step_name}' has dependencies on previous steps.\n"
                    error_msg += "\n"
                    error_msg += "RECOMMENDED COMMAND (run in order):\n"
                    error_msg += "-" * 80 + "\n"
                    
                    # Build the dependency chain command
                    error_msg += "# First, run the dependency chain:\n"
                    for dep_step in deps["dependency_chain"]:
                        error_msg += f"prompt-pipeline run-step {dep_step} --input-file nl_spec:doc/todo_list_nl_spec.md\n"
                    
                    error_msg += "\n" + f"prompt-pipeline run-step {step_name} --input-file nl_spec:doc/todo_list_nl_spec.md" + "\n"
                    error_msg += "\n"
                    error_msg += "Or run all steps at once:\n"
                    error_msg += "prompt-pipeline run-pipeline --input-file nl_spec:doc/todo_list_nl_spec.md\n"
                    error_msg += "=" * 80 + "\n\n"
            
            raise click.ClickException(f"Dry-run failed: {error_msg}")

    # Run step
    try:
        output_paths = asyncio.run(
            orchestrator.run_step_with_inputs(
                step_name=step_name,
                cli_inputs=cli_inputs,
                exogenous_inputs=exogenous_inputs,
            )
        )
        
        print_success(f"Step {format_step(step_name)} completed successfully!")
        print_info("Outputs:")
        for label, output_path in output_paths.items():
            print_info(f"  {label}: {output_path}")
    except Exception as e:
        print_error(f"Step {format_step(step_name)} failed!")
        raise click.ClickException(f"Step execution failed: {e}")
