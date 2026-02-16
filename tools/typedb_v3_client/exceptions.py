"""TypeDB v3 Client Library - Exceptions"""

from typing import Optional


class TypeDBError(Exception):
    """Base exception for TypeDB errors."""
    pass


class TypeDBConnectionError(TypeDBError):
    """Connection-related errors."""
    pass


class TypeDBAuthenticationError(TypeDBError):
    """Authentication-related errors."""
    pass


class TypeDBQueryError(TypeDBError):
    """Query execution errors."""
    
    def __init__(self, message: str, query: str = None, details: dict = None):
        super().__init__(message)
        self.query = query
        self.details = details or {}


class TypeDBServerError(TypeDBError):
    """Server-side errors."""
    pass


class TypeDBValidationError(TypeDBError):
    """Validation errors (e.g., entity already exists)."""
    pass
