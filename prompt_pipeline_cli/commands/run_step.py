"""Run Step CLI Command."""

import asyncio
import json
from pathlib import Path

import click

from prompt_pipeline.llm_client import OpenRouterClient
from prompt_pipeline.orchestrator import PipelineOrchestrator
from prompt_pipeline.prompt_manager import PromptManager
from prompt_pipeline.step_executor import StepExecutor
from prompt_pipeline.step_executor_dry_run import construct_prompt_without_api_call
from prompt_pipeline.terminal_utils import (
    print_success,
    print_warning,
    print_error,
    print_info,
    print_header,
    format_step,
    Color,
)


@click.command()
@click.argument("step_name")
@click.option(
    "--nl-spec",
    type=click.Path(exists=True),
    help="NL specification file",
)
@click.option(
    "--spec-file",
    type=click.Path(exists=True),
    help="Specification file",
)
@click.option(
    "--concepts-file",
    type=click.Path(exists=True),
    help="Path to concepts.json",
)
@click.option(
    "--aggregations-file",
    type=click.Path(exists=True),
    help="Path to aggregations.json",
)
@click.option(
    "--messages-file",
    type=click.Path(exists=True),
    help="Path to messages.json",
)
@click.option(
    "--requirements-file",
    type=click.Path(exists=True),
    help="Path to requirements.json",
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
@click.pass_context
def run_step(
    ctx,
    step_name,
    nl_spec,
    spec_file,
    concepts_file,
    aggregations_file,
    messages_file,
    requirements_file,
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
):
    """Run a single pipeline step.

    STEP_NAME: Name of the step to execute (e.g., step1, stepC3)
    """
    config_path = ctx.obj.get("config", "configuration/pipeline_config.yaml")
    verbosity = ctx.obj.get("verbosity", 1)
    verbose = verbosity > 1

    # Handle dry-run modes
    if dry_run or dry_run_prompt:
        # Initialize prompt manager
        prompt_manager = PromptManager(config_path)
        
        # Get step config to check requirements
        step_config = prompt_manager.get_step_config(step_name)
        if not step_config:
            raise click.ClickException(f"Step '{step_name}' not found in configuration")
        
        # Build inputs dict
        inputs = {}
        if nl_spec:
            inputs["nl_spec"] = nl_spec
        if spec_file:
            inputs["spec_file"] = spec_file
        if concepts_file:
            inputs["concepts_file"] = concepts_file
        if aggregations_file:
            inputs["aggregations_file"] = aggregations_file
        if messages_file:
            inputs["messages_file"] = messages_file
        if requirements_file:
            inputs["requirements_file"] = requirements_file
        
        # Check required inputs
        required_inputs = prompt_manager.get_required_inputs(step_name)
        for req in required_inputs:
            if req not in inputs:
                # Try to discover from output directory
                if req == "concepts_file":
                    check_file = Path(output_dir) / "concepts.json"
                elif req == "aggregations_file":
                    check_file = Path(output_dir) / "aggregations.json"
                elif req == "messages_file":
                    check_file = Path(output_dir) / "messages.json"
                elif req == "requirements_file":
                    check_file = Path(output_dir) / "requirements.json"
                elif req == "spec_file":
                    check_file = Path(output_dir) / "spec_1.yaml"
                elif req == "nl_spec":
                    continue  # Skip - user must provide
                else:
                    check_file = None
                
                if check_file and check_file.exists():
                    inputs[req] = check_file
                else:
                    raise click.ClickException(
                        f"Missing required input '{req}' for step '{step_name}'. "
                        f"Please provide --{req.replace('_', '-')} option."
                    )
        
        # Convert inputs to the new format
        cli_inputs = {}
        exogenous_inputs = {}
        
        # Map old flag names to new label names
        flag_to_label = {
            "spec_file": "spec",
            "nl_spec": "nl_spec",
            "concepts_file": "concepts",
            "aggregations_file": "aggregations",
            "messages_file": "messages",
            "requirements_file": "requirements",
        }
        
        for flag_name, file_path in inputs.items():
            # Map old flag name to new label name
            label = flag_to_label.get(flag_name, flag_name)
            
            # Check if this input expects source:cli or source:file
            input_configs = step_config.get("inputs", [])
            input_config = next((ic for ic in input_configs if ic.get("label") == label), None)
            if input_config and input_config.get("source") == "cli":
                # Read file content for CLI source
                try:
                    content = Path(file_path).read_text(encoding="utf-8")
                    cli_inputs[label] = content
                except Exception as e:
                    raise click.ClickException(f"Failed to read input file {file_path}: {e}")
                continue
            
            # Default: treat as exogenous input (file path)
            exogenous_inputs[label] = Path(file_path)
        
        # Construct the prompt without making API calls
        try:
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
                
                # Show inputs
                if cli_inputs:
                    click.echo(f"[DRY RUN] CLI inputs: {', '.join(cli_inputs.keys())}")
                if exogenous_inputs:
                    click.echo(f"[DRY RUN] File inputs: {', '.join(exogenous_inputs.keys())}")
            
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
            raise click.ClickException(f"Dry-run failed: {e}")

    # Initialize components
    # API key will be read from OPENROUTER_API_KEY environment variable
    llm_client = OpenRouterClient(api_key=None)
    prompt_manager = PromptManager(config_path)
    
    # Determine what to show
    show_both = show_both or (show_prompt and show_response)
    
    executor = StepExecutor(
        llm_client=llm_client,
        prompt_manager=prompt_manager,
        output_dir=output_dir,
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
        output_dir=output_dir,
        verbose=verbose,
    )

    # Get step config to check requirements
    step_config = prompt_manager.get_step_config(step_name)
    if not step_config:
        raise click.ClickException(f"Step '{step_name}' not found in configuration")

    # Build inputs dict
    inputs = {}
    if nl_spec:
        inputs["nl_spec"] = nl_spec
    if spec_file:
        inputs["spec_file"] = spec_file
    if concepts_file:
        inputs["concepts_file"] = concepts_file
    if aggregations_file:
        inputs["aggregations_file"] = aggregations_file
    if messages_file:
        inputs["messages_file"] = messages_file
    if requirements_file:
        inputs["requirements_file"] = requirements_file

    # Check required inputs
    required_inputs = prompt_manager.get_required_inputs(step_name)
    for req in required_inputs:
        if req not in inputs:
            # Try to discover from output directory
            if req == "concepts_file":
                check_file = Path(output_dir) / "concepts.json"
            elif req == "aggregations_file":
                check_file = Path(output_dir) / "aggregations.json"
            elif req == "messages_file":
                check_file = Path(output_dir) / "messages.json"
            elif req == "requirements_file":
                check_file = Path(output_dir) / "requirements.json"
            elif req == "spec_file":
                check_file = Path(output_dir) / "spec_1.yaml"
            elif req == "nl_spec":
                continue  # Skip - user must provide
            else:
                check_file = None

            if check_file and check_file.exists():
                inputs[req] = check_file
            else:
                raise click.ClickException(
                    f"Missing required input '{req}' for step '{step_name}'. "
                    f"Please provide --{req.replace('_', '-')} option."
                )

    # Run step
    try:
        # Convert inputs to the new format
        # For inputs with source:cli, read file content and pass as CLI input text
        # For inputs with source:file or label:*, pass as exogenous inputs
        cli_inputs = {}
        exogenous_inputs = {}
        
        # Map old flag names to new label names
        flag_to_label = {
            "spec_file": "spec",
            "nl_spec": "nl_spec",
            "concepts_file": "concepts",
            "aggregations_file": "aggregations",
            "messages_file": "messages",
            "requirements_file": "requirements",
        }
        
        for flag_name, file_path in inputs.items():
            # Map old flag name to new label name
            label = flag_to_label.get(flag_name, flag_name)
            
            # Check if this input expects source:cli or source:file
            step_config = prompt_manager.get_step_config(step_name)
            if step_config:
                input_configs = step_config.get("inputs", [])
                input_config = next((ic for ic in input_configs if ic.get("label") == label), None)
                if input_config and input_config.get("source") == "cli":
                    # Read file content for CLI source
                    try:
                        content = Path(file_path).read_text(encoding="utf-8")
                        cli_inputs[label] = content
                    except Exception as e:
                        raise click.ClickException(f"Failed to read input file {file_path}: {e}")
                    continue
            
            # Default: treat as exogenous input (file path)
            exogenous_inputs[label] = Path(file_path)
        
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
