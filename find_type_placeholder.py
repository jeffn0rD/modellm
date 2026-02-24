#!/usr/bin/env python
"""Find where {type} placeholder appears."""

from pathlib import Path
import os

# Search in all Python files
for root, dirs, files in os.walk("."):
    # Skip certain directories
    if any(x in root for x in ['.git', '__pycache__', '.pytest_cache', 'node_modules']):
        continue
    
    for file in files:
        if file.endswith('.py'):
            filepath = Path(root) / file
            try:
                content = filepath.read_text(encoding='utf-8')
                if '{type' in content:
                    print(f"\n{filepath}:")
                    for i, line in enumerate(content.split('\n'), 1):
                        if '{type' in line:
                            print(f"  Line {i}: {line.strip()}")
            except:
                pass
