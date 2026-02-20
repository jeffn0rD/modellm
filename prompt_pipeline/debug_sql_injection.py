#!/usr/bin/env python3
"""Debug the SQL injection test failure."""

from typedb_client3 import validate_credentials
from typedb_client3 import TypeDBValidationError
import re

def debug_validation():
    test_cases = [
        'admin"; --',
        "admin' OR '1'='1",
        'admin union select',
        'admin; DROP TABLE users;',
        '--',
    ]
    
    for test_input in test_cases:
        print(f"\nTesting: {repr(test_input)}")
        
        # Check each pattern individually
        injection_patterns = [
            r'union\s+select',  # SQL-style
            r'select\s+.*\s+from',
            r'insert\s+into',
            r'drop\s+table',
            r'delete\s+from',
            r'--',  # Comment injection (both SQL and TypeQL)
            r'".*";',  # TypeQL command separator
            r'\$.*isa\s+',  # Variable injection
            r'match\s+\$.*;',  # Match injection
            r'/\*.*\*/',  # Block comment
            r'javascript:',  # XSS
            r'<script',  # XSS
            r'onerror=',  # XSS
            r'onload=',  # XSS
        ]
        
        combined = (test_input + 'password123').lower()
        print(f"Combined: {repr(combined)}")
        
        any_match = False
        for pattern_str in injection_patterns:
            pattern_compiled = re.compile(pattern_str, re.IGNORECASE)
            match = pattern_compiled.search(combined)
            if match:
                print(f"  MATCH {repr(pattern_str)}: {match.group()}")
                any_match = True
        
        if not any_match:
            print("  NO MATCHES FOUND")
        
        try:
            validate_credentials(test_input, 'password123')
            print("  VALIDATION PASSED - will fail test")
        except TypeDBValidationError as e:
            print(f"  VALIDATION FAILED - test should pass: {e}")

if __name__ == "__main__":
    debug_validation()