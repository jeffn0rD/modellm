"""Step Executor Module for individual pipeline step execution."""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from prompt_pipeline.llm_client import OpenRouterClient
from prompt_pipeline.prompt_manager import PromptManager
from prompt_pipeline.tag_replacement import TagReplacer
from prompt_pipeline.terminal_utils import (
    Spinner,
    print_colored,
    print_header,
    print_success,
    print_warning,
    print_error,
    print_info,
    format_prompt,
    format_response,
    format_model,
    format_step,
    Color,
)
from prompt_pipeline.validation import (
    ConceptsValidator,
    MessagesValidator,
    RequirementsValidator,
    ValidationResult,
    YAMLValidator,
    AggregationsValidator,
)
from prompt_pipeline.validation.json_validator import JSONValidator


def safe_print(text: str) -> None:
    """Print text with encoding error handling.
    
    Args:
        text: Text to print
    """
    try:
        print(text)
    except UnicodeEncodeError:
        # If encoding fails, try to print with error replacement
        try:
            print(text.encode('utf-8', errors='replace').decode('utf-8'))
        except:
            # Last resort: print without special characters
            print(text.encode('ascii', errors='ignore').decode('ascii'))


class StepExecutionError(Exception):
    """Exception raised when step execution fails."""

    def __init__(
        self,
        message: str,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
    ):
        super().__init__(message)
        self.errors = errors or []
        self.warnings = warnings or []


