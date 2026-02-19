"""Pipeline Orchestrator Module for coordinating step execution."""

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

from prompt_pipeline.llm_client import OpenRouterClient
from prompt_pipeline.prompt_manager import PromptManager
from prompt_pipeline.step_executor import StepExecutor, StepExecutionError


class PipelineOrchestrator:
    """Orchestrate execution of pipeline steps.

    Handles:
    - Loading and sorting steps by order
    - Running full pipeline
    - Running individual steps
    - Input discovery and preparation
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
        outputs: Dict[str, Path] = {}
        current_file = nl_spec_path

        self._log("Starting pipeline execution...")
        print("Starting pipeline execution...")

        for step in self.steps:
            step_name = step["name"]

            # Skip revision steps in full pipeline (manual user steps)
            if step_name in self.SKIP_IN_AUTO:
                print(f"  Skipping {step_name} (manual revision step)")
                self._log(f"Skipping {step_name} - manual revision step")
                continue

            print(f"  Executing {step_name}...")
            self._log(f"Executing step: {step_name}")

            # Prepare inputs for this step
            inputs = self._prepare_inputs(step, outputs, current_file)

            # Execute step
            try:
                output_path = await self.step_executor.execute_step(
                    step_name,
                    inputs,
                )
            except StepExecutionError as e:
                print(f"  Error in {step_name}: {e}")
                raise

            # Track output
            outputs[step_name] = output_path
            current_file = output_path
            self._log(f"Step {step_name} complete: {output_path}")

        print("Pipeline execution complete!")
        self._log("Pipeline execution complete")

        # Import to TypeDB if requested
        if self.import_database:
            await self.import_to_typedb(self.output_dir)

        return outputs

    async def run_step(
        self,
        step_name: str,
        inputs: Optional[Dict[str, Path]] = None,
    ) -> Path:
        """Run a single step.

        Args:
            step_name: Name of step to run.
            inputs: Optional input files.

        Returns:
            Path to output file.

        Raises:
            StepExecutionError: If step fails.
        """
        self._log(f"Running single step: {step_name}")
        print(f"Executing step: {step_name}")

        # If no inputs provided, try to discover them
        if inputs is None:
            step_config = self.prompt_manager.get_step_config(step_name)
            if step_config:
                inputs = self._discover_inputs(step_config)

        output_path = await self.step_executor.execute_step(step_name, inputs)
        self._log(f"Step {step_name} complete: {output_path}")
        return output_path

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