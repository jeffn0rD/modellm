#!/usr/bin/env python
"""Find all methods in step_executor."""

from pathlib import Path

content = Path('prompt_pipeline/step_executor.py').read_text(encoding='utf-8')
lines = content.split('\n')

for i, line in enumerate(lines):
    if line.strip().startswith('def ') or line.strip().startswith('async def '):
        print(f'{i+1}: {line}')
