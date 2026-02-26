with open('prompt_pipeline_cli/commands/run_step.py', 'r') as f:
    content = f.read()
    # Find where we call info(
    lines = content.split('\n')
    for i, line in enumerate(lines, 1):
        # Look for calls to info( but not info_verbose, info_json, info_steps, or print_info
        if 'info(' in line and not any(x in line for x in ['info_verbose', 'info_json', 'info_steps', 'print_info', 'def info']):
            print(f'{i}: {line}')
