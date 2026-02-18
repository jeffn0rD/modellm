"""Authentication module for TypeDB client.

Provides:
- SecureTokenManager: Fernet encryption for JWT token storage
- Token caching and access logging
"""

import base64
import secrets
import time
from typing import Any, Dict, List, Optional

from cryptography.fernet import Fernet

from .exceptions import TypeDBAuthenticationError


class SecureTokenManager:
    """Secure token manager with Fernet encryption for JWT storage.
    
    This class provides secure storage of JWT tokens using Fernet symmetric
    encryption. Each token encryption uses a unique initialization vector (IV),
    preventing pattern analysis in stored tokens.
    
    Attributes:
        encryption_key: bytes - Fernet encryption key
        cipher: Fernet - Cipher instance for encrypt/decrypt
        token_access_log: List[Dict] - Audit log for token access
    """
    
    def __init__(self) -> None:
        """Initialize the secure token manager with a new encryption key."""
        self._encryption_key: bytes = Fernet.generate_key()
        self._cipher = Fernet(self._encryption_key)
        self._token_access_log: List[Dict[str, Any]] = []
        self._token_cache: Optional[str] = None
        self._token_cache_time: Optional[float] = None
        self._token_cache_timeout: float = 300  # 5 minutes default
    
    @property
    def encryption_key(self) -> bytes:
        """Get the encryption key (for storage/external use)."""
        return self._encryption_key
    
    def store_token(self, token: str) -> str:
        """Encrypt and store a JWT token.
        
        Args:
            token: The JWT token string to encrypt
            
        Returns:
            Encrypted token string (safe to store)
        """
        # Generate a random salt for this encryption
        salt = secrets.token_bytes(16)
        
        # Encrypt the token with the salt prepended
        token_bytes = token.encode('utf-8')
        encrypted = self._cipher.encrypt(token_bytes)
        encrypted_with_salt = salt + encrypted
        
        # Encode to base64 for storage (using base64 module)
        encrypted_b64 = base64.b64encode(encrypted_with_salt).decode('utf-8')
        
        # Log the token storage (don't expose token length for security)
        self._log_access("store", 0)
        
        # Cache the decrypted token for performance
        self._token_cache = token
        self._token_cache_time = time.time()
        
        return encrypted_b64
    
    def retrieve_token(self, encrypted_token: str) -> str:
        """Decrypt and retrieve a JWT token.
        
        Args:
            encrypted_token: The encrypted token string
            
        Returns:
            Decrypted JWT token string
        """
        # Check cache first
        if self._token_cache and self._token_cache_time:
            if time.time() - self._token_cache_time < self._token_cache_timeout:
                self._log_access("cache_hit", 0)
                return self._token_cache
        
        # Decode from base64
        try:
            encrypted_bytes = base64.b64decode(encrypted_token.encode('utf-8'))
            # Salt is unused but was part of the original format
            salt = encrypted_bytes[:16]
            encrypted = encrypted_bytes[16:]
            
            # Decrypt the token
            decrypted = self._cipher.decrypt(encrypted)
            token = decrypted.decode('utf-8')
            
            # Cache for future use
            self._token_cache = token
            self._token_cache_time = time.time()
            
            self._log_access("retrieve", 0)
            
            return token
        except Exception as e:
            raise TypeDBAuthenticationError(f"Failed to decrypt token: {e}")
    
    def clear_memory(self) -> None:
        """Clear cached token from memory.
        
        This should be called when the token is no longer needed
        to prevent memory exposure.
        """
        self._token_cache = None
        self._token_cache_time = None
        self._log_access("clear", 0)
    
    def rotate_key(self) -> bytes:
        """Rotate to a new encryption key.
        
        WARNING: This invalidates all previously encrypted tokens.
        Only use this when the token storage is also being updated.
        
        Returns:
            New encryption key
        """
        self._encryption_key = Fernet.generate_key()
        self._cipher = Fernet(self._encryption_key)
        
        # Clear cached tokens
        self._token_cache = None
        self._token_cache_time = None
        
        self._log_access("rotate", 0)
        
        return self._encryption_key
    
    def _log_access(self, action: str, token_length: int) -> None:
        """Log token access for audit purposes.
        
        Args:
            action: The action performed (store, retrieve, clear, rotate)
            token_length: Length of the token (0 to avoid exposing length)
        """
        self._token_access_log.append({
            "action": action,
            "token_length": token_length,
            "timestamp": time.time()
        })
        
        # Keep only last 100 log entries
        if len(self._token_access_log) > 100:
            self._token_access_log = self._token_access_log[-100:]
    
    def get_access_log(self) -> List[Dict[str, Any]]:
        """Get the token access log.
        
        Returns:
            List of access log entries
        """
        return self._token_access_log.copy()
