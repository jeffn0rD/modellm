"""Pytest configuration for TypeDB v3 client tests.

This file ensures that the project root is added to the Python path
so that tests can import the typedb_v3_client module correctly.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Also add tools directory to path
tools_dir = Path(__file__).parent.parent
sys.path.insert(0, str(tools_dir))
