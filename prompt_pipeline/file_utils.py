"""
Shared file utility functions for prompt pipeline.

This module provides common file operations with comprehensive error handling,
including file loading, writing, and path validation for security.
"""

from pathlib import Path
from typing import Optional
import json

from prompt_pipeline.exceptions import FileOperationError


def load_file_content(
    file_path: Path,
    encoding: str = "utf-8",
    allow_empty: bool = False,
) -> str:
    """
    Load content from a file with comprehensive error handling.
    
    Args:
        file_path: Path to the file to load.
        encoding: File encoding (default: utf-8).
        allow_empty: If False, raises error for empty files.
    
    Returns:
        File content as string.
    
    Raises:
        FileOperationError: If file not found, not a file, permission denied,
                           encoding error, or file is empty (when allow_empty=False).
    """
    if not isinstance(file_path, Path):
        file_path = Path(file_path)
    
    # Check if file exists
    if not file_path.exists():
        raise FileOperationError(
            f"File not found: {file_path}",
            file_path=file_path
        )
    
    # Check if it's a file (not a directory)
    if not file_path.is_file():
        raise FileOperationError(
            f"Path is not a file: {file_path}",
            file_path=file_path
        )
    
    # Read file content
    try:
        content = file_path.read_text(encoding=encoding)
    except PermissionError:
        raise FileOperationError(
            f"Permission denied reading file: {file_path}",
            file_path=file_path
        )
    except UnicodeDecodeError as e:
        raise FileOperationError(
            f"Encoding error reading {file_path}: {e}",
            file_path=file_path
        )
    except Exception as e:
        raise FileOperationError(
            f"Error reading file {file_path}: {e}",
            file_path=file_path
        )
    
    # Check for empty content (if not allowed)
    if not allow_empty and not content.strip():
        raise FileOperationError(
            f"File is empty: {file_path}",
            file_path=file_path
        )
    
    return content


def write_file_content(
    file_path: Path,
    content: str,
    encoding: str = "utf-8",
    create_parents: bool = True,
    atomic: bool = True,
) -> None:
    """
    Write content to a file with comprehensive error handling and atomic writes.
    
    Args:
        file_path: Path to the file to write.
        content: Content to write.
        encoding: File encoding (default: utf-8).
        create_parents: If True, creates parent directories if they don't exist.
        atomic: If True, uses atomic write (temp file + rename) to prevent corruption.
    
    Raises:
        FileOperationError: If write fails due to permission, OS error, or other issues.
    """
    if not isinstance(file_path, Path):
        file_path = Path(file_path)
    
    # Create parent directories if needed
    if create_parents:
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise FileOperationError(
                f"Failed to create parent directory {file_path.parent}: {e}",
                file_path=file_path
            )
    
    # Write content
    if atomic:
        # Atomic write: write to temp file, then rename
        temp_path = file_path.with_suffix(file_path.suffix + '.tmp')
        try:
            temp_path.write_text(content, encoding=encoding)
            temp_path.replace(file_path)
        except PermissionError:
            raise FileOperationError(
                f"Permission denied writing to {file_path}",
                file_path=file_path
            )
        except OSError as e:
            # Clean up temp file if it exists
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except:
                    pass
            raise FileOperationError(
                f"OS error writing to {file_path}: {e}",
                file_path=file_path
            )
        except Exception as e:
            # Clean up temp file if it exists
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except:
                    pass
            raise FileOperationError(
                f"Unexpected error writing to {file_path}: {e}",
                file_path=file_path
            )
    else:
        # Non-atomic write (for testing or when atomic is not needed)
        try:
            file_path.write_text(content, encoding=encoding)
        except PermissionError:
            raise FileOperationError(
                f"Permission denied writing to {file_path}",
                file_path=file_path
            )
        except Exception as e:
            raise FileOperationError(
                f"Error writing to {file_path}: {e}",
                file_path=file_path
            )


