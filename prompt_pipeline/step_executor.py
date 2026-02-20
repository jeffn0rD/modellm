"""Step Executor Module for individual pipeline step execution."""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from prompt_pipeline.llm_client import OpenRouterClient
from prompt_pipeline.prompt_manager import PromptManager
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

    async def execute_step(
        self,
        step_name: str,
        inputs: Optional[Dict[str, Path]] = None,
    ) -> Path:
        """Execute a single step.

        Args:
            step_name: Name of the step to execute.
            inputs: Optional dictionary of input file paths.

        Returns:
            Path to output file.

        Raises:
            StepExecutionError: If step execution fails.
        """
        inputs = inputs or {}
        self._log(f"Executing step: {step_name}")

        # Get step configuration
        step_config = self.prompt_manager.get_step_config(step_name)
        if not step_config:
            raise StepExecutionError(f"Step '{step_name}' not found in configuration")

        # Load prompt from configured file
        prompt_file = step_config.get("prompt_file")
        if not prompt_file:
            raise StepExecutionError(
                f"Step '{step_name}' has no prompt_file configured"
            )

        self._log(f"Loading prompt: {prompt_file}")
        prompt = self.prompt_manager.load_prompt(prompt_file)

        # Prepare variables for substitution
        variables = self._prepare_variables(inputs, step_config)

        # Substitute variables in prompt
        filled_prompt = self.prompt_manager.substitute_variables(prompt, variables)
        self._log(f"Prompt variables substituted")

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

        # Determine output path (use output_file override if provided, otherwise use config)
        if self.output_file:
            output_path = Path(self.output_file)
        else:
            output_filename = step_config.get("output_file", f"{step_name}_output.txt")
            output_path = self.output_dir / output_filename

        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

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
                    # Production mode: fail
                    raise StepExecutionError(
                        error_msg,
                        validation_result.errors,
                        validation_result.warnings,
                    )
            else:
                self._log("Validation passed")
        else:
            self._log("Validation skipped")

        # Handle multiple output files (for stepC5)
        if "output_files" in step_config:
            self._handle_multiple_outputs(response, step_config, output_path)
        else:
            # Save response to output file
            output_path.write_text(response, encoding="utf-8")

        self._log(f"Output saved to: {output_path}")
        return output_path

    def _log(self, message: str) -> None:
        """Log message if verbose mode is enabled."""
        if self.verbose:
            print(f"[StepExecutor] {message}")

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
    inputs: Optional[Dict[str, str]] = None,
    model_level: int = 1,
    skip_validation: bool = False,
    verbose: bool = False,
) -> str:
    """Run a single pipeline step.

    Args:
        step_name: Name of step to run.
        config_path: Path to pipeline configuration.
        output_dir: Directory for outputs.
        inputs: Optional input files.
        model_level: Model level (1-3).
        skip_validation: Skip validation.
        verbose: Print progress.

    Returns:
        Path to output file.

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
    )

    # Convert inputs to Path objects
    input_paths = None
    if inputs:
        input_paths = {k: Path(v) for k, v in inputs.items()}

    output_path = await executor.execute_step(step_name, input_paths)
    return str(output_path)