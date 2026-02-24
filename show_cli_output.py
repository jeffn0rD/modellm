#!/usr/bin/env python
"""Show CLI output."""

import subprocess
result = subprocess.run([
    "python", "-m", "prompt_pipeline_cli.main",
    "run-step",
    "--nl-spec", "doc/todo_list_nl_spec.md",
    "--dry-run-prompt",
    "step1"
], capture_output=True, text=True, cwd=".")

print("Return code:", result.returncode)

if result.returncode == 0:
    # Show lines with nl_spec or the preamble
    lines = result.stdout.split('\n')
    in_given = False
    for i, line in enumerate(lines):
        if "Given the inputs:" in line:
            in_given = True
        if in_given:
            print(f"{i}: {line}")
        if in_given and line.strip() and not line.startswith('  '):
            break
else:
    print("Error:", result.stderr)