class StepExecutor:
    """Execute individual pipeline steps.

    Handles:
    - Loading prompts from configured files
    - Variable substitution in prompts
    - LLM API calls
    - Output validation
    - Multiple output file handling
    - Progress reporting
    - Error handling with retry
    """

    def __init__(
        self,
        llm_client: OpenRouterClient,
        prompt_manager: PromptManager,
        output_dir: Path,
        model_level: int = 1,
        skip_validation: bool = False,
        verbose: bool = False,
        show_prompt: bool = False,
        show_response: bool = False,
        output_file: Optional[str] = None,
        force: bool = False,
    ):
        """Initialize step executor.

        Args:
            llm_client: LLM client for API calls.
            prompt_manager: Prompt manager for loading prompts.
            output_dir: Directory for output files.
            model_level: Model level (1=cheapest, 2=balanced, 3=best).
            skip_validation: If True, skip output validation.
            verbose: If True, print detailed progress.
            show_prompt: If True, display prompt sent to LLM.
            show_response: If True, display response from LLM.
            output_file: Override output file path (if specified).
            force: If True, substitute empty string for missing inputs instead of failing.
        """
        self.llm_client = llm_client
        self.prompt_manager = prompt_manager
        self.output_dir = Path(output_dir)
        self.model_level = model_level
        self.skip_validation = skip_validation
        self.verbose = verbose
        self.show_prompt = show_prompt
        self.show_response = show_response
        self.output_file = output_file
        self.force = force

    async def execute_step(
        self,
        step_name: str,
        cli_inputs: Optional[Dict[str, str]] = None,
        exogenous_inputs: Optional[Dict[str, Path]] = None,
        previous_outputs: Optional[Dict[str, Path]] = None,
    ) -> Dict[str, Path]:
        """Execute a single step.

        Args:
            step_name: Name of the step to execute.
            cli_inputs: CLI input values (from --input-file, --input-prompt, --input-text).
            exogenous_inputs: Exogenous input files (from config or CLI overrides).
            previous_outputs: Outputs from previous steps (for label resolution).

        Returns:
            Dictionary mapping output labels to output file paths.

        Raises:
            StepExecutionError: If step execution fails.
        """
        cli_inputs = cli_inputs or {}
        exogenous_inputs = exogenous_inputs or {}
        previous_outputs = previous_outputs or {}
        self._log(f"Executing step: {step_name}")

        # Get step configuration
        step_config = self.prompt_manager.get_step_config(step_name)
        if not step_config:
            raise StepExecutionError(f"Step '{step_name}' not found in configuration")

        # Prepare variables for substitution using new input format
        # Get inputs array from step config
        inputs_config = step_config.get("inputs", [])
        
        variables = self._prepare_variables_from_config(
            inputs_config=inputs_config,
            cli_inputs=cli_inputs,
            exogenous_inputs=exogenous_inputs,
            previous_outputs=previous_outputs,
            step_config=step_config,
        )
        self._log(f"Prompt variables prepared from {len(variables)} inputs")

        # In force mode, add empty strings for missing tags
        if self.force:
            # Get required tags from prompt
            prompt_file = step_config.get("prompt_file")
            if prompt_file:
                prompt_template = self.prompt_manager.load_prompt(prompt_file)
                replacer = TagReplacer(prompt_template)
                required_tags = replacer.get_required_tags()
                # Add empty string for any missing tags
                for tag in required_tags:
                    if tag not in variables:
                        variables[tag] = ""

        # Load prompt with preamble and substitute variables
        # Use get_prompt_with_variables which generates preamble and substitutes variables
        filled_prompt = self.prompt_manager.get_prompt_with_variables(
            step_name=step_name,
            variables=variables,
            validate=not self.force  # Skip validation if force mode
        )
        self._log(f"Prompt loaded with preamble and variables substituted")

        # Get model for this step
        model = self._get_model_for_step(step_name)
        self._log(f"Using model: {model}")

        # Call LLM
        self._log(f"Calling LLM...")
        
        # Show prompt if requested
        if self.show_prompt or self.show_response:
            print_header("PROMPT", Color.CYAN)
            # Print prompt with encoding error handling
            safe_print(format_prompt(filled_prompt))
            print_header(f"Calling model: {format_model(model)}", Color.MAGENTA)
        
        # Show progress indicator
        spinner_message = f"Waiting for response from {format_model(model)}..."
        with Spinner(spinner_message, Color.CYAN) as spinner:
            response = await self.llm_client.call_prompt_async(filled_prompt, model=model)
        
        # Show response if requested
        if self.show_response:
            print_header("RESPONSE", Color.GREEN)
            # Print response with encoding error handling
            safe_print(format_response(response))
            print_info(f"Response received ({len(response)} characters)")
        
        self._log(f"LLM response received ({len(response)} chars)")

        # Save outputs and collect output paths with labels
        output_paths = self._save_outputs(response, step_config)

        self._log(f"Output saved to: {list(output_paths.values())}")

        # Validate output if not skipped
        if not self.skip_validation:
            self._log("Validating output...")
            validation_result = self._validate_output(response, step_config)
            if not validation_result.is_valid():
                # Build detailed error message
                error_details = []
                if validation_result.errors:
                    error_details.append("Errors:")
                    for error in validation_result.errors:
                        error_details.append(f"  - {error}")
                if validation_result.warnings:
                    error_details.append("Warnings:")
                    for warning in validation_result.warnings:
                        error_details.append(f"  ⚠ {warning}")
                
                error_msg = f"Validation failed for {step_name}\n" + "\n".join(error_details)
                
                if self.skip_validation:
                    # Development mode: warn but continue
                    self._log(f"Warning: {error_msg}")
                else:
                    # Production mode: fail (but file is already saved)
                    raise StepExecutionError(
                        error_msg,
                        validation_result.errors,
                        validation_result.warnings,
                    )
            else:
                self._log("Validation passed")
        else:
            self._log("Validation skipped")

        return output_paths

    def _log(self, message: str) -> None:
        """Log message if verbose mode is enabled."""
        if self.verbose:
            print(f"[StepExecutor] {message}")

    def _prepare_variables_from_config(
        self,
        inputs_config: List[Dict[str, Any]],
        cli_inputs: Dict[str, str],
        exogenous_inputs: Dict[str, Path],
        previous_outputs: Dict[str, Path],
        step_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Prepare variables for prompt substitution from new input format.

        Args:
            inputs_config: List of input configurations from step config.
            cli_inputs: CLI input values (from --input-file, --input-prompt, --input-text).
            exogenous_inputs: Exogenous input files (from config or CLI overrides).
            previous_outputs: Outputs from previous steps (for label resolution).
            step_config: Step configuration.

        Returns:
            Dictionary mapping labels to content for substitution.
        """
        variables = {}
        
        for input_spec in inputs_config:
            label = input_spec.get("label")
            input_type = input_spec.get("type", "text")
            source = input_spec.get("source", "cli")
            compression = input_spec.get("compression", "full")
            
            # Resolve content based on source type
            content = self._resolve_input_content(
                label=label,
                input_type=input_type,
                source=source,
                cli_inputs=cli_inputs,
                exogenous_inputs=exogenous_inputs,
                previous_outputs=previous_outputs,
                step_config=step_config,
            )
            
            # Apply compression if specified (placeholder - full compression returns content as-is)
            if content is not None:
                compressed_content = self._apply_compression(content, compression, input_type)
                variables[label] = compressed_content
            elif self.force:
                # If force mode and input missing, substitute empty string
                variables[label] = ""
            else:
                raise StepExecutionError(
                    f"Missing required input for label '{label}' from source '{source}'"
                )
        
        return variables

    def _resolve_input_content(
        self,
        label: str,
        input_type: str,
        source: str,
        cli_inputs: Dict[str, str],
        exogenous_inputs: Dict[str, Path],
        previous_outputs: Dict[str, Path],
        step_config: Dict[str, Any],
    ) -> Optional[str]:
        """Resolve input content based on source type.

        Priority order:
        1. CLI inputs (highest)
        2. Exogenous inputs (from config or CLI overrides)
        3. Previous step outputs (label references)
        4. Missing (None)

        Args:
            label: Input label.
            input_type: Expected input type (md, json, yaml, text).
            source: Source type (cli, file, label:NAME).
            cli_inputs: CLI input values.
            exogenous_inputs: Exogenous input files.
            previous_outputs: Outputs from previous steps.
            step_config: Step configuration.

        Returns:
            Content string or None if not found.
        """
        # Source is in format "label:NAME" for previous step outputs
        if source.startswith("label:"):
            ref_label = source[6:]  # Remove "label:" prefix
            if ref_label in previous_outputs:
                file_path = previous_outputs[ref_label]
                return self._load_file_content(file_path, input_type)
            return None
        
        # CLI input - check cli_inputs dict
        if source == "cli":
            if label in cli_inputs:
                return cli_inputs[label]
            return None
        
        # File input - check exogenous_inputs
        if source == "file":
            if label in exogenous_inputs:
                file_path = exogenous_inputs[label]
                return self._load_file_content(file_path, input_type)
            return None
        
        # Default: try to resolve from various sources
        # First check CLI inputs
        if label in cli_inputs:
            return cli_inputs[label]
        
        # Then check exogenous inputs
        if label in exogenous_inputs:
            file_path = exogenous_inputs[label]
            return self._load_file_content(file_path, input_type)
        
        # Finally check previous outputs
        if label in previous_outputs:
            file_path = previous_outputs[label]
            return self._load_file_content(file_path, input_type)
        
        return None

    def _load_file_content(self, file_path: Path, input_type: str) -> str:
        """Load content from a file.

        Args:
            file_path: Path to the file.
            input_type: Expected input type (for validation).

        Returns:
            File content as string.

        Raises:
            StepExecutionError: If file not found or invalid.
        """
        if not isinstance(file_path, Path):
            file_path = Path(file_path)
        
        if not file_path.exists():
            raise StepExecutionError(f"Input file not found: {file_path}")
        
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            raise StepExecutionError(f"Failed to read input file {file_path}: {e}")
        
        return content

    def _apply_compression(
        self,
        content: str,
        compression: str,
        input_type: str,
    ) -> str:
        """Apply compression to content.

        Currently supports 'full' (no compression) as placeholder.
        Full compression returns content as-is.

        Args:
            content: Content to compress.
            compression: Compression strategy name.
            input_type: Input type (md, json, yaml, text).

        Returns:
            Compressed content.
        """
        # Placeholder: full compression returns content as-is
        # Actual compression strategies will be implemented in later tasks
        if compression in ("full", "none", None, ""):
            return content
        
        # For now, return content as-is for unknown compression strategies
        # This will be enhanced when compression strategies are implemented
        self._log(f"Compression '{compression}' not implemented, using full content")
        return content

    def _save_outputs(
        self,
        response: str,
        step_config: Dict[str, Any],
    ) -> Dict[str, Path]:
        """Save step outputs and return paths with labels.

        Args:
            response: LLM response content.
            step_config: Step configuration.

        Returns:
            Dictionary mapping output labels to output file paths.
        """
        output_paths: Dict[str, Path] = {}
        
        # Get outputs array from step config
        outputs_config = step_config.get("outputs", [])
        
        if not outputs_config:
            # Fallback to old format (single output_file)
            output_filename = step_config.get("output_file", "output.txt")
            output_path = self.output_dir / output_filename
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(response, encoding="utf-8")
            output_paths["default"] = output_path
            return output_paths
        
        # Handle multiple outputs
        if len(outputs_config) > 1:
            # Try to parse JSON response for multiple outputs
            try:
                data = json.loads(response)
                if isinstance(data, dict):
                    for output_spec in outputs_config:
                        if isinstance(output_spec, dict):
                            key = output_spec.get("key")
                            filename = output_spec.get("filename")
                            label = output_spec.get("label")
                            if key and filename and key in data:
                                file_path = self.output_dir / filename
                                file_path.parent.mkdir(parents=True, exist_ok=True)
                                file_path.write_text(
                                    json.dumps(data[key], indent=2), encoding="utf-8"
                                )
                                if label:
                                    output_paths[label] = file_path
                                self._log(f"Saved {key} to {filename}")
                else:
                    # Single JSON object, save to primary output
                    self._save_single_output(response, outputs_config[0], output_paths)
            except json.JSONDecodeError:
                # Not JSON, save entire response to first output
                self._save_single_output(response, outputs_config[0], output_paths)
        else:
            # Single output
            self._save_single_output(response, outputs_config[0], output_paths)
        
        return output_paths

    def _save_single_output(
        self,
        response: str,
        output_spec: Dict[str, Any],
        output_paths: Dict[str, Path],
    ) -> None:
        """Save a single output file.

        Args:
            response: LLM response content.
            output_spec: Output specification (file, label, type).
            output_paths: Dictionary to update with label -> path mapping.
        """
        filename = output_spec.get("file", "output.txt")
        label = output_spec.get("label")
        
        output_path = self.output_dir / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(response, encoding="utf-8")
        
        if label:
            output_paths[label] = output_path
        else:
            output_paths["default"] = output_path
        
        self._log(f"Saved output to {filename}")

    def _prepare_variables(
        self,
        inputs: Dict[str, Path],
        step_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Prepare variables for prompt substitution.

        Args:
            inputs: Input file paths.
            step_config: Step configuration.

        Returns:
            Dictionary of variables for substitution.
        """
        variables = {}

        # Add file paths
        for key, path in inputs.items():
            variables[key] = str(Path(path).resolve())

        # Add context from previous outputs (for revision cycles)
        if "context" in inputs:
            variables["context"] = inputs["context"].read_text(encoding="utf-8")

        return variables

    def _get_model_for_step(self, step_name: str) -> str:
        """Get model name for a step.

        Args:
            step_name: Name of the step.

        Returns:
            Model name to use for this step.
        """
        # Look up model from configuration
        model_levels = self.prompt_manager.steps_config.get("model_levels", {})
        step_models = model_levels.get(step_name, {})

        # Get model for current level
        model = step_models.get(self.model_level)
        if not model:
            # Fall back to level 1
            model = step_models.get(1)

        if not model:
            # Use default from client
            model = self.llm_client.default_model

        return model

    def _validate_output(
        self,
        content: str,
        step_config: Dict[str, Any],
    ) -> ValidationResult:
        """Validate step output based on configured schema.

        Args:
            content: Output content to validate.
            step_config: Step configuration.

        Returns:
            ValidationResult with errors and warnings.
        """
        output_type = step_config.get("output_type")

        if output_type == "yaml":
            validator = YAMLValidator()
            return validator.validate(content)

        elif output_type == "json":
            schema_path = step_config.get("json_schema")

            # Select appropriate validator based on output file
            output_file = step_config.get("output_file", "")

            if "concepts" in output_file:
                validator = ConceptsValidator(schema_path)
            elif "aggregations" in output_file:
                validator = AggregationsValidator(schema_path)
            elif "messages" in output_file:
                validator = MessagesValidator(schema_path)
            elif "requirements" in output_file:
                validator = RequirementsValidator(schema_path)
            else:
                validator = JSONValidator(schema_path)

            return validator.validate(content)

        elif output_type == "md":
            # Markdown validation - minimal
            result = ValidationResult()
            if not content.strip():
                result.add_error("Empty markdown content")
            result.passed = result.is_valid()
            return result

        else:
            # Unknown type - just check not empty
            result = ValidationResult()
            if not content.strip():
                result.add_error("Empty output")
            result.passed = result.is_valid()
            return result

    def _handle_multiple_outputs(
        self,
        content: str,
        step_config: Dict[str, Any],
        primary_output: Path,
    ) -> None:
        """Handle steps that produce multiple output files.

        Args:
            content: LLM response content.
            step_config: Step configuration.
            primary_output: Primary output path.
        """
        output_files = step_config.get("output_files", [])

        try:
            data = json.loads(content)

            if isinstance(data, dict):
                # Split into multiple files based on config
                for output_spec in output_files:
                    if isinstance(output_spec, dict):
                        key = output_spec.get("key")
                        filename = output_spec.get("filename")
                        if key and filename and key in data:
                            file_path = self.output_dir / filename
                            file_path.write_text(
                                json.dumps(data[key], indent=2), encoding="utf-8"
                            )
                            self._log(f"Saved {key} to {filename}")
            else:
                # Single JSON object, save to primary output
                primary_output.write_text(content, encoding="utf-8")

        except json.JSONDecodeError:
            # Not JSON or parse error, save to primary output
            primary_output.write_text(content, encoding="utf-8")
            self._log("Could not parse multiple outputs, saved to primary file")


# Convenience function for CLI
async def run_step(
    step_name: str,
    config_path: str,
    output_dir: str,
    cli_inputs: Optional[Dict[str, str]] = None,
    exogenous_inputs: Optional[Dict[str, str]] = None,
    previous_outputs: Optional[Dict[str, str]] = None,
    model_level: int = 1,
    skip_validation: bool = False,
    verbose: bool = False,
    show_prompt: bool = False,
    show_response: bool = False,
    force: bool = False,
) -> Dict[str, str]:
    """Run a single pipeline step.

    Args:
        step_name: Name of step to run.
        config_path: Path to pipeline configuration.
        output_dir: Directory for outputs.
        cli_inputs: CLI input values.
        exogenous_inputs: Exogenous input files.
        previous_outputs: Outputs from previous steps.
        model_level: Model level (1-3).
        skip_validation: Skip validation.
        verbose: Print progress.
        show_prompt: Show prompt sent to LLM.
        show_response: Show response from LLM.
        force: Substitute empty string for missing inputs.

    Returns:
        Dictionary mapping output labels to output file paths.

    Raises:
        StepExecutionError: If step fails.
    """
    from prompt_pipeline.llm_client import OpenRouterClient
    from prompt_pipeline.prompt_manager import PromptManager

    # Initialize components
    api_key = "dummy"  # Will be overridden by client

    llm_client = OpenRouterClient(api_key=api_key)
    prompt_manager = PromptManager(config_path)
    executor = StepExecutor(
        llm_client=llm_client,
        prompt_manager=prompt_manager,
        output_dir=output_dir,
        model_level=model_level,
        skip_validation=skip_validation,
        verbose=verbose,
        show_prompt=show_prompt,
        show_response=show_response,
        force=force,
    )

    # Convert inputs to Path objects
    exogenous_path_inputs = None
    if exogenous_inputs:
        exogenous_path_inputs = {k: Path(v) for k, v in exogenous_inputs.items()}
    
    previous_outputs_path = None
    if previous_outputs:
        previous_outputs_path = {k: Path(v) for k, v in previous_outputs.items()}

    output_paths = await executor.execute_step(
        step_name,
        cli_inputs=cli_inputs,
        exogenous_inputs=exogenous_path_inputs,
        previous_outputs=previous_outputs_path,
    )
    
    # Convert Path objects to strings for return
    return {k: str(v) for k, v in output_paths.items()}