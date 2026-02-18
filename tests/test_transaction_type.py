"""Unit tests for TransactionType enum.

Tests:
- READ and WRITE enum values
- .value property
- String representation
"""

import pytest
from typedb_client3 import TransactionType


@pytest.mark.unit
class TestTransactionType:
    """Tests for TransactionType enum."""
    
    def test_read_enum_value(self):
        """Test READ enum has correct value."""
        assert TransactionType.READ.value == "read"
    
    def test_write_enum_value(self):
        """Test WRITE enum has correct value."""
        assert TransactionType.WRITE.value == "write"
    
    def test_enum_has_two_values(self):
        """Test enum has exactly two values."""
        values = list(TransactionType)
        assert len(values) == 2
    
    def test_enum_from_string(self):
        """Test creating enum from string."""
        assert TransactionType("read") == TransactionType.READ
        assert TransactionType("write") == TransactionType.WRITE
    
    def test_enum_from_invalid_string_raises_error(self):
        """Test invalid string raises ValueError."""
        with pytest.raises(ValueError):
            TransactionType("invalid")
    
    def test_enum_repr(self):
        """Test enum string representation."""
        assert "READ" in repr(TransactionType.READ)
        assert "read" in repr(TransactionType.READ)
