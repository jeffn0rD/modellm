"""TypeDB Importer Library

Unified library for importing data into TypeDB from YAML/JSON files.
Combines functionality from typedb_import.py and typedb_concepts_import.py.
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from typedb_client3 import TypeDBClient, TransactionType
from typedb_client3 import TypeDBError


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


class TypeDBImporter:
    """Unified importer for YAML/JSON specification files into TypeDB."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        database: str = "specifications",
        username: Optional[str] = None,
        password: Optional[str] = None,
        verbose: int = VerboseLevel.NORMAL,
        auto_connect: bool = True
    ):
        """Initialize the importer.
        
        Args:
            base_url: TypeDB server URL
            database: Database name
            username: TypeDB username (optional)
            password: TypeDB password (optional)
            verbose: Verbosity level
            auto_connect: Automatically connect on initialization
        """
        self.database = database
        self.verbose = verbose
        self.logger = Logger(verbose)
        self.stats: Dict[str, int] = {
            "documents": 0,
            "sections": 0,
            "text_blocks": 0,
            "concepts": 0,
            "actors": 0,
            "actions": 0,
            "data_entities": 0,
            "requirements": 0,
            "messages": 0,
            "aggregations": 0,
            "semantic_cues": 0,
            "categories": 0,
            "relations": 0
        }
        
        self.client = TypeDBClient(
            base_url=base_url,
            username=username,
            password=password
        )
        
        if auto_connect:
            self.connect()
    
    def connect(self) -> None:
        """Establish connection to TypeDB and ensure database exists."""
        try:
            if not self.client.database_exists(self.database):
                self.client.create_database(self.database)
                self.logger.info(f"Created database: {self.database}")
            self.logger.success(f"Connected to database: {self.database}")
        except TypeDBError as e:
            self.logger.error(f"Error connecting to TypeDB: {e}")
            sys.exit(1)
    
    def close(self) -> None:
        """Close the TypeDB connection."""
        self.client.close()
    
    def _print_summary(self) -> None:
        """Print import summary."""
        self.logger.section("Import Summary")
        for key, value in self.stats.items():
            if value > 0:
                print(f"  {Colors.GREEN}{key.capitalize()}:{Colors.RESET} {value}")
    
    def entity_exists(self, entity_type: str, key_attr: str, key_value: str) -> bool:
        """Check if an entity with the given key already exists."""
        query = f'match $x isa {entity_type}, has {key_attr} "{key_value}"; fetch $x;'
        try:
            result = self.client.execute_query(self.database, query, TransactionType.READ)
            if result and isinstance(result, dict):
                answers = result.get("answers", [])
                return len(answers) > 0
            return False
        except Exception as e:
            self.logger.debug(f"Error checking entity existence: {e}")
            return False
    
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
    
    def _transform_label(self, label: str) -> str:
        """Transform label to match id-label regex: ^[A-Z_][a-zA-Z0-9_.-]*$"""
        transformed = re.sub(r'[^a-zA-Z0-9_.-]', '', label.replace(' ', '_'))
        if transformed and not (transformed[0].isupper() or transformed[0] == '_'):
            transformed = transformed[0].upper() + transformed[1:]
        transformed = re.sub(r'_+', '_', transformed)
        return transformed
    
    # ==================== SPECIFICATION IMPORT ====================
    
    def clear_specification_data(self) -> None:
        """Clear all specification-related entities from the database."""
        self.logger.info("Clearing specification data...")
        
        relation_types = ["anchoring", "membership", "outlining"]
        for relation_type in relation_types:
            try:
                self.client.execute_query(
                    self.database,
                    f"match $r isa {relation_type}; delete $r;",
                    TransactionType.WRITE
                )
            except Exception as e:
                self.logger.debug(f"Error deleting {relation_type}: {e}")
        
        entity_types = [
            "text-block", "concept", "semantic-cue",
            "spec-section", "spec-document", "fs-folder"
        ]
        for entity_type in entity_types:
            try:
                self.client.execute_query(
                    self.database,
                    f"match $x isa {entity_type}; delete $x;",
                    TransactionType.WRITE
                )
            except Exception as e:
                self.logger.debug(f"Error deleting {entity_type}: {e}")
        
        self.logger.success("Specification data cleared")
    
    def import_yaml(self, yaml_path: Path, force_update: bool = False) -> None:
        """Import a YAML specification file into TypeDB.
        
        Args:
            yaml_path: Path to YAML file
            force_update: Force update of existing entities
        """
        self.logger.section(f"Importing: {yaml_path.name}")
        
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
        
        sections = spec.get('sections', [])
        for section in sections:
            self._process_section(section, spec_doc_id, 'spec-document', force_update)
        
        self._print_summary()
        self.logger.success("Import completed")
    
    def _create_spec_document(self, yaml_path: Path, spec: Dict[str, Any]) -> None:
        """Create a spec-document entity."""
        spec_id = spec.get('id', 'SPEC1')
        title = self._escape_string(spec.get('title', ''))
        version = spec.get('version', '0.1')
        description = self._escape_string(spec.get('description', ''))
        
        query = f'''
            insert 
                $folder isa fs-folder, has foldername "{yaml_path.parent}";
                $doc isa spec-document,
                  has spec-doc-id "{spec_id}",
                  has title "{title}",
                  has version "{version}",
                  has status "draft",
                  has description "{description}",
                  has filename "{yaml_path}";
                filesystem(folder: $folder, entry: $doc);
        '''
        self.client.execute_query(self.database, query, TransactionType.WRITE)
    
    def _process_section(
        self,
        section: Dict[str, Any],
        parent_id: str,
        parent_type: str,
        force_update: bool
    ) -> None:
        """Process a section and its subsections/text-blocks recursively."""
        section_id = section.get('section_id')
        
        if not section_id:
            self.logger.warning("Section without section_id, skipping")
            return
        
        if force_update or not self.entity_exists('spec-section', 'spec-section-id', section_id):
            self._create_spec_section(section)
            self.stats['sections'] += 1
            self.logger.debug(f"Created spec-section: {section_id}")
        
        # Create outlining relation
        if parent_type == 'spec-document':
            rel_query = f'''
                match 
                    $parent isa spec-document, has spec-doc-id "{parent_id}";
                    $child isa spec-section, has spec-section-id "{section_id}";
                insert outlining(section: $parent, subsection: $child);
            '''
        else:
            rel_query = f'''
                match 
                    $parent isa spec-section, has spec-section-id "{parent_id}";
                    $child isa spec-section, has spec-section-id "{section_id}";
                insert outlining(section: $parent, subsection: $child);
            '''
        
        try:
            self.client.execute_query(self.database, rel_query, TransactionType.WRITE)
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
    
    def _create_spec_section(self, section: Dict[str, Any]) -> None:
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
        self.client.execute_query(self.database, query, TransactionType.WRITE)
    
    def _process_text_block(
        self,
        text_block: Dict[str, Any],
        section_id: str,
        order: int,
        force_update: bool
    ) -> None:
        """Process a text block with its concepts and semantic cues."""
        anchor_id = text_block.get('anchor_id')
        
        if not anchor_id:
            self.logger.warning("Text block without anchor_id, skipping")
            return
        
        if force_update or not self.entity_exists('text-block', 'anchor-id', anchor_id):
            self._create_text_block(text_block, order)
            self.stats['text_blocks'] += 1
            self.logger.debug(f"Created text-block: {anchor_id}")
        
        # Create outlining relation
        rel_query = f'''
            match 
                $parent isa spec-section, has spec-section-id "{section_id}";
                $child isa text-block, has anchor-id "{anchor_id}";
            insert outlining(section: $parent, subsection: $child);
        '''
        try:
            self.client.execute_query(self.database, rel_query, TransactionType.WRITE)
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
    
    def _create_text_block(self, text_block: Dict[str, Any], order: int) -> None:
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
        self.client.execute_query(self.database, query, TransactionType.WRITE)
    
    def _process_concept(
        self,
        concept: Dict[str, Any],
        anchor_id: str,
        force_update: bool
    ) -> None:
        """Process a concept and create anchoring relation."""
        concept_id = concept.get('concept_id')
        
        if not concept_id:
            self.logger.warning("Concept without concept_id, skipping")
            return
        
        if force_update or not self.entity_exists('concept', 'concept-id', concept_id):
            self._create_concept(concept)
            self.stats['concepts'] += 1
            self.logger.debug(f"Created concept: {concept_id}")
        
        rel_query = f'''
            match 
                $anchor isa text-block, has anchor-id "{anchor_id}";
                $concept isa concept, has concept-id "{concept_id}";
            insert anchoring(anchor: $anchor, concept: $concept);
        '''
        try:
            self.client.execute_query(self.database, rel_query, TransactionType.WRITE)
            self.stats['relations'] += 1
        except Exception:
            pass
    
    def _create_concept(self, concept: Dict[str, Any]) -> None:
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
        self.client.execute_query(self.database, query, TransactionType.WRITE)
    
    def _process_semantic_cue(
        self,
        cue: str,
        anchor_id: str,
        force_update: bool
    ) -> None:
        """Process a semantic cue and create membership relation."""
        if not cue:
            return
        
        cue_id = cue.replace('-', '_').replace(' ', '_')
        
        if force_update or not self.entity_exists('semantic-cue', 'identifier', cue_id):
            query = f'''
                insert $sc isa semantic-cue, has identifier "{cue_id}";
            '''
            try:
                self.client.execute_query(self.database, query, TransactionType.WRITE)
                self.stats['semantic_cues'] += 1
                self.logger.debug(f"Created semantic-cue: {cue_id}")
            except Exception as e:
                self.logger.warning(f"Could not create semantic-cue '{cue_id}': {e}")
        
        rel_query = f'''
            match 
                $tb isa text-block, has anchor-id "{anchor_id}";
                $sc isa semantic-cue, has identifier "{cue_id}";
            insert membership(member-of: $tb, member: $sc);
        '''
        try:
            self.client.execute_query(self.database, rel_query, TransactionType.WRITE)
            self.stats['relations'] += 1
        except Exception:
            pass
    
    # ==================== CONCEPTS IMPORT ====================
    
    def clear_concepts_data(self) -> None:
        """Clear all concept-related entities from the database."""
        self.logger.info("Clearing concepts data...")
        
        relation_types = [
            "membership", "membership-seq", "anchoring", "categorization",
            "messaging", "message-payload", "constrained-by", "requiring"
        ]
        
        for relation_type in relation_types:
            try:
                self.client.execute_query(
                    self.database,
                    f"match $r isa {relation_type}; delete $r;",
                    TransactionType.WRITE
                )
            except Exception as e:
                self.logger.debug(f"Error deleting {relation_type}: {e}")
        
        entity_types = [
            "constraint", "message-aggregate", "action-aggregate",
            "message", "requirement", "data-entity", "action",
            "actor", "category"
        ]
        
        for entity_type in entity_types:
            try:
                self.client.execute_query(
                    self.database,
                    f"match $x isa {entity_type}; delete $x;",
                    TransactionType.WRITE
                )
            except Exception as e:
                self.logger.debug(f"Error deleting {entity_type}: {e}")
        
        self.logger.success("Concepts data cleared")
    
    def import_json_directory(
        self,
        json_dir: Path,
        force_update: bool = False
    ) -> None:
        """Import all JSON concept files from a directory.
        
        Args:
            json_dir: Path to directory containing JSON files
            force_update: Force update of existing entities
        """
        self.logger.section(f"Importing concepts from: {json_dir}")
        
        if not json_dir.is_dir():
            self.logger.error(f"{json_dir} is not a directory")
            return
        
        files_map = {
            "concepts.json": self._import_concepts_json,
            "aggregations.json": self._import_aggregations_json,
            "messages.json": self._import_messages_json,
            "messageAggregations.json": self._import_message_aggregations_json,
            "requirements.json": self._import_requirements_json
        }
        
        for filename, import_func in files_map.items():
            filepath = json_dir / filename
            if filepath.exists():
                self.logger.info(f"Importing {filename}...")
                import_func(filepath, force_update)
            else:
                self.logger.debug(f"Skipping {filename} (not found)")
        
        self._print_summary()
        self.logger.success("All concepts imported")
    
    def _import_concepts_json(self, json_path: Path, force_update: bool) -> None:
        """Import concepts.json (Actor, Action, DataEntity)."""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        actors = [item for item in data if item.get('type') == 'Actor']
        actions = [item for item in data if item.get('type') == 'Action']
        data_entities = [item for item in data if item.get('type') == 'DataEntity']
        
        for actor in actors:
            self._import_actor(actor, force_update)
        
        for action in actions:
            self._import_action(action, force_update)
        
        for de in data_entities:
            self._import_data_entity(de, force_update)
        
        self.logger.info(f"Imported {len(actors)} actors, {len(actions)} actions, {len(data_entities)} data entities")
    
    def _import_actor(self, actor: Dict, force_update: bool) -> None:
        """Import a single Actor entity."""
        actor_id = actor.get('id')
        label = self._transform_label(actor.get('label', ''))
        description = self._escape_string(actor.get('description', ''))
        justification = self._escape_string(actor.get('justification', ''))
        categories = actor.get('categories', [])
        anchors = actor.get('anchors', [])
        
        if force_update or not self.entity_exists('actor', 'actor-id', actor_id):
            query = f'''
                insert $a isa actor,
                    has actor-id "{actor_id}",
                    has id-label "{label}",
                    has description "{description}",
                    has justification "{justification}";
            '''
            self.client.execute_query(self.database, query, TransactionType.WRITE)
            self.stats['actors'] += 1
            self.logger.debug(f"Created actor: {actor_id}")
        
        for cat_name in categories:
            self._ensure_category(cat_name)
            self._create_categorization(cat_name, 'actor', actor_id)
        
        for anchor_id in anchors:
            self._create_anchoring(anchor_id, 'actor', actor_id)
    
    def _import_action(self, action: Dict, force_update: bool) -> None:
        """Import a single Action entity."""
        action_id = action.get('id')
        label = self._transform_label(action.get('label', ''))
        description = self._escape_string(action.get('description', ''))
        justification = self._escape_string(action.get('justification', ''))
        categories = action.get('categories', [])
        anchors = action.get('anchors', [])
        
        if force_update or not self.entity_exists('action', 'action-id', action_id):
            query = f'''
                insert $act isa action,
                    has action-id "{action_id}",
                    has id-label "{label}",
                    has description "{description}",
                    has justification "{justification}";
            '''
            self.client.execute_query(self.database, query, TransactionType.WRITE)
            self.stats['actions'] += 1
            self.logger.debug(f"Created action: {action_id}")
        
        for cat_name in categories:
            self._ensure_category(cat_name)
            self._create_categorization(cat_name, 'action', action_id)
        
        for anchor_id in anchors:
            self._create_anchoring(anchor_id, 'action', action_id)
    
    def _import_data_entity(self, de: Dict, force_update: bool) -> None:
        """Import a single DataEntity entity."""
        de_id = de.get('id')
        label = self._transform_label(de.get('label', ''))
        description = self._escape_string(de.get('description', ''))
        justification = self._escape_string(de.get('justification', ''))
        categories = de.get('categories', [])
        anchors = de.get('anchors', [])
        
        if force_update or not self.entity_exists('data-entity', 'data-entity-id', de_id):
            query = f'''
                insert $de isa data-entity,
                    has data-entity-id "{de_id}",
                    has id-label "{label}",
                    has description "{description}",
                    has justification "{justification}";
            '''
            self.client.execute_query(self.database, query, TransactionType.WRITE)
            self.stats['data_entities'] += 1
            self.logger.debug(f"Created data-entity: {de_id}")
        
        for cat_name in categories:
            self._ensure_category(cat_name)
            self._create_categorization(cat_name, 'data-entity', de_id)
        
        for anchor_id in anchors:
            self._create_anchoring(anchor_id, 'data-entity', de_id)
    
    def _ensure_category(self, category_name: str) -> None:
        """Ensure a category entity exists."""
        cat_id = self._transform_label(category_name)
        
        if not self.entity_exists('category', 'category-id', cat_id):
            query = f'''
                insert $cat isa category,
                    has category-id "{cat_id}",
                    has category-name "{category_name}";
            '''
            try:
                self.client.execute_query(self.database, query, TransactionType.WRITE)
                self.stats['categories'] += 1
            except Exception as e:
                self.logger.debug(f"Could not create category '{category_name}': {e}")
    
    def _create_categorization(
        self,
        category_name: str,
        entity_type: str,
        entity_id: str
    ) -> None:
        """Create categorization relation between entity and category."""
        cat_id = self._transform_label(category_name)
        id_attr = {
            'actor': 'actor-id',
            'action': 'action-id',
            'data-entity': 'data-entity-id'
        }.get(entity_type, 'id')
        
        rel_query = f'''
            match 
                $cat isa category, has category-id "{cat_id}";
                $ent isa {entity_type}, has {id_attr} "{entity_id}";
            insert categorization(categorized: $ent, category: $cat);
        '''
        try:
            self.client.execute_query(self.database, rel_query, TransactionType.WRITE)
            self.stats['relations'] += 1
        except Exception:
            pass
    
    def _create_anchoring(
        self,
        anchor_id: str,
        entity_type: str,
        entity_id: str
    ) -> None:
        """Create anchoring relation between text block and entity."""
        id_attr = {
            'actor': 'actor-id',
            'action': 'action-id',
            'data-entity': 'data-entity-id'
        }.get(entity_type, 'id')
        
        rel_query = f'''
            match 
                $tb isa text-block, has anchor-id "{anchor_id}";
                $ent isa {entity_type}, has {id_attr} "{entity_id}";
            insert anchoring(anchor: $tb, concept: $ent);
        '''
        try:
            self.client.execute_query(self.database, rel_query, TransactionType.WRITE)
            self.stats['relations'] += 1
        except Exception:
            pass
    
    def _import_aggregations_json(self, json_path: Path, force_update: bool) -> None:
        """Import aggregations.json (ActionAggregate)."""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for agg in data:
            agg_id = agg.get('id')
            label = self._transform_label(agg.get('label', ''))
            description = self._escape_string(agg.get('description', ''))
            constituent_ids = agg.get('constituents', [])
            
            if force_update or not self.entity_exists('action-aggregate', 'action-aggregate-id', agg_id):
                query = f'''
                    insert $aa isa action-aggregate,
                        has action-aggregate-id "{agg_id}",
                        has id-label "{label}",
                        has description "{description}";
                '''
                try:
                    self.client.execute_query(self.database, query, TransactionType.WRITE)
                    self.stats['aggregations'] += 1
                    self.logger.debug(f"Created action-aggregate: {agg_id}")
                except Exception as e:
                    self.logger.warning(f"Could not create aggregation '{agg_id}': {e}")
        
        self.logger.info(f"Imported {len(data)} action aggregates")
    
    def _import_messages_json(self, json_path: Path, force_update: bool) -> None:
        """Import messages.json."""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for msg in data:
            msg_id = msg.get('id')
            label = self._transform_label(msg.get('label', ''))
            description = self._escape_string(msg.get('description', ''))
            constraints = msg.get('constraints', [])
            
            if force_update or not self.entity_exists('message', 'message-id', msg_id):
                query = f'''
                    insert $m isa message,
                        has message-id "{msg_id}",
                        has id-label "{label}",
                        has description "{description}";
                '''
                try:
                    self.client.execute_query(self.database, query, TransactionType.WRITE)
                    self.stats['messages'] += 1
                    self.logger.debug(f"Created message: {msg_id}")
                except Exception as e:
                    self.logger.warning(f"Could not create message '{msg_id}': {e}")
        
        self.logger.info(f"Imported {len(data)} messages")
    
    def _import_message_aggregations_json(self, json_path: Path, force_update: bool) -> None:
        """Import messageAggregations.json."""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for agg in data:
            agg_id = agg.get('id')
            label = self._transform_label(agg.get('label', ''))
            description = self._escape_string(agg.get('description', ''))
            
            if force_update or not self.entity_exists('message-aggregate', 'message-aggregate-id', agg_id):
                query = f'''
                    insert $ma isa message-aggregate,
                        has message-aggregate-id "{agg_id}",
                        has id-label "{label}",
                        has description "{description}";
                '''
                try:
                    self.client.execute_query(self.database, query, TransactionType.WRITE)
                    self.stats['aggregations'] += 1
                    self.logger.debug(f"Created message-aggregate: {agg_id}")
                except Exception as e:
                    self.logger.warning(f"Could not create message aggregate '{agg_id}': {e}")
        
        self.logger.info(f"Imported {len(data)} message aggregates")
    
    def _import_requirements_json(self, json_path: Path, force_update: bool) -> None:
        """Import requirements.json."""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for req in data:
            req_id = req.get('id')
            label = self._transform_label(req.get('label', ''))
            description = self._escape_string(req.get('description', ''))
            
            if force_update or not self.entity_exists('requirement', 'requirement-id', req_id):
                query = f'''
                    insert $r isa requirement,
                        has requirement-id "{req_id}",
                        has id-label "{label}",
                        has description "{description}";
                '''
                try:
                    self.client.execute_query(self.database, query, TransactionType.WRITE)
                    self.stats['requirements'] += 1
                    self.logger.debug(f"Created requirement: {req_id}")
                except Exception as e:
                    self.logger.warning(f"Could not create requirement '{req_id}': {e}")
        
        self.logger.info(f"Imported {len(data)} requirements")


def create_importer(
    base_url: str = "http://localhost:8000",
    database: str = "specifications",
    username: Optional[str] = None,
    password: Optional[str] = None,
    verbose: int = VerboseLevel.NORMAL
) -> TypeDBImporter:
    """Factory function to create a TypeDBImporter.
    
    Args:
        base_url: TypeDB server URL
        database: Database name
        username: TypeDB username (optional)
        password: TypeDB password (optional)
        verbose: Verbosity level
        
    Returns:
        TypeDBImporter instance
    """
    return TypeDBImporter(
        base_url=base_url,
        database=database,
        username=username,
        password=password,
        verbose=verbose,
        auto_connect=False
    )


__all__ = [
    "TypeDBImporter",
    "create_importer",
    "Colors",
    "VerboseLevel",
    "Logger",
]
