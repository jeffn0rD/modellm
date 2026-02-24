"""
Preamble Generator Module

Generates dynamic preamble text for prompts based on configuration.
The preamble includes persona, step number, and input descriptions.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class InputDescriptor:
    """Descriptor for a single input to the prompt."""
    label: str
    compression: str
    description: str
    type: str


class PreambleGenerator:
    """
    Generates preamble text for prompts.
    
    The preamble provides context about:
    - Who is generating the response (persona)
    - What step this is (step number)
    - What inputs are available (input descriptions)
    - How to interpret the inputs (compression format info)
    """
    
    # Predefined personas for different step types
    PERSONAS = {
        "systems_architect": "systems architect",
        "software_engineer": "software engineer",
        "systems_engineer": "systems engineer",
    }
    
    # Format descriptions for different compression types
    COMPRESSION_DESCRIPTIONS = {
        "none": "Complete {type}",
        "zero": "Complete {type}",
        "anchor_index": "anchor index format (AN1: definition, AN2: definition...)",
        "concept_summary": "concept summary format (markdown tables grouped by entity type)",
        "hierarchical": "hierarchical format",
        "schema_only": "schema-only format",
        "differential": "differential format",
    }
    
    # Type descriptions for different input types
    TYPE_DESCRIPTIONS = {
        "yaml": "YAML specification",
        "yml": "YAML specification",
        "json": "JSON data",
        "md": "markdown document",
        "text": "text document",
    }
    
    def generate_preamble(
        self,
        step_name: str,
        step_number: Optional[int],
        persona: str,
        inputs: List[InputDescriptor],
    ) -> str:
        """
        Generate preamble text for a prompt.
        
        Args:
            step_name: Name of the step (e.g., "stepC3")
            step_number: Numeric step number (e.g., 1, 2, 3)
            persona: Persona for this step (e.g., "systems_architect")
            inputs: List of input descriptors for this step
        
        Returns:
            Formatted preamble text to prepend to prompt template
        """
        # Get the persona text
        persona_text = self.PERSONAS.get(persona, persona)
        
        # Build the preamble
        preamble_lines = []
        
        # Step identifier (for analysis/debugging)
        step_info = f"Step: {step_name}"
        if step_number:
            step_info += f" (#{step_number})"
        preamble_lines.append(step_info)
        preamble_lines.append("")
        
        # Persona line
        preamble_lines.append(f"You are a {persona_text}.")
        preamble_lines.append("")
        
        # Input section (if there are inputs)
        if inputs:
            preamble_lines.append("Given the inputs:")
            
            for inp in inputs:
                description = self._format_input_description(inp)
                preamble_lines.append(f"  - {inp.label}: {description}")
            
            preamble_lines.append("")
        
        # Task declaration
        preamble_lines.append("Your task is:")
        preamble_lines.append("")
        
        return "\n".join(preamble_lines)
    
    def _format_input_description(self, inp: InputDescriptor) -> str:
        """
        Format a single input description.
        
        Args:
            inp: Input descriptor
        
        Returns:
            Formatted description string
        """
        # Get the base type description
        type_desc = self.TYPE_DESCRIPTIONS.get(inp.type, inp.type)
        
        # If a description is provided, use it
        if inp.description:
            return inp.description
        
        # Get compression description
        compression_desc = self.COMPRESSION_DESCRIPTIONS.get(
            inp.compression, 
            f"{inp.compression} format"
        )
        
        # For uncompressed formats, just show the type
        if inp.compression in ["none", "zero"]:
            return type_desc
        else:
            # For compressed formats, describe the format
            # (the model knows the format, just needs to know how to parse it)
            return compression_desc
    
    def create_input_descriptors(
        self,
        inputs_config: List[Dict],
    ) -> List[InputDescriptor]:
        """
        Convert input configuration to InputDescriptor objects.
        
        Args:
            inputs_config: List of input configs from pipeline_config.yaml
        
        Returns:
            List of InputDescriptor objects
        """
        descriptors = []
        
        for inp_config in inputs_config:
            descriptors.append(InputDescriptor(
                label=inp_config["label"],
                compression=inp_config.get("compression", "full"),
                description=inp_config.get("description", ""),
                type=inp_config.get("type", "unknown"),
            ))
        
        return descriptors
