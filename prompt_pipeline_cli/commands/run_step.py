"""Run Step CLI Command."""

import asyncio
from pathlib import Path

import click

from prompt_pipeline.llm_client import OpenRouterClient
from prompt_pipeline.orchestrator import PipelineOrchestrator
from prompt_pipeline.prompt_manager import PromptManager
from prompt_pipeline.step_executor import StepExecutor
from prompt_pipeline.terminal_utils import (
    print_success,
    print_warning,
    print_error,
    print_info,
    format_step,
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
    help="Show what would happen without executing",
)
@click.option(
    "--show-prompt",
    is_flag=True,
    help="Display the prompt sent to LLM",
)
@click.option(
    "--show-response",
    is_flag=True,
    help="Display the response from LLM",
)
@click.option(
    "--show-both",
    is_flag=True,
    help="Display both prompt and response",
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

    if dry_run:
        # Determine the output file path
        step_config = PromptManager(config_path).get_step_config(step_name)
        if step_config:
            # Use provided output file or fall back to config
            if output_file:
                output_path = Path(output_file)
            else:
                config_output_file = step_config.get("output_file", f"{step_name}_output.txt")
                output_path = Path(output_dir) / config_output_file
        else:
            output_path = Path(output_dir) / f"{step_name}_output.txt"
        
        click.echo(f"[DRY RUN] Would execute step: {step_name}")
        click.echo(f"[DRY RUN] Config: {config_path}")
        click.echo(f"[DRY RUN] Output path: {output_path}")
        click.echo(f"[DRY RUN] Model level: {model_level}")
        
        # Show required inputs
        if step_config:
            required_inputs = PromptManager(config_path).get_required_inputs(step_name)
            if required_inputs:
                click.echo(f"[DRY RUN] Required inputs: {', '.join(required_inputs)}")
        
        return

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
        output_path = asyncio.run(orchestrator.run_step(step_name, inputs))
        print_success(f"Step {format_step(step_name)} completed successfully!")
        print_info(f"Output: {output_path}")
    except Exception as e:
        print_error(f"Step {format_step(step_name)} failed!")
        raise click.ClickException(f"Step execution failed: {e}")
