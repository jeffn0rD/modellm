#!/usr/bin/env python3
"""Debug validation functions."""

from typedb_client3 import validate_credentials
from typedb_client3 import TypeDBValidationError
import re

def test_validation() -> None:
    """Test SQL injection validation patterns.
    
    This function tests various SQL injection patterns to ensure
    they are properly detected by the validation logic.
    """
    malicious_input = 'admin"; --'
    
    print(f"Testing input: {repr(malicious_input)}")
    print("SQL Patterns:")
    
    sql_patterns = [
        r'union\s+select',
        r'select\s+.*\s+from',
        r'insert\s+into',
        r'drop\s+table',
        r'delete\s+from',
        r'--',  # SQL comment
        r'/\*.*\*/',  # Block comment
    ]
    
    combined = (malicious_input + 'password123').lower()
    print(f"Combined: {repr(combined)}")
    
    for pattern in sql_patterns:
        match = re.search(pattern, combined, re.IGNORECASE)
        print(f"  Pattern {repr(pattern)}: {match is not None}")
        if match:
            print(f"    Match: {match.group()}")
    
    try:
        validate_credentials(malicious_input, 'password123')
        print("Validation passed - NOT EXPECTED!")
    except TypeDBValidationError as e:
        print(f"Validation failed as expected: {e}")

if __name__ == "__main__":
    test_validation()