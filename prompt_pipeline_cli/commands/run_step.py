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
):
    """Run a single pipeline step.

    STEP_NAME: Name of the step to execute (e.g., step1, stepC3)
    """
    config_path = ctx.obj.get("config", "configuration/pipeline_config.yaml")
    verbosity = ctx.obj.get("verbosity", 1)
    verbose = verbosity > 1

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
