"""Import CLI Command for TypeDB import."""

import os
from pathlib import Path

import click

from prompt_pipeline.typedb_integration import import_to_typedb


@click.command()
@click.argument("input_dir", type=click.Path(exists=True))
@click.option(
    "--database",
    "-d",
    required=True,
    help="TypeDB database name",
)
@click.option(
    "--wipe",
    is_flag=True,
    help="Wipe database before import",
)
@click.option(
    "--create",
    is_flag=True,
    help="Create database if it doesn't exist",
)
@click.option(
    "--host",
    default=os.environ.get("TYPEDB_HOST", "localhost"),
    help="TypeDB host (default: TYPEDB_HOST or localhost)",
)
@click.option(
    "--port",
    default=int(os.environ.get("TYPEDB_PORT", "1729")),
    help="TypeDB port (default: TYPEDB_PORT or 1729)",
)
@click.option(
    "--username",
    default=os.environ.get("TYPEDB_USERNAME", "admin"),
    help="TypeDB username (default: TYPEDB_USERNAME or admin)",
)
@click.option(
    "--password",
    default=os.environ.get("TYPEDB_PASSWORD", "password"),
    help="TypeDB password (default: TYPEDB_PASSWORD or password)",
)
@click.option(
    "--schema",
    type=click.Path(exists=True),
    help="Schema file to import (optional)",
)
@click.pass_context
def import_data(
    ctx,
    input_dir,
    database,
    wipe,
    create,
    host,
    port,
    username,
    password,
    schema,
):
    """Import pipeline outputs to TypeDB.

    INPUT_DIR: Directory containing pipeline output files.
    """
    input_path = Path(input_dir)
    verbosity = ctx.obj.get("verbosity", 1)

    click.echo(f"Importing to TypeDB database: {database}")
    click.echo(f"Host: {host}:{port}")
    click.echo(f"Input directory: {input_path}")

    # Find files to import
    files_to_import = []
    for filename in ["concepts.json", "aggregations.json", "messages.json", "requirements.json"]:
        file_path = input_path / filename
        if file_path.exists():
            files_to_import.append(filename)
            click.echo(f"  Found: {filename}")

    if not files_to_import:
        raise click.ClickException(
            f"No importable files found in {input_dir}. "
            "Expected: concepts.json, aggregations.json, messages.json, requirements.json"
        )

    # Run import
    try:
        success = import_to_typedb(
            input_dir=str(input_path),
            database=database,
            wipe=wipe,
            create=create,
            host=host,
            port=port,
            username=username,
            password=password,
            verbose=verbosity,
        )

        if success:
            click.secho("\nImport completed successfully!", fg="green")
        else:
            click.secho("\nImport failed!", fg="red")
            ctx.exit(1)

    except Exception as e:
        raise click.ClickException(f"Import error: {e}")
