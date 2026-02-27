"""
Tag Replacement Module for Prompt Templates

This module handles parsing prompt templates for tags ({{TAG}}),
replacing tags with content or file paths, validating required tags,
and providing error handling for missing tags.
"""

import re
from pathlib import Path
from typing import Dict, Any, List, Set, Optional, Tuple

from prompt_pipeline.exceptions import FileOperationError, PromptPipelineError
from prompt_pipeline.file_utils import load_file_content


class TagReplacementError(PromptPipelineError):
    """Base exception for tag replacement errors."""
    pass


class MissingTagError(TagReplacementError):
    """Raised when a required tag is missing from the replacement dictionary."""
    
    def __init__(self, tag_name: str, prompt_file: Optional[str] = None):
        self.tag_name = tag_name
        self.prompt_file = prompt_file
        message = f"Missing required tag: {{{tag_name}}}"
        if prompt_file:
            message += f" in prompt file: {prompt_file}"
        super().__init__(message)


class InvalidTagError(TagReplacementError):
    """Raised when a tag has invalid format or content."""
    
    def __init__(self, tag_name: str, reason: str):
        self.tag_name = tag_name
        self.reason = reason
        super().__init__(f"Invalid tag {{{tag_name}}}: {reason}")


class TagReplacer:
    """
    Handles tag replacement in prompt templates.
    
    Supports:
    - Parsing tags from prompt templates
    - Replacing tags with content or file paths
    - Validating all required tags are present
    - Error handling for missing or invalid tags
    - Content substitution and file path substitution
    """
    
    # Pattern to match {{tag_name}} placeholders
    TAG_PATTERN = re.compile(r'\{\{([^}]+)\}\}')
    
    def __init__(self, prompt: str):
        """
        Initialize the tag replacer with a prompt template.
        
        Args:
            prompt: Prompt template string containing {{tag}} placeholders.
        """
        self.prompt = prompt
        self.required_tags = self._extract_tags(prompt)
    
    def _extract_tags(self, prompt: str) -> Set[str]:
        """
        Extract all unique tag names from the prompt.
        
        Args:
            prompt: Prompt template string.
        
        Returns:
            Set of tag names found in the prompt.
        """
        tags = set()
        for match in self.TAG_PATTERN.findall(prompt):
            # Strip whitespace and validate tag name
            tag_name = match.strip()
            if tag_name:
                tags.add(tag_name)
        return tags
    
    def get_required_tags(self) -> Set[str]:
        """
        Get all required tags from the prompt.
        
        Returns:
            Set of tag names that need to be replaced.
        """
        return self.required_tags.copy()
    
    def validate_tags(self, replacements: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate that all required tags have replacements.
        
        Args:
            replacements: Dictionary mapping tag names to replacement values.
        
        Returns:
            Tuple of (is_valid, missing_tags)
            - is_valid: True if all tags have replacements
            - missing_tags: List of tag names that are missing from replacements
        """
        missing = list(self.required_tags - set(replacements.keys()))
        return len(missing) == 0, missing
    
    def _load_file_content(self, file_path: str) -> str:
        """
        Load content from a file using shared file utilities.
        
        Args:
            file_path: Path to the file to load.
        
        Returns:
            File content as string.
        
        Raises:
            TagReplacementError: If the file cannot be read.
        """
        try:
            return load_file_content(
                file_path=Path(file_path),
                encoding="utf-8",
                allow_empty=False,
            )
        except FileOperationError as e:
            raise TagReplacementError(str(e))
    
    def _resolve_replacement(
        self,
        tag_name: str,
        replacement: Any
    ) -> str:
        """
        Resolve a replacement value to a string.
        
        Handles:
        - Strings: Returned as-is
        - File paths: Loaded and content returned
        - Dictionaries with 'file' key: Load file and return content
        - Dictionaries with 'content' key: Return content
        - Other types: Converted to string
        
        Args:
            tag_name: Name of the tag being replaced.
            replacement: Replacement value (string, file path, or dict).
        
        Returns:
            Resolved string content for replacement.
        """
        if isinstance(replacement, str):
            # Check if it's a file path (heuristic: contains path separators or has extension)
            # But only if it's not a tag reference
            if ('/' in replacement or '\\' in replacement) and not replacement.startswith('{{'):
                # Check if it looks like a file path
                import os
                if os.path.exists(replacement):
                    return self._load_file_content(replacement)
                # If it doesn't exist as a file, treat as literal string
                return replacement
            # Literal string
            return replacement
        
        elif isinstance(replacement, dict):
            # Dictionary format
            if 'file' in replacement:
                file_path = replacement['file']
                return self._load_file_content(file_path)
            elif 'content' in replacement:
                return str(replacement['content'])
            elif 'path' in replacement:
                file_path = replacement['path']
                return self._load_file_content(file_path)
            else:
                raise InvalidTagError(
                    tag_name,
                    "Dictionary replacement must have 'file', 'path', or 'content' key"
                )
        
        else:
            # Convert to string
            return str(replacement)
    
    def replace(
        self,
        replacements: Dict[str, Any],
        validate: bool = True,
        default_value: str = ""
    ) -> str:
        """
        Replace all tags in the prompt with their replacement values.
        
        Args:
            replacements: Dictionary mapping tag names to replacement values.
            validate: If True, validate that all required tags are present.
            default_value: Default value to use for missing tags (if validate=False).
        
        Returns:
            Prompt with all tags replaced.
        
        Raises:
            MissingTagError: If validate=True and a required tag is missing.
            InvalidTagError: If a tag replacement is invalid.
        """
        if validate:
            is_valid, missing_tags = self.validate_tags(replacements)
            if not is_valid:
                raise MissingTagError(missing_tags[0])
        
        result = self.prompt
        
        for tag_name in self.required_tags:
            # Get replacement value or use default
            replacement_value = replacements.get(tag_name, default_value)
            
            # Resolve the replacement value
            resolved_content = self._resolve_replacement(tag_name, replacement_value)
            
            # Replace the tag in the prompt
            tag_pattern = f'{{{{{tag_name}}}}}'
            result = result.replace(tag_pattern, resolved_content)
        
        return result
    
    def replace_with_paths(
        self,
        replacements: Dict[str, Any],
        validate: bool = True
    ) -> str:
        """
        Replace tags with file paths instead of file content.
        
        Useful for cases where the LLM needs to reference files rather than
        receive their full content.
        
        Args:
            replacements: Dictionary mapping tag names to replacement values.
            validate: If True, validate that all required tags are present.
        
        Returns:
            Prompt with tags replaced by file paths.
        
        Raises:
            MissingTagError: If validate=True and a required tag is missing.
        """
        if validate:
            is_valid, missing_tags = self.validate_tags(replacements)
            if not is_valid:
                raise MissingTagError(missing_tags[0])
        
        result = self.prompt
        
        for tag_name in self.required_tags:
            replacement_value = replacements.get(tag_name, "")
            
            # Convert to file path string
            if isinstance(replacement_value, str):
                path_str = replacement_value
            elif isinstance(replacement_value, dict):
                if 'file' in replacement_value:
                    path_str = replacement_value['file']
                elif 'path' in replacement_value:
                    path_str = replacement_value['path']
                else:
                    path_str = str(replacement_value)
            else:
                path_str = str(replacement_value)
            
            # Replace the tag
            tag_pattern = f'{{{{{tag_name}}}}}'
            result = result.replace(tag_pattern, path_str)
        
        return result
    
    def replace_with_content_or_paths(
        self,
        replacements: Dict[str, Any],
        validate: bool = True
    ) -> str:
        """
        Replace tags intelligently: use content for file inputs, paths for label references.
        
        Args:
            replacements: Dictionary mapping tag names to replacement values.
            validate: If True, validate that all required tags are present.
        
        Returns:
            Prompt with tags replaced based on replacement type.
        
        Raises:
            MissingTagError: If validate=True and a required tag is missing.
        """
        if validate:
            is_valid, missing_tags = self.validate_tags(replacements)
            if not is_valid:
                raise MissingTagError(missing_tags[0])
        
        result = self.prompt
        
        for tag_name in self.required_tags:
            replacement_value = replacements.get(tag_name, "")
            
            # Determine if we should use content or path
            use_path = False
            
            if isinstance(replacement_value, dict):
                # Dictionary with 'path' key means use path, 'content' key means use content
                if 'path' in replacement_value:
                    use_path = True
                    path_str = replacement_value['path']
                    content_str = self._load_file_content(path_str)
                elif 'file' in replacement_value:
                    use_path = False
                    content_str = self._load_file_content(replacement_value['file'])
                elif 'content' in replacement_value:
                    use_path = False
                    content_str = str(replacement_value['content'])
                else:
                    use_path = False
                    content_str = str(replacement_value)
            elif isinstance(replacement_value, str):
                # String: check if it's a file path
                import os
                if os.path.exists(replacement_value):
                    use_path = False
                    content_str = self._load_file_content(replacement_value)
                else:
                    # Could be a label reference or literal string
                    # For now, treat as content
                    use_path = False
                    content_str = replacement_value
            else:
                use_path = False
                content_str = str(replacement_value)
            
            # Replace the tag
            tag_pattern = f'{{{{{tag_name}}}}}'
            replacement = path_str if use_path else content_str
            result = result.replace(tag_pattern, replacement)
        
        return result


def parse_prompt_tags(prompt: str) -> Set[str]:
    """
    Convenience function to extract all tags from a prompt.
    
    Args:
        prompt: Prompt template string.
    
    Returns:
        Set of tag names found in the prompt.
    """
    replacer = TagReplacer(prompt)
    return replacer.get_required_tags()


def replace_tags(
    prompt: str,
    replacements: Dict[str, Any],
    validate: bool = True
) -> str:
    """
    Convenience function to replace tags in a prompt.
    
    Args:
        prompt: Prompt template string with {{tag}} placeholders.
        replacements: Dictionary mapping tag names to replacement values.
        validate: If True, validate that all required tags are present.
    
    Returns:
        Prompt with all tags replaced.
    
    Raises:
        MissingTagError: If validate=True and a required tag is missing.
    """
    replacer = TagReplacer(prompt)
    return replacer.replace(replacements, validate=validate)


def validate_prompt_tags(
    prompt: str,
    replacements: Dict[str, Any]
) -> Tuple[bool, List[str]]:
    """
    Convenience function to validate that all tags have replacements.
    
    Args:
        prompt: Prompt template string.
        replacements: Dictionary mapping tag names to replacement values.
    
    Returns:
        Tuple of (is_valid, missing_tags)
    """
    replacer = TagReplacer(prompt)
    return replacer.validate_tags(replacements)
