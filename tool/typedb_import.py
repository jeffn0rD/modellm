#!/usr/bin/env python3
"""TypeDB Unified Importer - CLI Tool

A unified CLI tool that imports both YAML specification files and JSON concept files
into TypeDB. Supports database creation, wiping, and comprehensive import modes.

Usage:
    python tool/typedb_import.py --mode yaml --database mydb --yaml-file spec.yaml --create-db
    python tool/typedb_import.py --mode json --database mydb --json-dir ./json
    python tool/typedb_import.py --mode all --database mydb --wipe-db --create-db
    python tool/typedb_import.py --mode wipe --database mydb --check-wipe
"""

import argparse
import sys
import uuid
from pathlib import Path
from typing import Optional

# Import from typedb_v3_client library
from tools.typedb_v3_client import TypeDBClient, TransactionType
from tools.typedb_v3_client.importer import TypeDBImporter


# ANSI color codes for terminal output
class Colors:
    RESET = '\033[0m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    DIM = '\033[2m'


class VerboseLevel:
    """Verbosity levels."""
    ERROR = 0      # Only errors
    NORMAL = 1     # Summary (default)
    VERBOSE = 2    # Detailed progress
    DEBUG = 3      # All debug info


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description='TypeDB Unified Importer - Import YAML/JSON into TypeDB',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import YAML specification only
  python tool/typedb_import.py --mode yaml --database specs --yaml-file doc/spec.yaml --create-db

  # Import JSON concepts only
  python tool/typedb_import.py --mode json --database specs --json-dir json

  # Full pipeline: wipe, create, import YAML and JSON
  python tool/typedb_import.py --mode all --database specs --yaml-file doc/spec.yaml --json-dir json --wipe-db --create-db

  # Wipe database and verify
  python tool/typedb_import.py --mode wipe --database specs --check-wipe

  # Quiet mode (errors only)
  python tool/typedb_import.py --mode yaml --database specs --yaml-file spec.yaml --verbose 0
        """
    )
    
    # Add custom action for argument validation
    class ValidateModeAction(argparse.Action):
        """Custom action to validate mode-specific arguments."""
        def __call__(self, parser, namespace, values, option_string=None):
            # Validation will happen in main(), just set the value
            setattr(namespace, self.dest, values)
    
    # Required arguments
    parser.add_argument(
        '--mode',
        type=str,
        choices=['yaml', 'json', 'all', 'wipe'],
        required=True,
        help='Import mode: yaml (specifications), json (concepts), all (both), or wipe (clear database)'
    )
    
    parser.add_argument(
        '--database',
        type=str,
        required=True,
        help='TypeDB database name'
    )
    
    # Database operations
    parser.add_argument(
        '--create-db',
        action='store_true',
        help='Create database if it does not exist'
    )
    
    parser.add_argument(
        '--wipe-db',
        action='store_true',
        help='Wipe database before import (DANGEROUS - deletes all data!)'
    )
    
    parser.add_argument(
        '--check-wipe',
        action='store_true',
        help='Verify database is completely wiped (test mode)'
    )
    
    # Connection options
    parser.add_argument(
        '--base-url',
        type=str,
        default='http://localhost:8000',
        help='TypeDB server URL (default: http://localhost:8000)'
    )
    
    parser.add_argument(
        '--username',
        type=str,
        default='admin',
        help='TypeDB username (default: admin)'
    )
    
    parser.add_argument(
        '--password',
        type=str,
        default='password',
        help='TypeDB password (default: password)'
    )
    
    # File options
    parser.add_argument(
        '--yaml-file',
        type=Path,
        help='Path to YAML specification file (for yaml or all mode)'
    )
    
    parser.add_argument(
        '--json-dir',
        type=Path,
        help='Directory containing JSON concept files (for json or all mode)'
    )
    
    parser.add_argument(
        '--all-concepts',
        action='store_true',
        help='Import all concept JSON files from default location (./json)'
    )
    
    # Import options
    parser.add_argument(
        '--force-update',
        action='store_true',
        help='Force update of existing entities'
    )
    
    # Output options
    parser.add_argument(
        '--verbose',
        type=int,
        default=1,
        choices=[0, 1, 2, 3],
        help='Verbosity level: 0 (error), 1 (normal), 2 (verbose), 3 (debug)'
    )
    
    parser.add_argument(
        '--stats-only',
        action='store_true',
        help='Only print statistics, do not perform actual import'
    )
    
    return parser


class UnifiedTypeDBImporter:
    """Unified importer for both YAML and JSON files into TypeDB.
    
    This class provides a unified interface for importing both YAML specification
    files and JSON concept files into a TypeDB database. It handles database
    creation, wiping, and verification.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        database: str = "specifications",
        username: str = "admin",
        password: str = "password",
        verbose: int = VerboseLevel.NORMAL
    ):
        """Initialize the unified importer.
        
        Args:
            base_url: TypeDB server URL
            database: Database name
            username: TypeDB username
            password: TypeDB password
            verbose: Verbosity level
        """
        self.base_url = base_url
        self.database = database
        self.username = username
        self.password = password
        self.verbose = verbose
        
        # Create the TypeDB client
        self.client = TypeDBClient(
            base_url=base_url,
            username=username,
            password=password
        )
        
        # Create the importer (without auto-connect)
        self.importer = TypeDBImporter(
            base_url=base_url,
            database=database,
            username=username,
            password=password,
            verbose=verbose,
            auto_connect=False
        )
    
    def log(self, level: str, message: str) -> None:
        """Log a message based on verbosity level."""
        if level == "error":
            print(f"{Colors.RED}ERROR:{Colors.RESET} {message}", file=sys.stderr)
        elif level == "warning":
            if self.verbose >= VerboseLevel.NORMAL:
                print(f"{Colors.YELLOW}WARNING:{Colors.RESET} {message}")
        elif level == "success":
            if self.verbose >= VerboseLevel.NORMAL:
                print(f"{Colors.GREEN}SUCCESS:{Colors.RESET} {message}")
        elif level == "info":
            if self.verbose >= VerboseLevel.VERBOSE:
                print(f"{Colors.BLUE}INFO:{Colors.RESET} {message}")
        elif level == "debug":
            if self.verbose >= VerboseLevel.DEBUG:
                print(f"{Colors.DIM}DEBUG:{Colors.RESET} {message}")
    
    def section(self, title: str) -> None:
        """Print a section header."""
        if self.verbose >= VerboseLevel.VERBOSE:
            print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*50}{Colors.RESET}")
            print(f"{Colors.CYAN}{Colors.BOLD}{title}{Colors.RESET}")
            print(f"{Colors.CYAN}{Colors.BOLD}{'='*50}{Colors.RESET}")
    
    def connect(self) -> None:
        """Connect to TypeDB and ensure database exists."""
        self.section("Connecting to TypeDB")
        
        try:
            if self.client.database_exists(self.database):
                self.log("info", f"Database '{self.database}' already exists")
            else:
                self.log("info", f"Database '{self.database}' does not exist")
                self.log("warning", "Use --create-db to create the database")
                
        except Exception as e:
            self.log("error", f"Error connecting to TypeDB: {e}")
            sys.exit(1)
    
    def create_database(self) -> bool:
        """Create the database if it doesn't exist.
        
        Returns:
            bool: True if database was created or already exists
        """
        self.section("Database Creation")
        
        try:
            if self.client.database_exists(self.database):
                self.log("info", f"Database '{self.database}' already exists")
                return True
            
            self.client.create_database(self.database)
            self.log("success", f"Created database: {self.database}")
            return True
            
        except Exception as e:
            self.log("error", f"Failed to create database: {e}")
            return False
    
    def wipe_database(self, verify: bool = True) -> bool:
        """Wipe all data from the database.
        
        Args:
            verify: Whether to verify the wipe was successful
            
        Returns:
            bool: True if wipe was successful
        """
        self.section("Database Wipe")
        
        if not self.client.database_exists(self.database):
            self.log("error", f"Database '{self.database}' does not exist")
            return False
        
        self.log("warning", f"Wiping all data from database '{self.database}'...")
        
        try:
            result = self.client.wipe_database(self.database, verify=verify)
            if result:
                self.log("success", "Database wiped successfully")
            return result
            
        except Exception as e:
            self.log("error", f"Failed to wipe database: {e}")
            return False
    
    def verify_wipe(self) -> bool:
        """Verify that the database is completely wiped.
        
        Returns:
            bool: True if database is empty
        """
        self.section("Wipe Verification")
        
        if not self.client.database_exists(self.database):
            self.log("error", f"Database '{self.database}' does not exist")
            return False
        
        try:
            result = self.client._verify_wipe(self.database)
            self.log("success", "Database wipe verified - database is clean")
            return result
            
        except Exception as e:
            self.log("error", f"Wipe verification failed: {e}")
            return False
    
    def import_yaml(self, yaml_path: Path, force_update: bool = False) -> None:
        """Import a YAML specification file.
        
        Args:
            yaml_path: Path to YAML file
            force_update: Force update of existing entities
        """
        self.section("YAML Import")
        
        if not yaml_path.exists():
            self.log("error", f"YAML file not found: {yaml_path}")
            sys.exit(1)
        
        self.log("info", f"Importing YAML from: {yaml_path}")
        
        # Connect importer
        self.importer.connect()
        
        # Import YAML
        self.importer.import_yaml(yaml_path, force_update=force_update)
        
        self.log("success", "YAML import completed")
    
    def import_json(self, json_dir: Path, force_update: bool = False) -> None:
        """Import JSON concept files from a directory.
        
        Args:
            json_dir: Path to directory containing JSON files
            force_update: Force update of existing entities
        """
        self.section("JSON Import")
        
        if not json_dir.exists():
            self.log("error", f"JSON directory not found: {json_dir}")
            sys.exit(1)
        
        self.log("info", f"Importing JSON concepts from: {json_dir}")
        
        # Connect importer
        self.importer.connect()
        
        # Import JSON directory
        self.importer.import_json_directory(json_dir, force_update=force_update)
        
        self.log("success", "JSON import completed")
    
    def close(self) -> None:
        """Close connections and cleanup resources."""
        try:
            self.client.close()
        except Exception:
            pass


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Validate arguments based on mode
    if args.mode in ('yaml', 'all') and not args.yaml_file and not args.stats_only:
        parser.error("--yaml-file is required for yaml or all mode")
    
    if args.mode in ('json', 'all') and not args.json_dir and not args.all_concepts and not args.stats_only:
        parser.error("--json-dir or --all-concepts is required for json or all mode")
    
    if args.wipe_db and not args.create_db:
        # This is fine, just a warning
        pass
    
    # Create the unified importer
    importer = UnifiedTypeDBImporter(
        base_url=args.base_url,
        database=args.database,
        username=args.username,
        password=args.password,
        verbose=args.verbose
    )
    
    try:
        # Handle wipe mode first
        if args.mode == 'wipe':
            if args.wipe_db:
                success = importer.wipe_database(verify=args.check_wipe)
                if not success:
                    sys.exit(1)
            elif args.check_wipe:
                success = importer.verify_wipe()
                if not success:
                    sys.exit(1)
            else:
                importer.log("warning", "No action specified for wipe mode. Use --wipe-db or --check-wipe")
            return
        
        # Handle stats-only mode
        if args.stats_only:
            importer.section("Statistics")
            importer.log("info", f"Database: {args.database}")
            importer.log("info", f"Mode: {args.mode}")
            if args.yaml_file:
                importer.log("info", f"YAML file: {args.yaml_file}")
            if args.json_dir:
                importer.log("info", f"JSON directory: {args.json_dir}")
            elif args.all_concepts:
                importer.log("info", "JSON directory: ./json (default)")
            return
        
        # Create database if requested
        if args.create_db:
            success = importer.create_database()
            if not success:
                sys.exit(1)
        
        # Wipe database if requested (before import)
        if args.wipe_db:
            success = importer.wipe_database(verify=False)  # Don't verify before import
            if not success:
                sys.exit(1)
        
        # Import based on mode
        if args.mode == 'yaml':
            importer.import_yaml(args.yaml_file, force_update=args.force_update)
            
        elif args.mode == 'json':
            json_dir = args.json_dir if args.json_dir else Path('./json')
            importer.import_json(json_dir, force_update=args.force_update)
            
        elif args.mode == 'all':
            # Import YAML first
            if args.yaml_file:
                importer.import_yaml(args.yaml_file, force_update=args.force_update)
            
            # Then import JSON
            if args.json_dir:
                importer.import_json(args.json_dir, force_update=args.force_update)
            elif args.all_concepts:
                importer.import_json(Path('./json'), force_update=args.force_update)
        
        # Final verification if requested
        if args.wipe_db and args.check_wipe:
            importer.verify_wipe()
        
        importer.log("success", f"Operation completed successfully")
        
    except KeyboardInterrupt:
        importer.log("warning", "Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        importer.log("error", f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        importer.close()


if __name__ == '__main__':
    main()
