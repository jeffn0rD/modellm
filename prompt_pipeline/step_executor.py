"""Step Executor Module for individual pipeline step execution."""

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from prompt_pipeline.compression import CompressionManager, CompressionContext, CompressionConfig
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
    YAMLSchemaValidator,
)
from prompt_pipeline.validation.json_validator import JSONValidator
import yaml


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
        
        variables, compression_metrics = self._prepare_variables_from_config(
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
            
            # Display compression metrics if available
            if compression_metrics:
                print_header("COMPRESSION METRICS", Color.YELLOW)
                total_original = sum(m.get("original_length", 0) for m in compression_metrics.values())
                total_compressed = sum(m.get("compressed_length", 0) for m in compression_metrics.values())
                overall_ratio = total_compressed / total_original if total_original > 0 else 1.0
                
                print_info(f"Overall compression: {total_original} -> {total_compressed} ({overall_ratio:.3f} ratio)")
                for label, metrics in compression_metrics.items():
                    strategy = metrics.get("strategy", "none")
                    if strategy != "none":
                        ratio = metrics.get("compression_ratio", 1.0)
                        print_info(f"  {label}: {strategy} ({ratio:.3f} ratio)")
            
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

        # Get output labels from step config
        output_configs = step_config.get("outputs", [])
        output_paths = {}

        # Process each output
        for output_config in output_configs:
            output_label = output_config.get('label')
            
            # Get filename and type from data_entities
            data_entity = self.prompt_manager.get_data_entity(output_label)
            if not data_entity:
                raise StepExecutionError(
                    f"No data_entity defined for output label '{output_label}'"
                )
            
            filename = data_entity.get('filename')
            output_type = data_entity.get('type')
            
            # Convert response if needed (e.g., JSON to YAML)
            processed_response = self._convert_response_if_needed(
                response, output_label
            )
            
            # Save to file
            output_path = self.output_dir / filename
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(processed_response)
            
            output_paths[output_label] = output_path
            self._log(f"Saved output '{output_label}' to {filename}")

        # Validate output if not skipped
        if not self.skip_validation and step_config.get('validation', {}).get('enabled', False):
            self._log("Validating outputs...")
            
            # Validate each output
            for output_config in output_configs:
                output_label = output_config.get('label')
                output_path = output_paths[output_label]
                data_entity = self.prompt_manager.get_data_entity(output_label)
                output_type = data_entity.get('type')
                
                validation_result = self._validate_output(
                    output_path, output_type, data_entity, step_name
                )
                
                if not validation_result.is_valid:
                    # Output is already saved (as requested)
                    error_details = []
                    if validation_result.errors:
                        error_details.append("Errors:")
                        for error in validation_result.errors:
                            error_details.append(f"  - {error}")
                    
                    error_msg = f"Step '{step_name}' failed validation for output '{output_label}'\n" + "\n".join(error_details)
                    
                    print_error(
                        f"✗ Validation failed for {output_label}!\n"
                        f"  Output saved to: {output_path}\n"
                        f"  Errors:\n" + "\n".join(validation_result.errors)
                    )
                    
                    raise StepExecutionError(
                        error_msg,
                        validation_result.errors,
                        validation_result.warnings,
                    )
        
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
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Prepare variables for prompt substitution from new input format.

        Args:
            inputs_config: List of input configurations from step config.
            cli_inputs: CLI input values (from --input-file, --input-prompt, --input-text).
            exogenous_inputs: Exogenous input files (from config or CLI overrides).
            previous_outputs: Outputs from previous steps (for label resolution).
            step_config: Step configuration.

        Returns:
            Tuple of (variables_dict, compression_metrics_dict)
        """
        variables = {}
        compression_metrics = {}
        
        for input_spec in inputs_config:
            label = input_spec.get("label")
            input_type = input_spec.get("type", "text")
            source = input_spec.get("source", "cli")
            compression = input_spec.get("compression", "full")
            compression_params = input_spec.get("compression_params", {})
            
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
            
            # Apply compression if specified
            if content is not None:
                compressed_content, metrics = self._apply_compression(
                    content, compression, input_type, label, compression_params
                )
                variables[label] = compressed_content
                compression_metrics[label] = metrics
            elif self.force:
                # If force mode and input missing, substitute empty string
                variables[label] = ""
            else:
                raise StepExecutionError(
                    f"Missing required input for label '{label}' from source '{source}'"
                )
        
        return variables, compression_metrics

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
        # Check CLI inputs first (highest priority)
        if label in cli_inputs:
            return cli_inputs[label]
        
        # Check exogenous inputs (second priority)
        if label in exogenous_inputs:
            file_path = exogenous_inputs[label]
            return self._load_file_content(file_path, input_type)
        
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
        label: Optional[str] = None,
        compression_params: Optional[Dict[str, Any]] = None,
    ) -> tuple[str, dict]:
        """Apply compression to content.

        Args:
            content: Content to compress.
            compression: Compression strategy name.
            input_type: Input type (md, json, yaml, text).
            label: Optional label for the input (for better logging).
            compression_params: Optional compression parameters (e.g., truncation_length).

        Returns:
            Tuple of (compressed_content, metrics_dict)
        """
        # Handle no compression
        if compression in ("full", "none", None, ""):
            return content, {
                "original_length": len(content),
                "compressed_length": len(content),
                "compression_ratio": 1.0,
                "strategy": "none",
            }
        
        # Apply compression using CompressionManager
        try:
            # Create compression manager
            manager = CompressionManager()
            
            # Create compression config
            config = CompressionConfig(
                strategy=compression,
                level=2,  # Default to medium compression
            )
            
            # Extract truncation_length from compression_params if provided
            if compression_params and "truncation_length" in compression_params:
                config.truncation_length = compression_params["truncation_length"]
            
            # Extract level from compression_params if provided
            level = 2  # Default to medium compression
            if compression_params and "level" in compression_params:
                level = compression_params["level"]
            
            # Create compression context
            context = CompressionContext(
                content_type=input_type,
                label=label or "input",
                level=level,
            )
            
            # Apply compression
            result = manager.compress(content, config)
            
            # Build metrics
            metrics = {
                "original_length": result.original_length,
                "compressed_length": result.compressed_length,
                "compression_ratio": result.compression_ratio,
                "strategy": compression,
            }
            
            # Log compression metrics
            if self.verbose:
                self._log(
                    f"Applied '{compression}' compression: "
                    f"{result.original_length} -> {result.compressed_length} "
                    f"({result.compression_ratio:.3f} ratio)"
                )
            
            return result.content, metrics
            
        except Exception as e:
            # If compression fails, log and return original content
            self._log(f"Compression '{compression}' failed: {e}, using full content")
            return content, {
                "original_length": len(content),
                "compressed_length": len(content),
                "compression_ratio": 1.0,
                "strategy": "none",
                "error": str(e),
            }

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

    def _extract_json_from_response(
        self,
        response: str,
        output_label: str,
    ) -> str:
        """
        Extract JSON from LLM response if it contains reasoning section.

        Some prompts output reasoning followed by JSON in format:
        **Part 1 – Reasoning**: ...
        **Part 2 – Final JSON**:
        <json>

        Args:
            response: LLM response string.
            output_label: Output label for this response.

        Returns:
            Extracted JSON string.
        """
        # Try to find JSON markers in the response
        # Common patterns:
        # - "Final JSON:" or "**Part 2 – Final JSON**:"
        # - "Final JSON array:" or just JSON starting with [ or {
        
        json_patterns = [
            r'\*\*Part 2 – Final JSON\*\*:?\s*(\{[\s\S]*\}|\[[\s\S]*\])',
            r'Final JSON:?\s*(\{[\s\S]*\}|\[[\s\S]*\])',
            r'Final JSON array:?\s*(\{[\s\S]*\}|\[[\s\S]*\])',
            r'JSON Response:?\s*(\{[\s\S]*\}|\[[\s\S]*\])',
        ]
        
        for pattern in json_patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
            if match:
                json_str = match.group(1).strip()
                # Validate it's actually valid JSON
                try:
                    json.loads(json_str)
                    return json_str
                except json.JSONDecodeError:
                    continue
        
        # If no pattern matched, try to find valid JSON in the response
        # Look for first { or [ and try to parse from there
        for i, char in enumerate(response):
            if char in '{[':
                try:
                    json_str = response[i:]
                    json.loads(json_str)
                    return json_str
                except json.JSONDecodeError:
                    continue
        
        # If still no JSON found, check if response itself is valid JSON
        try:
            json.loads(response)
            return response
        except json.JSONDecodeError:
            # No valid JSON found
            return None
    
    def _convert_response_if_needed(
        self,
        response: str,
        output_label: str,
    ) -> str:
        """
        Convert LLM response if conversion is required.
        E.g., JSON back to YAML.

        Args:
            response: LLM response string.
            output_label: Output label for this response.

        Returns:
            Processed response string.
        """
        # Get data entity for this output label
        data_entity = self.prompt_manager.get_data_entity(output_label)
        if not data_entity:
            return response
        
        # Check if we need to convert based on data_entity type
        output_type = data_entity.get('type')
        
        # For JSON outputs, extract JSON from response if needed
        if output_type == 'json':
            extracted_json = self._extract_json_from_response(response, output_label)
            if extracted_json:
                return extracted_json
        
        # For YAML outputs that were converted to JSON, convert back
        if output_type == 'yaml':
            # First, try to extract JSON from the response
            extracted_json = self._extract_json_from_response(response, output_label)
            if extracted_json:
                response = extracted_json
            
            # Parse response as JSON and convert to YAML
            try:
                json_data = json.loads(response)
                
                # Convert to YAML
                yaml_output = yaml.safe_dump(
                    json_data,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )
                
                return yaml_output
                
            except json.JSONDecodeError:
                # Response is not JSON, might be a non-JSON error message
                # Save the raw response anyway (with .raw.json suffix for debugging)
                raw_path = self.output_dir / f"{output_label}.raw.json"
                raw_path.parent.mkdir(parents=True, exist_ok=True)
                with open(raw_path, 'w', encoding='utf-8') as f:
                    f.write(response)
                self._log(f"Response for '{output_label}' is not valid JSON, saved raw response to {raw_path}")
                
                # Re-raise with descriptive error
                raise StepExecutionError(
                    f"LLM response for '{output_label}' is not valid JSON.\n"
                    f"Raw response saved to: {raw_path}\n"
                    f"Note: The model may have returned an error message or non-JSON output.\n"
                    f"Check the raw response for details.",
                    errors=["Invalid JSON response from LLM"],
                    warnings=[f"Raw response saved to {raw_path}"]
                )
            except Exception as e:
                raise StepExecutionError(
                    f"Error converting JSON to YAML for '{output_label}': {e}",
                    errors=[f"Conversion error: {e}"]
                )
        
        # For other types, return response as-is
        return response

    def _validate_output(
        self,
        output_path: Path,
        output_type: str,
        data_entity: Dict[str, Any],
        step_name: str,
    ) -> ValidationResult:
        """
        Validate an output file based on type and schema.

        Args:
            output_path: Path to output file.
            output_type: Type of output (yaml, json, md, text).
            data_entity: Data entity configuration from config.
            step_name: Step name for context.

        Returns:
            ValidationResult with errors and warnings.
        """
        if output_type == 'yaml':
            yaml_schema = data_entity.get('yaml_schema')
            if yaml_schema:
                validator = YAMLSchemaValidator()
                return validator.validate_yaml_file(
                    output_path,
                    Path(yaml_schema)
                )
            else:
                # YAML without schema - basic syntax check
                validator = YAMLValidator()
                return validator.validate_file(output_path)
        
        elif output_type == 'json':
            schema_file = data_entity.get('schema')
            if schema_file:
                validator = JSONValidator(schema_file)
                return validator.validate_file(output_path)
            else:
                # JSON without schema - basic syntax check
                validator = JSONValidator()
                return validator.validate_file(output_path)
        
        elif output_type == 'md' or output_type == 'text':
            # Markdown/text - minimal validation (check not empty)
            result = ValidationResult()
            try:
                content = output_path.read_text(encoding='utf-8')
                if not content.strip():
                    result.add_error(f"Empty {output_type} content")
                result.passed = result.is_valid()
            except Exception as e:
                result.add_error(f"Could not read file: {e}")
                result.passed = False
            return result
        
        else:
            # Unknown type - pass for now
            return ValidationResult(
                is_valid=True,
                message=f"No validation for type '{output_type}'"
            )


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