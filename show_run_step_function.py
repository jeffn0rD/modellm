#!/usr/bin/env python
"""Show the run_step function definition."""

from pathlib import Path

content = Path('prompt_pipeline_cli/commands/run_step.py').read_text(encoding='utf-8')
lines = content.split('\n')
for i, line in enumerate(lines):
    if 'def run_step(' in line:
        print(f'{i+1}: {line}')
        # Show the decorator
        for j in range(i-10, i):
            print(f'{j+1}: {lines[j] if j >= 0 else ""}')
