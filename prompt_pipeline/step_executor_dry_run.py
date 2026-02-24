"""Dry-run prompt generation functionality for StepExecutor."""

from pathlib import Path
from typing import Dict, Any, Optional

from prompt_pipeline.compression import CompressionManager, CompressionContext, CompressionConfig
from prompt_pipeline.prompt_manager import PromptManager
from prompt_pipeline.tag_replacement import TagReplacer


class DryRunResult:
    """Result of a dry-run prompt construction."""
    
    def __init__(
        self,
        step_name: str,
        prompt_file: str,
        persona: str,
        step_number: int,
        cli_inputs: Dict[str, str],
        exogenous_inputs: Dict[str, Path],
        previous_outputs: Dict[str, Path],
        full_prompt: str,
        compression_metrics: Optional[Dict[str, Any]] = None,
    ):
        self.step_name = step_name
        self.prompt_file = prompt_file
        self.persona = persona
        self.step_number = step_number
        self.cli_inputs = cli_inputs
        self.exogenous_inputs = exogenous_inputs
        self.previous_outputs = previous_outputs
        self.full_prompt = full_prompt
        self.compression_metrics = compression_metrics or {}
        self.preamble_length = 0
        self.prompt_file_length = 0
        self.input_variables_length = 0
        self.total_length = len(full_prompt)
        
        # Calculate breakdown if possible
        # The full_prompt contains preamble + prompt + substituted variables
        # We can't easily split it back out, but we can estimate
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        # Calculate total compression metrics
        total_original = sum(m.get("original_length", 0) for m in self.compression_metrics.values())
        total_compressed = sum(m.get("compressed_length", 0) for m in self.compression_metrics.values())
        overall_ratio = total_compressed / total_original if total_original > 0 else 1.0
        
        return {
            "step_name": self.step_name,
            "prompt_file": self.prompt_file,
            "persona": self.persona,
            "step_number": self.step_number,
            "cli_inputs": {
                label: {
                    "content_length": len(content),
                    "preview": content[:100] + "..." if len(content) > 100 else content
                }
                for label, content in self.cli_inputs.items()
            },
            "exogenous_inputs": {
                label: str(path)
                for label, path in self.exogenous_inputs.items()
            },
            "previous_outputs": {
                label: str(path)
                for label, path in self.previous_outputs.items()
            },
            "prompt_lengths": {
                "total": self.total_length,
                "preamble": self.preamble_length,
                "prompt_file": self.prompt_file_length,
                "input_variables": self.input_variables_length,
            },
            "compression_metrics": self.compression_metrics,
            "overall_compression": {
                "total_original": total_original,
                "total_compressed": total_compressed,
                "overall_ratio": overall_ratio,
            },
            "full_prompt_preview": self.full_prompt[:500] + "..." if len(self.full_prompt) > 500 else self.full_prompt,
        }


