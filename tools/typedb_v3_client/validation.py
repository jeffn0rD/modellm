"""Input validation functions for TypeDB client.

Provides validation for:
- Base URL validation
- Credential validation
- Timeout validation
- Operation timeout validation
"""

import re
from urllib.parse import urlparse
from typing import Any, Dict, List, Optional

from .exceptions import TypeDBValidationError


# ============================================================================
# Connection Pooling Configuration
# ============================================================================

# Default connection pool settings
DEFAULT_POOL_CONNECTIONS = 50
DEFAULT_POOL_MAXSIZE = 100
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 0.3
DEFAULT_STATUS_FORCE_LIST = [500, 502, 503, 504]


# ============================================================================
# Operation-Specific Timeout Configuration
# ============================================================================

# Default timeout configuration for different operation types
DEFAULT_TIMEOUTS = {
    'authentication': 10,
    'read_operation': 30,
    'write_operation': 60,
    'schema_operation': 120,
    'transaction': 180,
    'health_check': 5
}

# Timeout validation limits
MIN_TIMEOUT = 1
MAX_TIMEOUT = 300  # 5 minutes


# ============================================================================
# URL Validation
# ============================================================================

def validate_base_url(url: str) -> str:
    """Validate and normalize the base URL.
    
    Args:
        url: The URL string to validate
        
    Returns:
        Normalized URL string
        
    Raises:
        TypeDBValidationError: If URL is invalid
    """
    if not url:
        raise TypeDBValidationError("Base URL cannot be empty")
    
    # Check for malicious protocol patterns first
    dangerous_patterns = [
        r'javascript:',  # XSS
        r'<script',  # XSS
        r'data:',  # Data URLs
        r'file://',  # File access
        r'ftp://',  # FTP access
        r'dict://',  # Protocol attacks
        r'ldap://',  # Protocol attacks
        r'gopher://',  # Protocol attacks
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, url, re.IGNORECASE):
            raise TypeDBValidationError(f"Invalid URL protocol/pattern: {pattern}")
    
    # Add scheme if missing
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    
    parsed = urlparse(url)
    
    # Validate scheme
    if parsed.scheme not in ('http', 'https'):
        raise TypeDBValidationError(f"Invalid URL scheme: {parsed.scheme}. Must be 'http' or 'https'")
    
    # Validate hostname
    if not parsed.hostname:
        raise TypeDBValidationError("Invalid URL: no hostname specified")
    
    # Check for injection patterns in hostname
    injection_patterns = [
        r'[\x00-\x1f\x7f]',  # Control characters
        r'[<>"\']',  # HTML/script characters
    ]
    for pattern in injection_patterns:
        if re.search(pattern, parsed.hostname):
            raise TypeDBValidationError("Invalid characters in hostname")
    
    # Validate port range (handle potential parsing errors)
    try:
        if parsed.port is not None:
            if parsed.port < 1 or parsed.port > 65535:
                raise TypeDBValidationError(f"Invalid port number: {parsed.port}. Must be between 1 and 65535")
    except ValueError:
        raise TypeDBValidationError("Invalid port format in URL")
    
    # Check path for injection patterns
    if parsed.path:
        path_injection = ['../', '\\x', '<script', 'javascript:', 'onerror=']
        for pattern in path_injection:
            if pattern in parsed.path.lower():
                raise TypeDBValidationError(f"Invalid path pattern: {pattern}")
    
    return url.rstrip('/')


# ============================================================================
# Credential Validation
# ============================================================================

