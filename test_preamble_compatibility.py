"""
Test if prompts will work with the new preamble design
"""

import re

# Check each prompt for issues
prompts_to_check = [
    "prompts/prompt_step1_v2.md",
    "prompts/prompt_step2_v2.md",
    "prompts/prompt_step3_v2.md",
    "prompts/prompt_step_C3.md",
    "prompts/prompt_step_C4.md",
    "prompts/prompt_step_C5.md",
    "prompts/prompt_step_D1.md",
]

print("=" * 80)
print("PROMPT REWRITE VALIDATION")
print("=" * 80)

for prompt_file in prompts_to_check:
    with open(prompt_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"\n{prompt_file}:")
    print("-" * 80)
    
    issues = []
    
    # Check 1: Input structure descriptions
    input_structure_patterns = [
        r'input is a .+? document',
        r'input is .+? structure',
        r'the input .+? has .+? structure',
        r'input format',
        r'input structure',
        r'given the following input',
        r'you will receive',
        r'you will be given',
    ]
    
    for pattern in input_structure_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            issues.append(f"  [ERROR] Input structure description found: {pattern}")
    
    # Check 2: YAML structure examples
    if re.search(r'specification:\s*id:', content):
        issues.append(f"  [ERROR] YAML structure example found in prompt")
    
    # Check 3: Schema examples
    if re.search(r'JSON schema|schema description', content, re.IGNORECASE):
        issues.append(f"  [ERROR] Schema description found (should be in preamble)")
    
    # Check 4: Tag placeholders
    tags = re.findall(r'{{[^}]+}}', content)
    if tags:
        print(f"  [OK] Tag placeholders found: {tags}")
        for tag in tags:
            if tag in content.split('*** INPUT DATA ***')[0]:
                issues.append(f"  [ERROR] Tag {tag} found before INPUT DATA section")
    
    # Check 5: Input data section
    input_data_match = re.search(r'\*\*\* INPUT DATA \*\*\*', content)
    if input_data_match:
        print(f"  [OK] *** INPUT DATA *** section found")
        # Check if there's anything between the marker and the tag
        after_marker = content[input_data_match.end():]
        lines_after = after_marker.strip().split('\n')
        if lines_after and lines_after[0].strip() and not lines_after[0].strip().startswith('{{'):
            issues.append(f"  [WARNING] Text between INPUT DATA marker and tag")
    else:
        issues.append(f"  [ERROR] Missing *** INPUT DATA *** section")
    
    # Check 6: Task-specific input structure definitions
    # These should NOT be in the prompt
    task_specific_patterns = [
        r'YAML document with the following structure',
        r'JSON array of .+? objects',
        r'JSON object with .+? fields',
        r'the input .+? consists of',
        r'format of the input',
    ]
    
    for pattern in task_specific_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            issues.append(f"  [ERROR] Input format description found: {pattern}")
    
    # Check 7: Multiple INPUT DATA sections (duplicated content)
    input_data_count = len(re.findall(r'\*\*\* INPUT DATA \*\*\*', content))
    if input_data_count > 1:
        issues.append(f"  [ERROR] Multiple *** INPUT DATA *** sections ({input_data_count} found)")
    
    # Check 8: Compression-related text
    compression_patterns = [
        r'anchor index',
        r'concept summary',
        r'compressed',
        r'full format',
    ]
    
    for pattern in compression_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            issues.append(f"  [WARNING] Compression text found: {pattern} (should be in preamble)")
    
    # Summary
    if issues:
        for issue in issues:
            print(issue)
        print(f"  [WARNING] {len(issues)} issues found")
    else:
        print(f"  [OK] No issues found - ready for preamble integration")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("Expected structure:")
print("  1. Task logic and definitions")
print("  2. Output format requirements")
print("  3. *** INPUT DATA *** section with tag placeholders")
print("  4. NO input structure descriptions (those come from preamble)")
