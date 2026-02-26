"""Unit tests for --info switch functionality in run_step command."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
import click

from prompt_pipeline_cli.commands.run_step import (
    _get_step_info,
    display_step_info,
    handle_info,
    _display_input_requirements,
    _display_output_definitions,
    _display_configuration_settings,
    _display_cli_switches,
    _display_example_commands,
    _display_dependency_analysis,
    _display_verbose_explanations,
)


class TestGetStepInfo:
    """Test _get_step_info() function."""

    def test_get_step_info_valid_step(self):
        """Test _get_step_info with a valid step."""
        # Create mock prompt manager
        prompt_manager = Mock()
        
        # Mock step configuration
        step_config = {
            "order": 1,
            "persona": "analyst",
            "prompt_file": "prompt.txt",
            "inputs": [
                {
                    "label": "spec",
                    "source": "cli",
                    "type": "yaml",
                    "compression": "yaml_as_json",
                }
            ],
            "outputs": [
                {
                    "label": "output",
                    "type": "json",
                }
            ],
            "model_levels": {"1": "model1", "2": "model2"},
            "validation": {"enabled": True, "schema": "schema.json"},
        }
        
        prompt_manager.get_step_config.return_value = step_config
        prompt_manager.get_data_entity.return_value = {
            "filename": "spec.yaml",
            "description": "Test specification",
            "yaml_schema": "test_schema.json",
        }
        
        result = _get_step_info(prompt_manager, "step1")
        
        assert result is not None
        assert result["step_name"] == "step1"
        assert result["configuration"]["name"] == "step1"
        assert result["configuration"]["order"] == 1
        assert result["configuration"]["persona"] == "analyst"
        assert result["configuration"]["prompt_file"] == "prompt.txt"
        assert len(result["inputs"]) == 1
        assert result["inputs"][0]["label"] == "spec"
        assert result["inputs"][0]["source"] == "cli"
        assert result["inputs"][0]["type"] == "yaml"
        assert result["inputs"][0]["compression"] == "yaml_as_json"
        assert len(result["outputs"]) == 1
        assert result["outputs"][0]["label"] == "output"
        assert result["outputs"][0]["type"] == "json"
        assert result["model_levels"] == {"1": "model1", "2": "model2"}
        assert result["validation"]["enabled"] is True
        assert result["validation"]["schema"] == "schema.json"

    def test_get_step_info_missing_step(self):
        """Test _get_step_info with a missing step."""
        prompt_manager = Mock()
        prompt_manager.get_step_config.return_value = None
        
        result = _get_step_info(prompt_manager, "missing_step")
        
        assert result is None

    def test_get_step_info_with_compression_params(self):
        """Test _get_step_info with compression_params in input."""
        prompt_manager = Mock()
        
        step_config = {
            "order": 1,
            "persona": "analyst",
            "prompt_file": "prompt.txt",
            "inputs": [
                {
                    "label": "spec",
                    "source": "cli",
                    "type": "yaml",
                    "compression": "hierarchical",
                    "compression_params": {"max_length": 1000},
                }
            ],
            "outputs": [],
            "model_levels": {},
            "validation": {},
        }
        
        prompt_manager.get_step_config.return_value = step_config
        prompt_manager.get_data_entity.return_value = None
        
        result = _get_step_info(prompt_manager, "step1")
        
        assert result is not None
        assert result["inputs"][0]["compression"] == "hierarchical"
        assert result["inputs"][0]["compression_params"] == {"max_length": 1000}

    def test_get_step_info_with_color(self):
        """Test _get_step_info with color in input."""
        prompt_manager = Mock()
        
        step_config = {
            "order": 1,
            "persona": "analyst",
            "prompt_file": "prompt.txt",
            "inputs": [
                {
                    "label": "spec",
                    "source": "cli",
                    "type": "yaml",
                    "color": "CYAN",
                }
            ],
            "outputs": [],
            "model_levels": {},
            "validation": {},
        }
        
        prompt_manager.get_step_config.return_value = step_config
        prompt_manager.get_data_entity.return_value = None
        
        result = _get_step_info(prompt_manager, "step1")
        
        assert result is not None
        assert result["inputs"][0]["color"] == "CYAN"

    def test_get_step_info_with_dependencies(self):
        """Test _get_step_info with dependencies (label: source)."""
        prompt_manager = Mock()
        
        step_config = {
            "order": 2,
            "persona": "analyst",
            "prompt_file": "prompt.txt",
            "inputs": [
                {
                    "label": "input1",
                    "source": "label:output1",
                    "type": "json",
                }
            ],
            "outputs": [],
            "model_levels": {},
            "validation": {},
        }
        
        prompt_manager.get_step_config.return_value = step_config
        prompt_manager.get_data_entity.return_value = None
        
        result = _get_step_info(prompt_manager, "step2")
        
        assert result is not None
        assert result["dependencies"] == ["output1"]


class TestDisplayStepInfo:
    """Test display_step_info() function."""

    @patch('builtins.print')
    def test_display_step_info_basic(self, mock_print):
        """Test display_step_info with basic info."""
        info = {
            "step_name": "step1",
            "configuration": {"name": "step1", "order": 1, "persona": "analyst", "prompt_file": "prompt.txt"},
            "inputs": [],
            "outputs": [],
            "model_levels": {},
            "validation": {},
            "dependencies": [],
        }
        
        display_step_info(info, verbose=False, as_json=False)
        
        # Check that print was called
        assert mock_print.called

    @patch('builtins.print')
    def test_display_step_info_as_json(self, mock_print):
        """Test display_step_info with JSON output."""
        import json
        info = {
            "step_name": "step1",
            "configuration": {"name": "step1"},
            "inputs": [],
            "outputs": [],
            "model_levels": {},
            "validation": {},
            "dependencies": [],
        }
        
        display_step_info(info, verbose=False, as_json=True)
        
        # Check that print was called with JSON
        assert mock_print.called
        # Verify it's valid JSON
        call_args = mock_print.call_args[0][0]
        parsed = json.loads(call_args)
        assert parsed["step_name"] == "step1"

    @patch('builtins.print')
    def test_display_step_info_verbose(self, mock_print):
        """Test display_step_info with verbose mode."""
        info = {
            "step_name": "step1",
            "configuration": {"name": "step1", "order": 1, "persona": "analyst", "prompt_file": "prompt.txt"},
            "inputs": [
                {
                    "label": "spec",
                    "source": "cli",
                    "type": "yaml",
                    "compression": "hierarchical",
                }
            ],
            "outputs": [],
            "model_levels": {"1": "model1"},
            "validation": {"enabled": True},
            "dependencies": ["output1"],
        }
        
        display_step_info(info, verbose=True, as_json=False)
        
        # Check that print was called
        assert mock_print.called


class TestDisplayInputRequirements:
    """Test _display_input_requirements() function."""

    @patch('builtins.print')
    def test_display_input_requirements_basic(self, mock_print):
        """Test _display_input_requirements with basic inputs."""
        inputs = [
            {
                "label": "spec",
                "source": "cli",
                "type": "yaml",
                "compression": "none",
            }
        ]
        
        _display_input_requirements(inputs)
        
        assert mock_print.called

    @patch('builtins.print')
    def test_display_input_requirements_with_compression_params(self, mock_print):
        """Test _display_input_requirements with compression params."""
        inputs = [
            {
                "label": "spec",
                "source": "cli",
                "type": "yaml",
                "compression": "hierarchical",
                "compression_params": {"max_length": 1000},
                "color": "CYAN",
            }
        ]
        
        _display_input_requirements(inputs)
        
        assert mock_print.called

    @patch('builtins.print')
    def test_display_input_requirements_with_data_entity(self, mock_print):
        """Test _display_input_requirements with data entity."""
        inputs = [
            {
                "label": "spec",
                "source": "cli",
                "type": "yaml",
                "compression": "none",
                "data_entity": {
                    "filename": "spec.yaml",
                    "description": "Test spec",
                    "schema": "test_schema.json",
                }
            }
        ]
        
        _display_input_requirements(inputs)
        
        assert mock_print.called


class TestDisplayOutputDefinitions:
    """Test _display_output_definitions() function."""

    @patch('builtins.print')
    def test_display_output_definitions_basic(self, mock_print):
        """Test _display_output_definitions with basic outputs."""
        outputs = [
            {
                "label": "output",
                "type": "json",
            }
        ]
        
        _display_output_definitions(outputs)
        
        assert mock_print.called

    @patch('builtins.print')
    def test_display_output_definitions_with_data_entity(self, mock_print):
        """Test _display_output_definitions with data entity."""
        outputs = [
            {
                "label": "output",
                "type": "json",
                "data_entity": {
                    "filename": "output.json",
                    "description": "Test output",
                    "schema": "test_schema.json",
                }
            }
        ]
        
        _display_output_definitions(outputs)
        
        assert mock_print.called


class TestDisplayConfigurationSettings:
    """Test _display_configuration_settings() function."""

    @patch('builtins.print')
    def test_display_configuration_settings_with_model_levels(self, mock_print):
        """Test _display_configuration_settings with model levels."""
        info = {
            "model_levels": {"1": "model1", "2": "model2"},
            "validation": {},
            "dependencies": [],
        }
        
        _display_configuration_settings(info)
        
        assert mock_print.called

    @patch('builtins.print')
    def test_display_configuration_settings_with_validation(self, mock_print):
        """Test _display_configuration_settings with validation."""
        info = {
            "model_levels": {},
            "validation": {"enabled": True, "schema": "schema.json"},
            "dependencies": [],
        }
        
        _display_configuration_settings(info)
        
        assert mock_print.called

    @patch('builtins.print')
    def test_display_configuration_settings_with_dependencies(self, mock_print):
        """Test _display_configuration_settings with dependencies."""
        info = {
            "model_levels": {},
            "validation": {},
            "dependencies": ["output1", "output2"],
        }
        
        _display_configuration_settings(info)
        
        assert mock_print.called


class TestDisplayCliSwitches:
    """Test _display_cli_switches() function."""

    @patch('builtins.print')
    def test_display_cli_switches(self, mock_print):
        """Test _display_cli_switches displays all categories."""
        _display_cli_switches()
        
        # Should print multiple times
        assert mock_print.call_count > 0
        
        # Check that key categories are printed
        calls = [str(call) for call in mock_print.call_args_list]
        assert any("Required Inputs" in call for call in calls)
        assert any("Execution Control" in call for call in calls)
        assert any("Info Mode" in call for call in calls)


class TestDisplayExampleCommands:
    """Test _display_example_commands() function."""

    @patch('builtins.print')
    def test_display_example_commands(self, mock_print):
        """Test _display_example_commands displays example commands."""
        _display_example_commands("step1")
        
        # Should print multiple examples
        assert mock_print.call_count > 0
        
        # Check that --info is included
        calls = [str(call) for call in mock_print.call_args_list]
        assert any("--info" in call for call in calls)


class TestDisplayDependencyAnalysis:
    """Test _display_dependency_analysis() function."""

    @patch('builtins.print')
    def test_display_dependency_analysis(self, mock_print):
        """Test _display_dependency_analysis displays dependencies."""
        _display_dependency_analysis("step2", ["output1", "output2"])
        
        # Should print dependency information
        assert mock_print.call_count > 0
        
        # Check that dependencies are mentioned
        calls = [str(call) for call in mock_print.call_args_list]
        assert any("output1" in call for call in calls)


class TestDisplayVerboseExplanations:
    """Test _display_verbose_explanations() function."""

    @patch('builtins.print')
    def test_display_verbose_explanations_compression_strategies(self, mock_print):
        """Test _display_verbose_explanations with compression strategies."""
        info = {
            "inputs": [
                {
                    "label": "spec",
                    "compression": "hierarchical",
                },
                {
                    "label": "spec2",
                    "compression": "anchor_index",
                },
                {
                    "label": "spec3",
                    "compression": "concept_summary",
                },
                {
                    "label": "spec4",
                    "compression": "yaml_as_json",
                },
            ],
            "model_levels": {"1": "model1"},
        }
        
        _display_verbose_explanations(info)
        
        assert mock_print.call_count > 0
        
        # Check that compression strategies are explained
        calls = [str(call) for call in mock_print.call_args_list]
        assert any("hierarchical" in call for call in calls)
        assert any("anchor_index" in call for call in calls)
        assert any("concept_summary" in call for call in calls)
        assert any("yaml_as_json" in call for call in calls)

    @patch('builtins.print')
    def test_display_verbose_explanations_input_sources(self, mock_print):
        """Test _display_verbose_explanations with input sources."""
        info = {
            "inputs": [
                {
                    "label": "spec",
                    "source": "label:output1",
                },
                {
                    "label": "spec2",
                    "source": "cli",
                },
            ],
            "model_levels": {},
        }
        
        _display_verbose_explanations(info)
        
        assert mock_print.call_count > 0
        
        # Check that input sources are explained
        calls = [str(call) for call in mock_print.call_args_list]
        # The function prints the label, not the full source
        assert any("spec" in call for call in calls)
        assert any("spec2" in call for call in calls)
        # And it mentions the source types
        assert any("from previous step" in call for call in calls)
        assert any("interactive" in call for call in calls)

    @patch('builtins.print')
    def test_display_verbose_explanations_model_levels(self, mock_print):
        """Test _display_verbose_explanations with model levels."""
        info = {
            "inputs": [],
            "model_levels": {"1": "model1", "2": "model2", "3": "model3"},
        }
        
        _display_verbose_explanations(info)
        
        assert mock_print.call_count > 0
        
        # Check that model levels are explained
        calls = [str(call) for call in mock_print.call_args_list]
        assert any("Level 1" in call for call in calls)
        assert any("Level 2" in call for call in calls)
        assert any("Level 3" in call for call in calls)

    @patch('builtins.print')
    def test_display_verbose_explanations_switch_explanations(self, mock_print):
        """Test _display_verbose_explanations with switch explanations."""
        info = {
            "inputs": [],
            "model_levels": {},
        }
        
        _display_verbose_explanations(info)
        
        assert mock_print.call_count > 0
        
        # Check that switches are explained
        calls = [str(call) for call in mock_print.call_args_list]
        assert any("--dry-run" in call for call in calls)
        assert any("--approve" in call for call in calls)


class TestInfo:
    """Test info() function."""

    def test_handle_info_valid_step(self):
        """Test handle_info with a valid step."""
        from prompt_pipeline_cli.commands.run_step import handle_info
        ctx = Mock()
        ctx.obj = {"config": "configuration/pipeline_config.yaml"}
        
        with patch('prompt_pipeline_cli.commands.run_step.PromptManager') as mock_pm_class:
            with patch('prompt_pipeline_cli.commands.run_step.display_step_info') as mock_display:
                mock_prompt_manager = Mock()
                mock_pm_class.return_value = mock_prompt_manager
                
                # Mock _get_step_info to return valid data
                with patch('prompt_pipeline_cli.commands.run_step._get_step_info') as mock_get_info:
                    mock_get_info.return_value = {
                        "step_name": "step1",
                        "configuration": {"name": "step1"},
                        "inputs": [],
                        "outputs": [],
                        "model_levels": {},
                        "validation": {},
                        "dependencies": [],
                    }
                    
                    handle_info(ctx, "step1", False, False, None)
                    
                    # Verify display_step_info was called
                    assert mock_display.called

    def test_handle_info_missing_step(self):
        """Test handle_info with a missing step."""
        from prompt_pipeline_cli.commands.run_step import handle_info
        ctx = Mock()
        ctx.obj = {"config": "configuration/pipeline_config.yaml"}
        
        with patch('prompt_pipeline_cli.commands.run_step.PromptManager') as mock_pm_class:
            mock_prompt_manager = Mock()
            mock_pm_class.return_value = mock_prompt_manager
            
            with patch('prompt_pipeline_cli.commands.run_step._get_step_info') as mock_get_info:
                mock_get_info.return_value = None
                
                # Should raise ClickException
                with pytest.raises(click.ClickException):
                    handle_info(ctx, "missing_step", False, False, None)

    def test_handle_info_invalid_config(self):
        """Test handle_info with invalid config path."""
        from prompt_pipeline_cli.commands.run_step import handle_info
        ctx = Mock()
        ctx.obj = {"config": "nonexistent_config.yaml"}
        
        with patch('prompt_pipeline_cli.commands.run_step.PromptManager') as mock_pm_class:
            mock_pm_class.side_effect = Exception("Config not found")
            
            # Should raise ClickException
            with pytest.raises(click.ClickException):
                handle_info(ctx, "step1", False, False, None)

    def test_handle_info_multiple_steps(self):
        """Test handle_info with multiple steps."""
        from prompt_pipeline_cli.commands.run_step import handle_info
        ctx = Mock()
        ctx.obj = {"config": "configuration/pipeline_config.yaml"}
        
        with patch('prompt_pipeline_cli.commands.run_step.PromptManager') as mock_pm_class:
            with patch('prompt_pipeline_cli.commands.run_step.display_step_info') as mock_display:
                mock_prompt_manager = Mock()
                mock_pm_class.return_value = mock_prompt_manager
                
                with patch('prompt_pipeline_cli.commands.run_step._get_step_info') as mock_get_info:
                    mock_get_info.return_value = {
                        "step_name": "step1",
                        "configuration": {"name": "step1"},
                        "inputs": [],
                        "outputs": [],
                        "model_levels": {},
                        "validation": {},
                        "dependencies": [],
                    }
                    
                    handle_info(ctx, "step1", False, False, "step2,step3")
                    
                    # Should be called 3 times (step1, step2, step3)
                    assert mock_display.call_count == 3

    def test_handle_info_json_output(self):
        """Test handle_info with JSON output."""
        from prompt_pipeline_cli.commands.run_step import handle_info
        ctx = Mock()
        ctx.obj = {"config": "configuration/pipeline_config.yaml"}
        
        with patch('prompt_pipeline_cli.commands.run_step.PromptManager') as mock_pm_class:
            with patch('prompt_pipeline_cli.commands.run_step.display_step_info') as mock_display:
                mock_prompt_manager = Mock()
                mock_pm_class.return_value = mock_prompt_manager
                
                with patch('prompt_pipeline_cli.commands.run_step._get_step_info') as mock_get_info:
                    mock_get_info.return_value = {
                        "step_name": "step1",
                        "configuration": {"name": "step1"},
                        "inputs": [],
                        "outputs": [],
                        "model_levels": {},
                        "validation": {},
                        "dependencies": [],
                    }
                    
                    handle_info(ctx, "step1", False, True, None)
                    
                    # Verify display_step_info was called with as_json=True
                    assert mock_display.called
                    # Check that as_json parameter was True
                    call_kwargs = mock_display.call_args[1]
                    assert call_kwargs.get('as_json') is True

    def test_handle_info_verbose_output(self):
        """Test handle_info with verbose output."""
        from prompt_pipeline_cli.commands.run_step import handle_info
        ctx = Mock()
        ctx.obj = {"config": "configuration/pipeline_config.yaml"}
        
        with patch('prompt_pipeline_cli.commands.run_step.PromptManager') as mock_pm_class:
            with patch('prompt_pipeline_cli.commands.run_step.display_step_info') as mock_display:
                mock_prompt_manager = Mock()
                mock_pm_class.return_value = mock_prompt_manager
                
                with patch('prompt_pipeline_cli.commands.run_step._get_step_info') as mock_get_info:
                    mock_get_info.return_value = {
                        "step_name": "step1",
                        "configuration": {"name": "step1"},
                        "inputs": [],
                        "outputs": [],
                        "model_levels": {},
                        "validation": {},
                        "dependencies": [],
                    }
                    
                    handle_info(ctx, "step1", True, False, None)
                    
                    # Verify display_step_info was called with verbose=True
                    assert mock_display.called
                    # Check that verbose parameter was True
                    call_kwargs = mock_display.call_args[1]
                    assert call_kwargs.get('verbose') is True


class TestRunStepInfoOptions:
    """Test the run_step function with --info options."""

    def test_run_step_with_info_flag(self):
        """Test that run_step calls info() when --info flag is set."""
        from click.testing import CliRunner
        from prompt_pipeline_cli.main import cli
        
        runner = CliRunner()
        
        with patch('prompt_pipeline_cli.commands.run_step.PromptManager') as mock_pm_class:
            with patch('prompt_pipeline_cli.commands.run_step._get_step_info') as mock_get_info:
                with patch('prompt_pipeline_cli.commands.run_step.display_step_info') as mock_display:
                    mock_prompt_manager = Mock()
                    mock_pm_class.return_value = mock_prompt_manager
                    
                    # Mock _get_step_info to return valid data
                    mock_get_info.return_value = {
                        "step_name": "step1",
                        "configuration": {"name": "step1"},
                        "inputs": [],
                        "outputs": [],
                        "model_levels": {},
                        "validation": {},
                        "dependencies": [],
                    }
                    
                    # Invoke the full CLI with --info flag
                    result = runner.invoke(cli, ['run-step', 'step1', '--info'])
                    
                    # Should succeed (info() function handles the rest)
                    assert result.exit_code == 0
                    # Verify display_step_info was called (info() was called internally)
                    assert mock_display.called

    def test_run_step_info_verbose_without_info(self):
        """Test that --info-verbose without --info raises an error."""
        from click.testing import CliRunner
        from prompt_pipeline_cli.main import cli
        
        runner = CliRunner()
        
        with patch('prompt_pipeline_cli.commands.run_step.PromptManager'):
            result = runner.invoke(cli, ['run-step', 'step1', '--info-verbose'])
            
            # Should fail with appropriate error message
            assert result.exit_code != 0
            assert "--info-verbose" in result.output or "info-verbose" in result.output

    def test_run_step_info_json_without_info(self):
        """Test that --info-json without --info raises an error."""
        from click.testing import CliRunner
        from prompt_pipeline_cli.main import cli
        
        runner = CliRunner()
        
        with patch('prompt_pipeline_cli.commands.run_step.PromptManager'):
            result = runner.invoke(cli, ['run-step', 'step1', '--info-json'])
            
            # Should fail with appropriate error message
            assert result.exit_code != 0
            assert "--info-json" in result.output or "info-json" in result.output

    def test_run_step_info_steps_without_info(self):
        """Test that --info-steps without --info raises an error."""
        from click.testing import CliRunner
        from prompt_pipeline_cli.main import cli
        
        runner = CliRunner()
        
        with patch('prompt_pipeline_cli.commands.run_step.PromptManager'):
            result = runner.invoke(cli, ['run-step', 'step1', '--info-steps', 'step2'])
            
            # Should fail with appropriate error message
            assert result.exit_code != 0
            assert "--info-steps" in result.output or "info-steps" in result.output


class TestTerminalUtils:
    """Test the print_section() helper function."""

    @patch('builtins.print')
    def test_print_section(self, mock_print):
        """Test print_section displays section header."""
        from prompt_pipeline.terminal_utils import print_section, Color
        
        print_section("Test Section", Color.CYAN)
        
        # Should print at least 2 times (underline + text)
        assert mock_print.call_count >= 2
        
        # Check that section title is printed
        calls = [str(call) for call in mock_print.call_args_list]
        assert any("Test Section" in call for call in calls)

    @patch('builtins.print')
    def test_print_section_without_color(self, mock_print):
        """Test print_section with color disabled."""
        from prompt_pipeline.terminal_utils import print_section
        
        print_section("Test Section")
        
        # Should still print
        assert mock_print.call_count >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