def validate_credentials(username: Optional[str], password: Optional[str]) -> None:
    """Validate username and password credentials.
    
    Args:
        username: The username to validate
        password: The password to validate
        
    Raises:
        TypeDBValidationError: If credentials are invalid
    """
    # If neither is provided, that's ok (anonymous access)
    if username is None and password is None:
        return
    
    # If one is provided without the other, that's invalid
    if username is None or password is None:
        raise TypeDBValidationError("Both username and password must be provided together")
    
    # Validate length
    if len(username) < 1 or len(username) > 128:
        raise TypeDBValidationError("Username must be between 1 and 128 characters")
    
    if len(password) < 1 or len(password) > 128:
        raise TypeDBValidationError("Password must be between 1 and 128 characters")
    
    # Check for TypeQL injection patterns (and general injection attempts)
    # Includes XSS patterns in the same check to avoid duplication
    injection_patterns = [
        r'union\s+select',  # SQL-style
        r'select\s+.*\s+from',
        r'insert\s+into',
        r'drop\s+table',
        r'delete\s+from',
        r'or\s+.*=.*',  # Logical OR injection
        r'\'.*=.*\'',  # Quote-based injection
        r'--',  # Comment injection (both SQL and TypeQL)
        r'".*";',  # TypeQL command separator
        r'\$.*isa\s+',  # Variable injection
        r'match\s+\$.*;',  # Match injection
        r'/\*.*\*/',  # Block comment
        r'javascript:',  # XSS
        r'<script',  # XSS
        r'onerror=',  # XSS
        r'onload=',  # XSS
        r'`.*`',  # Backtick injection
        r'\|',  # Command pipes
        r';.*;',  # Multiple statements
    ]
    
    combined = (username + password).lower()
    for pattern in injection_patterns:
        if re.search(pattern, combined, re.IGNORECASE):
            raise TypeDBValidationError("Invalid characters in credentials")


# ============================================================================
# Timeout Validation
# ============================================================================

def validate_timeout(timeout: Any) -> int:
    """Validate and normalize timeout value.
    
    Args:
        timeout: The timeout value to validate (can be int or float)
        
    Returns:
        Validated timeout as integer
        
    Raises:
        TypeDBValidationError: If timeout is invalid
    """
    # Allow None to use default
    if timeout is None:
        return 30
    
    # Try to convert to int
    try:
        timeout = int(timeout)
    except (ValueError, TypeError):
        raise TypeDBValidationError(f"Timeout must be a number, got {type(timeout).__name__}")
    
    # Validate range
    min_timeout = 1
    max_timeout = 300  # 5 minutes
    
    if timeout < min_timeout:
        raise TypeDBValidationError(f"Timeout must be at least {min_timeout} seconds")
    
    if timeout > max_timeout:
        raise TypeDBValidationError(f"Timeout cannot exceed {max_timeout} seconds")
    
    return timeout


def validate_operation_timeouts(timeouts: Dict[str, int]) -> Dict[str, int]:
    """Validate operation-specific timeouts.
    
    Args:
        timeouts: Dictionary of operation name to timeout in seconds
        
    Returns:
        Validated timeouts dictionary
        
    Raises:
        TypeDBValidationError: If any timeout is invalid
    """
    validated = DEFAULT_TIMEOUTS.copy()
    
    for key, value in timeouts.items():
        if key not in DEFAULT_TIMEOUTS:
            raise TypeDBValidationError(f"Unknown timeout operation: {key}")
        
        try:
            timeout_value = int(value)
        except (ValueError, TypeError):
            raise TypeDBValidationError(f"Timeout must be a number for {key}")
        
        if timeout_value < MIN_TIMEOUT or timeout_value > MAX_TIMEOUT:
            raise TypeDBValidationError(
                f"Timeout for {key} must be between {MIN_TIMEOUT} and {MAX_TIMEOUT} seconds"
            )
        
        validated[key] = timeout_value
    
    return validated


# ============================================================================
# Session Configuration
# ============================================================================

def create_optimized_session(
    pool_connections: int = DEFAULT_POOL_CONNECTIONS,
    pool_maxsize: int = DEFAULT_POOL_MAXSIZE,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    status_forcelist: List[int] = None
):
    """Create an optimized requests Session with connection pooling.
    
    Args:
        pool_connections: Number of connection pools to cache
        pool_maxsize: Maximum number of connections per host
        max_retries: Maximum number of retry attempts
        backoff_factor: Exponential backoff factor
        status_forcelist: HTTP status codes to retry on
        
    Returns:
        Configured requests Session with connection pooling
    """
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    
    if status_forcelist is None:
        status_forcelist = DEFAULT_STATUS_FORCE_LIST
    
    # Create retry strategy
    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"]
    )
    
    # Create HTTP adapter with connection pooling
    adapter = HTTPAdapter(
        pool_connections=pool_connections,
        pool_maxsize=pool_maxsize,
        max_retries=retry_strategy
    )
    
    # Create session and mount adapter
    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session
