"""Unit tests for TypeDBClient module

These tests use mocking to avoid requiring an actual TypeDB server.
"""

import pytest
import requests
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from ..client import TypeDBClient, TransactionType, TransactionContext
from ..exceptions import (
    TypeDBConnectionError, TypeDBAuthenticationError,
    TypeDBQueryError, TypeDBServerError, TypeDBValidationError
)


class TestTypeDBClient:
    """Test TypeDBClient class."""
    
    def test_init_without_auth(self):
        """Test initialization without authentication."""
        client = TypeDBClient(base_url="http://localhost:8000")
        assert client.base_url == "http://localhost:8000"
        assert client.username is None
        assert client.password is None
    
    def test_init_with_auth(self):
        """Test initialization with authentication."""
        with patch.object(TypeDBClient, '_authenticate'):
            client = TypeDBClient(
                base_url="http://localhost:8000",
                username="admin",
                password="password"
            )
            assert client.username == "admin"
            assert client.password == "password"
    
    @patch('tools.typedb_v3_client.client.requests.Session')
    def test_authenticate_success(self, mock_session_class):
        """Test successful authentication."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        mock_response = Mock()
        mock_response.json.return_value = {"token": "test_token"}
        mock_response.raise_for_status = Mock()
        mock_session.post.return_value = mock_response
        
        client = TypeDBClient(
            base_url="http://localhost:8000",
            username="admin",
            password="password"
        )
        
        assert client._token == "test_token"
    
    @patch('tools.typedb_v3_client.client.requests.Session')
    def test_authenticate_failure(self, mock_session_class):
        """Test authentication failure."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        mock_session.post.side_effect = requests.exceptions.RequestException("Connection failed")
        
        with pytest.raises(TypeDBConnectionError):
            TypeDBClient(
                base_url="http://localhost:8000",
                username="admin",
                password="password"
            )
    
    @patch('tools.typedb_v3_client.client.requests.Session')
    def test_authenticate_no_token(self, mock_session_class):
        """Test authentication with no token in response."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = Mock()
        mock_session.post.return_value = mock_response
        
        with pytest.raises(TypeDBAuthenticationError):
            TypeDBClient(
                base_url="http://localhost:8000",
                username="admin",
                password="password"
            )
    
    def test_get_headers_no_auth(self):
        """Test _get_headers without authentication."""
        client = TypeDBClient(base_url="http://localhost:8000")
        headers = client._get_headers()
        assert headers["Content-Type"] == "application/json"
        assert "Authorization" not in headers
    
    def test_get_headers_with_auth(self):
        """Test _get_headers with authentication."""
        with patch.object(TypeDBClient, '_authenticate'):
            client = TypeDBClient(
                base_url="http://localhost:8000",
                username="admin",
                password="password"
            )
            client._token = "test_token"
            headers = client._get_headers()
            assert headers["Content-Type"] == "application/json"
            assert headers["Authorization"] == "Bearer test_token"
    
    @patch('tools.typedb_v3_client.client.requests.Session')
    def test_list_databases(self, mock_session_class):
        """Test list_databases."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        mock_response = Mock()
        mock_response.json.return_value = {"databases": ["db1", "db2"]}
        mock_response.raise_for_status = Mock()
        mock_session.get.return_value = mock_response
        
        client = TypeDBClient(base_url="http://localhost:8000")
        databases = client.list_databases()
        assert databases == ["db1", "db2"]
    
    @patch('tools.typedb_v3_client.client.requests.Session')
    def test_create_database_success(self, mock_session_class):
        """Test create_database success."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_session.post.return_value = mock_response
        
        client = TypeDBClient(base_url="http://localhost:8000")
        client.create_database("test_db")
        
        # Should not raise
    
    @patch('tools.typedb_v3_client.client.requests.Session')
    def test_create_database_already_exists(self, mock_session_class):
        """Test create_database when database already exists."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        mock_response = Mock()
        mock_response.status_code = 409
        http_error = requests.exceptions.HTTPError()
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        mock_response.json.return_value = {"message": "Database already exists"}
        mock_session.post.return_value = mock_response
        
        client = TypeDBClient(base_url="http://localhost:8000")
        
        with pytest.raises(TypeDBValidationError):
            client.create_database("test_db")
    
    @patch('tools.typedb_v3_client.client.requests.Session')
    def test_delete_database_success(self, mock_session_class):
        """Test delete_database success."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_session.delete.return_value = mock_response
        
        client = TypeDBClient(base_url="http://localhost:8000")
        client.delete_database("test_db")
        
        # Should not raise
    
    @patch('tools.typedb_v3_client.client.requests.Session')
    def test_delete_database_not_found(self, mock_session_class):
        """Test delete_database when database doesn't exist."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        mock_response = Mock()
        mock_response.status_code = 404
        http_error = requests.exceptions.HTTPError()
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        mock_response.json.return_value = {"message": "Database not found"}
        mock_session.delete.return_value = mock_response
        
        client = TypeDBClient(base_url="http://localhost:8000")
        
        with pytest.raises(TypeDBValidationError):
            client.delete_database("test_db")
    
    @patch('tools.typedb_v3_client.client.requests.Session')
    def test_database_exists_true(self, mock_session_class):
        """Test database_exists returns True."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        mock_response = Mock()
        mock_response.json.return_value = {"databases": ["test_db", "other_db"]}
        mock_response.raise_for_status = Mock()
        mock_session.get.return_value = mock_response
        
        client = TypeDBClient(base_url="http://localhost:8000")
        assert client.database_exists("test_db") is True
    
    @patch('tools.typedb_v3_client.client.requests.Session')
    def test_database_exists_false(self, mock_session_class):
        """Test database_exists returns False."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        mock_response = Mock()
        mock_response.json.return_value = {"databases": ["other_db"]}
        mock_response.raise_for_status = Mock()
        mock_session.get.return_value = mock_response
        
        client = TypeDBClient(base_url="http://localhost:8000")
        assert client.database_exists("test_db") is False
    
    @patch('tools.typedb_v3_client.client.requests.Session')
    def test_execute_query_read(self, mock_session_class):
        """Test execute_query for READ transaction."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        mock_response = Mock()
        mock_response.json.return_value = {"answers": []}
        mock_response.raise_for_status = Mock()
        mock_session.post.return_value = mock_response
        
        client = TypeDBClient(base_url="http://localhost:8000")
        result = client.execute_query(
            "test_db",
            "match $x isa actor; fetch $x;",
            TransactionType.READ
        )
        
        assert result == {"answers": []}
        
        # Check the request was made with correct parameters
        call_args = mock_session.post.call_args
        assert call_args[1]["json"]["transaction_type"] == "read"
        assert call_args[1]["json"]["query"] == "match $x isa actor; fetch $x;"
    
    @patch('tools.typedb_v3_client.client.requests.Session')
    def test_execute_query_write(self, mock_session_class):
        """Test execute_query for WRITE transaction."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        mock_response = Mock()
        mock_response.json.return_value = {"answers": []}
        mock_response.raise_for_status = Mock()
        mock_session.post.return_value = mock_response
        
        client = TypeDBClient(base_url="http://localhost:8000")
        result = client.execute_query(
            "test_db",
            "insert $a isa actor, has actor-id \"A1\";",
            TransactionType.WRITE
        )
        
        assert result == {"answers": []}
        
        # Check the request was made with correct parameters
        call_args = mock_session.post.call_args
        assert call_args[1]["json"]["transaction_type"] == "write"
    
    @patch('tools.typedb_v3_client.client.requests.Session')
    def test_execute_query_http_error(self, mock_session_class):
        """Test execute_query with HTTP error."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        mock_response = Mock()
        mock_response.status_code = 500
        http_error = requests.exceptions.HTTPError("Server error")
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        mock_response.json.return_value = {"message": "Query failed"}
        mock_session.post.return_value = mock_response
        
        client = TypeDBClient(base_url="http://localhost:8000")
        
        with pytest.raises(TypeDBQueryError):
            client.execute_query("test_db", "invalid query")
    
    @patch('tools.typedb_v3_client.client.requests.Session')
    def test_execute_transaction(self, mock_session_class):
        """Test execute_transaction."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        mock_response = Mock()
        mock_response.json.return_value = {"results": [{"answer": 1}, {"answer": 2}]}
        mock_response.raise_for_status = Mock()
        mock_session.post.return_value = mock_response
        
        client = TypeDBClient(base_url="http://localhost:8000")
        operations = [
            {"query": "insert $a isa actor, has actor-id \"A1\";"},
            {"query": "insert $a isa actor, has actor-id \"A2\";"}
        ]
        result = client.execute_transaction(
            "test_db",
            TransactionType.WRITE,
            operations
        )
        
        assert result == {"results": [{"answer": 1}, {"answer": 2}]}
        
        # Check the request was made with correct parameters
        call_args = mock_session.post.call_args
        assert call_args[1]["json"]["transaction_type"] == "write"
        assert call_args[1]["json"]["operations"] == operations
    
    @patch('tools.typedb_v3_client.client.requests.Session')
    def test_execute_queries(self, mock_session_class):
        """Test execute_queries helper."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        mock_response = Mock()
        mock_response.json.return_value = {"answers": []}
        mock_response.raise_for_status = Mock()
        mock_session.post.return_value = mock_response
        
        client = TypeDBClient(base_url="http://localhost:8000")
        results = client.execute_queries(
            "test_db",
            "insert $a isa actor, has actor-id \"A1\";",
            "insert $a isa actor, has actor-id \"A2\";",
            transaction_type=TransactionType.WRITE
        )
        
        # Check the request was made with correct parameters
        call_args = mock_session.post.call_args
        operations = call_args[1]["json"]["operations"]
        assert len(operations) == 2
        assert operations[0]["query"] == "insert $a isa actor, has actor-id \"A1\";"
        assert operations[1]["query"] == "insert $a isa actor, has actor-id \"A2\";"
    
    def test_with_transaction(self):
        """Test with_transaction returns TransactionContext."""
        client = TypeDBClient(base_url="http://localhost:8000")
        ctx = client.with_transaction("test_db", TransactionType.WRITE)
        assert isinstance(ctx, TransactionContext)
        assert ctx.client is client
        assert ctx.database == "test_db"
        assert ctx.transaction_type == TransactionType.WRITE
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.read_text')
    @patch('tools.typedb_v3_client.client.requests.Session')
    def test_load_schema(self, mock_session_class, mock_read_text, mock_exists):
        """Test load_schema."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        mock_exists.return_value = True
        mock_read_text.return_value = "define actor sub entity;"
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_session.post.return_value = mock_response
        
        client = TypeDBClient(base_url="http://localhost:8000")
        schema_path = Path("/path/to/schema.tql")
        client.load_schema("test_db", schema_path)
        
        # Should not raise
    
    @patch('pathlib.Path.exists')
    def test_load_schema_file_not_found(self, mock_exists):
        """Test load_schema when file doesn't exist."""
        mock_exists.return_value = False
        
        client = TypeDBClient(base_url="http://localhost:8000")
        schema_path = Path("/path/to/schema.tql")
        
        with pytest.raises(FileNotFoundError):
            client.load_schema("test_db", schema_path)
    
    @patch('tools.typedb_v3_client.client.requests.Session')
    def test_clear_database(self, mock_session_class):
        """Test clear_database."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        mock_response = Mock()
        mock_response.json.return_value = {"answers": []}
        mock_response.raise_for_status = Mock()
        mock_session.post.return_value = mock_response
        
        client = TypeDBClient(base_url="http://localhost:8000")
        client.clear_database("test_db")
        
        # Check the delete query was called
        assert mock_session.post.called
    
    @patch('tools.typedb_v3_client.client.requests.Session')
    def test_close(self, mock_session_class):
        """Test close method."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        client = TypeDBClient(base_url="http://localhost:8000")
        client.close()
        
        mock_session.close.assert_called_once()


