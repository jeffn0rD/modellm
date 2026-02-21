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
    
    # Pattern 1: Remove "You will receive:" section
    # This section describes what inputs will be given
    # We want to remove it because the preamble will handle it
    # Example:
    # "You will receive:"
    # "1. **Specification YAML**  one or more YAML documents that..."
    # "2. **Concepts.json**: ..."
    # Then the actual tag placeholders (which we need to keep)
    
    # The challenge is we want to remove the descriptive text but KEEP the tag placeholders
    # Let's match from "You will receive:" up to and including the first tag placeholder
    
    you_will_receive_pattern = r'(\n\s*You will receive:\s*\n)(.*?\n)(\s*\n\s*\{\{[^}]+\}\}\s*\n)'
    
    def replace_you_will_receive(match):
        """Replace with just the tag placeholder"""
        return match.group(3)  # Just return the tag line
    
    content = re.sub(you_will_receive_pattern, replace_you_will_receive, content, flags=re.IGNORECASE | re.DOTALL)
    
    # Pattern 2: Remove lines that describe the input format
    # These are lines like:
    # "1. **Specification YAML**  one or more YAML documents that..."
    # "2. **Concepts.json**: ..."
    # After removing "You will receive:", these orphaned lines should be removed
    
    # Match standalone lines that are input descriptions (numbered list items)
    input_desc_pattern = r'\n\s*\d+\.\s*\*\*[^*]+\*\*.*?\n'
    content = re.sub(input_desc_pattern, '', content, flags=re.DOTALL)
    
    # Pattern 3: Remove the "Assumptions:" section that follows input descriptions
    # This section is just more description about what the inputs look like
    assumptions_pattern = r'\n\s*Assumptions:\s*\n\s*\n(?:.*?\n)*?\n'
    content = re.sub(assumptions_pattern, '\n', content, flags=re.IGNORECASE | re.DOTALL)
    
    # Pattern 4: Remove "Input" section that just describes format
    # Pattern: "Input" followed by description then tag
    input_section_pattern = r'\n\s*Input\s*\n\s*\([^)]+\)\s*\n\s*\{\{[^}]+\}\}\s*\n\n'
    content = re.sub(input_section_pattern, '\n\n', content, flags=re.IGNORECASE)
    
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
