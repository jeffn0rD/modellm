import re

content = open('prompts/prompt_step_C4.md', 'r', encoding='utf-8').read()

print("Checking for INPUTS keyword...")
matches = re.findall(r'INPUTS', content)
print(f"Found {len(matches)} INPUTS matches")

print("\nChecking for 'You will receive'...")
matches = re.findall(r'You will receive', content, re.IGNORECASE)
print(f"Found {len(matches)} 'You will receive' matches")

print("\nChecking for 'Given the inputs'...")
matches = re.findall(r'Given the inputs', content, re.IGNORECASE)
print(f"Found {len(matches)} 'Given the inputs' matches")

# Show context around INPUTS if found
for match in re.finditer(r'INPUTS', content):
    start = max(0, match.start() - 100)
    end = min(len(content), match.end() + 100)
    print(f"\nContext around 'INPUTS':\n{repr(content[start:end])}")
    print("=" * 80)
