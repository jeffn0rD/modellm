#!/usr/bin/env python
"""Show execute_step method."""

from pathlib import Path

content = Path('prompt_pipeline/step_executor.py').read_text(encoding='utf-8')
lines = content.split('\n')
start = 119
end = 255
print('\n'.join([f'{i+1}: {lines[i]}' for i in range(start, end)]))
