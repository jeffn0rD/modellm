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
    
    # Pattern 1: Remove "INPUTS" section completely
    # This section includes:
    # - "INPUTS" header
    # - "You will be given:" description
    # - Input markers like "*** SPEC YAML ***" and tag placeholders
    # - "Assumptions:" section
    # - YAML structure examples (which are just context)
    
    # We want to remove everything from "INPUTS" up to the next section (which starts with "UPDATE LOGIC" or similar)
    inputs_section_pattern = r'(\n\s*INPUTS\s*\n)(.*?)(\n\s*UPDATE LOGIC|\n\s*UPDATE |\n\s*Task|\n\s*Output)'
    
    # If we match, we need to keep the tag placeholders but remove everything else
    def replace_inputs_section(match):
        """Keep only the tag placeholders"""
        full_section = match.group(0)
        
        # Extract just the tag placeholders
        tags = re.findall(r'\{\{[^}]+\}\}', full_section)
        
        if tags:
            # Return just the tags (one per line)
            return '\n' + '\n'.join(tags) + '\n'
        else:
            # No tags found, return empty
            return ''
    
    content = re.sub(inputs_section_pattern, replace_inputs_section, content, flags=re.IGNORECASE | re.DOTALL)
    
    # Pattern 2: Remove standalone input description lines
    # Lines like:
    # "1. **Specification YAML**  one or more YAML documents that..."
    # These are orphaned after removing INPUTS section
    input_desc_pattern = r'\n\s*\d+\.\s*\*\*[^*]+\*\*.*?\n\s*\n'
    content = re.sub(input_desc_pattern, '\n', content, flags=re.DOTALL)
    
    # Pattern 3: Remove "You will receive:" section (for prompts without INPUTS header)
    you_will_receive_pattern = r'(\n\s*You will receive:\s*\n)(.*?\n)(\s*\n\s*\{\{[^}]+\}\}\s*\n)'
    
    def replace_you_will_receive(match):
        """Replace with just the tag placeholder"""
        return match.group(3)  # Just return the tag line
    
    content = re.sub(you_will_receive_pattern, replace_you_will_receive, content, flags=re.IGNORECASE | re.DOTALL)
    
    # Pattern 4: Remove "Input" section (for step2 which doesn't have INPUTS header)
    # Pattern: "Input" followed by description then tag
    input_section_pattern = r'\n\s*Input\s*\n\s*\([^)]+\)\s*\n\s*\{\{[^}]+\}\}\s*\n\n'
    content = re.sub(input_section_pattern, '\n\n', content, flags=re.IGNORECASE)
    
    # Pattern 5: Remove "Assumptions:" section and everything after it until next section
    assumptions_pattern = r'\n\s*Assumptions:\s*\n\s*\n(?:.*?\n)*?(?=\n\s*---|\n\s*UPDATE LOGIC|\n\s*Task|\n\s*Output|\n\s*Step|\n\s*2\.|\n\s*3\.)'
    content = re.sub(assumptions_pattern, '\n', content, flags=re.IGNORECASE | re.DOTALL)
    
    # Pattern 6: Remove "You will be given:" and lines that follow until the first tag
    you_will_be_given_pattern = r'\n\s*You will be given:\s*\n(?:\s*\d+\.\s*.*?\n)*\s*\n\s*\{\{[^}]+\}\}\s*\n'
    content = re.sub(you_will_be_given_pattern, r'\n{{' + r'}}\n', content, flags=re.IGNORECASE | re.DOTALL)
    
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
