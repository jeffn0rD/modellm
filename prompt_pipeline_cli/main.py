"""CLI Main Entry Point for prompt pipeline."""

import click

from prompt_pipeline_cli.commands import (
    run_step,
    run_pipeline,
    validate,
    import_cmd,
    config,
)


@click.group()
@click.option(
    "--config",
    type=click.Path(exists=True),
    default="configuration/pipeline_config.yaml",
    help="Configuration file path",
)
@click.option(
    "--verbosity",
    "-v",
    type=int,
    default=1,
    help="Verbosity level (0=quiet, 1=normal, 2=verbose, 3=debug)",
)
@click.pass_context
def cli(ctx: click.Context, config: str, verbosity: int) -> None:
    """Prompt Pipeline - Transform NL specs to TypeDB.

    A flexible pipeline for transforming natural language specifications
    into structured data for TypeDB knowledge graphs.
    """
    ctx.ensure_object(dict)
    ctx.obj["config"] = config
    ctx.obj["verbosity"] = verbosity


# Register commands
cli.add_command(run_step.run_step)
cli.add_command(run_pipeline.run_pipeline)
cli.add_command(validate.validate)
cli.add_command(import_cmd.import_data)
cli.add_command(config.config)


def main() -> None:
    """Entry point for the CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
