with open('prompt_pipeline_cli/commands/run_step.py', 'r') as f:
    content = f.read()
    # Find where we call info(
    if 'info(' in content:
        # Find the line numbers
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if 'info(' in line and 'def info' not in line:
                print(f'{i}: {line}')
