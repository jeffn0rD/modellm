from prompt_pipeline.preamble_generator import PreambleGenerator, InputDescriptor

generator = PreambleGenerator()

# Test with stepC3 inputs
inputs = [
    InputDescriptor(
        label="spec",
        compression="anchor_index",
        description="anchor index format (AN1: definition, AN2: definition...)",
        type="yaml"
    )
]

preamble = generator.generate_preamble(
    step_name="stepC3",
    step_number=4,
    persona="systems_architect",
    inputs=inputs
)

print("=" * 80)
print("PREAMBLE FOR stepC3:")
print("=" * 80)
print(preamble)
print("=" * 80)

# Test with stepC4 inputs (multiple)
inputs2 = [
    InputDescriptor(
        label="spec",
        compression="anchor_index",
        description="anchor index format (AN1: definition, AN2: definition...)",
        type="yaml"
    ),
    InputDescriptor(
        label="concepts",
        compression="concept_summary",
        description="concept summary format (markdown tables grouped by entity type)",
        type="json"
    )
]

preamble2 = generator.generate_preamble(
    step_name="stepC4",
    step_number=5,
    persona="software_engineer",
    inputs=inputs2
)

print("\n" + "=" * 80)
print("PREAMBLE FOR stepC4:")
print("=" * 80)
print(preamble2)
print("=" * 80)
