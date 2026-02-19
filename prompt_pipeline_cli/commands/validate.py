"""Validate CLI Command."""

from pathlib import Path

import click

from prompt_pipeline.validation import (
    ConceptsValidator,
    MessagesValidator,
    RequirementsValidator,
    ValidationResult,
    YAMLValidator,
    AggregationsValidator,
)


@click.command()
@click.argument("file", type=click.Path(exists=True))
@click.option(
    "--type",
    "validation_type",
    type=click.Choice(["yaml", "concepts", "aggregations", "messages", "requirements", "auto"]),
    default="auto",
    help="Type of validation to perform",
)
@click.option(
    "--strict",
    is_flag=True,
    help="Fail on warnings as well as errors",
)
@click.pass_context
def validate(ctx, file, validation_type, strict):
    """Validate a pipeline output file.

    FILE: Path to the file to validate.
    """
    file_path = Path(file)

    # Auto-detect type if not specified
    if validation_type == "auto":
        validation_type = _detect_type(file_path)

    if validation_type == "auto":
        raise click.ClickException(
            "Could not auto-detect validation type. Please specify with --type."
        )

    # Get validator
    validator = _get_validator(validation_type)

    # Run validation
    result = validator.validate_file(str(file_path))

    # Report results
    if result.is_valid():
        click.secho("Validation PASSED", fg="green")
        if result.warnings and not strict:
            click.echo("\nWarnings:")
            for warning in result.warnings:
                click.secho(f"  - {warning}", fg="yellow")
    else:
        click.secho("Validation FAILED", fg="red")
        click.echo("\nErrors:")
        for error in result.errors:
            click.secho(f"  - {error}", fg="red")

        if result.warnings:
            click.echo("\nWarnings:")
            for warning in result.warnings:
                click.secho(f"  - {warning}", fg="yellow")

        # Exit with error code
        ctx.exit(1)

    # Strict mode: fail on warnings too
    if strict and result.warnings:
        click.secho("\nStrict mode: Failing on warnings", fg="red")
        ctx.exit(1)


def _detect_type(file_path: Path) -> str:
    """Auto-detect validation type based on filename."""
    name = file_path.name.lower()

    if name.endswith(".yaml") or name.endswith(".yml"):
        return "yaml"
    elif "concepts" in name:
        return "concepts"
    elif "aggregations" in name:
        return "aggregations"
    elif "messages" in name:
        return "messages"
    elif "requirements" in name:
        return "requirements"
    else:
        return "auto"


def _get_validator(validation_type: str):
    """Get validator instance for the specified type."""
    validators = {
        "yaml": YAMLValidator,
        "concepts": ConceptsValidator,
        "aggregations": AggregationsValidator,
        "messages": MessagesValidator,
        "requirements": RequirementsValidator,
    }

    validator_class = validators.get(validation_type)
    if not validator_class:
        raise click.ClickException(f"Unknown validation type: {validation_type}")

    return validator_class()
