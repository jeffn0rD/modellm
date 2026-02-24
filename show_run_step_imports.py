#!/usr/bin/env python
"""Show imports in run_step.py."""

from pathlib import Path

content = Path('prompt_pipeline_cli/commands/run_step.py').read_text(encoding='utf-8')
lines = content.split('\n')
for i, line in enumerate(lines):
    if 'import ' in line or 'from ' in line:
        print(f'{i+1}: {line}')
