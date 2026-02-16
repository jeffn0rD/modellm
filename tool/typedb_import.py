#!/usr/bin/env python3
"""TypeDB Specification Importer - Version 2
Adds colors and verbosity switches to the importer.
"""

import argparse
import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml
import requests

# ANSI color codes
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


class Logger:
    """Colored logger with verbosity control."""
    
    def __init__(self, verbose: int = VerboseLevel.NORMAL):
        self.verbose = verbose
    
    def error(self, msg: str):
        """Print error message."""
        print(f"{Colors.RED}ERROR:{Colors.RESET} {msg}", file=sys.stderr)
    
    def warning(self, msg: str):
        """Print warning message."""
        if self.verbose >= VerboseLevel.NORMAL:
            print(f"{Colors.YELLOW}WARNING:{Colors.RESET} {msg}")
    
    def success(self, msg: str):
        """Print success message."""
        if self.verbose >= VerboseLevel.NORMAL:
            print(f"{Colors.GREEN}SUCCESS:{Colors.RESET} {msg}")
    
    def info(self, msg: str):
        """Print info message."""
        if self.verbose >= VerboseLevel.VERBOSE:
            print(f"{Colors.BLUE}INFO:{Colors.RESET} {msg}")
    
    def debug(self, msg: str):
        """Print debug message."""
        if self.verbose >= VerboseLevel.DEBUG:
            print(f"{Colors.DIM}DEBUG:{Colors.RESET} {msg}")
    
    def section(self, title: str):
        """Print section header."""
        if self.verbose >= VerboseLevel.VERBOSE:
            print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*50}{Colors.RESET}")
            print(f"{Colors.CYAN}{Colors.BOLD}{title}{Colors.RESET}")
            print(f"{Colors.CYAN}{Colors.BOLD}{'='*50}{Colors.RESET}")
    
    def subsection(self, title: str):
        """Print subsection header."""
        if self.verbose >= VerboseLevel.VERBOSE:
            print(f"\n{Colors.MAGENTA}{title}{Colors.RESET}")


