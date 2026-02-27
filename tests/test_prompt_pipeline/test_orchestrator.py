"""Unit tests for PipelineOrchestrator class.

Tests cover:
- Pipeline execution order and sequencing
- Step failure handling
- Label registry updates
- Skip steps functionality
- Dependency resolution
- Output collection
- Step execution with various input types

Reference: CR-13 in agents/implementation_guide.md
"""

import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock

import pytest

from prompt_pipeline.orchestrator import PipelineOrchestrator
from prompt_pipeline.exceptions import StepExecutionError


@pytest.mark.unit
class TestPipelineOrchestrator:

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mocked OpenRouterClient."""
        client = Mock()
        client.call_prompt_async = AsyncMock(return_value='{"result": "test"}')
        client.default_model = "test/model"
        return client

    @pytest.fixture
    def mock_prompt_manager(self):
        """Create a mocked PromptManager."""
        manager = Mock()
        
        # Configure steps in execution order
        manager.get_all_steps.return_value = [
            {
                "name": "step1",
                "order": 1,
                "prompt_file": "prompt_step1.md",
                "inputs": [{"label": "nl_spec", "source": "file", "compression": "none"}],
                "outputs": [{"label": "spec"}],
                "validation": {"enabled": False},
            },
            {
                "name": "stepC3",
                "order": 4,
                "prompt_file": "prompt_stepC3.md",
                "inputs": [
                    {"label": "spec", "source": "label:spec", "compression": "none"},
                ],
                "outputs": [{"label": "concepts"}],
                "validation": {"enabled": False},
            },
        ]
        
        # Set up steps_config with the same data for merge_from_config
        manager.steps_config = {
            "steps": {
                "step1": manager.get_all_steps.return_value[0],
                "stepC3": manager.get_all_steps.return_value[1],
            }
        }
        
        # Mock step config retrieval
        def get_step_config_side_effect(step_name):
            if step_name == "step1":
                return manager.get_all_steps.return_value[0]
            elif step_name == "stepC3":
                return manager.get_all_steps.return_value[1]
            return None
        
        manager.get_step_config.side_effect = get_step_config_side_effect
        
        # Mock data entity retrieval
        def get_data_entity_side_effect(label):
            entities = {
                "spec": {"filename": "spec_1.yaml", "type": "yaml"},
                "concepts": {"filename": "concepts.json", "type": "json"},
            }
            return entities.get(label)
        
        manager.get_data_entity.side_effect = get_data_entity_side_effect
        
        return manager

    @pytest.fixture
    def mock_step_executor(self):
        """Create a mocked StepExecutor."""
        executor = Mock()
        executor.execute_step = AsyncMock(return_value={"output": Path("test.json")})
        return executor

    @pytest.fixture
    def orchestrator(self, mock_llm_client, mock_prompt_manager, mock_step_executor, tmp_path):
        """Create a PipelineOrchestrator instance with mocked dependencies."""
        return PipelineOrchestrator(
            config_path="test_config.yaml",
            llm_client=mock_llm_client,
            prompt_manager=mock_prompt_manager,
            step_executor=mock_step_executor,
            output_dir=tmp_path,
            import_database=None,
            wipe_database=False,
            verbose=False,
        )

    @pytest.mark.asyncio
    async def test_steps_executed_in_order(self, orchestrator, mock_step_executor, tmp_path):
        """Test steps are executed in dependency order."""
        call_order = []
        
        async def track_calls(step_name, **kwargs):
            call_order.append(step_name)
            return {step_name + "_out": tmp_path / f"{step_name}.json"}
        
        mock_step_executor.execute_step.side_effect = track_calls
        
        # Create a dummy NL spec file
        nl_spec_path = tmp_path / "nl_spec.md"
        nl_spec_path.write_text("# Test NL Spec")
        
        await orchestrator.run_pipeline(nl_spec_path)
        
        # Verify steps were called in order
        assert len(call_order) == 2
        assert call_order[0] == "step1"
        assert call_order[1] == "stepC3"

    @pytest.mark.asyncio
    async def test_step_failure_stops_pipeline(self, orchestrator, mock_step_executor, tmp_path):
        """Test that a step failure stops the pipeline."""
        # Make the first step fail
        mock_step_executor.execute_step.side_effect = StepExecutionError("Step failed")
        
        # Create a dummy NL spec file
        nl_spec_path = tmp_path / "nl_spec.md"
        nl_spec_path.write_text("# Test NL Spec")
        
        with pytest.raises(StepExecutionError, match="Step failed"):
            await orchestrator.run_pipeline(nl_spec_path)

    @pytest.mark.asyncio
    async def test_skip_steps_functionality(self, orchestrator, mock_step_executor, tmp_path):
        """Test that skip_steps functionality works."""
        call_order = []
        
        async def track_calls(step_name, **kwargs):
            call_order.append(step_name)
            return {step_name + "_out": tmp_path / f"{step_name}.json"}
        
        mock_step_executor.execute_step.side_effect = track_calls
        
        # Create a dummy NL spec file
        nl_spec_path = tmp_path / "nl_spec.md"
        nl_spec_path.write_text("# Test NL Spec")
        
        await orchestrator.run_pipeline(nl_spec_path)
        
        # Verify that revision steps (step2, step3) were skipped
        assert "step2" not in call_order
        assert "step3" not in call_order

    @pytest.mark.asyncio
    async def test_label_registry_updated(self, orchestrator, mock_step_executor, tmp_path):
        """Test that label registry is updated after each step."""
        call_order = []
        registered_labels = []
        
        async def track_calls(step_name, **kwargs):
            call_order.append(step_name)
            output_path = tmp_path / f"{step_name}.json"
            output_path.write_text('{"data": "test"}')
            return {step_name + "_out": output_path}
        
        mock_step_executor.execute_step.side_effect = track_calls
        
        # Create a dummy NL spec file
        nl_spec_path = tmp_path / "nl_spec.md"
        nl_spec_path.write_text("# Test NL Spec")
        
        await orchestrator.run_pipeline(nl_spec_path)
        
        # Verify labels were registered
        assert "spec" in orchestrator.label_registry._labels
        assert "concepts" in orchestrator.label_registry._labels

    @pytest.mark.asyncio
    async def test_previous_outputs_provided(self, orchestrator, mock_step_executor, tmp_path):
        """Test that previous outputs are provided to each step."""
        previous_outputs_received = []
        
        async def track_calls(step_name, **kwargs):
            output_path = tmp_path / f"{step_name}.json"
            output_path.write_text('{"data": "test"}')
            
            # Collect previous_outputs from kwargs
            if "previous_outputs" in kwargs:
                previous_outputs_received.append((step_name, kwargs["previous_outputs"]))
            
            return {step_name + "_out": output_path}
        
        mock_step_executor.execute_step.side_effect = track_calls
        
        # Create a dummy NL spec file
        nl_spec_path = tmp_path / "nl_spec.md"
        nl_spec_path.write_text("# Test NL Spec")
        
        await orchestrator.run_pipeline(nl_spec_path)
        
        # Verify that stepC3 received previous outputs from step1
        stepC3_calls = [call for call in previous_outputs_received if call[0] == "stepC3"]
        assert len(stepC3_calls) == 1
        # The previous_outputs should contain outputs from step1

    @pytest.mark.asyncio
    async def test_run_step_with_inputs(self, orchestrator, mock_step_executor, tmp_path):
        """Test running a single step with inputs."""
        mock_step_executor.execute_step.return_value = {
            "test_output": tmp_path / "test_output.json"
        }
        
        result = await orchestrator.run_step_with_inputs(
            step_name="step1",
            cli_inputs={"test": "value"},
            exogenous_inputs={},
            previous_outputs={},
        )
        
        assert "test_output" in result
        mock_step_executor.execute_step.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_step_with_previous_outputs(self, orchestrator, mock_step_executor, tmp_path):
        """Test running a step with previous outputs as input."""
        # Create a previous output file
        prev_output = tmp_path / "previous_output.json"
        prev_output.write_text('{"data": "from previous step"}')
        
        mock_step_executor.execute_step.return_value = {
            "test_output": tmp_path / "test_output.json"
        }
        
        result = await orchestrator.run_step_with_inputs(
            step_name="stepC3",
            cli_inputs={},
            exogenous_inputs={},
            previous_outputs={"spec": prev_output},
        )
        
        assert "test_output" in result
        # Verify the step was called with the previous outputs
        call_args = mock_step_executor.execute_step.call_args
        assert call_args.kwargs["previous_outputs"] == {"spec": prev_output}

    def test_get_step_order(self, orchestrator):
        """Test getting ordered list of step names."""
        step_order = orchestrator.get_step_order()
        
        assert len(step_order) == 2
        assert step_order[0] == "step1"
        assert step_order[1] == "stepC3"

    def test_get_step_config(self, orchestrator, mock_prompt_manager):
        """Test getting configuration for a specific step."""
        step_config = orchestrator.get_step_config("step1")
        
        assert step_config is not None
        assert step_config["name"] == "step1"
        assert step_config["order"] == 1

    def test_get_step_config_not_found(self, orchestrator):
        """Test getting configuration for non-existent step."""
        step_config = orchestrator.get_step_config("nonexistent_step")
        
        assert step_config is None

    @pytest.mark.asyncio
    async def test_output_collection(self, orchestrator, mock_step_executor, tmp_path):
        """Test that outputs are collected and returned."""
        # Create output files
        output1 = tmp_path / "spec_1.yaml"
        output1.write_text("spec: test")
        output2 = tmp_path / "concepts.json"
        output2.write_text('{"test": "data"}')
        
        mock_step_executor.execute_step.side_effect = [
            {"spec": output1},
            {"concepts": output2},
        ]
        
        # Create a dummy NL spec file
        nl_spec_path = tmp_path / "nl_spec.md"
        nl_spec_path.write_text("# Test NL Spec")
        
        outputs = await orchestrator.run_pipeline(nl_spec_path)
        
        assert len(outputs) == 2
        assert "spec" in outputs
        assert "concepts" in outputs

    @pytest.mark.asyncio
    async def test_skip_steps_not_executed(self, orchestrator, mock_step_executor, tmp_path):
        """Test that revision steps are not executed in full pipeline."""
        # Track all executed steps
        executed_steps = []
        
        async def track_calls(step_name, **kwargs):
            executed_steps.append(step_name)
            output_path = tmp_path / f"{step_name}.json"
            output_path.write_text('{"data": "test"}')
            return {step_name + "_out": output_path}
        
        mock_step_executor.execute_step.side_effect = track_calls
        
        # Create a dummy NL spec file
        nl_spec_path = tmp_path / "nl_spec.md"
        nl_spec_path.write_text("# Test NL Spec")
        
        await orchestrator.run_pipeline(nl_spec_path)
        
        # Verify that only automatic steps were executed
        assert len(executed_steps) == 2
        assert "step2" not in executed_steps
        assert "step3" not in executed_steps

    @pytest.mark.asyncio
    async def test_exogenous_inputs_for_nl_spec(self, orchestrator, mock_step_executor, tmp_path):
        """Test that NL spec is passed as exogenous input."""
        # Track the exogenous_inputs passed to execute_step
        exogenous_inputs_received = []
        
        async def track_calls(step_name, **kwargs):
            if "exogenous_inputs" in kwargs:
                exogenous_inputs_received.append((step_name, kwargs["exogenous_inputs"]))
            output_path = tmp_path / f"{step_name}.json"
            output_path.write_text('{"data": "test"}')
            return {step_name + "_out": output_path}
        
        mock_step_executor.execute_step.side_effect = track_calls
        
        # Create a dummy NL spec file
        nl_spec_path = tmp_path / "nl_spec.md"
        nl_spec_path.write_text("# Test NL Spec")
        
        await orchestrator.run_pipeline(nl_spec_path)
        
        # Verify that step1 received the NL spec as exogenous input
        step1_calls = [call for call in exogenous_inputs_received if call[0] == "step1"]
        assert len(step1_calls) == 1
        assert "nl_spec" in step1_calls[0][1]
