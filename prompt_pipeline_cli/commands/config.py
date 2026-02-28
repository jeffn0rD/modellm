"""Config CLI Command."""

import json

import click
import yaml


@click.group()
@click.pass_context
def config(ctx: click.Context) -> None:
    """Manage pipeline configuration."""
    pass


@config.command("show")
@click.option(
    "--format",
    type=click.Choice(["yaml", "json"]),
    default="yaml",
    help="Output format",
)
@click.option(
    "--step",
    help="Show only a specific step",
)
@click.pass_context
def show(ctx: click.Context, format: str, step: str) -> None:
    """Show current configuration."""
    config_path = ctx.parent.params.get("config", "configuration/pipeline_config.yaml")

    try:
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)
    except FileNotFoundError:
        raise click.ClickException(f"Config file not found: {config_path}")
    except yaml.YAMLError as e:
        raise click.ClickException(f"Error parsing config: {e}")

    # Filter by step if specified
    if step:
        if "steps" in config_data and step in config_data["steps"]:
            config_data = {"steps": {step: config_data["steps"][step]}}
        else:
            raise click.ClickException(f"Step '{step}' not found in configuration")

    # Output
    if format == "json":
        click.echo(json.dumps(config_data, indent=2))
    else:
        click.echo(yaml.dump(config_data, default_flow_style=False))


@config.command("list-steps")
@click.pass_context
def list_steps(ctx: click.Context) -> None:
    """List all configured steps."""
    config_path = ctx.parent.params.get("config", "configuration/pipeline_config.yaml")

    try:
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)
    except FileNotFoundError:
        raise click.ClickException(f"Config file not found: {config_path}")

    steps = config_data.get("steps", {})
    if not steps:
        click.echo("No steps configured")
        return

    click.echo("Configured steps:")
    for step_name, step_config in steps.items():
        order = step_config.get("order", "?")
        output = step_config.get("output_file", "N/A")
        click.echo(f"  {order}. {step_name} -> {output}")


@config.command("get")
@click.argument("key")
@click.pass_context
def get(ctx: click.Context, key: str) -> None:
    """Get a configuration value."""
    config_path = ctx.parent.params.get("config", "configuration/pipeline_config.yaml")

    try:
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)
    except FileNotFoundError:
        raise click.ClickException(f"Config file not found: {config_path}")

    # Navigate nested keys
    keys = key.split(".")
    value = config_data
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            raise click.ClickException(f"Key not found: {key}")

    click.echo(yaml.dump(value, default_flow_style=False))