def construct_prompt_without_api_call(
    step_name: str,
    cli_inputs: Optional[Dict[str, str]] = None,
    exogenous_inputs: Optional[Dict[str, Path]] = None,
    previous_outputs: Optional[Dict[str, Path]] = None,
    prompt_manager: Optional[PromptManager] = None,
    force: bool = False,
) -> DryRunResult:
    """
    Construct the complete prompt without making any API calls.
    
    This function mirrors the logic in StepExecutor.execute_step() but stops
    before the LLM API call, allowing users to inspect the full prompt that
    would be sent.
    
    Args:
        step_name: Name of the step to execute.
        cli_inputs: CLI input values (text content).
        exogenous_inputs: Exogenous input files (file paths).
        previous_outputs: Outputs from previous steps (for label resolution).
        prompt_manager: PromptManager instance.
        force: If True, substitute empty strings for missing tags.
    
    Returns:
        DryRunResult containing the complete prompt and metadata.
    
    Raises:
        ValueError: If step not found or input missing.
    """
    if cli_inputs is None:
        cli_inputs = {}
    if exogenous_inputs is None:
        exogenous_inputs = {}
    if previous_outputs is None:
        previous_outputs = {}
    
    if prompt_manager is None:
        raise ValueError("PromptManager is required")
    
    # Get step configuration
    step_config = prompt_manager.get_step_config(step_name)
    if not step_config:
        raise ValueError(f"Step '{step_name}' not found in configuration")
    
    # Prepare variables from inputs
    inputs_config = step_config.get("inputs", [])
    variables = {}
    compression_metrics = {}
    
    for input_spec in inputs_config:
        label = input_spec.get("label")
        input_type = input_spec.get("type", "text")
        source = input_spec.get("source", "cli")
        compression = input_spec.get("compression", "full")
        
        # Resolve content based on source with priority order:
        # 1. CLI inputs (highest)
        # 2. Exogenous inputs (from config or CLI overrides)
        # 3. Previous step outputs (label references)
        content = None
        
        # Check CLI inputs first (highest priority)
        if label in cli_inputs:
            content = cli_inputs[label]
        
        # Check exogenous inputs (second priority)
        elif label in exogenous_inputs:
            file_path = exogenous_inputs[label]
            content = file_path.read_text(encoding="utf-8")
        
        # Source is in format "label:NAME" for previous step outputs
        elif source.startswith("label:"):
            ref_label = source[6:]
            if ref_label in previous_outputs:
                file_path = previous_outputs[ref_label]
                content = file_path.read_text(encoding="utf-8")
        
        # CLI input - check cli_inputs dict
        elif source == "cli":
            if label in cli_inputs:
                content = cli_inputs[label]
        
        # File input - check exogenous_inputs
        elif source == "file":
            if label in exogenous_inputs:
                file_path = exogenous_inputs[label]
                content = file_path.read_text(encoding="utf-8")
        
        # Finally check previous outputs
        elif label in previous_outputs:
            file_path = previous_outputs[label]
            content = file_path.read_text(encoding="utf-8")
        
        if content is not None:
            # Apply compression if specified
            compressed_content, metrics = _apply_compression(content, compression, input_type, label)
            variables[label] = compressed_content
            compression_metrics[label] = metrics
        elif force:
            variables[label] = ""
        else:
            # Generate descriptive error message
            error_msg = _generate_missing_input_error_message(
                label=label,
                source=source,
                input_type=input_type,
                compression=compression,
                cli_inputs=cli_inputs,
                exogenous_inputs=exogenous_inputs,
                previous_outputs=previous_outputs,
                step_name=step_name,
            )
            raise ValueError(error_msg)
    
    # In force mode, add empty strings for missing tags
    if force:
        prompt_file = step_config.get("prompt_file")
        if prompt_file:
            prompt_template = prompt_manager.load_prompt(prompt_file)
            replacer = TagReplacer(prompt_template)
            required_tags = replacer.get_required_tags()
            for tag in required_tags:
                if tag not in variables:
                    variables[tag] = ""
    
    # Load prompt with preamble and substitute variables
    filled_prompt = prompt_manager.get_prompt_with_variables(
        step_name=step_name,
        variables=variables,
        validate=not force,
    )
    
    # Get prompt file info
    prompt_file = step_config.get("prompt_file", "unknown")
    persona = step_config.get("persona", "software_engineer")
    step_number = step_config.get("order", 0)
    
    return DryRunResult(
        step_name=step_name,
        prompt_file=prompt_file,
        persona=persona,
        step_number=step_number,
        cli_inputs=cli_inputs,
        exogenous_inputs=exogenous_inputs,
        previous_outputs=previous_outputs,
        full_prompt=filled_prompt,
        compression_metrics=compression_metrics,
    )


