import re

content = open('prompts/prompt_step_C4.md', 'r', encoding='utf-8').read()

for match in re.finditer(r'You will receive', content, re.IGNORECASE):
    start = max(0, match.start() - 200)
    end = min(len(content), match.end() + 200)
    print(f"Context around 'You will receive':")
    print(repr(content[start:end]))
    print("=" * 80)
