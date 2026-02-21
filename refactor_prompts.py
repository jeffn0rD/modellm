"""
Script to refactor prompts by removing input descriptions that will be replaced by preamble
"""

import re
import os

def refactor_prompt(filename, prompt_dir="prompts"):
    """
    Refactor a single prompt file.
    
    Args:
        filename: Name of the prompt file
        prompt_dir: Directory containing prompts
    
    Returns:
        Updated content or None if no changes needed
    """
    filepath = os.path.join(prompt_dir, filename)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Pattern 1: Remove "Input" section followed by input description
    # This removes lines like:
    # "Input"
    # "Informal specification (client-style...):"
    # "{{nl_spec}}"
    input_section_pattern = r'\n\s*Input\s*\n\s*\([^)]+\)\s*\n\s*\{\{[^}]+\}\}\s*\n\n'
    content = re.sub(input_section_pattern, '\n\n', content, flags=re.IGNORECASE)
    
    # Pattern 2: Remove "You will receive:" followed by input descriptions
    # But only if not followed by YAML examples
    you_will_receive_pattern = r'\n\s*You will receive:\s*\n(?:\s*- .*\n)*\s*\{\{[^}]+\}\}\s*\n\n'
    content = re.sub(you_will_receive_pattern, '\n\n', content, flags=re.IGNORECASE)
    
    # Pattern 3: Remove "INPUTS" section header and input descriptions
    # But preserve YAML structure examples
    inputs_section_pattern = r'\n\s*INPUTS\s*\n\s*You will be given:\s*\n\s*\n\s*\*\*\*.*?\*\*\*\s*\n\s*\{\{[^}]+\}\}\s*\n\s*\n\s*\*\*\*.*?\*\*\*\s*\n\s*\{\{[^}]+\}\}\s*\n\s*\n\s*Assumptions:\s*\n\s*\n'
    content = re.sub(inputs_section_pattern, '\n\n', content, flags=re.IGNORECASE | re.DOTALL)
    
    # Pattern 4: Remove lines that describe input formats
    # Lines like:
    # "One or more YAML documents that..."
    # "A list of Concepts produced in..."
    input_desc_pattern = r'\n\s*- .* (that|produced in|with).*?\n'
    # This is too broad, skip it
    
    # Check if content changed
    if content != original_content:
        return content
    else:
        return None


def refactor_all_prompts():
    """Refactor all prompt files."""
    
    prompts_dir = "prompts"
    
    # List of prompts to refactor (excluding step1 which doesn't have input description)
    prompts_to_refactor = [
        "prompt_step2_v2.md",
        "prompt_step3_v2.md",
        "prompt_step_C3.md",
        "prompt_step_C4.md",
        "prompt_step_C5.md",
        "prompt_step_D1.md",
    ]
    
    for filename in prompts_to_refactor:
        updated_content = refactor_prompt(filename, prompts_dir)
        
        if updated_content:
            filepath = os.path.join(prompts_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            print(f"Updated: {filename}")
        else:
            print(f"No changes needed: {filename}")


if __name__ == '__main__':
    refactor_all_prompts()
