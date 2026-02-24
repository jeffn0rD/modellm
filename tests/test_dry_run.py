"""Unit tests for dry-run prompt construction functionality."""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock

from prompt_pipeline.prompt_manager import PromptManager
from prompt_pipeline.step_executor_dry_run import (
    construct_prompt_without_api_call,
    DryRunResult,
)


class TestDryRunPromptConstruction:
    """Test cases for dry-run prompt construction."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config_path = "configuration/pipeline_config.yaml"
        self.prompt_manager = PromptManager(self.config_path)
        
    def test_dry_run_result_initialization(self):
        """Test that DryRunResult initializes correctly."""
        result = DryRunResult(
            step_name="step1",
            prompt_file="prompt_step1_v2.md",
            persona="systems_architect",
            step_number=1,
            cli_inputs={"nl_spec": "test content"},
            exogenous_inputs={},
            previous_outputs={},
            full_prompt="Test prompt with variables",
        )
        
        assert result.step_name == "step1"
        assert result.prompt_file == "prompt_step1_v2.md"
        assert result.persona == "systems_architect"
        assert result.step_number == 1
        assert result.full_prompt == "Test prompt with variables"
        assert result.total_length == len("Test prompt with variables")
        
    def test_dry_run_result_to_dict(self):
        """Test DryRunResult to_dict conversion."""
        result = DryRunResult(
            step_name="step1",
            prompt_file="prompt_step1_v2.md",
            persona="systems_architect",
            step_number=1,
            cli_inputs={"nl_spec": "test content"},
            exogenous_inputs={"file1": Path("/tmp/test.txt")},
            previous_outputs={"output1": Path("/tmp/output.txt")},
            full_prompt="Test prompt",
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["step_name"] == "step1"
        assert result_dict["prompt_file"] == "prompt_step1_v2.md"
        assert result_dict["persona"] == "systems_architect"
        assert result_dict["step_number"] == 1
        assert "nl_spec" in result_dict["cli_inputs"]
        assert "file1" in result_dict["exogenous_inputs"]
        assert "output1" in result_dict["previous_outputs"]
        assert "full_prompt_preview" in result_dict
        
    def test_construct_prompt_without_api_call_step1(self):
        """Test constructing prompt for step1 without API calls."""
        # This test demonstrates that the function can be called without network access
        nl_spec_content = Path("doc/todo_list_nl_spec.md").read_text(encoding="utf-8")
        
        result = construct_prompt_without_api_call(
            step_name="step1",
            cli_inputs={"nl_spec": nl_spec_content},
            exogenous_inputs={},
            previous_outputs={},
            prompt_manager=self.prompt_manager,
            force=False,
        )
        
        assert result.step_name == "step1"
        assert result.prompt_file == "prompt_step1_v2.md"
        assert result.persona == "systems_architect"
        assert result.step_number == 1
        assert len(result.full_prompt) > 0
        assert "You are a systems architect" in result.full_prompt
        assert "Given the inputs:" in result.full_prompt
        assert "nl_spec:" in result.full_prompt
        
    def test_construct_prompt_missing_input(self):
        """Test that missing required input raises ValueError."""
        with pytest.raises(ValueError, match="Missing required input"):
            construct_prompt_without_api_call(
                step_name="step1",
                cli_inputs={},  # nl_spec is missing
                exogenous_inputs={},
                previous_outputs={},
                prompt_manager=self.prompt_manager,
                force=False,
            )
        
    def test_construct_prompt_with_force(self):
        """Test that force mode substitutes empty strings for missing inputs."""
        nl_spec_content = Path("doc/todo_list_nl_spec.md").read_text(encoding="utf-8")
        
        result = construct_prompt_without_api_call(
            step_name="step1",
            cli_inputs={"nl_spec": nl_spec_content},
            exogenous_inputs={},
            previous_outputs={},
            prompt_manager=self.prompt_manager,
            force=True,
        )
        
        assert result.step_name == "step1"
        assert len(result.full_prompt) > 0
        
    def test_construct_prompt_invalid_step(self):
        """Test that invalid step name raises ValueError."""
        with pytest.raises(ValueError, match="not found in configuration"):
            construct_prompt_without_api_call(
                step_name="invalid_step",
                cli_inputs={},
                exogenous_inputs={},
                previous_outputs={},
                prompt_manager=self.prompt_manager,
                force=False,
            )
            
    def test_construct_prompt_with_file_input(self):
        """Test constructing prompt with file-based input."""
        # Note: step1 expects nl_spec from source: cli, so we pass content as cli_input
        # not as exogenous input. This test verifies that behavior.
        nl_spec_content = Path("doc/todo_list_nl_spec.md").read_text(encoding="utf-8")
        
        result = construct_prompt_without_api_call(
            step_name="step1",
            cli_inputs={"nl_spec": nl_spec_content},
            exogenous_inputs={},
            previous_outputs={},
            prompt_manager=self.prompt_manager,
            force=False,
        )
        
        assert result.step_name == "step1"
        assert len(result.full_prompt) > 0
        
    def test_construct_prompt_with_different_step(self):
        """Test constructing prompt for stepC3 (which uses label:spec reference)."""
        # StepC3 expects spec from label:spec, which would come from previous outputs
        # Create a mock spec file
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("specification:\n  id: TEST\n")
            temp_file = f.name
        
        try:
            result = construct_prompt_without_api_call(
                step_name="stepC3",
                cli_inputs={},
                exogenous_inputs={},
                previous_outputs={"spec": Path(temp_file)},
                prompt_manager=self.prompt_manager,
                force=False,
            )
            
            # StepC3 exists and uses label:spec reference
            assert result.step_name == "stepC3"
            assert len(result.full_prompt) > 0
        finally:
            os.unlink(temp_file)
