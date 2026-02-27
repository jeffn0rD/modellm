"""Run Pipeline CLI Command - Updated with Generic Input Options."""

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import click

from prompt_pipeline.exceptions import FileOperationError
from prompt_pipeline.file_utils import validate_file_path
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
from prompt_pipeline_cli.input_validation import InputTypeValidator, InputValidationError


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
    
    # Validate the file path for security (prevent path traversal)
    try:
        validated_path = validate_file_path(
            file_path=Path(filename),
            allowed_base_dir=Path.cwd(),
            must_exist=False,
        )
    except FileOperationError as e:
        raise click.ClickException(
            f"Invalid file path '{filename}': {e}"
        )
    
    return label, str(validated_path)


def _collect_inputs_from_cli(
    ctx: click.Context,
    config_path: str,
    input_file_options: List[str],
) -> Tuple[Dict[str, str], Dict[str, Path], Dict[str, Any]]:
    """
    Collect and process all CLI inputs.
    
    Args:
        ctx: Click context
        config_path: Path to configuration file
        input_file_options: List of --input-file values
    
    Returns:
        Tuple of (cli_inputs, exogenous_inputs, input_metadata)
    
    Raises:
        click.ClickException: If input parsing fails
    """
    cli_inputs = {}
    exogenous_inputs = {}
    input_metadata = {}
    
    prompt_manager = PromptManager(config_path)
    
    # Process --input-file options
    for option_value in input_file_options:
        label, filename = _parse_input_file_option(option_value)
        
        # Get expected type from data_entities or default to text
        data_entity = prompt_manager.get_data_entity(label)
        expected_type = data_entity.get('type', 'text') if data_entity else 'text'
        
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
        # Check step configs to see which step expects this label
        exogenous_inputs[label] = Path(filename)
        input_metadata[label] = {
            "source": "file",
            "path": filename,
            "type": expected_type,
        }
    
    return cli_inputs, exogenous_inputs, input_metadata


@click.command()
@click.option(
    "--input-file",
    type=str,
    multiple=True,
    help="Input from file (format: label:filename). "
         "Overrides config exogenous_inputs.",
)
@click.option(
    "--output-dir",
    type=click.Path(),
    default="pipeline_output/",
    help="Output directory",
)
@click.option(
    "--model-level",
    type=int,
    default=1,
    help="Model quality level (1=fast/cheap, 2=balanced, 3=best)",
)
@click.option(
    "--skip-validation",
    is_flag=True,
    help="Skip output validation",
)
@click.option(
    "--import-database",
    type=str,
    help="Import results to TypeDB database",
)
@click.option(
    "--wipe",
    "wipe_database",
    is_flag=True,
    help="Wipe database before import",
)
@click.option(
    "--create",
    "create_database",
    is_flag=True,
    help="Create database if it doesn't exist",
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
@click.option(
    "--nl-spec",
    type=click.Path(exists=True),
    help="Path to NL specification file (backward compatible option)",
)
@click.pass_context
def run_pipeline(
    ctx,
    input_file,
    output_dir,
    model_level,
    skip_validation,
    import_database,
    wipe_database,
    create_database,
    dry_run,
    show_prompt,
    show_response,
    show_both,
    force,
    nl_spec,
):
    """Run the full pipeline from NL specification.

    You can provide NL spec using --nl-spec (legacy) or --input-file nl_spec:filename
    """
    config_path = ctx.obj.get("config", "configuration/pipeline_config.yaml")
    verbosity = ctx.obj.get("verbosity", 1)
    verbose = verbosity > 1

    # Collect inputs from CLI
    try:
        cli_inputs, exogenous_inputs, input_metadata = _collect_inputs_from_cli(
            ctx=ctx,
            config_path=config_path,
            input_file_options=input_file,
        )
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(f"Failed to parse CLI inputs: {e}")

    # Handle --nl-spec for backward compatibility
    if nl_spec:
        if "nl_spec" not in exogenous_inputs:
            exogenous_inputs["nl_spec"] = Path(nl_spec)
            input_metadata["nl_spec"] = {
                "source": "file",
                "path": nl_spec,
                "type": "md",
            }
    
    # Check if nl_spec is provided
    if "nl_spec" not in exogenous_inputs:
        raise click.ClickException(
            "NL specification file is required.\n"
            "Please provide using --nl-spec <path> or --input-file nl_spec:<path>"
        )

    nl_spec_file = exogenous_inputs["nl_spec"]

    if dry_run:
        click.echo(f"[DRY RUN] Would run full pipeline")
        click.echo(f"[DRY RUN] NL Spec: {nl_spec_file}")
        click.echo(f"[DRY RUN] Config: {config_path}")
        click.echo(f"[DRY RUN] Output dir: {output_dir}")
        click.echo(f"[DRY RUN] Model level: {model_level}")
        click.echo(f"[DRY RUN] Import database: {import_database}")
        click.echo(f"[DRY RUN] Wipe database: {wipe_database}")
        
        # Show label-based inputs/outputs
        prompt_manager = PromptManager(config_path)
        for step_name in prompt_manager.get_all_step_names():
            step_config = prompt_manager.get_step_config(step_name)
            if step_config:
                inputs_config = step_config.get("inputs", [])
                outputs_config = step_config.get("outputs", [])
                if inputs_config or outputs_config:
                    click.echo(f"[DRY RUN] Step {step_name}:")
                    if inputs_config:
                        inputs_str = ", ".join([f"{i.get('label', '?')}" for i in inputs_config])
                        click.echo(f"[DRY RUN]   Inputs: {inputs_str}")
                    if outputs_config:
                        outputs_str = ", ".join([f"{o.get('label', '?')}" for o in outputs_config])
                        click.echo(f"[DRY RUN]   Outputs: {outputs_str}")
        
        # Show input metadata
        if input_metadata:
            click.echo(f"[DRY RUN] Input sources:")
            for label, meta in input_metadata.items():
                source_type = meta.get("source", "unknown")
                input_type = meta.get("type", "unknown")
                click.echo(f"    {label}: {source_type} ({input_type})")
                if "path" in meta:
                    click.echo(f"        path: {meta['path']}")
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
        output_dir=Path(output_dir),
        model_level=model_level,
        skip_validation=skip_validation,
        verbose=verbose,
        show_prompt=show_prompt or show_both,
        show_response=show_response or show_both,
        force=force,
    )

    orchestrator = PipelineOrchestrator(
        config_path=config_path,
        llm_client=llm_client,
        prompt_manager=prompt_manager,
        step_executor=executor,
        output_dir=Path(output_dir),
        import_database=import_database,
        wipe_database=wipe_database,
        verbose=verbose,
    )

    # Show step order
    step_order = orchestrator.get_step_order()
    print_info(f"Pipeline steps: {' -> '.join(step_order)}")

    # Run pipeline
    try:
        outputs = asyncio.run(orchestrator.run_pipeline(nl_spec_file))
        print_success("Pipeline completed successfully!")
        print_info("\nOutputs:")
        for step_name, output_path in outputs.items():
            print_info(f"  {format_step(step_name)}: {output_path}")

        if import_database:
            print_success(f"Import to TypeDB database '{import_database}' complete!")

    except Exception as e:
        print_error(f"Pipeline execution failed!")
        raise click.ClickException(f"Pipeline execution failed: {e}")
