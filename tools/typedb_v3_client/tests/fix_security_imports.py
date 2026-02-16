#!/usr/bin/env python3
"""Fix security_tests.py imports."""

with open('security_tests.py', 'r') as f:
    content = f.read()

# Add sys.path setup at the very beginning
sys_path_setup = '''import sys
from pathlib import Path

# Add project root to Python path for absolute imports
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
'''

# Replace the tools imports
old_import_section = '''import pytest
from tools.typedb_v3_client import (
    TypeDBClient, Actor, Action, Message, SecureTokenManager,
    validate_base_url, validate_credentials, validate_timeout,
    validate_operation_timeouts
)
from tools.typedb_v3_client.exceptions import TypeDBValidationError'''

new_import_section = '''import pytest
from tools.typedb_v3_client import (
    TypeDBClient, Actor, Action, Message, SecureTokenManager,
    validate_base_url, validate_credentials, validate_timeout,
    validate_operation_timeouts
)
from tools.typedb_v3_client.exceptions import TypeDBValidationError'''

# Replace the import section
content = content.replace(old_import_section, sys_path_setup + new_import_section)

# Fix patch decorators
content = content.replace("@patch('tools.typedb_v3_client.client.requests.Session')", 
                         "@patch('typedb_v3_client.client.requests.Session')")
content = content.replace('@patch("tools.typedb_v3_client.client.requests.Session")', 
                         '@patch("typedb_v3_client.client.requests.Session")')

with open('security_tests.py', 'w') as f:
    f.write(content)

print("Fixed security_tests.py imports")