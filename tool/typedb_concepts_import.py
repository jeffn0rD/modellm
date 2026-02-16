#!/usr/bin/env python3
"""
TypeDB Concepts Importer - Extends typedb_import.py
Imports JSON concept files into a TypeDB 3 database using HTTP API.

Files processed:
- concepts.json: Actor, Action, DataEntity
- aggregations.json: ActionAggregate
- messages.json: Message (with constraints)
- messageAggregations.json: MessageAggregate
- requirements.json: Requirement
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional


class TypeDBConceptsImporter:
    """Imports JSON concept files into TypeDB."""
    
    def __init__(self, base_url: str = "http://localhost:8000", 
                 database: str = "specifications",
                 username: Optional[str] = None, 
                 password: Optional[str] = None,
                 http_client=None):
        """Initialize the importer with TypeDB connection details."""
        self.database = database
        # Use provided client or create new one
        if http_client:
            self.client = http_client
        else:
            from typedb_import import TypeDBHTTPClient
            self.client = TypeDBHTTPClient(base_url, username, password)
    
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
            print(f"  Warning: Error checking entity existence: {e}", file=sys.stderr)
            return False
    
    def _escape_string(self, s: str) -> str:
        """Escape special characters in strings for TypeQL."""
        if not s:
            return ""
        # Only escape backslashes and double quotes for TypeQL
        s = s.replace('\\', '\\\\')
        s = s.replace('"', '\\"')
        s = s.replace('\n', ' ')
        s = s.replace('\r', ' ')
        s = ' '.join(s.split())
        return s
    
    def _transform_label(self, label: str) -> str:
        """Transform label to match id-label regex: ^[A-Z_][a-zA-Z0-9_.-]*$"""
        # Replace spaces with underscores, remove special chars except underscore/dot/hyphen
        transformed = re.sub(r'[^a-zA-Z0-9_.-]', '', label.replace(' ', '_'))
        # Ensure it starts with uppercase or underscore
        if transformed and not (transformed[0].isupper() or transformed[0] == '_'):
            transformed = transformed[0].upper() + transformed[1:]
        # Collapse multiple underscores
        transformed = re.sub(r'_+', '_', transformed)
        return transformed
    
    def clear_concepts_data(self):
        """Clear all concept-related entities from the database."""
        print("Clearing concepts data from database...")
        
        # Delete relations first
        relation_types = [
            "membership",
            "membership-seq", 
            "anchoring",
            "categorization",
            "messaging",
            "message-payload",
            "constrained-by",
            "requiring"
        ]
        
        for relation_type in relation_types:
            try:
                delete_query = f"match $r isa {relation_type}; delete $r;"
                self.client.execute_write_query(self.database, delete_query)
                print(f"  Deleted {relation_type} relations")
            except Exception as e:
                print(f"  Warning: Error deleting {relation_type}: {e}", file=sys.stderr)
        
        # Delete entities (in order of dependencies)
        entity_types = [
            "constraint",
            "message-aggregate",
            "action-aggregate",
            "message",
            "requirement",
            "data-entity",
            "action",
            "actor",
            "category"
        ]
        
        for entity_type in entity_types:
            try:
                delete_query = f"match $x isa {entity_type}; delete $x;"
                self.client.execute_write_query(self.database, delete_query)
                print(f"  Deleted {entity_type} entities")
            except Exception as e:
                print(f"  Warning: Error deleting {entity_type}: {e}", file=sys.stderr)
        
        print("Concepts data cleared successfully")
    
    def import_concepts_directory(self, json_dir: Path, force_update: bool = False):
        """Import all JSON concept files from a directory."""
        print(f"Importing concepts from: {json_dir}")
        
        if not json_dir.is_dir():
            print(f"Error: {json_dir} is not a directory", file=sys.stderr)
            return
        
        # Define the files to import and their order
        files_map = {
            "concepts.json": self.import_concepts,
            "aggregations.json": self.import_aggregations,
            "messages.json": self.import_messages,
            "messageAggregations.json": self.import_message_aggregations,
            "requirements.json": self.import_requirements
        }
        
        for filename, import_func in files_map.items():
            filepath = json_dir / filename
            if filepath.exists():
                print(f"\n--- Importing {filename} ---")
                import_func(filepath, force_update)
            else:
                print(f"  Skipping {filename} (not found)")
        
        print("\nAll concepts imported successfully")
    
    def import_concepts(self, json_path: Path, force_update: bool = False):
        """Import concepts.json (Actor, Action, DataEntity)."""
        print(f"Importing concepts from: {json_path}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        actors = []
        actions = []
        data_entities = []
        
        for item in data:
            item_type = item.get('type')
            if item_type == 'Actor':
                actors.append(item)
            elif item_type == 'Action':
                actions.append(item)
            elif item_type == 'DataEntity':
                data_entities.append(item)
        
        # Import actors
        for actor in actors:
            self._import_actor(actor, force_update)
        
        # Import actions
        for action in actions:
            self._import_action(action, force_update)
        
        # Import data entities
        for de in data_entities:
            self._import_data_entity(de, force_update)
        
        print(f"  Imported {len(actors)} actors, {len(actions)} actions, {len(data_entities)} data entities")
    
    def _import_actor(self, actor: Dict, force_update: bool):
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
            self.client.execute_write_query(self.database, query)
            print(f"    Created actor: {actor_id}")
        
        # Handle categories
        for cat_name in categories:
            self._ensure_category(cat_name)
            self._create_categorization(cat_name, 'actor', actor_id)
        
        # Handle anchors
        for anchor_id in anchors:
            self._create_anchoring(anchor_id, 'actor', actor_id)
    
    def _import_action(self, action: Dict, force_update: bool):
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
            self.client.execute_write_query(self.database, query)
            print(f"    Created action: {action_id}")
        
        # Handle categories
        for cat_name in categories:
            self._ensure_category(cat_name)
            self._create_categorization(cat_name, 'action', action_id)
        
        # Handle anchors
        for anchor_id in anchors:
            self._create_anchoring(anchor_id, 'action', action_id)
    
    def _import_data_entity(self, de: Dict, force_update: bool):
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
            self.client.execute_write_query(self.database, query)
            print(f"    Created data-entity: {de_id}")
        
        # Handle categories
        for cat_name in categories:
            self._ensure_category(cat_name)
            self._create_categorization(cat_name, 'data-entity', de_id)
        
        # Handle anchors
        for anchor_id in anchors:
            self._create_anchoring(anchor_id, 'data-entity', de_id)
    
    def _ensure_category(self, name: str):
        """Ensure a category entity exists."""
        if not self.entity_exists('category', 'name', name):
            query = f'insert $c isa category, has name "{name}";'
            self.client.execute_write_query(self.database, query)
            print(f"    Created category: {name}")
    
    def _create_categorization(self, category_name: str, entity_type: str, entity_id: str):
        """Create categorization relation."""
        key_attr = self._get_key_attr(entity_type)
        query = f'''
            match 
                $cat isa category, has name "{category_name}";
                $obj isa {entity_type}, has {key_attr} "{entity_id}";
            insert categorization(category: $cat, object: $obj);
        '''
        try:
            self.client.execute_write_query(self.database, query)
        except Exception:
            pass  # Relation may already exist
    
    def _create_anchoring(self, anchor_id: str, entity_type: str, entity_id: str):
        """Create anchoring relation to text-block."""
        key_attr = self._get_key_attr(entity_type)
        query = f'''
            match 
                $anchor isa text-block, has anchor-id "{anchor_id}";
                $concept isa {entity_type}, has {key_attr} "{entity_id}";
            insert anchoring(anchor: $anchor, concept: $concept);
        '''
        try:
            self.client.execute_write_query(self.database, query)
        except Exception as e:
            print(f"      Warning: Could not create anchoring for {entity_id}: {e}")
    
    def _get_key_attr(self, entity_type: str) -> str:
        """Get the key attribute name for an entity type."""
        key_attrs = {
            'actor': 'actor-id',
            'action': 'action-id',
            'data-entity': 'data-entity-id',
            'message': 'message-id',
            'action-aggregate': 'action-agg-id',
            'message-aggregate': 'message-agg-id',
            'requirement': 'requirement-id'
        }
        return key_attrs.get(entity_type, 'id')
    
    def import_aggregations(self, json_path: Path, force_update: bool = False):
        """Import aggregations.json (ActionAggregate)."""
        print(f"Importing aggregations from: {json_path}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for agg in data:
            agg_id = agg.get('id')
            label = self._transform_label(agg.get('label', ''))
            category = agg.get('category', '')
            description = self._escape_string(agg.get('description', ''))
            justification = self._escape_string(agg.get('justification', ''))
            members = agg.get('members', [])
            anchors = agg.get('anchors', [])
            
            if force_update or not self.entity_exists('action-aggregate', 'action-agg-id', agg_id):
                query = f'''
                    insert $agg isa action-aggregate,
                        has action-agg-id "{agg_id}",
                        has id-label "{label}",
                        has description "{description}",
                        has justification "{justification}";
                '''
                self.client.execute_write_query(self.database, query)
                print(f"    Created action-aggregate: {agg_id}")
            
            # Handle category
            if category:
                self._ensure_category(category)
                self._create_categorization(category, 'action-aggregate', agg_id)
            
            # Handle members (membership relation)
            for member_id in members:
                self._create_membership(agg_id, member_id)
            
            # Handle anchors
            for anchor_id in anchors:
                self._create_anchoring(anchor_id, 'action-aggregate', agg_id)
        
        print(f"  Imported {len(data)} action aggregates")
    
    def _create_membership(self, agg_id: str, member_id: str):
        """Create membership relation between aggregate and member."""
        query = f'''
            match 
                $agg isa action-aggregate, has action-agg-id "{agg_id}";
                $member isa action, has action-id "{member_id}";
            insert membership(member-of: $agg, member: $member);
        '''
        try:
            self.client.execute_write_query(self.database, query)
        except Exception as e:
            print(f"      Warning: Could not create membership for {member_id}: {e}")
    
    def import_messages(self, json_path: Path, force_update: bool = False):
        """Import messages.json (Message with constraints)."""
        print(f"Importing messages from: {json_path}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for msg in data:
            msg_id = msg.get('id')
            label = self._transform_label(msg.get('label', ''))
            category = msg.get('category', '')
            description = self._escape_string(msg.get('description', ''))
            justification = self._escape_string(msg.get('justification', ''))
            producer = msg.get('producer')
            consumer = msg.get('consumer')
            payload = msg.get('payload', [])
            constraints = msg.get('constraints', [])
            anchors = msg.get('anchors', [])
            
            # Create message entity
            if force_update or not self.entity_exists('message', 'message-id', msg_id):
                query = f'''
                    insert $m isa message,
                        has message-id "{msg_id}",
                        has id-label "{label}",
                        has description "{description}",
                        has justification "{justification}";
                '''
                self.client.execute_write_query(self.database, query)
                print(f"    Created message: {msg_id}")
            
            # Handle category
            if category:
                self._ensure_category(category)
                self._create_categorization(category, 'message', msg_id)
            
            # Handle producer/consumer (messaging relation)
            if producer and consumer:
                self._create_messaging(msg_id, producer, consumer)
            
            # Handle payload (message-payload relation)
            for p in payload:
                ref_id = p.get('refConceptId') or p.get('id')
                if ref_id:
                    self._create_message_payload(msg_id, ref_id)
            
            # Handle constraints
            for constraint in constraints:
                self._import_constraint(msg_id, constraint)
            
            # Handle anchors
            for anchor_id in anchors:
                self._create_anchoring(anchor_id, 'message', msg_id)
        
        print(f"  Imported {len(data)} messages")
    
    def _create_messaging(self, message_id: str, producer_id: str, consumer_id: str):
        """Create messaging relation (producer/consumer -> message)."""
        query = f'''
            match 
                $prod isa actor, has actor-id "{producer_id}";
                $cons isa actor, has actor-id "{consumer_id}";
                $msg isa message, has message-id "{message_id}";
            insert messaging(producer: $prod, consumer: $cons, message: $msg);
        '''
        try:
            self.client.execute_write_query(self.database, query)
        except Exception as e:
            print(f"      Warning: Could not create messaging for {message_id}: {e}")
    
    def _create_message_payload(self, message_id: str, data_entity_id: str):
        """Create message-payload relation."""
        query = f'''
            match 
                $msg isa message, has message-id "{message_id}";
                $de isa data-entity, has data-entity-id "{data_entity_id}";
            insert message-payload(message: $msg, payload: $de);
        '''
        try:
            self.client.execute_write_query(self.database, query)
        except Exception as e:
            print(f"      Warning: Could not create message-payload: {e}")
    
    def _import_constraint(self, message_id: str, constraint: Dict):
        """Import a constraint and create constrained-by relation."""
        constraint_id = constraint.get('id')
        label = self._transform_label(constraint.get('label', ''))
        description = self._escape_string(constraint.get('constraint', ''))
        
        if not constraint_id:
            return
        
        if not self.entity_exists('constraint', 'constraint-id', constraint_id):
            query = f'''
                insert $c isa constraint,
                    has constraint-id "{constraint_id}",
                    has id-label "{label}",
                    has description "{description}";
            '''
            self.client.execute_write_query(self.database, query)
            print(f"    Created constraint: {constraint_id}")
        
        # Create constrained-by relation
        query = f'''
            match 
                $c isa constraint, has constraint-id "{constraint_id}";
                $msg isa message, has message-id "{message_id}";
            insert constrained-by(constraint: $c, object: $msg);
        '''
        try:
            self.client.execute_write_query(self.database, query)
        except Exception as e:
            print(f"      Warning: Could not create constrained-by: {e}")
    
    def import_message_aggregations(self, json_path: Path, force_update: bool = False):
        """Import messageAggregations.json (MessageAggregate with sequences)."""
        print(f"Importing message aggregations from: {json_path}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for mag in data:
            mag_id = mag.get('id')
            label = self._transform_label(mag.get('label', ''))
            category = mag.get('category', '')
            description = self._escape_string(mag.get('description', ''))
            justification = self._escape_string(mag.get('justification', ''))
            sequences = mag.get('sequences', [])
            anchors = mag.get('anchors', [])
            
            # Create message-aggregate entity
            if force_update or not self.entity_exists('message-aggregate', 'message-agg-id', mag_id):
                query = f'''
                    insert $mag isa message-aggregate,
                        has message-agg-id "{mag_id}",
                        has id-label "{label}",
                        has description "{description}",
                        has justification "{justification}";
                '''
                self.client.execute_write_query(self.database, query)
                print(f"    Created message-aggregate: {mag_id}")
            
            # Handle category
            if category:
                self._ensure_category(category)
                self._create_categorization(category, 'message-aggregate', mag_id)
            
            # Handle sequences (membership-seq with order)
            order = 0
            for sequence in sequences:
                for msg_item in sequence:
                    msg_id = msg_item.get('id')
                    if msg_id:
                        self._create_membership_seq(mag_id, msg_id, order)
                        order += 10  # Leave room for insertion
            
            # Handle anchors
            for anchor_id in anchors:
                self._create_anchoring(anchor_id, 'message-aggregate', mag_id)
        
        print(f"  Imported {len(data)} message aggregates")
    
    def _create_membership_seq(self, agg_id: str, message_id: str, order: int):
        """Create membership-seq relation with order."""
        # First try with subrelation syntax
        query = f'''
            match 
                $mag isa message-aggregate, has message-agg-id "{agg_id}";
                $msg isa message, has message-id "{message_id}";
            insert (member-of: $mag, member: $msg) isa membership-seq, has order {order};
        '''
        try:
            self.client.execute_write_query(self.database, query)
        except Exception as e:
            # Fallback: try regular membership without order
            print(f"      Warning: Could not create membership-seq (trying regular membership): {e}")
            try:
                query = f'''
                    match 
                        $mag isa message-aggregate, has message-agg-id "{agg_id}";
                        $msg isa message, has message-id "{message_id}";
                    insert membership(member-of: $mag, member: $msg);
                '''
                self.client.execute_write_query(self.database, query)
            except Exception as e2:
                print(f"      Warning: Could not create membership: {e2}")
    
    def import_requirements(self, json_path: Path, force_update: bool = False):
        """Import requirements.json (Requirement entities)."""
        print(f"Importing requirements from: {json_path}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for req in data:
            req_id = req.get('id')
            label = self._transform_label(req.get('label', ''))
            req_type = req.get('type', 'functional')  # Maps to requirement-type
            status = req.get('status', 'draft')
            priority = req.get('priority', 'must')
            description = self._escape_string(req.get('description', ''))
            justification = self._escape_string(req.get('justification', ''))
            anchors = req.get('anchors', [])
            related_concepts = req.get('relatedConcepts', [])
            related_messages = req.get('relatedMessages', [])
            
            # Create requirement entity
            if force_update or not self.entity_exists('requirement', 'requirement-id', req_id):
                query = f'''
                    insert $req isa requirement,
                        has requirement-id "{req_id}",
                        has requirement-type "{req_type}",
                        has status "{status}",
                        has priority "{priority}",
                        has id-label "{label}",
                        has description "{description}",
                        has justification "{justification}";
                '''
                self.client.execute_write_query(self.database, query)
                print(f"    Created requirement: {req_id}")
            
            # Handle anchors
            for anchor_id in anchors:
                self._create_anchoring(anchor_id, 'requirement', req_id)
            
            # Handle requiring relation (relatedConcepts + relatedMessages)
            for concept_id in related_concepts:
                self._create_requiring(req_id, concept_id, 'concept')
            
            for msg_id in related_messages:
                self._create_requiring(req_id, msg_id, 'message')
        
        print(f"  Imported {len(data)} requirements")
    
    def _create_requiring(self, req_id: str, target_id: str, target_type: str):
        """Create requiring relation for related concepts/messages."""
        if target_type == 'concept':
            key_attr = 'concept-id'
        elif target_type == 'message':
            key_attr = 'message-id'
        else:
            return
        
        query = f'''
            match 
                $req isa requirement, has requirement-id "{req_id}";
                $target isa {target_type}, has {key_attr} "{target_id}";
            insert requiring(required-by: $req, conceptualized-as: $target);
        '''
        try:
            self.client.execute_write_query(self.database, query)
        except Exception as e:
            print(f"      Warning: Could not create requiring: {e}")


def main():
    """Main CLI entry point for concepts importer."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Import JSON concept files into TypeDB 3 (HTTP API)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import all JSON files from directory
  %(prog)s --parse-concepts ./json/
  
  # Import with force update
  %(prog)s --parse-concepts ./json/ --force-update
  
  # Connect to remote TypeDB with authentication
  %(prog)s --url http://cloud.typedb.com:8000 --username admin --password secret --parse-concepts ./json/
        """
    )
    
    parser.add_argument(
        '--parse-concepts',
        type=Path,
        help='Path to JSON concepts file to import (or directory containing multiple JSON files)'
    )
    
    parser.add_argument(
        '--clear',
        action='store_true',
        help='Clear all concepts data from database before import'
    )
    
    parser.add_argument(
        '--url',
        default='http://localhost:8000',
        help='TypeDB server URL (default: http://localhost:8000)'
    )
    
    parser.add_argument(
        '--database',
        default='scratch3',
        help='TypeDB database name (default: scratch3)'
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
    if not args.parse_concepts and not args.clear:
        parser.error("At least one of --parse-concepts or --clear must be specified")
    
    if args.parse_concepts and not args.parse_concepts.exists():
        parser.error(f"File or directory not found: {args.parse_concepts}")
    
    # Import the main importer to get the client class
    import typedb_import
    
    # Create importer
    importer = TypeDBConceptsImporter(
        base_url=args.url,
        database=args.database,
        username=args.username,
        password=args.password
    )
    
    try:
        # Client doesn't have a connect method - connection happens on first query
        
        if args.clear:
            importer.clear_concepts_data()
        
        if args.parse_concepts:
            if args.parse_concepts.is_dir():
                importer.import_concepts_directory(args.parse_concepts, args.force_update)
            else:
                # Single file - determine which type
                filename = args.parse_concepts.name
                if filename == 'concepts.json':
                    importer.import_concepts(args.parse_concepts, args.force_update)
                elif filename == 'aggregations.json':
                    importer.import_aggregations(args.parse_concepts, args.force_update)
                elif filename == 'messages.json':
                    importer.import_messages(args.parse_concepts, args.force_update)
                elif filename == 'messageAggregations.json':
                    importer.import_message_aggregations(args.parse_concepts, args.force_update)
                elif filename == 'requirements.json':
                    importer.import_requirements(args.parse_concepts, args.force_update)
                else:
                    print(f"Unknown file: {filename}")
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        importer.client.close()


if __name__ == '__main__':
    main()