class TypeDBHTTPClient:
    """HTTP client for TypeDB 3 API."""
    
    def __init__(self, base_url: str = "http://localhost:8000", 
                 username: Optional[str] = None, 
                 password: Optional[str] = None,
                 verbose: int = VerboseLevel.NORMAL):
        """Initialize the HTTP client."""
        self.base_url = base_url.rstrip('/')
        self.token = None
        self.session = requests.Session()
        self.logger = Logger(verbose)
        
        # Authenticate if credentials provided
        if username and password:
            self._authenticate(username, password)
    
    def _authenticate(self, username: str, password: str):
        """Authenticate and get JWT token."""
        url = f"{self.base_url}/v1/signin"
        body = {"username": username, "password": password}
        
        response = requests.post(url, json=body)
        response.raise_for_status()
        
        self.token = response.json()["token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        self.logger.success(f"Authenticated successfully")
    
    def list_databases(self) -> List[str]:
        """List all databases."""
        url = f"{self.base_url}/v1/databases"
        response = self.session.get(url)
        response.raise_for_status()
        
        self.logger.debug(f"GET: {url}")
        databases = response.json().get("databases", [])
        return [db["name"] for db in databases]
    
    def database_exists(self, database: str) -> bool:
        """Check if a database exists."""
        databases = self.list_databases()
        exists = database in databases
        
        if exists:
            self.logger.debug(f"Database '{database}' exists")
        else:
            self.logger.debug(f"Database '{database}' not found")
        
        return exists
    
    def create_database(self, database: str):
        """Create a new database."""
        url = f"{self.base_url}/v1/databases"
        body = {"name": database}
        response = self.session.post(url, json=body)
        
        self.logger.debug(f"POST: {url}")
        response.raise_for_status()
        self.logger.success(f"Created database: {database}")
    
    def delete_database(self, database: str):
        """Delete a database."""
        url = f"{self.base_url}/v1/databases/{database}"
        response = self.session.delete(url)
        
        self.logger.debug(f"DELETE: {url}")
        response.raise_for_status()
        self.logger.success(f"Deleted database: {database}")
    
    def execute_query(self, database: str, query: str, transaction_type: str) -> Optional[Dict]:
        """Execute a query (read or write)."""
        url = f"{self.base_url}/v1/query"
        body = {
            "query": query,
            "commit": True,
            "databaseName": database,
            "transactionType": transaction_type
        }
        
        self.logger.debug(f"Executing {transaction_type} query: {query[:100]}...")
        
        try:
            response = self.session.post(url, json=body)
            
            if response.status_code == 200:
                self.logger.debug("Query succeeded")
                return response.json() if response.text else None
            else:
                self.logger.error(f"HTTP {response.status_code}: {response.text}")
                response.raise_for_status()
                
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP Error: {e}")
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request Error: {e}")
            return None

    def execute_read_query(self, database: str, query: str) -> Optional[Dict]:
        """Execute a read query (match)."""
        return self.execute_query(database, query, "read")

    def execute_write_query(self, database: str, query: str) -> Optional[Dict]:
        """Execute a write query."""
        return self.execute_query(database, query, "write")
    
    def close(self):
        """Close the session."""
        self.session.close()


class TypeDBSpecImporter:
    """Imports specification YAML files into TypeDB."""
    
    def __init__(self, base_url: str = "http://localhost:8000", 
                 database: str = "specifications",
                 username: Optional[str] = None, 
                 password: Optional[str] = None,
                 verbose: int = VerboseLevel.NORMAL):
        """Initialize the importer with TypeDB connection details."""
        self.database = database
        self.verbose = verbose
        self.logger = Logger(verbose)
        self.stats = {
            "documents": 0,
            "sections": 0,
            "text_blocks": 0,
            "concepts": 0,
            "semantic_cues": 0,
            "relations": 0
        }
        
        self.client = TypeDBHTTPClient(base_url, username, password, verbose)
        
    def connect(self):
        """Establish connection to TypeDB and ensure database exists."""
        try:
            if not self.client.database_exists(self.database):
                self.client.create_database(self.database)
            self.logger.success(f"Connected to database: {self.database}")
                
        except Exception as e:
            self.logger.error(f"Error connecting to TypeDB: {e}")
            sys.exit(1)
    
    def close(self):
        """Close the TypeDB connection."""
        self.client.close()
    
    def _print_summary(self):
        """Print import summary."""
        self.logger.section("Import Summary")
        print(f"  {Colors.GREEN}Documents:{Colors.RESET} {self.stats['documents']}")
        print(f"  {Colors.GREEN}Sections:{Colors.RESET} {self.stats['sections']}")
        print(f"  {Colors.GREEN}Text Blocks:{Colors.RESET} {self.stats['text_blocks']}")
        print(f"  {Colors.GREEN}Concepts:{Colors.RESET} {self.stats['concepts']}")
        print(f"  {Colors.GREEN}Semantic Cues:{Colors.RESET} {self.stats['semantic_cues']}")
        print(f"  {Colors.GREEN}Relations:{Colors.RESET} {self.stats['relations']}")
    
    def clear_specification_data(self):
        """Clear all specification-related entities from the database."""
        self.logger.info("Clearing specification data from database...")
        
        # Delete relations first, then entities
        relation_types = ["anchoring", "membership", "outlining"]
        
        for relation_type in relation_types:
            try:
                delete_query = f"match $r isa {relation_type}; delete $r;"
                self.client.execute_write_query(self.database, delete_query)
                self.logger.debug(f"  Deleted {relation_type} relations")
            except Exception as e:
                self.logger.warning(f"Error deleting {relation_type}: {e}")
        
        # Now delete entities
        entity_types = [
            "text-block", "concept", "semantic-cue",
            "spec-section", "spec-document"
        ]
        
        for entity_type in entity_types:
            try:
                delete_query = f"match $x isa {entity_type}; delete $x;"
                self.client.execute_write_query(self.database, delete_query)
                self.logger.debug(f"  Deleted {entity_type} entities")
            except Exception as e:
                self.logger.warning(f"Error deleting {entity_type}: {e}")
        
        self.logger.success("Database cleared")
    
    def entity_exists(self, entity_type: str, key_attr: str, key_value: str) -> bool:
        """Check if an entity with the given key already exists."""
        query = f'match $x isa {entity_type}, has {key_attr} "{key_value}";'
        try:
            result = self.client.execute_read_query(self.database, query)
            if result and isinstance(result, dict):
                answers = result.get("answers", [])
                return len(answers) > 0
            return False
        except Exception as e:
            self.logger.debug(f"Error checking entity existence: {e}")
            return False
    
    def import_spec_file(self, yaml_path: Path, force_update: bool = False):
        """Import a specification YAML file into TypeDB."""
        self.logger.section(f"Importing: {yaml_path.name}")
        
        # Load YAML file
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Loading YAML file: {e}")
            sys.exit(1)
        
        spec = data.get('specification', {})
        spec_doc_id = spec.get('id', 'SPEC1')
        
        if force_update or not self.entity_exists('spec-document', 'spec-doc-id', spec_doc_id):
            self._create_spec_document(yaml_path, spec)
            self.stats['documents'] += 1
            self.logger.info(f"Created spec-document: {spec_doc_id}")
        
        # Process sections recursively
        sections = spec.get('sections', [])
        for section in sections:
            self._process_section(section, spec_doc_id, 'spec-document', force_update)
        
        self._print_summary()
        self.logger.success("Import completed")
    
    def _create_spec_document(self, yaml_path: Path, spec: Dict[str, Any]):
        """Create a spec-document entity."""
        spec_id = spec.get('id', 'SPEC1')
        title = self._escape_string(spec.get('title', ''))
        version = spec.get('version', '0.1')
        description = self._escape_string(spec.get('description', ''))
        
        query = f'''
            insert 
                $folder isa fs-folder,
                  has foldername "{yaml_path.parent}";
                $doc isa spec-document,
                  has spec-doc-id "{spec_id}",
                  has title "{title}",
                  has version "{version}",
                  has status "draft",
                  has description "{description}",
                  has filename "{yaml_path}";
                filesystem(folder: $folder, entry: $doc);
        '''
        self.client.execute_write_query(self.database, query)
    
    def _process_section(self, section: Dict[str, Any], parent_id: str, 
                        parent_type: str, force_update: bool):
        """Process a section and its subsections/text-blocks recursively."""
        section_id = section.get('section_id')
        
        if not section_id:
            self.logger.warning("Section without section_id, skipping")
            return
        
        # Create section entity
        if force_update or not self.entity_exists('spec-section', 'spec-section-id', section_id):
            self._create_spec_section(section)
            self.stats['sections'] += 1
            self.logger.debug(f"Created spec-section: {section_id}")
        
        # Create outlining relation
        if parent_type == 'spec-document':
            relation_query = f'''
                match 
                    $parent isa spec-document, has spec-doc-id "{parent_id}";
                    $child isa spec-section, has spec-section-id "{section_id}";
                insert outlining(section: $parent, subsection: $child);
            '''
        else:
            relation_query = f'''
                match 
                    $parent isa spec-section, has spec-section-id "{parent_id}";
                    $child isa spec-section, has spec-section-id "{section_id}";
                insert outlining(section: $parent, subsection: $child);
            '''
        
        try:
            self.client.execute_write_query(self.database, relation_query)
            self.stats['relations'] += 1
        except Exception:
            pass
        
        # Process text blocks
        text_blocks = section.get('text_blocks', [])
        block_order = 0
        for text_block in text_blocks:
            self._process_text_block(text_block, section_id, block_order, force_update)
            block_order += 1
        
        # Process subsections recursively
        subsections = section.get('sections', [])
        for subsection in subsections:
            self._process_section(subsection, section_id, 'spec-section', force_update)
    
    def _create_spec_section(self, section: Dict[str, Any]):
        """Create a spec-section entity."""
        section_id = section.get('section_id')
        title = self._escape_string(section.get('title', ''))
        label = section.get('label', '')
        order = section.get('order', 0)
        
        query = f'''
            insert $sec isa spec-section,
                has spec-section-id "{section_id}",
                has title "{title}",
                has id-label "{label}",
                has order {order};
        '''
        self.client.execute_write_query(self.database, query)
    
    def _process_text_block(self, text_block: Dict[str, Any], 
                           section_id: str, order: int, force_update: bool):
        """Process a text block with its concepts and semantic cues."""
        anchor_id = text_block.get('anchor_id')
        
        if not anchor_id:
            self.logger.warning("Text block without anchor_id, skipping")
            return
        
        # Create text-block entity
        if force_update or not self.entity_exists('text-block', 'anchor-id', anchor_id):
            self._create_text_block(text_block, order)
            self.stats['text_blocks'] += 1
            self.logger.debug(f"Created text-block: {anchor_id}")
        
        # Create outlining relation
        relation_query = f'''
            match 
                $parent isa spec-section, has spec-section-id "{section_id}";
                $child isa text-block, has anchor-id "{anchor_id}";
            insert outlining(section: $parent, subsection: $child);
        '''
        try:
            self.client.execute_write_query(self.database, relation_query)
            self.stats['relations'] += 1
        except Exception:
            pass
        
        # Process concepts
        concepts = text_block.get('concepts', [])
        for concept in concepts:
            self._process_concept(concept, anchor_id, force_update)
        
        # Process semantic cues
        semantic_cues = text_block.get('semantic_cues', [])
        for cue in semantic_cues:
            self._process_semantic_cue(cue, anchor_id, force_update)
    
    def _create_text_block(self, text_block: Dict[str, Any], order: int):
        """Create a text-block entity."""
        anchor_id = text_block.get('anchor_id')
        label = text_block.get('label', '')
        anchor_type = text_block.get('type', 'goal')
        text = self._escape_string(text_block.get('text', ''))
        
        query = f'''
            insert $tb isa text-block,
                has anchor-id "{anchor_id}",
                has id-label "{label}",
                has anchor-type "{anchor_type}",
                has text "{text}",
                has order {order};
        '''
        self.client.execute_write_query(self.database, query)
    
    def _process_concept(self, concept: Dict[str, Any], 
                        anchor_id: str, force_update: bool):
        """Process a concept and create anchoring relation."""
        concept_id = concept.get('concept_id')
        
        if not concept_id:
            self.logger.warning("Concept without concept_id, skipping")
            return
        
        # Create concept entity
        if force_update or not self.entity_exists('concept', 'concept-id', concept_id):
            self._create_concept(concept)
            self.stats['concepts'] += 1
            self.logger.debug(f"Created concept: {concept_id}")
        
        # Create anchoring relation
        relation_query = f'''
            match 
                $anchor isa text-block, has anchor-id "{anchor_id}";
                $concept isa concept, has concept-id "{concept_id}";
            insert anchoring(anchor: $anchor, concept: $concept);
        '''
        try:
            self.client.execute_write_query(self.database, relation_query)
            self.stats['relations'] += 1
        except Exception:
            pass
    
    def _create_concept(self, concept: Dict[str, Any]):
        """Create a concept entity."""
        concept_id = concept.get('concept_id')
        name = concept.get('name', '')
        description = self._escape_string(concept.get('description', ''))
        
        query = f'''
            insert $c isa concept,
                has concept-id "{concept_id}",
                has id-label "{name}",
                has description "{description}";
        '''
        self.client.execute_write_query(self.database, query)
    
    def _process_semantic_cue(self, cue: str, anchor_id: str, force_update: bool):
        """Process a semantic cue and create membership relation."""
        if not cue:
            return
        
        cue_id = cue.replace('-', '_').replace(' ', '_')
        
        if force_update or not self.entity_exists('semantic-cue', 'identifier', cue_id):
            query = f'''
                insert $sc isa semantic-cue,
                    has identifier "{cue_id}";
            '''
            try:
                self.client.execute_write_query(self.database, query)
                self.stats['semantic_cues'] += 1
                self.logger.debug(f"Created semantic-cue: {cue_id}")
            except Exception as e:
                self.logger.warning(f"Could not create semantic-cue '{cue_id}': {e}")
        
        # Create membership relation
        relation_query = f'''
            match 
                $tb isa text-block, has anchor-id "{anchor_id}";
                $sc isa semantic-cue, has identifier "{cue_id}";
            insert membership(member-of: $tb, member: $sc);
        '''
        try:
            self.client.execute_write_query(self.database, relation_query)
            self.stats['relations'] += 1
        except Exception:
            pass
    
    def _escape_string(self, s: str) -> str:
        """Escape special characters in strings for TypeQL."""
        if not s:
            return ""
        s = s.replace('\\', '\\\\')
        s = s.replace('"', '\\"')
        s = s.replace('\n', ' ')
        s = s.replace('\r', ' ')
        s = ' '.join(s.split())
        return s


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Import YAML specification files into TypeDB 3 (HTTP API)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Verbosity levels:
  -q, --quiet     Error messages only
  -v, --verbose   Detailed progress information
  -vv, --debug    All debug information

Examples:
  %(prog)s --parse-spec-file spec.yaml
  %(prog)s -v --clear --parse-spec-file spec.yaml
  %(prog)s -vv --url http://cloud.typedb.com:8000 \\
      --username admin --password secret --parse-spec-file spec.yaml
        """
    )
    
    parser.add_argument(
        '--parse-spec-file', type=Path,
        help='Path to YAML specification file to import'
    )
    
    parser.add_argument(
        '--clear', action='store_true',
        help='Clear all specification data from database before import'
    )
    
    parser.add_argument(
        '--url', default='http://localhost:8000',
        help='TypeDB server URL (default: http://localhost:8000)'
    )
    
    parser.add_argument(
        '--database', default='specifications',
        help='TypeDB database name (default: specifications)'
    )
    
    parser.add_argument(
        '--username', help='TypeDB username (for authentication)'
    )
    
    parser.add_argument(
        '--password', help='TypeDB password (for authentication)'
    )
    
    parser.add_argument(
        '--force-update', action='store_true',
        help='Force update of existing entities'
    )
    
    # Verbosity flags
    parser.add_argument(
        '-q', '--quiet', action='store_true',
        help='Error messages only'
    )
    parser.add_argument(
        '-v', '--verbose', action='count', default=0,
        help='Increase verbosity (-v, -vv, -vvv)'
    )
    parser.add_argument(
        '-vv', '--debug', action='store_true',
        help='All debug information'
    )
    
    args = parser.parse_args()
    
    # Determine verbosity level
    if args.quiet:
        verbose = VerboseLevel.ERROR
    elif args.debug:
        verbose = VerboseLevel.DEBUG
    elif args.verbose >= 2:
        verbose = VerboseLevel.DEBUG
    elif args.verbose == 1:
        verbose = VerboseLevel.VERBOSE
    else:
        verbose = VerboseLevel.NORMAL
    
    # Validate arguments
    if not args.parse_spec_file and not args.clear:
        parser.error("At least one of --parse-spec-file or --clear must be specified")
    
    if args.parse_spec_file and not args.parse_spec_file.exists():
        parser.error(f"File not found: {args.parse_spec_file}")
    
    # Create importer
    importer = TypeDBSpecImporter(
        base_url=args.url,
        database=args.database,
        username=args.username,
        password=args.password,
        verbose=verbose
    )
    
    try:
        importer.connect()
        
        if args.clear:
            importer.clear_specification_data()
        
        if args.parse_spec_file:
            importer.import_spec_file(args.parse_spec_file, args.force_update)
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        importer.close()


if __name__ == '__main__':
    main()
