"""TypeDB Import Integration Module.

This module provides integration with the existing tools/typedb_import.py
for importing pipeline outputs into TypeDB.
"""

import sys
from pathlib import Path
from typing import Optional

# Import from typedb_client3 library (in tools directory)
try:
    from typedb_client3 import TypeDBClient
    from typedb_client3.importer import TypeDBImporter
except ImportError:
    # Fallback if not installed as a package
    import os
    tools_path = Path(__file__).parent.parent / "tools"
    if str(tools_path) not in sys.path:
        sys.path.insert(0, str(tools_path))
    from typedb_client3 import TypeDBClient
    from typedb_client3.importer import TypeDBImporter


class PipelineImporter:
    """Importer for pipeline outputs to TypeDB.

    Integrates with the existing typedb_import.py functionality.
    """

    def __init__(
        self,
        database: str,
        host: str = "localhost",
        port: int = 1729,
        username: str = "admin",
        password: str = "password",
        verbose: int = 1,
    ):
        """Initialize the pipeline importer.

        Args:
            database: TypeDB database name.
            host: TypeDB host.
            port: TypeDB port.
            username: TypeDB username.
            password: TypeDB password.
            verbose: Verbosity level (0=quiet, 1=normal, 2=verbose).
        """
        self.database = database
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.verbose = verbose
        self.base_url = f"http://{host}:{port}"

        # Create client and importer
        self.client = TypeDBClient(
            base_url=self.base_url,
            username=username,
            password=password,
        )
        self.importer = TypeDBImporter(
            base_url=self.base_url,
            database=database,
            username=username,
            password=password,
            verbose=verbose,
            auto_connect=False,
        )

    def database_exists(self) -> bool:
        """Check if database exists.

        Returns:
            True if database exists.
        """
        return self.client.database_exists(self.database)

    def create_database(self) -> bool:
        """Create the database if it doesn't exist.

        Returns:
            True if created or already exists.
        """
        if not self.database_exists():
            self.client.create_database(self.database)
            if self.verbose >= 1:
                print(f"Created database: {self.database}")
            return True
        if self.verbose >= 2:
            print(f"Database already exists: {self.database}")
        return False

    def wipe_database(self, verify: bool = True) -> bool:
        """Wipe all data from the database.

        Args:
            verify: Verify wipe was successful.

        Returns:
            True if wipe successful.
        """
        return self.client.wipe_database(self.database, verify=verify)

    def import_yaml(self, yaml_path: Path, force_update: bool = False) -> None:
        """Import a YAML specification file.

        Args:
            yaml_path: Path to YAML file.
            force_update: Force update of existing entities.
        """
        if not yaml_path.exists():
            raise FileNotFoundError(f"YAML file not found: {yaml_path}")

        if self.verbose >= 1:
            print(f"Importing YAML from: {yaml_path}")

        self.importer.connect()
        self.importer.import_yaml(yaml_path, force_update=force_update)

        if self.verbose >= 1:
            print("YAML import completed")

    def import_json_directory(
        self, json_dir: Path, force_update: bool = False
    ) -> None:
        """Import JSON concept files from a directory.

        Args:
            json_dir: Path to directory containing JSON files.
            force_update: Force update of existing entities.
        """
        if not json_dir.exists():
            raise FileNotFoundError(f"JSON directory not found: {json_dir}")

        if self.verbose >= 1:
            print(f"Importing JSON from: {json_dir}")

        self.importer.connect()
        self.importer.import_json_directory(json_dir, force_update=force_update)

        if self.verbose >= 1:
            print("JSON import completed")

    def import_all(
        self,
        yaml_path: Optional[Path] = None,
        json_dir: Optional[Path] = None,
        wipe: bool = False,
        create: bool = False,
        force_update: bool = False,
    ) -> None:
        """Import all pipeline outputs to TypeDB.

        Args:
            yaml_path: Optional path to YAML specification.
            json_dir: Optional path to JSON directory.
            wipe: Wipe database before import.
            create: Create database if it doesn't exist.
            force_update: Force update of existing entities.
        """
        # Handle database operations
        if wipe:
            if self.verbose >= 1:
                print(f"Wiping database: {self.database}")
            self.wipe_database()

        if create:
            self.create_database()

        # Import YAML
        if yaml_path:
            self.import_yaml(yaml_path, force_update)

        # Import JSON
        if json_dir:
            self.import_json_directory(json_dir, force_update)

        if self.verbose >= 1:
            print(f"Import to database '{self.database}' completed")

    def close(self) -> None:
        """Close connections and cleanup resources."""
        try:
            self.client.close()
        except Exception:
            pass


# Convenience function for CLI
def import_to_typedb(
    input_dir: str,
    database: str,
    wipe: bool = False,
    create: bool = False,
    host: str = "localhost",
    port: int = 1729,
    username: str = "admin",
    password: str = "password",
    verbose: int = 1,
) -> bool:
    """Import pipeline outputs to TypeDB.

    Args:
        input_dir: Directory containing pipeline output files.
        database: TypeDB database name.
        wipe: Wipe database before import.
        create: Create database if it doesn't exist.
        host: TypeDB host.
        port: TypeDB port.
        username: TypeDB username.
        password: TypeDB password.
        verbose: Verbosity level.

    Returns:
        True if import successful.
    """
    input_path = Path(input_dir)

    # Create importer
    importer = PipelineImporter(
        database=database,
        host=host,
        port=port,
        username=username,
        password=password,
        verbose=verbose,
    )

    try:
        # Find files to import
        yaml_path = None
        json_dir = None

        # Look for YAML file
        for yaml_file in input_path.glob("spec*.yaml"):
            yaml_path = yaml_file
            if verbose >= 1:
                print(f"Found YAML: {yaml_file}")
            break

        # Look for JSON directory or files
        json_files = list(input_path.glob("*.json"))
        if json_files:
            json_dir = input_path
            if verbose >= 1:
                print(f"Found JSON files: {[f.name for f in json_files]}")

        if not yaml_path and not json_files:
            print(
                f"No importable files found in {input_dir}",
                file=sys.stderr,
            )
            return False

        # Import
        importer.import_all(
            yaml_path=yaml_path,
            json_dir=json_dir,
            wipe=wipe,
            create=create,
        )

        return True

    except Exception as e:
        print(f"Import failed: {e}", file=sys.stderr)
        return False

    finally:
        importer.close()
