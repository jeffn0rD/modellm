#!/usr/bin/env python3
"""Test that imports work correctly."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from tools.typedb_v3_client import TypeDBClient, TransactionType, TransactionContext
    print("SUCCESS: All imports working!")
    print(f"TypeDBClient: {TypeDBClient}")
    print(f"TransactionType: {TransactionType}")
    print(f"TransactionContext: {TransactionContext}")
except ImportError as e:
    print(f"FAILED: Import error - {e}")
    import traceback
    traceback.print_exc()