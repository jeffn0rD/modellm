from click.testing import CliRunner
from prompt_pipeline_cli.main import cli
from unittest.mock import Mock, patch

runner = CliRunner()

with patch('prompt_pipeline_cli.commands.run_step.PromptManager') as mock_pm_class:
    with patch('prompt_pipeline_cli.commands.run_step._get_step_info') as mock_get_info:
        with patch('prompt_pipeline_cli.commands.run_step.display_step_info') as mock_display:
            mock_prompt_manager = Mock()
            mock_pm_class.return_value = mock_prompt_manager
            
            # Mock _get_step_info to return valid data
            mock_get_info.return_value = {
                'step_name': 'step1',
                'configuration': {'name': 'step1'},
                'inputs': [],
                'outputs': [],
                'model_levels': {},
                'validation': {},
                'dependencies': [],
            }
            
            # Invoke the full CLI with --info flag
            result = runner.invoke(cli, ['run-step', 'step1', '--info'])
            
            # Check result
            print('Exit code:', result.exit_code)
            print('Output:', result.output)
            print('Exception:', result.exception)
            print('Exception type:', type(result.exception) if result.exception else None)