class TestTransactionContext:
    """Test TransactionContext class."""
    
    def test_execute(self):
        """Test execute adds query to operations."""
        client = Mock(spec=TypeDBClient)
        ctx = TransactionContext(client, "test_db", TransactionType.WRITE)
        
        ctx.execute("insert $a isa actor, has actor-id \"A1\";")
        
        assert len(ctx.operations) == 1
        assert ctx.operations[0]["query"] == "insert $a isa actor, has actor-id \"A1\";"
    
    @patch('tools.typedb_v3_client.query_builder.QueryBuilder')
    def test_execute_builder(self, mock_query_builder):
        """Test execute_builder adds query from QueryBuilder."""
        client = Mock(spec=TypeDBClient)
        ctx = TransactionContext(client, "test_db", TransactionType.WRITE)
        
        builder = Mock()
        builder.get_tql.return_value = "insert $a isa actor, has actor-id \"A1\";"
        
        ctx.execute_builder(builder)
        
        assert len(ctx.operations) == 1
        assert ctx.operations[0]["query"] == "insert $a isa actor, has actor-id \"A1\";"
    
    def test_execute_builder_type_error(self):
        """Test execute_builder with non-QueryBuilder raises TypeError."""
        client = Mock(spec=TypeDBClient)
        ctx = TransactionContext(client, "test_db", TransactionType.WRITE)
        
        with pytest.raises(TypeError):
            ctx.execute_builder("not a builder")
    
    def test_context_manager(self):
        """Test TransactionContext as context manager."""
        client = Mock(spec=TypeDBClient)
        ctx = TransactionContext(client, "test_db", TransactionType.WRITE)
        
        with ctx as tx:
            tx.execute("insert $a isa actor, has actor-id \"A1\";")
        
        # Should execute transaction on exit
        client.execute_transaction.assert_called_once()
        
        # Check that operations were passed
        call_args = client.execute_transaction.call_args
        assert call_args[0][0] == "test_db"
        assert call_args[0][1] == TransactionType.WRITE
        assert len(call_args[0][2]) == 1
    
    def test_context_manager_empty(self):
        """Test TransactionContext with no operations doesn't call execute_transaction."""
        client = Mock(spec=TypeDBClient)
        ctx = TransactionContext(client, "test_db", TransactionType.WRITE)
        
        with ctx:
            pass  # No operations added
        
        # Should not call execute_transaction
        client.execute_transaction.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