def validate_file_path(
    file_path: Path,
    allowed_base_dir: Optional[Path] = None,
    must_exist: bool = False,
) -> Path:
    """
    Validate a file path for security and correctness.
    
    This function checks for path traversal attempts and ensures the path
    is within an allowed base directory.
    
    Args:
        file_path: Path to validate.
        allowed_base_dir: Base directory that the file path must be within.
                         If None, uses current working directory.
        must_exist: If True, the file must already exist.
    
    Returns:
        Resolved, validated path.
    
    Raises:
        FileOperationError: If path is invalid, contains traversal attempts,
                           is outside allowed base directory, or doesn't exist (when required).
    """
    if not isinstance(file_path, Path):
        file_path = Path(file_path)
    
    # Resolve the path (removes . and .. from the path)
    try:
        resolved_path = file_path.resolve()
    except Exception as e:
        raise FileOperationError(
            f"Failed to resolve path {file_path}: {e}",
            file_path=file_path
        )
    
    # Check if path contains parent directory references (..)
    # This is a security check even after resolve() because resolve() doesn't
    # always prevent traversal if the path string contains ".."
    str_path = str(file_path)
    if ".." in str_path:
        raise FileOperationError(
            f"Path contains parent directory references (..): {file_path}",
            file_path=file_path
        )
    
    # If base directory is specified, check that path is within it
    if allowed_base_dir is not None:
        if not isinstance(allowed_base_dir, Path):
            allowed_base_dir = Path(allowed_base_dir)
        
        try:
            allowed_base_dir_resolved = allowed_base_dir.resolve()
            resolved_path.relative_to(allowed_base_dir_resolved)
        except ValueError:
            raise FileOperationError(
                f"Path '{file_path}' is outside allowed base directory '{allowed_base_dir}'",
                file_path=file_path
            )
    
    # Check if file exists (if required)
    if must_exist and not resolved_path.exists():
        raise FileOperationError(
            f"File does not exist: {resolved_path}",
            file_path=resolved_path
        )
    
    return resolved_path


def load_json_file(
    file_path: Path,
    encoding: str = "utf-8",
) -> dict:
    """
    Load a JSON file and parse it.
    
    Args:
        file_path: Path to the JSON file.
        encoding: File encoding (default: utf-8).
    
    Returns:
        Parsed JSON data as dict/list.
    
    Raises:
        FileOperationError: If file loading or JSON parsing fails.
    """
    try:
        content = load_file_content(file_path, encoding=encoding, allow_empty=False)
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise FileOperationError(
            f"Invalid JSON in {file_path}: {e}",
            file_path=file_path
        )
    except Exception as e:
        raise FileOperationError(
            f"Error loading JSON file {file_path}: {e}",
            file_path=file_path
        )


def write_json_file(
    file_path: Path,
    data: dict,
    encoding: str = "utf-8",
    indent: int = 2,
    atomic: bool = True,
) -> None:
    """
    Write data to a JSON file with atomic writes.
    
    Args:
        file_path: Path to the JSON file.
        data: Data to write (must be JSON-serializable).
        encoding: File encoding (default: utf-8).
        indent: JSON indentation level (default: 2).
        atomic: If True, uses atomic write (default: True).
    
    Raises:
        FileOperationError: If write fails or data is not JSON-serializable.
    """
    try:
        content = json.dumps(data, indent=indent, ensure_ascii=False)
    except Exception as e:
        raise FileOperationError(
            f"Failed to serialize data to JSON: {e}",
            file_path=file_path
        )
    
    write_file_content(
        file_path=file_path,
        content=content,
        encoding=encoding,
        atomic=atomic,
    )


def read_yaml_file(
    file_path: Path,
    encoding: str = "utf-8",
) -> dict:
    """
    Load and parse a YAML file.
    
    Args:
        file_path: Path to the YAML file.
        encoding: File encoding (default: utf-8).
    
    Returns:
        Parsed YAML data as dict/list.
    
    Raises:
        FileOperationError: If file loading or YAML parsing fails.
    """
    try:
        import yaml
    except ImportError:
        raise FileOperationError(
            "PyYAML library is required to read YAML files. Install with: pip install PyYAML",
            file_path=file_path
        )
    
    try:
        content = load_file_content(file_path, encoding=encoding, allow_empty=False)
        return yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise FileOperationError(
            f"Invalid YAML in {file_path}: {e}",
            file_path=file_path
        )
    except Exception as e:
        raise FileOperationError(
            f"Error loading YAML file {file_path}: {e}",
            file_path=file_path
        )
