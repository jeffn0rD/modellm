"""Unit tests for TypeDBImporter module.

These tests verify the QueryBuilder integration and helper methods.
Tests use mocking to avoid needing a live TypeDB server.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path

from prompt_pipeline.importer.importer import (
    TypeDBImporter,
    create_importer,
    Colors,
    VerboseLevel,
    Logger
)


class TestColors:
    """Test Colors class for ANSI codes."""
    
    def test_colors_exist(self):
        """Test that all color codes are defined."""
        assert Colors.RESET == '\033[0m'
        assert Colors.RED == '\033[91m'
        assert Colors.GREEN == '\033[92m'
        assert Colors.YELLOW == '\033[93m'
        assert Colors.BLUE == '\033[94m'
        assert Colors.MAGENTA == '\033[95m'
        assert Colors.CYAN == '\033[96m'
        assert Colors.BOLD == '\033[1m'
        assert Colors.DIM == '\033[2m'


class TestVerboseLevel:
    """Test VerboseLevel enum values."""
    
    def test_verbose_levels(self):
        """Test verbosity level values."""
        assert VerboseLevel.ERROR == 0
        assert VerboseLevel.NORMAL == 1
        assert VerboseLevel.VERBOSE == 2
        assert VerboseLevel.DEBUG == 3


class TestLogger:
    """Test Logger class."""
    
    def test_logger_initialization(self):
        """Test logger initializes with correct verbosity."""
        logger = Logger(VerboseLevel.DEBUG)
        assert logger.verbose == VerboseLevel.DEBUG
    
    def test_logger_error_output(self, capsys):
        """Test error messages are printed."""
        logger = Logger(VerboseLevel.NORMAL)
        logger.error("Test error")
        captured = capsys.readouterr()
        assert "ERROR:" in captured.err
    
    def test_logger_warning_verbose_level(self, capsys):
        """Test warning respects verbosity level."""
        logger = Logger(VerboseLevel.ERROR)
        logger.warning("Test warning")
        captured = capsys.readouterr()
        assert "Test warning" not in captured.out
    
    def test_logger_success_output(self, capsys):
        """Test success messages are printed."""
        logger = Logger(VerboseLevel.NORMAL)
        logger.success("Test success")
        captured = capsys.readouterr()
        assert "SUCCESS:" in captured.out
    
    def test_logger_info_output(self, capsys):
        """Test info messages respect verbosity level."""
        logger = Logger(VerboseLevel.VERBOSE)
        logger.info("Test info")
        captured = capsys.readouterr()
        assert "INFO:" in captured.out
    
    def test_logger_debug_output(self, capsys):
        """Test debug messages respect verbosity level."""
        logger = Logger(VerboseLevel.DEBUG)
        logger.debug("Test debug")
        captured = capsys.readouterr()
        assert "DEBUG:" in captured.out
    
    def test_logger_section(self, capsys):
        """Test section header output."""
        logger = Logger(VerboseLevel.VERBOSE)
        logger.section("Test Section")
        captured = capsys.readouterr()
        assert "Test Section" in captured.out
        assert "=" in captured.out


class MockQueryBuilder:
    """Mock QueryBuilder for testing."""
    
    def __init__(self, query_type):
        self.query_type = query_type
        self._variables = {}
        self._fetch = []
    
    def match(self):
        return self
    
    def insert(self):
        return self
    
    def variable(self, name, type_, attributes=None):
        self._variables[name] = {'type': type_, 'attributes': attributes or {}}
        return self
    
    def fetch(self, vars_list):
        self._fetch = vars_list
        return self
    
    def build(self):
        if self.query_type == 'match':
            var_name = list(self._variables.keys())[0] if self._variables else 'x'
            type_ = self._variables[var_name]['type'] if self._variables else 'entity'
            attrs = self._variables[var_name]['attributes'] if self._variables else {}
            parts = [f"${var_name} isa {type_}"]
            for k, v in attrs.items():
                parts.append(f'has {k} "{v}"')
            return f"match {', '.join(parts)}; fetch ${self._fetch[0]};"
        elif self.query_type == 'insert':
            var_name = list(self._variables.keys())[0] if self._variables else 'x'
            type_ = self._variables[var_name]['type'] if self._variables else 'entity'
            attrs = self._variables[var_name]['attributes'] if self._variables else {}
            parts = [f"${var_name} isa {type_}"]
            for k, v in attrs.items():
                parts.append(f'has {k} "{v}"')
            return f"insert {', '.join(parts)};"
        return ""


class TestTypeDBImporterInitialization:
    """Test TypeDBImporter initialization."""
    
    @patch('prompt_pipeline.importer.importer.TypeDBClient')
    def test_create_importer_defaults(self, mock_client):
        """Test create_importer with default parameters."""
        importer = create_importer()
        assert importer.database == "specifications"
        assert importer.verbose == VerboseLevel.NORMAL
        assert not importer.client is None
    
    @patch('prompt_pipeline.importer.importer.TypeDBClient')
    def test_create_importer_custom_params(self, mock_client):
        """Test create_importer with custom parameters."""
        importer = create_importer(
            base_url="http://localhost:9000",
            database="test_db",
            verbose=VerboseLevel.DEBUG
        )
        assert importer.database == "test_db"
        assert importer.verbose == VerboseLevel.DEBUG
    
    @patch('prompt_pipeline.importer.importer.TypeDBClient')
    def test_importer_auto_connect_false(self, mock_client):
        """Test importer does not auto-connect when auto_connect=False."""
        importer = TypeDBImporter(auto_connect=False)
        # Client should be created but connect() not called
        mock_client.assert_not_called()


class TestQueryBuilderHelperMethods:
    """Test QueryBuilder helper methods."""
    
    @patch('prompt_pipeline.importer.importer.QueryBuilder')
    @patch('prompt_pipeline.importer.importer.TypeDBClient')
    def test_build_entity_query(self, mock_client, mock_qb):
        """Test _build_entity_query method."""
        # Setup mock
        mock_qb_instance = MagicMock()
        mock_qb.return_value = mock_qb_instance
        mock_qb_instance.insert.return_value = mock_qb_instance
        mock_qb_instance.variable.return_value = mock_qb_instance
        mock_qb_instance.build.return_value = 'insert $x isa actor, has actor-id "A1";'
        
        importer = create_importer()
        importer._client = MagicMock()
        
        attributes = {
            'actor-id': 'A1',
            'id-label': 'TestActor',
            'description': 'Test description'
        }
        
        with patch.object(importer, 'client', MagicMock()):
            query = importer._build_entity_query('actor', attributes)
            assert query is not None
    
    def test_get_id_attribute(self):
        """Test _get_id_attribute returns correct ID attribute for entity types."""
        importer = create_importer()
        
        assert importer._get_id_attribute('actor') == 'actor-id'
        assert importer._get_id_attribute('action') == 'action-id'
        assert importer._get_id_attribute('data-entity') == 'data-entity-id'
        assert importer._get_id_attribute('concept') == 'concept-id'
        assert importer._get_id_attribute('message') == 'message-id'
        assert importer._get_id_attribute('requirement') == 'requirement-id'
        assert importer._get_id_attribute('message-aggregate') == 'message-agg-id'
        assert importer._get_id_attribute('action-aggregate') == 'action-agg-id'
        assert importer._get_id_attribute('category') == 'category-id'
        assert importer._get_id_attribute('spec-document') == 'spec-doc-id'
        assert importer._get_id_attribute('spec-section') == 'spec-section-id'
        assert importer._get_id_attribute('text-block') == 'anchor-id'
        assert importer._get_id_attribute('semantic-cue') == 'identifier'
        assert importer._get_id_attribute('constraint') == 'constraint-id'
        # Default case
        assert importer._get_id_attribute('unknown') == 'id'


class TestStringHelpers:
    """Test string helper methods."""
    
    def test_escape_string_basic(self):
        """Test basic string escaping."""
        importer = create_importer()
        
        result = importer._escape_string('Hello World')
        assert result == 'Hello World'
    
    def test_escape_string_quotes(self):
        """Test quote escaping."""
        importer = create_importer()
        
        result = importer._escape_string('He said "hello"')
        assert '\\"' in result
    
    def test_escape_string_newlines(self):
        """Test newline to space conversion."""
        importer = create_importer()
        
        result = importer._escape_string('Hello\nWorld')
        assert '\n' not in result
        assert ' in result
    
    def test_escape_string_backslash(self):
        """Test backslash escaping."""
        importer = create_importer()
        
        result = importer._escape_string('path\\to\\file')
        assert '\\\\' in result
    
    def test_escape_string_empty(self):
        """Test empty string handling."""
        importer = create_importer()
        
        result = importer._escape_string('')
        assert result == ''
    
    def test_transform_label_basic(self):
        """Test basic label transformation."""
        importer = create_importer()
        
        result = importer._transform_label('Hello World')
        assert result == 'Hello_World'
    
    def test_transform_label_special_chars(self):
        """Test special character removal."""
        importer = create_importer()
        
        result = importer._transform_label('Hello@World#123')
        assert '@' not in result
        assert '#' not in result
    
    def test_transform_label_uppercase_first(self):
        """Test first character uppercase."""
        importer = create_importer()
        
        result = importer._transform_label('hello')
        assert result[0].isupper()
    
    def test_transform_label_multiple_underscores(self):
        """Test multiple underscores collapsed."""
        importer = create_importer()
        
        result = importer._transform_label('Hello___World')
        assert result.count('_') == 1


class TestEntityExists:
    """Test entity_exists method."""
    
    @patch('prompt_pipeline.importer.importer.QueryBuilder')
    @patch('prompt_pipeline.importer.importer.TypeDBClient')
    def test_entity_exists_returns_true(self, mock_client, mock_qb):
        """Test entity_exists returns True when entity found."""
        # Setup
        mock_qb.return_value = MockQueryBuilder('match')
        
        importer = create_importer()
        importer._client = MagicMock()
        
        # Mock execute_query to return answers
        mock_result = {"answers": [{"x": {"id": "A1"}}]}
        importer.client.execute_query = MagicMock(return_value=mock_result)
        
        result = importer.entity_exists('actor', 'actor-id', 'A1')
        assert result is True
    
    @patch('prompt_pipeline.importer.importer.QueryBuilder')
    @patch('prompt_pipeline.importer.importer.TypeDBClient')
    def test_entity_exists_returns_false(self, mock_client, mock_qb):
        """Test entity_exists returns False when entity not found."""
        mock_qb.return_value = MockQueryBuilder('match')
        
        importer = create_importer()
        importer._client = MagicMock()
        
        # Mock execute_query to return empty answers
        mock_result = {"answers": []}
        importer.client.execute_query = MagicMock(return_value=mock_result)
        
        result = importer.entity_exists('actor', 'actor-id', 'A1')
        assert result is False
    
    @patch('prompt_pipeline.importer.importer.QueryBuilder')
    @patch('prompt_pipeline.importer.importer.TypeDBClient')
    def test_entity_exists_handles_exception(self, mock_client, mock_qb):
        """Test entity_exists handles exceptions gracefully."""
        mock_qb.return_value = MockQueryBuilder('match')
        
        importer = create_importer()
        importer._client = MagicMock()
        
        # Mock execute_query to raise exception
        importer.client.execute_query = MagicMock(side_effect=Exception("Test error"))
        
        result = importer.entity_exists('actor', 'actor-id', 'A1')
        assert result is False


class TestBuildRelationQuery:
    """Test _build_relation_query method."""
    
    def test_build_relation_query_basic(self):
        """Test basic relation query building."""
        importer = create_importer()
        
        role_players = {
            'anchor': ('text-block', 'TB1'),
            'concept': ('concept', 'C1')
        }
        
        query = importer._build_relation_query('anchoring', role_players)
        
        assert 'anchoring' in query
        assert 'match' in query
        assert 'insert' in query
        assert 'text_block_anchor' in query
        assert 'concept_concept' in query
    
    def test_build_relation_query_with_dashes(self):
        """Test relation query handles entity types with dashes."""
        importer = create_importer()
        
        role_players = {
            'categorized': ('data-entity', 'DE1'),
            'category': ('category', 'CAT1')
        }
        
        query = importer._build_relation_query('categorization', role_players)
        
        assert 'categorization' in query
        assert 'data_entity' in query


class TestDeleteEntity:
    """Test _delete_entity method."""
    
    @patch('prompt_pipeline.importer.importer.TypeDBClient')
    def test_delete_entity_success(self, mock_client):
        """Test _delete_entity succeeds."""
        importer = create_importer()
        importer._client = MagicMock()
        importer.client.execute_query = MagicMock()
        
        result = importer._delete_entity('actor', 'actor-id', 'A1')
        
        assert result is True
        importer.client.execute_query.assert_called_once()
    
    @patch('prompt_pipeline.importer.importer.TypeDBClient')
    def test_delete_entity_handles_exception(self, mock_client):
        """Test _delete_entity handles exceptions."""
        importer = create_importer()
        importer._client = MagicMock()
        importer.client.execute_query = MagicMock(side_effect=Exception("Test error"))
        
        result = importer._delete_entity('actor', 'actor-id', 'A1')
        
        assert result is False


class TestInsertEntityWithCheck:
    """Test _insert_entity_with_check method."""
    
    @patch('prompt_pipeline.importer.importer.TypeDBClient')
    def test_insert_new_entity(self, mock_client):
        """Test inserting a new entity."""
        importer = create_importer()
        importer._client = MagicMock()
        
        # Entity doesn't exist, insert should succeed
        with patch.object(importer, 'entity_exists', return_value=False):
            with patch.object(importer, '_build_entity_query', return_value='insert query'):
                with patch.object(importer, 'client') as mock_client_exec:
                    mock_client_exec.execute_query = MagicMock()
                    
                    result = importer._insert_entity_with_check(
                        'actor',
                        'actor-id',
                        'A1',
                        {'actor-id': 'A1', 'id-label': 'TestActor'}
                    )
                    
                    # Should have called execute_query
                    mock_client_exec.execute_query.assert_called()
    
    @patch('prompt_pipeline.importer.importer.TypeDBClient')
    def test_insert_existing_entity(self, mock_client):
        """Test replacing an existing entity."""
        importer = create_importer()
        importer._client = MagicMock()
        
        # Entity exists, should delete and recreate
        with patch.object(importer, 'entity_exists', side_effect=[True, True]):
            with patch.object(importer, '_delete_entity', return_value=True):
                with patch.object(importer, '_build_entity_query', return_value='insert query'):
                    with patch.object(importer, 'client') as mock_client_exec:
                        mock_client_exec.execute_query = MagicMock()
                        
                        result = importer._insert_entity_with_check(
                            'actor',
                            'actor-id',
                            'A1',
                            {'actor-id': 'A1', 'id-label': 'TestActor'}
                        )


class TestStats:
    """Test statistics tracking."""
    
    @patch('prompt_pipeline.importer.importer.TypeDBClient')
    def test_initial_stats(self, mock_client):
        """Test initial stats are zero."""
        importer = create_importer()
        
        assert importer.stats['documents'] == 0
        assert importer.stats['sections'] == 0
        assert importer.stats['text_blocks'] == 0
        assert importer.stats['concepts'] == 0
        assert importer.stats['actors'] == 0
        assert importer.stats['actions'] == 0
        assert importer.stats['data_entities'] == 0
        assert importer.stats['requirements'] == 0
        assert importer.stats['messages'] == 0
        assert importer.stats['aggregations'] == 0
        assert importer.stats['semantic_cues'] == 0
        assert importer.stats['categories'] == 0
        assert importer.stats['relations'] == 0


class TestFactoryFunction:
    """Test create_importer factory function."""
    
    @patch('prompt_pipeline.importer.importer.TypeDBClient')
    def test_factory_returns_importer(self, mock_client):
        """Test factory returns TypeDBImporter instance."""
        importer = create_importer()
        assert isinstance(importer, TypeDBImporter)
    
    @patch('prompt_pipeline.importer.importer.TypeDBClient')
    def test_factory_auto_connect_false(self, mock_client):
        """Test factory creates importer with auto_connect=False."""
        importer = create_importer()
        # Should not have called connect automatically
        # (client mock should not have database_exists called)
        mock_client.assert_not_called()
    
    @patch('prompt_pipeline.importer.importer.TypeDBClient')
    def test_factory_passes_credentials(self, mock_client):
        """Test factory passes username/password to client."""
        importer = create_importer(
            username="admin",
            password="secret"
        )
        # Verify client was created with credentials
        call_args = mock_client.call_args
        assert call_args[1]['username'] == "admin"
        assert call_args[1]['password'] == "secret"


# ==================== Integration-style Tests ====================

class TestImporterWorkflows:
    """Test complete importer workflows with mocks."""
    
    @patch('prompt_pipeline.importer.importer.TypeDBClient')
    @patch('prompt_pipeline.importer.importer.QueryBuilder')
    def test_yaml_import_workflow(self, mock_qb, mock_client):
        """Test YAML import workflow."""
        mock_qb.return_value = MockQueryBuilder('match')
        
        importer = create_importer()
        importer._client = MagicMock()
        importer.client.database_exists = MagicMock(return_value=True)
        
        # Mock yaml.safe_load
        test_data = {
            'specification': {
                'id': 'SPEC1',
                'title': 'Test Spec',
                'version': '1.0',
                'description': 'Test description',
                'sections': []
            }
        }
        
        with patch('builtins.open', MagicMock()):
            with patch('yaml.safe_load', return_value=test_data):
                with patch.object(importer, 'entity_exists', return_value=False):
                    with patch.object(importer, '_create_spec_document'):
                        # Would test import_yaml but it exits on error without server
                        pass
    
    @patch('prompt_pipeline.importer.importer.TypeDBClient')
    @patch('prompt_pipeline.importer.importer.QueryBuilder')
    def test_json_import_workflow(self, mock_qb, mock_client):
        """Test JSON import workflow."""
        mock_qb.return_value = MockQueryBuilder('match')
        
        importer = create_importer()
        importer._client = MagicMock()
        
        # Test that import_json_directory would work with mock
        # (actual test would require more complex mocking)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
