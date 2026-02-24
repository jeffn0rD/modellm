#!/usr/bin/env python
"""Show full CLI output."""

import subprocess
result = subprocess.run([
    "python", "-m", "prompt_pipeline_cli.main",
    "run-step",
    "--nl-spec", "doc/todo_list_nl_spec.md",
    "--dry-run-prompt",
    "step1"
], capture_output=True, text=True, cwd=".")

print("Return code:", result.returncode)
print("\nStdout length:", len(result.stdout))
print("\nStderr length:", len(result.stderr))

# Show first 20 lines of stdout
print("\nFirst 20 lines of stdout:")
for i, line in enumerate(result.stdout.split('\n')[:20], 1):
    print(f"{i}: {line}")

# Show stderr if not empty
if result.stderr:
    print("\nStderr:")
    print(result.stderr[:500])
