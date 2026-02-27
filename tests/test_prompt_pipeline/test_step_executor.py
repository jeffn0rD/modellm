"""Unit tests for StepExecutor class.

Tests cover:
- Step execution success and failure scenarios
- Input resolution and preparation
- File operations (read/write)
- JSON extraction from LLM responses
- Force mode behavior
- Compression application
- Validation triggering
- YAML output conversion
- Error handling and propagation

Reference: CR-12 in agents/implementation_guide.md
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock

import pytest
import yaml

from prompt_pipeline.step_executor import StepExecutor
from prompt_pipeline.exceptions import StepExecutionError, FileOperationError


@pytest.mark.unit
class TestStepExecutor:

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
        manager.get_step_config.return_value = {
            "name": "test_step",
            "prompt_file": "test.md",
            "order": 1,
            "inputs": [{"label": "input1", "source": "cli", "compression": "none"}],
            "outputs": [{"label": "test_output"}],
            "validation": {"enabled": False},
        }
        manager.get_prompt_with_variables.return_value = "Test prompt with input1"
        manager.get_data_entity.return_value = {
            "filename": "test_output.json",
            "type": "json"
        }
        manager.steps_config = {"model_levels": {}}
        return manager

    @pytest.fixture
    def executor(self, mock_llm_client, mock_prompt_manager, tmp_path):
        """Create a StepExecutor instance with mocked dependencies."""
        return StepExecutor(
            llm_client=mock_llm_client,
            prompt_manager=mock_prompt_manager,
            output_dir=tmp_path,
            model_level=1,
            skip_validation=True,
            verbose=False,
            show_prompt=False,
            show_response=False,
        )

    @pytest.mark.asyncio
    async def test_execute_step_success(self, executor, tmp_path):
        """Test successful step execution creates output file."""
        result = await executor.execute_step(
            step_name="test_step",
            cli_inputs={"input1": "test value"},
        )
        
        assert "test_output" in result
        assert result["test_output"].exists()
        assert result["test_output"].name == "test_output.json"

    @pytest.mark.asyncio
    async def test_execute_step_missing_input_raises(self, executor):
        """Test step execution with missing required input raises StepExecutionError."""
        with pytest.raises(StepExecutionError) as exc_info:
            await executor.execute_step(step_name="test_step", cli_inputs={})
        
        assert "Missing required input" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_step_unknown_step_raises(self, executor, mock_prompt_manager):
        """Test step execution with unknown step name raises StepExecutionError."""
        mock_prompt_manager.get_step_config.return_value = None
        
        with pytest.raises(StepExecutionError) as exc_info:
            await executor.execute_step(step_name="nonexistent_step")
        
        assert "not found in configuration" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_step_llm_failure_propagates(self, executor, mock_llm_client):
        """Test LLM call failure propagates as exception."""
        mock_llm_client.call_prompt_async.side_effect = Exception("LLM API error")
        
        with pytest.raises(Exception, match="LLM API error"):
            await executor.execute_step(
                step_name="test_step",
                cli_inputs={"input1": "v"}
            )

    @pytest.mark.asyncio
    async def test_execute_step_with_multiple_outputs(self, executor, mock_prompt_manager, tmp_path):
        """Test step execution with multiple output files."""
        mock_prompt_manager.get_step_config.return_value = {
            "name": "test_step",
            "prompt_file": "test.md",
            "inputs": [{"label": "input1", "source": "cli"}],
            "outputs": [
                {"label": "output1"},
                {"label": "output2"},
            ],
            "validation": {"enabled": False},
        }
        
        # Mock multiple data entities
        def get_data_entity_side_effect(label):
            if label == "output1":
                return {"filename": "output1.json", "type": "json"}
            elif label == "output2":
                return {"filename": "output2.json", "type": "json"}
            return None
        mock_prompt_manager.get_data_entity.side_effect = get_data_entity_side_effect
        
        # Mock LLM response for multiple outputs
        mock_llm_client = executor.llm_client
        mock_llm_client.call_prompt_async.return_value = json.dumps({
            "output1": {"data": "value1"},
            "output2": {"data": "value2"}
        })
        
        result = await executor.execute_step(
            step_name="test_step",
            cli_inputs={"input1": "test"},
        )
        
        assert "output1" in result
        assert "output2" in result
        assert result["output1"].exists()
        assert result["output2"].exists()

    @pytest.mark.asyncio
    async def test_force_mode_substitutes_empty_for_missing(self, executor, mock_llm_client, mock_prompt_manager):
        """Test force mode substitutes empty string for missing inputs."""
        # Update prompt manager to return a prompt file
        mock_prompt_manager.load_prompt.return_value = "Test prompt with {{input1}}"
        
        executor.force = True
        # Should not raise even with missing input
        result = await executor.execute_step(
            step_name="test_step",
            cli_inputs={}
        )
        
        assert "test_output" in result

    @pytest.mark.asyncio
    async def test_execute_step_with_compression(self, executor, mock_prompt_manager, tmp_path):
        """Test that compression is applied to inputs."""
        mock_prompt_manager.get_step_config.return_value = {
            "name": "test_step",
            "prompt_file": "test.md",
            "inputs": [
                {
                    "label": "input1",
                    "source": "cli",
                    "compression": "truncate",
                    "compression_params": {"truncation_length": 100}
                }
            ],
            "outputs": [{"label": "test_output"}],
            "validation": {"enabled": False},
        }
        
        # Create a large input to test truncation
        large_input = "x" * 1000
        
        result = await executor.execute_step(
            step_name="test_step",
            cli_inputs={"input1": large_input},
        )
        
        assert "test_output" in result
        assert result["test_output"].exists()

    @pytest.mark.asyncio
    async def test_execute_step_with_validation(self, executor, mock_prompt_manager, tmp_path):
        """Test that validation is triggered when enabled."""
        mock_prompt_manager.get_step_config.return_value = {
            "name": "test_step",
            "prompt_file": "test.md",
            "inputs": [{"label": "input1", "source": "cli", "compression": "none"}],
            "outputs": [{"label": "test_output"}],
            "validation": {"enabled": True},
        }
        
        # Skip validation in executor
        executor.skip_validation = False
        
        # Mock validation to fail
        with patch.object(executor, '_validate_output') as mock_validate:
            from prompt_pipeline.validation import ValidationResult
            # Create a ValidationResult and add errors to it
            result = ValidationResult()
            result.add_error("Test validation error")
            mock_validate.return_value = result
            
            with pytest.raises(StepExecutionError) as exc_info:
                await executor.execute_step(
                    step_name="test_step",
                    cli_inputs={"input1": "test"}
                )
            
            assert "validation error" in str(exc_info.value)

    def test_load_file_content_success(self, executor, tmp_path):
        """Test loading existing file returns content."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        content = executor._load_file_content(test_file, "text")
        
        assert content == "test content"

    def test_load_file_content_missing_file_raises(self, executor, tmp_path):
        """Test loading missing file raises StepExecutionError."""
        with pytest.raises(StepExecutionError, match="not found"):
            executor._load_file_content(tmp_path / "nonexistent.yaml", "yaml")

    def test_extract_json_from_response_valid(self, executor):
        """Test JSON extraction from clean JSON response."""
        result = executor._extract_json_from_response('{"key": "value"}', "output")
        
        assert result == '{"key": "value"}'
        # Verify it's valid JSON
        assert json.loads(result) == {"key": "value"}

    def test_extract_json_from_response_with_preamble(self, executor):
        """Test JSON extraction from response with reasoning preamble."""
        response = "Some reasoning...\n**Part 2 – Final JSON**:\n{\"key\": \"value\"}"
        result = executor._extract_json_from_response(response, "output")
        
        assert result is not None
        assert json.loads(result) == {"key": "value"}

    def test_extract_json_from_response_no_json_returns_none(self, executor):
        """Test JSON extraction returns None when no JSON found."""
        result = executor._extract_json_from_response("No JSON here at all.", "output")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_execute_step_yaml_output_conversion(self, executor, mock_prompt_manager, tmp_path):
        """Test that YAML output is converted from JSON response."""
        mock_prompt_manager.get_step_config.return_value = {
            "name": "test_step",
            "prompt_file": "test.md",
            "inputs": [{"label": "input1", "source": "cli"}],
            "outputs": [{"label": "test_output"}],
            "validation": {"enabled": False},
        }
        
        # Mock YAML data entity
        mock_prompt_manager.get_data_entity.return_value = {
            "filename": "test_output.yaml",
            "type": "yaml"
        }
        
        # Mock LLM to return JSON (will be converted to YAML)
        mock_llm_client = executor.llm_client
        mock_llm_client.call_prompt_async.return_value = json.dumps({
            "key": "value",
            "nested": {"data": "test"}
        })
        
        result = await executor.execute_step(
            step_name="test_step",
            cli_inputs={"input1": "test"}
        )
        
        assert "test_output" in result
        output_path = result["test_output"]
        assert output_path.exists()
        
        # Verify output is valid YAML
        content = output_path.read_text()
        yaml_data = yaml.safe_load(content)
        assert yaml_data["key"] == "value"
        assert yaml_data["nested"]["data"] == "test"

    @pytest.mark.asyncio
    async def test_execute_step_json_output_converts_response(self, executor, mock_prompt_manager, tmp_path):
        """Test that JSON output extracts JSON from reasoning response."""
        mock_prompt_manager.get_step_config.return_value = {
            "name": "test_step",
            "prompt_file": "test.md",
            "inputs": [{"label": "input1", "source": "cli"}],
            "outputs": [{"label": "test_output"}],
            "validation": {"enabled": False},
        }
        
        # Mock JSON data entity
        mock_prompt_manager.get_data_entity.return_value = {
            "filename": "test_output.json",
            "type": "json"
        }
        
        # Mock LLM to return response with reasoning
        mock_llm_client = executor.llm_client
        mock_llm_client.call_prompt_async.return_value = (
            "Here's my reasoning...\n\n"
            "**Part 2 – Final JSON**:\n"
            '{"result": "success", "data": [1, 2, 3]}'
        )
        
        result = await executor.execute_step(
            step_name="test_step",
            cli_inputs={"input1": "test"}
        )
        
        assert "test_output" in result
        output_path = result["test_output"]
        assert output_path.exists()
        
        # Verify output is valid JSON
        content = output_path.read_text()
        json_data = json.loads(content)
        assert json_data["result"] == "success"
        assert json_data["data"] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_execute_step_json_extraction_fails(self, executor, mock_prompt_manager, tmp_path):
        """Test that invalid JSON in response raises StepExecutionError."""
        mock_prompt_manager.get_step_config.return_value = {
            "name": "test_step",
            "prompt_file": "test.md",
            "inputs": [{"label": "input1", "source": "cli"}],
            "outputs": [{"label": "test_output"}],
            "validation": {"enabled": False},
        }
        
        # Mock JSON data entity
        mock_prompt_manager.get_data_entity.return_value = {
            "filename": "test_output.json",
            "type": "json"
        }
        
        # Mock LLM to return non-JSON response
        mock_llm_client = executor.llm_client
        mock_llm_client.call_prompt_async.return_value = "This is not valid JSON at all"
        
        with pytest.raises(StepExecutionError) as exc_info:
            await executor.execute_step(
                step_name="test_step",
                cli_inputs={"input1": "test"}
            )
        
        assert "Failed to extract valid JSON" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_step_with_previous_outputs(self, executor, mock_prompt_manager, tmp_path):
        """Test step execution with previous step outputs as input."""
        # Create a previous output file
        prev_output = tmp_path / "previous_output.json"
        prev_output.write_text('{"data": "from previous step"}')
        
        mock_prompt_manager.get_step_config.return_value = {
            "name": "test_step",
            "prompt_file": "test.md",
            "inputs": [
                {
                    "label": "prev_output",
                    "source": "label:previous_output",
                    "compression": "none"
                }
            ],
            "outputs": [{"label": "test_output"}],
            "validation": {"enabled": False},
        }
        
        result = await executor.execute_step(
            step_name="test_step",
            cli_inputs={},
            previous_outputs={"previous_output": prev_output}
        )
        
        assert "test_output" in result
        assert result["test_output"].exists()

    @pytest.mark.asyncio
    async def test_execute_step_with_exogenous_inputs(self, executor, mock_prompt_manager, tmp_path):
        """Test step execution with exogenous input files."""
        # Create an exogenous input file
        exo_input = tmp_path / "external_input.txt"
        exo_input.write_text("External input content")
        
        mock_prompt_manager.get_step_config.return_value = {
            "name": "test_step",
            "prompt_file": "test.md",
            "inputs": [
                {
                    "label": "external",
                    "source": "file",
                    "compression": "none"
                }
            ],
            "outputs": [{"label": "test_output"}],
            "validation": {"enabled": False},
        }
        
        result = await executor.execute_step(
            step_name="test_step",
            cli_inputs={},
            exogenous_inputs={"external": exo_input}
        )
        
        assert "test_output" in result
        assert result["test_output"].exists()

    @pytest.mark.asyncio
    async def test_execute_step_with_encoding_errors(self, executor, mock_prompt_manager, tmp_path):
        """Test step execution handles encoding errors gracefully."""
        # Mock prompt manager to return a prompt with special characters
        mock_prompt_manager.get_prompt_with_variables.return_value = "Prompt with unicode: ñ, é, 中文"
        
        # Mock LLM response with special characters
        mock_llm_client = executor.llm_client
        mock_llm_client.call_prompt_async.return_value = json.dumps({
            "data": "Response with unicode: ñ, é, 中文"
        })
        
        result = await executor.execute_step(
            step_name="test_step",
            cli_inputs={"input1": "test"}
        )
        
        assert "test_output" in result
        assert result["test_output"].exists()
        
        # Verify content was written correctly
        content = result["test_output"].read_text()
        json_data = json.loads(content)
        assert "中文" in json_data["data"]

    def test_get_model_for_step_with_level(self, executor, mock_prompt_manager):
        """Test model selection based on model level."""
        mock_prompt_manager.steps_config = {
            "model_levels": {
                "test_step": {
                    1: "test/model/cheap",
                    2: "test/model/balanced",
                    3: "test/model/best"
                }
            }
        }
        
        executor.model_level = 2
        model = executor._get_model_for_step("test_step")
        
        assert model == "test/model/balanced"

    def test_get_model_for_step_fallback(self, executor, mock_prompt_manager):
        """Test model fallback when level not available."""
        mock_prompt_manager.steps_config = {
            "model_levels": {
                "test_step": {
                    1: "test/model/cheap"
                }
            }
        }
        
        executor.model_level = 3
        model = executor._get_model_for_step("test_step")
        
        # Should fall back to level 1
        assert model == "test/model/cheap"

    def test_get_model_for_step_default(self, executor, mock_prompt_manager):
        """Test default model when no level configured."""
        mock_prompt_manager.steps_config = {"model_levels": {}}
        
        model = executor._get_model_for_step("test_step")
        
        # Should use LLM client default
        assert model == "test/model"
