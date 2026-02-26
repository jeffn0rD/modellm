from unittest.mock import Mock, patch
from prompt_pipeline_cli.commands.run_step import _display_verbose_explanations

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

# Capture the print calls
with patch('builtins.print') as mock_print:
    _display_verbose_explanations(info)
    
    # Print all the calls
    print(f"Number of calls: {len(mock_print.call_args_list)}")
    for i, call in enumerate(mock_print.call_args_list):
        # Get the arguments
        args, kwargs = call
        if args:
            print(f"Call {i}: {args[0]}")
