"""Run Pipeline CLI Command."""

import asyncio
from pathlib import Path

import click

from prompt_pipeline.llm_client import OpenRouterClient
from prompt_pipeline.orchestrator import PipelineOrchestrator
from prompt_pipeline.prompt_manager import PromptManager
from prompt_pipeline.step_executor import StepExecutor


@click.command()
@click.argument("nl_spec_file", type=click.Path(exists=True))
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
@click.pass_context
def run_pipeline(
    ctx,
    nl_spec_file,
    output_dir,
    model_level,
    skip_validation,
    import_database,
    wipe_database,
    create_database,
    dry_run,
):
    """Run the full pipeline from NL specification.

    NL_SPEC_FILE: Path to the natural language specification file.
    """
    config_path = ctx.obj.get("config", "configuration/pipeline_config.yaml")
    verbosity = ctx.obj.get("verbosity", 1)
    verbose = verbosity > 1

    if dry_run:
        click.echo(f"[DRY RUN] Would run full pipeline")
        click.echo(f"[DRY RUN] NL Spec: {nl_spec_file}")
        click.echo(f"[DRY RUN] Config: {config_path}")
        click.echo(f"[DRY RUN] Output dir: {output_dir}")
        click.echo(f"[DRY RUN] Model level: {model_level}")
        click.echo(f"[DRY RUN] Import database: {import_database}")
        click.echo(f"[DRY RUN] Wipe database: {wipe_database}")
        return

    # Initialize components
    api_key = "dummy"  # Will be overridden by client

    llm_client = OpenRouterClient(api_key=api_key)
    prompt_manager = PromptManager(config_path)
    executor = StepExecutor(
        llm_client=llm_client,
        prompt_manager=prompt_manager,
        output_dir=output_dir,
        model_level=model_level,
        skip_validation=skip_validation,
        verbose=verbose,
    )

    orchestrator = PipelineOrchestrator(
        config_path=config_path,
        llm_client=llm_client,
        prompt_manager=prompt_manager,
        step_executor=executor,
        output_dir=output_dir,
        import_database=import_database,
        wipe_database=wipe_database,
        verbose=verbose,
    )

    # Show step order
    step_order = orchestrator.get_step_order()
    click.echo(f"Pipeline steps: {' -> '.join(step_order)}")

    # Run pipeline
    try:
        outputs = asyncio.run(orchestrator.run_pipeline(Path(nl_spec_file)))
        click.echo("\nPipeline completed successfully!")
        click.echo("\nOutputs:")
        for step_name, output_path in outputs.items():
            click.echo(f"  {step_name}: {output_path}")

        if import_database:
            click.echo(f"\nImport to TypeDB database '{import_database}' complete!")

    except Exception as e:
        raise click.ClickException(f"Pipeline execution failed: {e}")
