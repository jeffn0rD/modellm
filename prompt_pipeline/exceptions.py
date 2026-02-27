"""
Centralized exception definitions for prompt pipeline.

This module contains all exception classes used across the prompt pipeline.
All modules should import exceptions from this file rather than defining their own.
"""

from pathlib import Path
from typing import Optional, List


class PromptPipelineError(Exception):
    """Base exception for all prompt pipeline errors."""
    pass


class ConfigurationError(PromptPipelineError):
    """Raised when configuration is invalid or missing."""
    pass


class StepExecutionError(PromptPipelineError):
    """Raised when a step execution fails."""
    
    def __init__(
        self,
        message: str,
        step_name: Optional[str] = None,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None
    ):
        super().__init__(message)
        self.step_name = step_name
        self.errors = errors or []
        self.warnings = warnings or []


class ValidationError(PromptPipelineError):
    """Raised when validation fails."""
    
    def __init__(
        self,
        message: str,
        validation_errors: Optional[List[str]] = None
    ):
        super().__init__(message)
        self.validation_errors = validation_errors or []


class FileOperationError(PromptPipelineError):
    """Raised when file operations fail."""
    
    def __init__(
        self,
        message: str,
        file_path: Optional[Path] = None
    ):
        super().__init__(message)
        self.file_path = file_path


class LLMClientError(PromptPipelineError):
    """Raised when LLM client operations fail."""
    
    def __init__(
        self,
        message: str,
        retry_count: int = 0,
        last_status_code: Optional[int] = None
    ):
        super().__init__(message)
        self.retry_count = retry_count
        self.last_status_code = last_status_code


class CompressionError(PromptPipelineError):
    """Raised when compression operations fail."""
    pass


class InputResolutionError(PromptPipelineError):
    """Raised when input resolution fails."""
    
    def __init__(
        self,
        message: str,
        label: Optional[str] = None,
        source: Optional[str] = None
    ):
        super().__init__(message)
        self.label = label
        self.source = source
