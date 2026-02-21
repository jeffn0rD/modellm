import re

content = open('prompts/prompt_step2_v2.md', 'r', encoding='utf-8').read()
lines = content.split('\n')

print("Lines 15-40:")
for i in range(15, 40):
    if i < len(lines):
        print(f"{i+1}: {lines[i]}")
