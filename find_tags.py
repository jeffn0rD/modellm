import re

content = open('prompts/prompt_step2_v2.md', 'r', encoding='utf-8').read()

print("Finding tags...")
tags = re.findall(r'{{[^}]+}}', content)
print(f"Found {len(tags)} tags:")
for tag in tags:
    print(f"  - {tag}")
