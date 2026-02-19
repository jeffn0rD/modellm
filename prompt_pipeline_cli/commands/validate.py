"""Validate CLI Command."""

from pathlib import Path
from typing import Optional

import click
import yaml

from prompt_pipeline.validation import (
    ConceptsValidator,
    MessagesValidator,
    RequirementsValidator,
    ValidationResult,
    YAMLValidator,
    AggregationsValidator,
)


# Default schemas directory
SCHEMAS_DIR = Path("schemas")
# Default pipeline config path
DEFAULT_CONFIG_PATH = Path("configuration/pipeline_config.yaml")


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
    "--schema",
    "schema_path",
    type=click.Path(exists=True),
    default=None,
    help="Path to JSON schema file for validation",
)
@click.option(
    "--strict",
    is_flag=True,
    help="Fail on warnings as well as errors",
)
@click.pass_context
def validate(ctx, file, validation_type, schema_path, strict):
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

    # Resolve schema path with fallback chain:
    # 1. Explicit --schema option
    # 2. Look up from pipeline_config.yaml based on output file
    # 3. Fallback to schemas/{filename}.schema.json
    resolved_schema_path = schema_path
    if not resolved_schema_path:
        resolved_schema_path = _find_schema_from_config(file_path)
    if not resolved_schema_path:
        resolved_schema_path = _find_schema_fallback(file_path)

    if resolved_schema_path:
        click.echo(f"Using schema: {resolved_schema_path}")

    # Get validator with schema path
    validator = _get_validator(validation_type, resolved_schema_path)

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


def _get_validator(validation_type: str, schema_path: str = None):
    """Get validator instance for the specified type.

    Args:
        validation_type: The type of validation (concepts, aggregations, etc.)
        schema_path: Optional path to JSON schema file.

    Returns:
        Validator instance.
    """
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

    return validator_class(schema_path)


def _find_schema_from_config(file_path: Path) -> Optional[str]:
    """Find schema path from pipeline_config.yaml based on output file.

    Looks up the configuration file to find which step produces this output
    file, then retrieves the associated json_schema.

    For steps with multiple output files (like stepC5), checks each output
    file against the provided file to find the matching schema.

    Args:
        file_path: Path to the file being validated.

    Returns:
        Path to schema file if found, None otherwise.
    """
    config_path = DEFAULT_CONFIG_PATH
    if not config_path.exists():
        return None

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            # Handle multi-document YAML files (with --- separators)
            docs = list(yaml.safe_load_all(f))
            config = docs[0] if docs else None
    except Exception:
        return None

    if not config or "steps" not in config:
        return None

    filename = file_path.name
    steps = config.get("steps", {})

    # Search through all steps for matching output file
    for step_name, step_config in steps.items():
        # Check single output_file
        output_file = step_config.get("output_file")
        if output_file and output_file == filename:
            schema = step_config.get("json_schema")
            if schema:
                return str(Path(schema))

        # Check output_files (list for steps with multiple outputs)
        output_files = step_config.get("output_files", [])
        if output_files and isinstance(output_files, list):
            # Check if file matches one of the output files
            if filename in output_files:
                # Check for per-output schema first
                output_schemas = step_config.get("json_schemas", {})
                if isinstance(output_schemas, dict) and filename in output_schemas:
                    schema = output_schemas.get(filename)
                    if schema:
                        return str(Path(schema))
                # Fall back to single json_schema if present
                schema = step_config.get("json_schema")
                if schema:
                    return str(Path(schema))

    return None


def _find_schema_fallback(file_path: Path) -> Optional[str]:
    """Find schema using fallback naming convention.

    Looks for schema file using the pattern: schemas/{stem}.schema.json
    where stem is the filename without extension.

    Examples:
        concepts.json -> schemas/concepts.schema.json
        messageAggregations.json -> schemas/messageAggregations.schema.json

    Args:
        file_path: Path to the file being validated.

    Returns:
        Path to schema file if found, None otherwise.
    """
    if not SCHEMAS_DIR.exists():
        return None

    # Get stem (filename without extension)
    stem = file_path.stem
    # Handle plural/singular variations
    # Try both singular and plural forms
    possible_names = [
        f"{stem}.schema.json",
    ]

    # Add singular/plural variations
    if stem.endswith("s"):
        possible_names.append(f"{stem[:-1]}.schema.json")
    else:
        possible_names.append(f"{stem}s.schema.json")

    for name in possible_names:
        schema_path = SCHEMAS_DIR / name
        if schema_path.exists():
            return str(schema_path)

    return None
