"""Pipeline Orchestrator Module for coordinating step execution."""

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

from prompt_pipeline.llm_client import OpenRouterClient
from prompt_pipeline.label_registry import LabelRegistry
from prompt_pipeline.prompt_manager import PromptManager
from prompt_pipeline.step_executor import StepExecutor, StepExecutionError


class PipelineOrchestrator:
    """Orchestrate execution of pipeline steps.

    Handles:
    - Loading and sorting steps by order
    - Running full pipeline
    - Running individual steps
    - Input discovery and preparation
    - Label-based dependency resolution
    - TypeDB import integration
    - Wipe database option
    """

    # Steps to skip in automatic pipeline (manual revision steps)
    SKIP_IN_AUTO = ["step2", "step3"]

    def __init__(
        self,
        config_path: str,
        llm_client: OpenRouterClient,
        prompt_manager: PromptManager,
        step_executor: StepExecutor,
        output_dir: Path,
        import_database: Optional[str] = None,
        wipe_database: bool = False,
        verbose: bool = False,
    ):
        """Initialize pipeline orchestrator.

        Args:
            config_path: Path to pipeline configuration.
            llm_client: LLM client for API calls.
            prompt_manager: Prompt manager for configuration.
            step_executor: Step executor for running steps.
            output_dir: Directory for output files.
            import_database: Optional database name to import to.
            wipe_database: If True, wipe database before import.
            verbose: If True, print detailed progress.
        """
        self.config_path = config_path
        self.llm_client = llm_client
        self.prompt_manager = prompt_manager
        self.step_executor = step_executor
        self.output_dir = Path(output_dir)
        self.import_database = import_database
        self.wipe_database = wipe_database
        self.verbose = verbose
        self.steps = self._load_and_sort_steps()
        self.label_registry = LabelRegistry()
        self._initialize_label_registry()

    def _load_and_sort_steps(self) -> List[Dict[str, Any]]:
        """Load and sort steps by order field.

        Returns:
            List of step configurations sorted by order.
        """
        steps = self.prompt_manager.get_all_steps()
        return sorted(steps, key=lambda s: s.get("order", 999))

    def _log(self, message: str) -> None:
        """Log message if verbose mode is enabled."""
        if self.verbose:
            print(f"[Orchestrator] {message}")

    def _initialize_label_registry(self) -> None:
        """Initialize label registry from pipeline configuration.
        
        Loads output labels from the configuration and registers them
        in the label registry with placeholder paths. Actual file paths
        will be updated as steps execute.
        """
        config = self.prompt_manager.get_config()
        if config and "output_labels" in config:
            self.label_registry.merge_from_config(config)
            self._log(f"Initialized label registry with {len(self.label_registry)} labels")
    
    async def run_pipeline(
        self,
        nl_spec_path: Path,
    ) -> Dict[str, Path]:
        """Run full pipeline from NL spec to final outputs.

        Args:
            nl_spec_path: Path to NL specification file.

        Returns:
            Dictionary mapping step names to output paths.

        Raises:
            StepExecutionError: If any step fails.
        """
        self._log("Starting pipeline execution...")
        print("Starting pipeline execution...")

        # Register the initial NL spec as an exogenous input with label "nl_spec"
        exogenous_inputs = {"nl_spec": nl_spec_path}

        for step in self.steps:
            step_name = step["name"]

            # Skip revision steps in full pipeline (manual user steps)
            if step_name in self.SKIP_IN_AUTO:
                print(f"  Skipping {step_name} (manual revision step)")
                self._log(f"Skipping {step_name} - manual revision step")
                continue

            print(f"  Executing {step_name}...")
            self._log(f"Executing step: {step_name}")

            # Execute step with label registry
            try:
                output_paths = await self.step_executor.execute_step(
                    step_name=step_name,
                    cli_inputs={},
                    exogenous_inputs=exogenous_inputs,
                    previous_outputs=self._get_previous_outputs(step_name),
                )
            except StepExecutionError as e:
                print(f"  Error in {step_name}: {e}")
                raise

            # Update label registry with actual output paths
            for label, output_path in output_paths.items():
                self.label_registry.update_label_file(label, output_path)
                self._log(f"Registered output: {label} -> {output_path}")

            # Update exogenous_inputs with outputs from this step
            # (these become available for subsequent steps)
            for label, output_path in output_paths.items():
                exogenous_inputs[label] = output_path

            self._log(f"Step {step_name} complete")

        print("Pipeline execution complete!")
        self._log("Pipeline execution complete")

        # Import to TypeDB if requested
        if self.import_database:
            await self.import_to_typedb(self.output_dir)

        # Return all outputs from registry
        outputs = {}
        for label, info in self.label_registry._labels.items():
            if info.file_path.exists() and info.file_path != nl_spec_path:
                outputs[label] = info.file_path

        return outputs

    async def run_step(
        self,
        step_name: str,
        inputs: Optional[Dict[str, Path]] = None,
    ) -> Path:
        """Run a single step (backward compatibility wrapper).

        Args:
            step_name: Name of step to run.
            inputs: Optional input files.

        Returns:
            Path to output file.

        Raises:
            StepExecutionError: If step fails.
        """
        output_paths = await self.run_step_with_inputs(
            step_name=step_name,
            cli_inputs={},
            exogenous_inputs=inputs or {},
            previous_outputs=self._get_previous_outputs(step_name),
        )
        
        # Return the first output path (for backward compatibility)
        if output_paths:
            first_output = list(output_paths.values())[0]
            self._log(f"Step {step_name} complete: {first_output}")
            return first_output
        
        raise StepExecutionError(f"No outputs generated for step {step_name}")

    async def run_step_with_inputs(
        self,
        step_name: str,
        cli_inputs: Optional[Dict[str, str]] = None,
        exogenous_inputs: Optional[Dict[str, Path]] = None,
        previous_outputs: Optional[Dict[str, Path]] = None,
    ) -> Dict[str, Path]:
        """Run a single step with the new input format.

        Args:
            step_name: Name of step to run.
            cli_inputs: CLI input values (from --input-file, --input-prompt, --input-text).
            exogenous_inputs: Exogenous input files (from config or CLI overrides).
            previous_outputs: Outputs from previous steps (for label resolution).

        Returns:
            Dictionary mapping output labels to output file paths.

        Raises:
            StepExecutionError: If step fails.
        """
        self._log(f"Running single step: {step_name}")
        print(f"Executing step: {step_name}")

        # Execute step
        try:
            output_paths = await self.step_executor.execute_step(
                step_name=step_name,
                cli_inputs=cli_inputs or {},
                exogenous_inputs=exogenous_inputs or {},
                previous_outputs=previous_outputs or {},
            )
        except StepExecutionError as e:
            print(f"  Error in {step_name}: {e}")
            raise

        # Update label registry with actual output paths
        for label, output_path in output_paths.items():
            self.label_registry.update_label_file(label, output_path)
            self._log(f"Registered output: {label} -> {output_path}")

        self._log(f"Step {step_name} complete")
        return output_paths

    def _prepare_inputs(
        self,
        step: Dict[str, Any],
        outputs: Dict[str, Path],
        current_file: Path,
    ) -> Dict[str, Path]:
        """Prepare inputs for a step based on its configuration.

        Args:
            step: Step configuration.
            outputs: Dictionary of previous outputs.
            current_file: Current file (latest output).

        Returns:
            Dictionary of input paths.
        """
        inputs: Dict[str, Path] = {}

        # Get required input types from step config
        required_inputs = self.prompt_manager.get_required_inputs(step["name"])

        for input_type in required_inputs:
            if input_type == "nl_spec":
                inputs["nl_spec"] = current_file
            elif input_type == "spec_file":
                # Use the current file (latest output)
                inputs["spec_file"] = current_file
            elif input_type == "concepts_file":
                # Find concepts.json from outputs or from output directory
                concepts_path = self._find_file(outputs, self.output_dir, "concepts.json")
                inputs["concepts_file"] = concepts_path
            elif input_type == "aggregations_file":
                aggs_path = self._find_file(outputs, self.output_dir, "aggregations.json")
                inputs["aggregations_file"] = aggs_path
            elif input_type == "messages_file":
                messages_path = self._find_file(outputs, self.output_dir, "messages.json")
                inputs["messages_file"] = messages_path

        return inputs

    def _discover_inputs(self, step_config: Dict[str, Any]) -> Dict[str, Path]:
        """Discover input files for a step from output directory.

        Args:
            step_config: Step configuration.

        Returns:
            Dictionary of discovered input paths.
        """
        inputs: Dict[str, Path] = {}
        required_inputs = self.prompt_manager.get_required_inputs(
            step_config.get("name", "")
        )

        for input_type in required_inputs:
            if input_type == "concepts_file":
                path = self.output_dir / "concepts.json"
                if path.exists():
                    inputs["concepts_file"] = path
            elif input_type == "aggregations_file":
                path = self.output_dir / "aggregations.json"
                if path.exists():
                    inputs["aggregations_file"] = path
            elif input_type == "messages_file":
                path = self.output_dir / "messages.json"
                if path.exists():
                    inputs["messages_file"] = path
            elif input_type == "spec_file":
                # Try to find spec file
                for f in self.output_dir.glob("spec*.yaml"):
                    inputs["spec_file"] = f
                    break
            elif input_type == "nl_spec":
                for f in self.output_dir.glob("nl_spec*"):
                    inputs["nl_spec"] = f
                    break

        return inputs

    def _get_previous_outputs(self, current_step: str) -> Dict[str, Path]:
        """Get outputs from all steps before the current step.
        
        This is used to provide previous_outputs to the step executor,
        which can then resolve label references.
        
        Args:
            current_step: Name of the current step.
            
        Returns:
            Dictionary mapping labels to output file paths for all
            steps that have executed before the current step.
        """
        previous_outputs = {}
        
        # Get the order of the current step
        current_order = None
        for step in self.steps:
            if step["name"] == current_step:
                current_order = step.get("order", 0)
                break
        
        if current_order is None:
            return previous_outputs
        
        # Collect outputs from all steps with lower order
        for label, info in self.label_registry._labels.items():
            # Skip if this is the NL spec input (not an output)
            if info.file_path == Path():
                continue
            
            # Only include outputs from steps that come before the current step
            if info.order < current_order and info.file_path.exists():
                previous_outputs[label] = info.file_path
        
        return previous_outputs
    
    def _find_file(
        self,
        outputs: Dict[str, Path],
        output_dir: Path,
        filename: str,
    ) -> Path:
        """Find a file in outputs or output directory.

        Args:
            outputs: Dictionary of step outputs.
            output_dir: Output directory.
            filename: Filename to find.

        Returns:
            Path to found file.

        Raises:
            FileNotFoundError: If file not found.
        """
        # Check outputs first
        for step_name, path in outputs.items():
            if path.name == filename:
                return path

        # Check output directory
        filepath = output_dir / filename
        if filepath.exists():
            return filepath

        raise FileNotFoundError(f"Required file not found: {filename}")

    async def import_to_typedb(self, output_dir: Path) -> None:
        """Import generated files to TypeDB.

        Args:
            output_dir: Directory containing output files.
        """
        print(f"Importing to TypeDB database: {self.import_database}")
        self._log(f"Starting TypeDB import to {self.import_database}")

        # Check if database exists
        # Wipe if requested
        # Create if doesn't exist
        # Import schema
        # Import each file
        # Create relations

        # This will integrate with existing tools/typedb_import.py
        # Placeholder - actual implementation in CLI commands
        self._log("TypeDB import not yet implemented in orchestrator")

    def get_step_order(self) -> List[str]:
        """Get ordered list of step names.

        Returns:
            List of step names in execution order.
        """
        return [step["name"] for step in self.steps]

    def get_step_config(self, step_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific step.

        Args:
            step_name: Name of step.

        Returns:
            Step configuration or None if not found.
        """
        for step in self.steps:
            if step["name"] == step_name:
                return step
        return None


# Convenience function
async def run_pipeline(
    config_path: str,
    nl_spec_path: str,
    output_dir: str,
    model_level: int = 1,
    skip_validation: bool = False,
    import_database: Optional[str] = None,
    wipe_database: bool = False,
    verbose: bool = False,
) -> Dict[str, str]:
    """Run full pipeline.

    Args:
        config_path: Path to pipeline configuration.
        nl_spec_path: Path to NL specification file.
        output_dir: Directory for outputs.
        model_level: Model level (1-3).
        skip_validation: Skip validation.
        import_database: Optional database name to import to.
        wipe_database: If True, wipe database before import.
        verbose: Print progress.

    Returns:
        Dictionary mapping step names to output paths.
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

    orchestrator = PipelineOrchestrator(
        config_path=config_path,
        llm_client=llm_client,
        prompt_manager=prompt_manager,
        step_executor=executor,
        output_dir=output_dir,
        import_database=import_database,
        wipe_database=wipe_database,
        verbose=verbose,
    )

    outputs = await orchestrator.run_pipeline(Path(nl_spec_path))
    return {k: str(v) for k, v in outputs.items()}