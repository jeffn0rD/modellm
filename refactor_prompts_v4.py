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
    
    # Pattern 1: Remove "INPUTS" section header and "You will be given:" description
    # But keep the tag placeholders
    
    # First, capture the INPUTS section
    inputs_start_pattern = r'(\n\s*INPUTS\s*\n\s*You will be given:\s*\n)'
    
    def replace_inputs_start(match):
        """Replace INPUTS header with empty"""
        return ''
    
    content = re.sub(inputs_start_pattern, replace_inputs_start, content, flags=re.IGNORECASE | re.DOTALL)
    
    # Pattern 2: Remove numbered input descriptions (like "1. The edited formal markdown specification:")
    # These are lines that describe inputs
    numbered_input_pattern = r'\n\s*\d+\.\s*The .+?\n\s*\{\{[^}]+\}\}\s*\n\s*\n'
    content = re.sub(numbered_input_pattern, r'\n{{' + r'}}\n\n', content, flags=re.IGNORECASE | re.DOTALL)
    
    # Pattern 3: Remove "Assumptions:" section and the YAML example that follows
    assumptions_pattern = r'\n\s*Assumptions:\s*\n\s*\n\s*The .+? follows .+?\n\s*\n(?:.*?\n)*?(?=\n\s*---|\n\s*UPDATE LOGIC|\n\s*UPDATE |\n\s*Task|\n\s*Output|\n\s*Step|\n\s*\d+\.\s*|\n\s*2\.)'
    content = re.sub(assumptions_pattern, '\n', content, flags=re.IGNORECASE | re.DOTALL)
    
    # Pattern 4: Remove YAML structure examples (lines that start with "specification:" or specific YAML patterns)
    # These are examples of what the YAML looks like
    yaml_example_pattern = r'\n\s*specification:\s*\n\s*id:\s*SPEC1\n(?:.*?\n)*?(?=\n\s*---|\n\s*UPDATE LOGIC|\n\s*Task|\n\s*Output|\n\s*Step|\n\s*\d+\.\s*|\n\s*2\.)'
    content = re.sub(yaml_example_pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
    
    # Pattern 5: Remove "You will receive:" section
    you_will_receive_pattern = r'(\n\s*You will receive:\s*\n)(.*?\n)(\s*\n\s*\{\{[^}]+\}\}\s*\n)'
    
    def replace_you_will_receive(match):
        """Replace with just the tag placeholder"""
        return match.group(3)  # Just return the tag line
    
    content = re.sub(you_will_receive_pattern, replace_you_will_receive, content, flags=re.IGNORECASE | re.DOTALL)
    
    # Pattern 6: Remove "Input" section (for step2 which doesn't have INPUTS header)
    # Pattern: "Input" followed by description then tag
    input_section_pattern = r'\n\s*Input\s*\n\s*\([^)]+\)\s*\n\s*\{\{[^}]+\}\}\s*\n\n'
    content = re.sub(input_section_pattern, '\n\n', content, flags=re.IGNORECASE)
    
    # Pattern 7: Clean up orphaned input description lines
    # Lines like:
    # "1. **Specification YAML**  one or more YAML documents that..."
    orphaned_desc_pattern = r'\n\s*\d+\.\s*\*\*[^*]+\*\*.*?\n\s*\n'
    content = re.sub(orphaned_desc_pattern, '\n', content, flags=re.DOTALL)
    
    # Pattern 8: Remove lines that start with "•" (bullet points in input descriptions)
    bullet_input_pattern = r'\n\s*• .+?\n'
    content = re.sub(bullet_input_pattern, '\n', content, flags=re.IGNORECASE | re.DOTALL)
    
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
