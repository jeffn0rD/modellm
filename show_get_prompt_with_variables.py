#!/usr/bin/env python
"""Show get_prompt_with_variables method."""

from pathlib import Path

content = Path('prompt_pipeline/prompt_manager.py').read_text(encoding='utf-8')
lines = content.split('\n')
start = 352
end = 420
for i in range(start, end):
    try:
        print(f'{i+1}: {lines[i]}')
    except:
        print(f'{i+1}: [UNICODE ERROR]')
