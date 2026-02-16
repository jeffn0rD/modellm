#!/usr/bin/env python3
"""
Script to fix import paths in test files.
"""

import re
import os
from pathlib import Path

def fix_test_file(filename):
    """Fix import paths in a test file."""
    print(f"Fixing {filename}...")
    
    with open(filename, 'r') as f:
        content = f.read()
    
    # Add sys.path setup at the beginning
    project_root_str = "project_root = Path(__file__).parent.parent.parent.parent\nif str(project_root) not in sys.path:\n    sys.path.insert(0, str(project_root))"
    
    # Check if file already has sys.path setup
    if 'sys.path.insert' not in content:
        # Find the import section and replace it
        if '# Import directly from the typedb_v3_client package' in content:
            # Replace the old import structure
            new_import_section = '''import sys
from pathlib import Path

# Add project root to Python path for absolute imports
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import from tools.typedb_v3_client package
from tools.typedb_v3_client import TypeDBClient, TransactionType, TransactionContext
from tools.typedb_v3_client.exceptions import (
    TypeDBConnectionError, TypeDBAuthenticationError,
    TypeDBQueryError, TypeDBServerError, TypeDBValidationError
)'''
            
            # Find the import section
            start_marker = '''# Import directly from the typedb_v3_client package'''
            end_marker = '''class Test'''
            
            start_idx = content.find(start_marker)
            end_idx = content.find(end_marker)
            
            if start_idx != -1 and end_idx != -1:
                old_import_section = content[start_idx:end_idx]
                content = content.replace(old_import_section, new_import_section + '\n\n')
                print(f"Replaced import section in {filename}")
    
    # Replace tools.typedb_v3_client with typedb_v3_client in patch decorators
    content = content.replace("@patch('tools.typedb_v3_client.client.requests.Session')", 
                             "@patch('typedb_v3_client.client.requests.Session')")
    content = content.replace('@patch("tools.typedb_v3_client.client.requests.Session")', 
                             '@patch("typedb_v3_client.client.requests.Session")')
    content = content.replace('@patch("tools.typedb_v3_client.query_builder.QueryBuilder")', 
                             '@patch("typedb_v3_client.query_builder.QueryBuilder")')
    
    with open(filename, 'w') as f:
        f.write(content)
    
    print(f"Fixed {filename}")

# Fix all test files
for filename in ['test_client.py', 'test_entities.py', 'test_entity_manager.py', 'test_query_builder.py', 'test_query_patterns.py', 'security_tests.py', 'performance_tests.py']:
    if os.path.exists(filename):
        fix_test_file(filename)