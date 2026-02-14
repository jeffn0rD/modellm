#!/usr/bin/env python3
"""
TypeDB Specification Importer (HTTP API)
Imports YAML specification files into a TypeDB 3 database using HTTP API.
"""

import argparse
import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml
import requests


class TypeDBHTTPClient:
    """HTTP client for TypeDB 3 API."""
    
    def __init__(self, base_url: str = "http://localhost:8000", 
                 username: Optional[str] = None, 
                 password: Optional[str] = None):
        """Initialize the HTTP client."""
        self.base_url = base_url.rstrip('/')
        self.token = None
        self.session = requests.Session()
        
        # Authenticate if credentials provided
        if username and password:
            self._authenticate(username, password)
    
    def _authenticate(self, username: str, password: str):
        """Authenticate and get JWT token."""
        url = f"{self.base_url}/v1/signin"
        body = {
            "username": username,
            "password": password
        }
        
        response = requests.post(url, json=body)
        response.raise_for_status()
        
        self.token = response.json()["token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        print("Authenticated successfully (" + self.token + ")")
    
    def list_databases(self) -> List[str]:
        """List all databases."""
        url = f"{self.base_url}/v1/databases"
 
        response = self.session.get(url)
        response.raise_for_status()
        
        print(f"list_databases()\n  GET: {url}");
        
        print(json.dumps(response.json(), indent=4))
        databases = response.json().get("databases", [])
        return [db["name"] for db in databases]
    
    def database_exists(self, database: str) -> bool:
        """Check if a database exists."""
        databases = self.list_databases()
        
        print(databases)
        if database in databases:
            print(f"Database '{database}' exists")
        else:
            print(f"Database '{database}' not found")
        
        return database in databases
    
    def create_database(self, database: str):
        """Create a new database."""
        url = f"{self.base_url}/v1/databases"
        body = {"name": database}
        response = self.session.post(url, json=body)
        
        print(f"create_database()\n  POST: {url}");
        print(json.dumps(response.json(), indent=4))
        
        response.raise_for_status()
    
    def delete_database(self, database: str):
        """Delete a database."""
        url = f"{self.base_url}/v1/databases/{database}"
        response = self.session.delete(url)
        
        print(f"delete_database()\n  DELETE: {url}");
        print(json.dumps(response.json(), indent=4))
        
        response.raise_for_status()
    
    def execute_query(self, database: str, query: str, transaction_type: str) -> Optional[Dict]:
        """Execute a query (read or write)."""
        url = f"{self.base_url}/v1/query"
        body = {
            "query": query,
            "commit": True,
            "databaseName": database,
            "transactionType": transaction_type
        }
        print(f"execute_{transaction_type}_query():\n {query}")
        
        try:
            response = self.session.post(url, json=body)
            
            if response.status_code == 200:
                print("Success")
                return response.json() if response.text else None
            else:
                print(f"Error: HTTP {response.status_code}")
                print(json.dumps(response.json(), indent=4))
                response.raise_for_status()
                
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"Request Error: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e}")
            return None
        except Exception as e:
            print(f"Unexpected Error: {e}")
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
                 password: Optional[str] = None):
        """Initialize the importer with TypeDB connection details."""
        self.database = database
        self.client = TypeDBHTTPClient(base_url, username, password)
        
    def connect(self):
        """Establish connection to TypeDB and ensure database exists."""
        try:
            # Check if database exists, create if not
            if not self.client.database_exists(self.database):
                self.client.create_database(self.database)
                print(f"Created database: {self.database}")
            else:
                print(f"Connected to database: {self.database}")
                
        except Exception as e:
            print(f"Error connecting to TypeDB: {e}", file=sys.stderr)
            sys.exit(1)
    
    def close(self):
        """Close the TypeDB connection."""
        self.client.close()
    
    def clear_specification_data(self):
        """Clear all specification-related entities from the database."""
        print("Clearing specification data from database...")
        
        # Delete relations first, then entities
        relation_types = [
            "anchoring",
            "membership",
            "outlining"
        ]
        
        for relation_type in relation_types:
            try:
                delete_query = f"match $r isa {relation_type}; delete $r;"
                self.client.execute_write_query(self.database, delete_query)
                print(f"  Deleted {relation_type} relations")
            except Exception as e:
                print(f"  Warning: Error deleting {relation_type}: {e}", file=sys.stderr)
        
        # Now delete entities
        entity_types = [
            "text-block",
            "concept", 
            "semantic-cue",
            "spec-section",
            "spec-document"
        ]
        
        for entity_type in entity_types:
            try:
                delete_query = f"match $x isa {entity_type}; delete $x;"
                self.client.execute_write_query(self.database, delete_query)
                print(f"  Deleted {entity_type} entities")
            except Exception as e:
                print(f"  Warning: Error deleting {entity_type}: {e}", file=sys.stderr)
        
        print("Database cleared successfully")
    
    def entity_exists(self, entity_type: str, key_attr: str, key_value: str) -> bool:
        """Check if an entity with the given key already exists."""
        query = f'match $x isa {entity_type}, has {key_attr} "{key_value}";'
        try:
            result = self.client.execute_read_query(self.database, query)
            # Check if result has any answers
            if result and isinstance(result, dict):
                answers = result.get("answers", [])
                return len(answers) > 0
            return False
        except Exception as e:
            print(f"  Warning: Error checking entity existence: {e}", file=sys.stderr)
            return False
    
    def import_spec_file(self, yaml_path: Path, force_update: bool = False):
        """Import a specification YAML file into TypeDB."""
        print(f"Importing specification from: {yaml_path}")
        
        # Load YAML file
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading YAML file: {e}", file=sys.stderr)
            sys.exit(1)
        
        spec = data.get('specification', {})
        
        # Create spec-document
        spec_doc_id = spec.get('id', 'SPEC1')
        
        if force_update or not self.entity_exists('spec-document', 'spec-doc-id', spec_doc_id):
            self._create_spec_document(yaml_path, spec)
            print(f"  Created spec-document: {spec_doc_id}")
        else:
            print(f"  Spec-document {spec_doc_id} already exists, skipping")
        
        # Process sections recursively
        sections = spec.get('sections', [])
        for section in sections:
            self._process_section(section, spec_doc_id, 'spec-document', force_update)
        
        print("Import completed successfully")
    
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
            print(f"  Warning: Section without section_id, skipping", file=sys.stderr)
            return
        
        # Create section entity
        if force_update or not self.entity_exists('spec-section', 'spec-section-id', section_id):
            self._create_spec_section(section)
            print(f"  Created spec-section: {section_id}")
        
        # Create outlining relation
        if parent_type == 'spec-document':
            relation_query = f'''
                match 
                    $parent isa spec-document, has spec-doc-id "{parent_id}";
                    $child isa spec-section, has spec-section-id "{section_id}";
                insert outlining(section: $parent, subsection: $child);
            '''
        else:  # parent is another spec-section
            relation_query = f'''
                match 
                    $parent isa spec-section, has spec-section-id "{parent_id}";
                    $child isa spec-section, has spec-section-id "{section_id}";
                insert outlining(section: $parent, subsection: $child);
            '''
        
        try:
            self.client.execute_write_query(self.database, relation_query)
        except Exception as e:
            # Relation might already exist
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
                           section_id: str, order:int, force_update: bool):
        """Process a text block with its concepts and semantic cues."""
        anchor_id = text_block.get('anchor_id')
        
        if not anchor_id:
            print(f"  Warning: Text block without anchor_id, skipping", file=sys.stderr)
            return
        
        # Create text-block entity
        if force_update or not self.entity_exists('text-block', 'anchor-id', anchor_id):
            self._create_text_block(text_block, order)
            print(f"    Created text-block: {anchor_id}")
        
        # Create outlining relation between section and text-block
        relation_query = f'''
            match 
                $parent isa spec-section, has spec-section-id "{section_id}";
                $child isa text-block, has anchor-id "{anchor_id}";
            insert outlining(section: $parent, subsection: $child);
        '''
        try:
            self.client.execute_write_query(self.database, relation_query)
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
        #order = text_block.get('order', 0)
        
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
            print(f"    Warning: Concept without concept_id, skipping", file=sys.stderr)
            return
        
        # Create concept entity
        if force_update or not self.entity_exists('concept', 'concept-id', concept_id):
            self._create_concept(concept)
            print(f"      Created concept: {concept_id}")
        
        # Create anchoring relation
        relation_query = f'''
            match 
                $anchor isa text-block, has anchor-id "{anchor_id}";
                $concept isa concept, has concept-id "{concept_id}";
            insert anchoring(anchor: $anchor, concept: $concept);
        '''
        try:
            self.client.execute_write_query(self.database, relation_query)
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
        
        # Ensure cue matches identifier regex
        cue_id = cue.replace('-', '_').replace(' ', '_')
        
        # Create semantic-cue entity
        if force_update or not self.entity_exists('semantic-cue', 'identifier', cue_id):
            query = f'''
                insert $sc isa semantic-cue,
                    has identifier "{cue_id}";
            '''
            try:
                self.client.execute_write_query(self.database, query)
                print(f"      Created semantic-cue: {cue_id}")
            except Exception as e:
                print(f"      Warning: Could not create semantic-cue '{cue_id}': {e}", 
                      file=sys.stderr)
                return
        
        # Create membership relation
        relation_query = f'''
            match 
                $tb isa text-block, has anchor-id "{anchor_id}";
                $sc isa semantic-cue, has identifier "{cue_id}";
            insert membership(member-of: $tb, member: $sc);
        '''
        try:
            self.client.execute_write_query(self.database, relation_query)
        except Exception:
            pass
    
    def _escape_string(self, s: str) -> str:
        """Escape special characters in strings for TypeQL."""
        if not s:
            return ""
        # Escape backslashes first, then quotes
        s = s.replace('\\', '\\\\')
        s = s.replace('"', '\\"')
        s = s.replace('\n', ' ')
        s = s.replace('\r', ' ')
        # Collapse multiple spaces
        s = ' '.join(s.split())
        return s


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Import YAML specification files into TypeDB 3 (HTTP API)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import a specification file
  %(prog)s --parse-spec-file spec.yaml
  
  # Clear database before import
  %(prog)s --clear --parse-spec-file spec.yaml
  
  # Connect to remote TypeDB with authentication
  %(prog)s --url http://cloud.typedb.com:8000 --username admin --password secret --parse-spec-file spec.yaml
        """
    )
    
    parser.add_argument(
        '--parse-spec-file',
        type=Path,
        help='Path to YAML specification file to import'
    )
    
    parser.add_argument(
        '--clear',
        action='store_true',
        help='Clear all specification data from database before import'
    )
    
    parser.add_argument(
        '--url',
        default='http://localhost:8000',
        help='TypeDB server URL (default: http://localhost:8000)'
    )
    
    parser.add_argument(
        '--database',
        default='specifications',
        help='TypeDB database name (default: specifications)'
    )
    
    parser.add_argument(
        '--username',
        help='TypeDB username (for authentication)'
    )
    
    parser.add_argument(
        '--password',
        help='TypeDB password (for authentication)'
    )
    
    parser.add_argument(
        '--force-update',
        action='store_true',
        help='Force update of existing entities'
    )
    
    args = parser.parse_args()
    
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
        password=args.password
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
