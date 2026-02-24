#!/usr/bin/env python
"""Find the method that constructs the prompt."""

from pathlib import Path

content = Path('prompt_pipeline/step_executor.py').read_text(encoding='utf-8')
lines = content.split('\n')

for i, line in enumerate(lines):
    if 'def execute_step' in line or 'def get_prompt' in line or 'def construct_prompt' in line:
        print(f'{i+1}: {line}')