def _generate_missing_input_error_message(
    label: str,
    source: str,
    input_type: str,
    compression: str,
    cli_inputs: Dict[str, str],
    exogenous_inputs: Dict[str, Path],
    previous_outputs: Dict[str, Path],
    step_name: str,
) -> str:
    """
    Generate a comprehensive error message for missing inputs.
    
    This function provides detailed information about why an input is missing,
    what sources were checked, and how to fix the issue.
    
    Args:
        label: The label of the missing input.
        source: The expected source for this input (e.g., 'cli', 'label:spec', 'file').
        input_type: Type of input (md, json, yaml, text).
        compression: Compression strategy being used.
        cli_inputs: Dictionary of CLI inputs provided.
        exogenous_inputs: Dictionary of exogenous input files provided.
        previous_outputs: Dictionary of previous step outputs.
        step_name: Name of the step being executed.
    
    Returns:
        A detailed error message explaining the problem and solutions.
    """
    # Build diagnostic information
    lines = []
    lines.append("=" * 80)
    lines.append("MISSING INPUT ERROR")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"Step: {step_name}")
    lines.append(f"Missing input: '{label}'")
    lines.append(f"Expected type: {input_type}")
    lines.append(f"Compression: {compression}")
    lines.append("")
    
    # Explain the source type
    if source.startswith("label:"):
        ref_label = source[6:]
        lines.append(f"INPUT SOURCE: Previous step output (label: {ref_label})")
        lines.append("")
        lines.append(f"This input requires output from a previous step labeled '{ref_label}'.")
        lines.append("")
        lines.append("FILES CHECKED (none found):")
        lines.append(f"  • Previous outputs: {ref_label}")
        lines.append("")
        
        # Check if we have any previous outputs at all
        if previous_outputs:
            lines.append(f"Available previous outputs: {list(previous_outputs.keys())}")
            lines.append("")
        else:
            lines.append("No previous outputs available.")
            lines.append("")
            
        lines.append("SOLUTION OPTIONS:")
        lines.append(f"  1. Run the dependent step first (RECOMMENDED):")
        lines.append(f"     prompt-pipeline run-step <dependent_step> --nl-spec <file>")
        lines.append(f"     (This will create the output file needed by {step_name})")
        lines.append("")
        
        # Map label to CLI flag name
        label_to_flag = {
            "nl_spec": "nl-spec",
            "spec": "spec-file",
            "concepts": "concepts-file",
            "aggregations": "aggregations-file",
            "messages": "messages-file",
            "requirements": "requirements-file",
        }
        cli_flag = label_to_flag.get(ref_label, f"{ref_label.replace('_', '-')}-file")
        
        lines.append(f"  2. Provide the file directly using --{cli_flag}:")
        lines.append(f"     prompt-pipeline run-step {step_name} --{cli_flag} <path_to_file>")
        lines.append("")
        lines.append(f"  3. Use --force to substitute empty strings (may produce poor results):")
        lines.append(f"     prompt-pipeline run-step {step_name} --nl-spec <file> --force")
        lines.append("")
        lines.append("DEPENDENCY ANALYSIS:")
        lines.append(f"  • {step_name} depends on step producing '{ref_label}'")
        lines.append(f"  • Based on pipeline_config.yaml, label '{ref_label}' comes from an earlier step")
        lines.append(f"  • You must run that step first, or provide the file manually")
        
    elif source == "cli":
        lines.append("INPUT SOURCE: CLI input (--nl-spec or similar)")
        lines.append("")
        lines.append("This input expects direct text content from the command line.")
        lines.append("")
        lines.append("SOLUTION:")
        lines.append(f"  • You must provide this input via command line option")
        lines.append(f"  • Check available CLI options for {step_name}")
        lines.append("")
        lines.append("CURRENTLY PROVIDED CLI INPUTS:")
        if cli_inputs:
            for key in cli_inputs.keys():
                lines.append(f"  • {key}")
        else:
            lines.append("  (none)")
        lines.append("")
        
    elif source == "file":
        lines.append("INPUT SOURCE: File input")
        lines.append("")
        lines.append("This input expects a file to be provided.")
        lines.append("")
        lines.append("SOLUTION:")
        lines.append(f"  • Provide the file using --{label.replace('_', '-')}-file option")
        lines.append("")
        
    else:
        lines.append(f"INPUT SOURCE: {source}")
        lines.append("")
    
    # Show what was actually provided
    lines.append("WHAT WAS PROVIDED:")
    lines.append(f"  CLI inputs: {list(cli_inputs.keys())}")
    lines.append(f"  Exogenous inputs: {list(exogenous_inputs.keys())}")
    lines.append(f"  Previous outputs: {list(previous_outputs.keys())}")
    lines.append("")
    
    # Additional context
    lines.append("STEP CONFIGURATION:")
    lines.append(f"  This step ({step_name}) requires this input as per pipeline_config.yaml")
    lines.append("")
    
    lines.append("=" * 80)
    lines.append("")
    
    return "\n".join(lines)


def _apply_compression(
    content: str,
    compression: str,
    input_type: str,
    label: Optional[str] = None,
) -> tuple[str, dict]:
    """Apply compression to content.
    
    Args:
        content: Content to compress.
        compression: Compression strategy name.
        input_type: Input type (md, json, yaml, text).
        label: Optional label for the input (for better logging).
    
    Returns:
        Tuple of (compressed_content, metrics_dict)
    """
    # Handle no compression
    if compression in ("full", "none", None, ""):
        return content, {"original_length": len(content), "compressed_length": len(content), "compression_ratio": 1.0, "strategy": "none"}
    
    # Apply compression using CompressionManager
    try:
        # Create compression manager
        manager = CompressionManager()
        
        # Create compression config
        config = CompressionConfig(
            strategy=compression,
            level=2,  # Default to medium compression
        )
        
        # Create compression context
        context = CompressionContext(
            content_type=input_type,
            label=label or "input",
            level=2,  # Default to medium compression
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
        
        return result.content, metrics
        
    except Exception as e:
        # If compression fails, return original content
        return content, {
            "original_length": len(content),
            "compressed_length": len(content),
            "compression_ratio": 1.0,
            "strategy": "none",
            "error": str(e),
        }
