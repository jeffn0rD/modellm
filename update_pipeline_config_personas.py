"""
Script to update pipeline_config.yaml with personas and input descriptions
"""

import re
import yaml

def update_pipeline_config():
    """
    Update pipeline_config.yaml to add:
    - persona field for each step
    - description field for each input
    """
    
    filepath = 'configuration/pipeline_config.yaml'
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Define persona for each step
    step_personas = {
        "step1": "systems_architect",
        "step2": "software_engineer",
        "step3": "software_engineer",
        "stepC3": "systems_architect",
        "stepC4": "software_engineer",
        "stepC5": "systems_architect",
        "stepD1": "systems_engineer",
    }
    
    # Define input descriptions based on compression type
    input_descriptions = {
        "nl_spec": "Natural language specification (markdown)",
        "spec": {
            "full": "YAML specification with sections, anchors, and text blocks",
            "anchor_index": "anchor index format (AN1: definition, AN2: definition...)",
        },
        "spec_formal": "Formal markdown specification",
        "concepts": {
            "full": "JSON array of concepts (Actors, Actions, DataEntities)",
            "concept_summary": "concept summary format (markdown tables grouped by entity type)",
        },
        "aggregations": {
            "full": "JSON array of aggregations",
            "concept_summary": "concept summary format (markdown tables grouped by entity type)",
        },
        "messages": {
            "full": "JSON array of messages",
            "concept_summary": "concept summary format (markdown tables grouped by entity type)",
        },
        "requirements": "JSON array of requirements",
    }
    
    # Parse YAML to get the structure
    config = yaml.safe_load(content)
    
    # Update each step
    for step_name, step_config in config['steps'].items():
        # Add persona if not present
        if 'persona' not in step_config:
            persona = step_personas.get(step_name, "software_engineer")
            # Add persona after name field
            step_config['persona'] = persona
        
        # Update input descriptions
        for inp in step_config.get('inputs', []):
            label = inp['label']
            compression = inp.get('compression', 'full')
            
            # Get description based on label and compression
            if label in input_descriptions:
                desc_config = input_descriptions[label]
                if isinstance(desc_config, dict):
                    # Description varies by compression type
                    inp['description'] = desc_config.get(compression, desc_config.get('full', ''))
                else:
                    # Simple description
                    inp['description'] = desc_config
            else:
                # Default description
                inp['description'] = f"Input with label: {label}"
    
    # Write back to file
    with open(filepath, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, width=100)
    
    print("Updated pipeline_config.yaml with:")
    print("- Persona field for each step")
    print("- Input description field for each input")
    print("")
    print("Step personas:")
    for step, persona in step_personas.items():
        print(f"  {step}: {persona}")


if __name__ == '__main__':
    update_pipeline_config()
