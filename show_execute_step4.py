#!/usr/bin/env python
"""Show execute_step method."""

from pathlib import Path

content = Path('prompt_pipeline/step_executor.py').read_text(encoding='utf-8')
lines = content.split('\n')
start = 200
end = 255
for i in range(start, end):
    try:
        print(f'{i+1}: {lines[i]}')
    except:
        print(f'{i+1}: [UNICODE ERROR]')
