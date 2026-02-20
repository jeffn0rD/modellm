"""
Prompt Manager Module for the prompt pipeline.

This module handles loading prompts from files, managing step configurations,
and performing variable substitution in prompt templates.
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from prompt_pipeline.tag_replacement import (
    TagReplacer,
    replace_tags,
    validate_prompt_tags,
    MissingTagError,
    InvalidTagError,
    TagReplacementError
)


class PromptManager:
    """
    Load prompts and manage step configurations.
    
    Handles loading prompt templates from files, substituting variables,
    and managing step dependencies and configurations.
    """
    
    def __init__(
        self,
        config_path: str,
        prompts_dir: str = "prompts"
    ):
        """
        Initialize the Prompt Manager.
        
        Args:
            config_path: Path to the pipeline configuration YAML file.
            prompts_dir: Directory containing prompt template files.
        """
        self.config_path = config_path
        self.prompts_dir = prompts_dir
        self.steps_config = self._load_step_config()
    
    def _load_step_config(self) -> Dict[str, Any]:
        """Load step configurations from YAML file.
        
        Raises:
            FileNotFoundError: If configuration file doesn't exist.
            yaml.YAMLError: If configuration file has invalid YAML syntax.
            ValueError: If configuration file is empty or invalid structure.
        """
        import yaml
        
        # Check if file exists
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(
                f"Configuration file not found: {self.config_path}. "
                "Please specify a valid configuration file using --config option "
                "or create a configuration file at the default location."
            )
        
        # Check if file is readable
        if not os.path.isfile(self.config_path):
            raise ValueError(
                f"Configuration path is not a file: {self.config_path}"
            )
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(
                f"Invalid YAML syntax in configuration file '{self.config_path}': {e}"
            )
        except PermissionError:
            raise PermissionError(
                f"Permission denied: Cannot read configuration file '{self.config_path}'"
            )
        except Exception as e:
            raise ValueError(
                f"Error reading configuration file '{self.config_path}': {e}"
            )
        
        if config is None:
            raise ValueError(
                f"Configuration file '{self.config_path}' is empty or contains only comments"
            )
        
        if not isinstance(config, dict):
            raise ValueError(
                f"Invalid configuration structure in '{self.config_path}'. "
                f"Expected a dictionary, but got {type(config).__name__}"
            )
        
        return config
    
    def get_step_config(self, step_name: str) -> Optional[Dict[str, Any]]:
        """
        Get full configuration for a step.
        
        Args:
            step_name: Name of the step.
        
        Returns:
            Step configuration dictionary, or None if step not found.
        """
        steps = self.steps_config.get('steps', {})
        return steps.get(step_name)
    
    def load_prompt(self, prompt_file: str) -> str:
        """
        Load prompt template from file.
        
        Args:
            prompt_file: Name of the prompt file in prompts_dir.
        
        Returns:
            Prompt template content as string.
        
        Raises:
            FileNotFoundError: If prompt file doesn't exist.
        """
        path = Path(self.prompts_dir) / prompt_file
        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {path}")
        return path.read_text(encoding='utf-8')
    
    def substitute_variables(
        self,
        prompt: str,
        variables: Dict[str, Any],
        validate: bool = True
    ) -> str:
        """
        Replace {{variable}} placeholders in prompt.
        
        Args:
            prompt: Prompt template string with {{variable}} placeholders.
            variables: Dictionary of variable names to values.
            validate: If True, validate that all required tags are present.
        
        Returns:
            Prompt with all variables substituted.
        
        Raises:
            MissingTagError: If validate=True and a required tag is missing.
            InvalidTagError: If a tag replacement is invalid.
        """
        try:
            return replace_tags(prompt, variables, validate=validate)
        except (MissingTagError, InvalidTagError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Wrap any other errors in our exception type
            raise TagReplacementError(f"Error substituting variables: {e}")
    
    def get_prompt_file(self, step_name: str) -> Optional[str]:
        """
        Get prompt filename for step.
        
        Args:
            step_name: Name of the step.
        
        Returns:
            Prompt filename, or None if step not found.
        """
        config = self.get_step_config(step_name)
        if config is None:
            return None
        return config.get('prompt_file')
    
    def get_output_file(self, step_name: str) -> Optional[str]:
        """
        Get output filename for step.
        
        Args:
            step_name: Name of the step.
        
        Returns:
            Output filename, or None if step not found.
        """
        config = self.get_step_config(step_name)
        if config is None:
            return None
        return config.get('output_file')
    
    def get_output_type(self, step_name: str) -> Optional[str]:
        """
        Get output type for step (yaml, json, md).
        
        Args:
            step_name: Name of the step.
        
        Returns:
            Output type string, or None if step not found.
        """
        config = self.get_step_config(step_name)
        if config is None:
            return None
        return config.get('output_type')
    
    def get_json_schema(self, step_name: str) -> Optional[str]:
        """
        Get JSON schema path for step.
        
        Args:
            step_name: Name of the step.
        
        Returns:
            Path to JSON schema file, or None if not specified.
        """
        config = self.get_step_config(step_name)
        if config is None:
            return None
        return config.get('json_schema')
    
    def get_required_inputs(self, step_name: str) -> List[str]:
        """
        Determine what inputs a step needs.
        
        Args:
            step_name: Name of the step.
        
        Returns:
            List of required input types (e.g., 'nl_spec', 'spec_file', 'concepts_file').
        """
        config = self.get_step_config(step_name)
        if config is None:
            return []
        
        inputs = []
        if config.get('requires_nl_spec'):
            inputs.append('nl_spec')
        if config.get('requires_spec_file'):
            inputs.append('spec_file')
        if config.get('requires_concepts_file'):
            inputs.append('concepts_file')
        if config.get('requires_aggregations_file'):
            inputs.append('aggregations_file')
        if config.get('requires_messages_file'):
            inputs.append('messages_file')
        if config.get('requires_requirements_file'):
            inputs.append('requirements_file')
        
        return inputs
    
    def get_dependencies(self, step_name: str) -> List[str]:
        """
        Get step dependencies from config.
        
        Args:
            step_name: Name of the step.
        
        Returns:
            List of step names this step depends on.
        """
        config = self.get_step_config(step_name)
        if config is None:
            return []
        return config.get('dependencies', [])
    
    def get_step_order(self, step_name: str) -> int:
        """
        Get execution order for step.
        
        Args:
            step_name: Name of the step.
        
        Returns:
            Order number (lower = earlier execution).
        """
        config = self.get_step_config(step_name)
        if config is None:
            return 999
        return config.get('order', 999)
    
    def get_all_steps(self) -> List[Dict[str, Any]]:
        """
        Get all step configurations.
        
        Returns:
            List of all step configuration dictionaries.
        """
        steps = self.steps_config.get('steps', {})
        return list(steps.values())
    
    def get_all_step_names(self) -> List[str]:
        """
        Get all step names.
        
        Returns:
            List of step names.
        """
        steps = self.steps_config.get('steps', {})
        return list(steps.keys())
    
    def get_sorted_steps(self) -> List[Dict[str, Any]]:
        """
        Get all steps sorted by execution order.
        
        Returns:
            List of step configurations sorted by 'order' field.
        """
        steps = self.get_all_steps()
        return sorted(steps, key=lambda s: s.get('order', 999))
    
    def get_steps_for_execution(self, start_step: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get steps that need to be executed based on dependencies.
        
        If start_step is provided, returns steps from start_step onwards
        (including dependencies).
        
        Args:
            start_step: Optional step name to start from.
        
        Returns:
            List of steps to execute in order.
        """
        if start_step is None:
            return self.get_sorted_steps()
        
        # Get all steps needed - start step and its dependencies
        steps_to_execute = []
        visited = set()
        
        def add_step_and_deps(step_name: str):
            if step_name in visited:
                return
            visited.add(step_name)
            
            # First add dependencies
            deps = self.get_dependencies(step_name)
            for dep in deps:
                add_step_and_deps(dep)
            
            # Then add this step
            config = self.get_step_config(step_name)
            if config:
                steps_to_execute.append(config)
        
        add_step_and_deps(start_step)
        
        # Sort by order
        return sorted(steps_to_execute, key=lambda s: s.get('order', 999))
    
    def get_prompt_with_variables(
        self,
        step_name: str,
        variables: Dict[str, Any],
        validate: bool = True
    ) -> str:
        """
        Load prompt for step and substitute variables.
        
        Args:
            step_name: Name of the step.
            variables: Dictionary of variables to substitute.
            validate: If True, validate that all required tags are present.
        
        Returns:
            Processed prompt string.
        
        Raises:
            MissingTagError: If validate=True and a required tag is missing.
            InvalidTagError: If a tag replacement is invalid.
        """
        prompt_file = self.get_prompt_file(step_name)
        if prompt_file is None:
            raise ValueError(f"Step '{step_name}' not found in configuration")
        
        prompt = self.load_prompt(prompt_file)
        return self.substitute_variables(prompt, variables, validate=validate)
    
    def get_required_tags(self, step_name: str) -> Set[str]:
        """
        Get all required tags from a step's prompt.
        
        Args:
            step_name: Name of the step.
        
        Returns:
            Set of tag names required by the prompt.
        
        Raises:
            ValueError: If step not found.
        """
        prompt_file = self.get_prompt_file(step_name)
        if prompt_file is None:
            raise ValueError(f"Step '{step_name}' not found in configuration")
        
        prompt = self.load_prompt(prompt_file)
        replacer = TagReplacer(prompt)
        return replacer.get_required_tags()
    
    def validate_prompt_tags(
        self,
        step_name: str,
        variables: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Validate that all required tags in a step's prompt have replacements.
        
        Args:
            step_name: Name of the step.
            variables: Dictionary of variable names to values.
        
        Returns:
            Tuple of (is_valid, missing_tags)
        """
        prompt_file = self.get_prompt_file(step_name)
        if prompt_file is None:
            return False, [f"Step '{step_name}' not found"]
        
        prompt = self.load_prompt(prompt_file)
        return validate_prompt_tags(prompt, variables)
    
    def get_dev_defaults(self) -> Dict[str, Any]:
        """
        Get development default settings.
        
        Returns:
            Dictionary of dev defaults.
        """
        return self.steps_config.get('dev_defaults', {})
    
    def get_validation_config(self) -> Dict[str, Any]:
        """
        Get validation configuration.
        
        Returns:
            Dictionary of validation settings.
        """
        return self.steps_config.get('validation', {})
    
    def get_paths_config(self) -> Dict[str, Any]:
        """
        Get paths configuration.
        
        Returns:
            Dictionary of path settings.
        """
        return self.steps_config.get('paths', {})


# Convenience function for simple usage
def create_prompt_manager(
    config_path: str = "configuration/pipeline_config.yaml",
    prompts_dir: str = "prompts"
) -> PromptManager:
    """
    Create a PromptManager instance.
    
    Args:
        config_path: Path to pipeline config.
        prompts_dir: Directory containing prompts.
    
    Returns:
        Configured PromptManager instance.
    """
    return PromptManager(config_path=config_path, prompts_dir=prompts_dir)
