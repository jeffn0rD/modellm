import re

content = open('prompts/prompt_step2_v2.md', 'r', encoding='utf-8').read()

print("Finding 'Input' keyword...")
for match in re.finditer(r'Input', content, re.IGNORECASE):
    start = max(0, match.start() - 100)
    end = min(len(content), match.end() + 200)
    print(f"Context around 'Input':")
    print(repr(content[start:end]))
    print("=" * 80)
