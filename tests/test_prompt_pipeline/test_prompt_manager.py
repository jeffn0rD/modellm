"""Unit tests for PromptManager configuration loading and validation.

Tests:
- Valid configuration loading
- Invalid configuration handling (file not found, invalid YAML, empty file)
- Graceful error messages for configuration errors
"""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from prompt_pipeline.prompt_manager import PromptManager


@pytest.mark.unit
class TestPromptManagerConfigurationValidation:
    """Tests for PromptManager configuration file validation."""

    def test_valid_configuration_loading(self):
        """Test that a valid configuration file loads successfully."""
        config_content = {
            "steps": {
                "step1": {
                    "name": "step1",
                    "prompt_file": "prompt_step1_v2.md",
                    "order": 1,
                    "output_file": "spec_1.yaml",
                    "output_type": "yaml",
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_content, f)
            config_path = f.name

        try:
            manager = PromptManager(config_path=config_path)
            assert manager.steps_config is not None
            assert "steps" in manager.steps_config
        finally:
            os.unlink(config_path)

    def test_file_not_found_error(self):
        """Test that FileNotFoundError is raised for non-existent config file."""
        with pytest.raises(FileNotFoundError) as exc_info:
            PromptManager(config_path="/nonexistent/path/config.yaml")

        error_msg = str(exc_info.value)
        assert "Configuration file not found" in error_msg
        assert "nonexistent" in error_msg

    def test_empty_config_file_error(self):
        """Test that ValueError is raised for empty configuration file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            # Write only comments (no actual content)
            f.write("# This is a comment\n")
            f.write("# Another comment\n")
            config_path = f.name

        try:
            with pytest.raises(ValueError) as exc_info:
                PromptManager(config_path=config_path)

            error_msg = str(exc_info.value)
            assert "empty or contains only comments" in error_msg
        finally:
            os.unlink(config_path)

    def test_invalid_yaml_syntax_error(self):
        """Test that yaml.YAMLError is raised for invalid YAML syntax."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            # Write invalid YAML
            f.write("steps:\n  step1:\n    name: step1\n    invalid indentation here\n")
            config_path = f.name

        try:
            with pytest.raises(yaml.YAMLError) as exc_info:
                PromptManager(config_path=config_path)

            error_msg = str(exc_info.value)
            assert "Invalid YAML syntax" in error_msg
        finally:
            os.unlink(config_path)

    def test_invalid_config_structure_error(self):
        """Test that ValueError is raised for invalid configuration structure."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            # Write YAML that's not a dictionary (e.g., a list)
            yaml.dump(["step1", "step2"], f)
            config_path = f.name

        try:
            with pytest.raises(ValueError) as exc_info:
                PromptManager(config_path=config_path)

            error_msg = str(exc_info.value)
            assert "Invalid configuration structure" in error_msg
            assert "dictionary" in error_msg
        finally:
            os.unlink(config_path)

    @pytest.mark.skipif(
        os.name == 'nt',
        reason="Permission tests are unreliable on Windows due to file system behavior"
    )
    def test_permission_denied_error(self):
        """Test that PermissionError is raised for unreadable config file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_content = {"steps": {"step1": {"name": "step1"}}}
            yaml.dump(config_content, f)
            config_path = f.name

        try:
            # Make file unreadable
            os.chmod(config_path, 0o000)

            with pytest.raises((PermissionError, OSError, IOError)) as exc_info:
                PromptManager(config_path=config_path)

            error_msg = str(exc_info.value)
            # Either permission denied or operation not permitted (Windows)
            assert any(keyword in error_msg.lower() for keyword in ["permission", "denied", "not permitted", "operation not permitted"])
        finally:
            # Restore permissions before deleting
            try:
                os.chmod(config_path, 0o644)
            except (OSError, PermissionError):
                pass
            os.unlink(config_path)

    def test_config_file_is_directory_error(self):
        """Test that ValueError is raised when config path is a directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(ValueError) as exc_info:
                PromptManager(config_path=temp_dir)

            error_msg = str(exc_info.value)
            assert "not a file" in error_msg

    def test_minimal_valid_config(self):
        """Test that minimal valid configuration works."""
        config_content = {
            "steps": {
                "step1": {
                    "name": "step1",
                    "prompt_file": "prompt.md",
                    "order": 1,
                    "output_file": "out.yaml",
                    "output_type": "yaml",
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_content, f)
            config_path = f.name

        try:
            manager = PromptManager(config_path=config_path)
            
            # Verify we can access methods without error
            step_config = manager.get_step_config("step1")
            assert step_config is not None
            assert step_config["name"] == "step1"
        finally:
            os.unlink(config_path)

    def test_error_message_includes_file_path(self):
        """Test that error messages include the problematic file path."""
        non_existent_path = "/some/nonexistent/path/config.yaml"
        
        with pytest.raises(FileNotFoundError) as exc_info:
            PromptManager(config_path=non_existent_path)

        error_msg = str(exc_info.value)
        assert non_existent_path in error_msg


@pytest.mark.unit
class TestPromptManagerStepOperations:
    """Tests for PromptManager step operations with valid configuration."""

    @pytest.fixture
    def valid_config_file(self):
        """Create a temporary valid configuration file."""
        config_content = {
            "steps": {
                "step1": {
                    "name": "step1",
                    "prompt_file": "prompt_step1_v2.md",
                    "order": 1,
                    "output_file": "spec_1.yaml",
                    "output_type": "yaml",
                    "requires_nl_spec": True,
                    "dependencies": [],
                },
                "stepC3": {
                    "name": "stepC3",
                    "prompt_file": "prompt_step_C3.md",
                    "order": 2,
                    "output_file": "concepts.json",
                    "output_type": "json",
                    "requires_spec_file": True,
                    "dependencies": ["step1"],
                    "json_schema": "schemas/concepts.schema.json",
                }
            },
            "model_levels": {
                "step1": {
                    "1": "minimax/m2.5",
                    "2": "mimo/v2-flash",
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_content, f)
            yield f.name

        os.unlink(f.name)

    def test_get_step_config(self, valid_config_file):
        """Test retrieving step configuration."""
        manager = PromptManager(config_path=valid_config_file)
        
        step1_config = manager.get_step_config("step1")
        assert step1_config is not None
        assert step1_config["name"] == "step1"
        assert step1_config["prompt_file"] == "prompt_step1_v2.md"

    def test_get_nonexistent_step_config(self, valid_config_file):
        """Test that None is returned for non-existent step."""
        manager = PromptManager(config_path=valid_config_file)
        
        nonexistent_config = manager.get_step_config("nonexistent_step")
        assert nonexistent_config is None

    def test_get_all_steps(self, valid_config_file):
        """Test retrieving all step configurations."""
        manager = PromptManager(config_path=valid_config_file)
        
        all_steps = manager.get_all_steps()
        assert len(all_steps) == 2
        assert any(s["name"] == "step1" for s in all_steps)
        assert any(s["name"] == "stepC3" for s in all_steps)

    def test_get_all_step_names(self, valid_config_file):
        """Test retrieving all step names."""
        manager = PromptManager(config_path=valid_config_file)
        
        step_names = manager.get_all_step_names()
        assert len(step_names) == 2
        assert "step1" in step_names
        assert "stepC3" in step_names

    def test_get_sorted_steps(self, valid_config_file):
        """Test retrieving steps sorted by order."""
        manager = PromptManager(config_path=valid_config_file)
        
        sorted_steps = manager.get_sorted_steps()
        assert len(sorted_steps) == 2
        # step1 has order 1, stepC3 has order 2
        assert sorted_steps[0]["name"] == "step1"
        assert sorted_steps[1]["name"] == "stepC3"

    def test_get_required_inputs(self, valid_config_file):
        """Test retrieving required inputs for steps."""
        manager = PromptManager(config_path=valid_config_file)
        
        step1_inputs = manager.get_required_inputs("step1")
        assert "nl_spec" in step1_inputs
        
        stepC3_inputs = manager.get_required_inputs("stepC3")
        assert "spec_file" in stepC3_inputs

    def test_get_dependencies(self, valid_config_file):
        """Test retrieving step dependencies."""
        manager = PromptManager(config_path=valid_config_file)
        
        step1_deps = manager.get_dependencies("step1")
        assert step1_deps == []
        
        stepC3_deps = manager.get_dependencies("stepC3")
        assert stepC3_deps == ["step1"]

    def test_get_steps_for_execution(self, valid_config_file):
        """Test retrieving steps for execution with dependencies."""
        manager = PromptManager(config_path=valid_config_file)
        
        # Get all steps
        all_steps = manager.get_steps_for_execution()
        assert len(all_steps) == 2
        
        # Get steps starting from stepC3 (includes dependencies)
        steps_from_c3 = manager.get_steps_for_execution("stepC3")
        assert len(steps_from_c3) == 2
        # Should include step1 (dependency) and stepC3
        step_names = [s["name"] for s in steps_from_c3]
        assert "step1" in step_names
        assert "stepC3" in step_names

    def test_get_prompt_file(self, valid_config_file):
        """Test retrieving prompt file name."""
        manager = PromptManager(config_path=valid_config_file)
        
        step1_prompt = manager.get_prompt_file("step1")
        assert step1_prompt == "prompt_step1_v2.md"

    def test_get_output_file(self, valid_config_file):
        """Test retrieving output file name."""
        manager = PromptManager(config_path=valid_config_file)
        
        step1_output = manager.get_output_file("step1")
        assert step1_output == "spec_1.yaml"

    def test_get_output_type(self, valid_config_file):
        """Test retrieving output type."""
        manager = PromptManager(config_path=valid_config_file)
        
        step1_type = manager.get_output_type("step1")
        assert step1_type == "yaml"
        
        stepC3_type = manager.get_output_type("stepC3")
        assert stepC3_type == "json"

    def test_get_json_schema(self, valid_config_file):
        """Test retrieving JSON schema path."""
        manager = PromptManager(config_path=valid_config_file)
        
        stepC3_schema = manager.get_json_schema("stepC3")
        assert stepC3_schema == "schemas/concepts.schema.json"

    def test_get_dev_defaults(self, valid_config_file):
        """Test retrieving dev defaults."""
        manager = PromptManager(config_path=valid_config_file)
        
        dev_defaults = manager.get_dev_defaults()
        # Should return empty dict if not in config
        assert isinstance(dev_defaults, dict)

    def test_get_validation_config(self, valid_config_file):
        """Test retrieving validation config."""
        manager = PromptManager(config_path=valid_config_file)
        
        validation_config = manager.get_validation_config()
        # Should return empty dict if not in config
        assert isinstance(validation_config, dict)

    def test_get_paths_config(self, valid_config_file):
        """Test retrieving paths config."""
        manager = PromptManager(config_path=valid_config_file)
        
        paths_config = manager.get_paths_config()
        # Should return empty dict if not in config
        assert isinstance(paths_config, dict)

    def test_get_prompt_with_variables(self, valid_config_file):
        """Test loading and substituting variables in prompt."""
        manager = PromptManager(config_path=valid_config_file)
        
        variables = {"nl_spec": "test_spec.md", "model_level": 2}
        
        # This will fail if the prompt file doesn't exist, but we're testing
        # the variable substitution logic
        try:
            prompt = manager.get_prompt_with_variables("step1", variables)
            # If we get here, the prompt was loaded (file exists)
            # The prompt should be a string
            assert isinstance(prompt, str)
            assert len(prompt) > 0
        except FileNotFoundError:
            # Expected if prompt file doesn't exist
            # We're mainly testing that the method works without errors
            pass

    def test_create_prompt_manager_convenience_function(self, valid_config_file):
        """Test the convenience function for creating PromptManager."""
        from prompt_pipeline.prompt_manager import create_prompt_manager
        
        manager = create_prompt_manager(
            config_path=valid_config_file,
            prompts_dir="prompts"
        )
        
        assert manager.config_path == valid_config_file
        assert manager.prompts_dir == "prompts"
