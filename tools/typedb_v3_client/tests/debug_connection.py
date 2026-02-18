#!/usr/bin/env python3
"""Debug the TypeDB client connection to identify the actual issue."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from typedb_v3_client import TypeDBClient
from typedb_v3_client.exceptions import TypeDBConnectionError, TypeDBAuthenticationError

def test_connection():
    """Test connection to TypeDB server."""
    client = None
    try:
        print("Creating TypeDB client...")
        client = TypeDBClient(
            base_url='http://localhost:8000',
            username='admin', 
            password='password'
        )
        
        print("Testing list_databases...")
        databases = client.list_databases()
        print(f"List databases successful: {databases}")
        
        # Test database creation
        test_db = "test_debug_connection"
        print(f"Testing create_database '{test_db}'...")
        client.create_database(test_db)
        print("Create database successful")
        
        # Test database exists
        print(f"Testing database_exists '{test_db}'...")
        exists = client.database_exists(test_db)
        print(f"Database exists check: {exists}")
        
        # Cleanup
        print(f"Cleaning up database '{test_db}'...")
        client.delete_database(test_db)
        print("Delete database successful")
        
        return True
        
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if client:
            print("Closing client...")
            client.close()

if __name__ == "__main__":
    success = test_connection()
    exit(0 if success else 1)