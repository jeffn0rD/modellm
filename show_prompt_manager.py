#!/usr/bin/env python
"""Show PromptManager methods."""

from pathlib import Path

content = Path('prompt_pipeline/prompt_manager.py').read_text(encoding='utf-8')
lines = content.split('\n')
for i, line in enumerate(lines):
    if 'def ' in line and not line.strip().startswith('#'):
        print(f'{i+1}: {line}')
