# Prompt Update Summary

## Task: Update prompts for compression support

### Changes Made

Updated all 7 prompt files to:
1. Use the new `{{TAG}}` format instead of the old `<<<TAG>>>` format
2. Match tag names with the pipeline configuration labels

### Updated Files

1. **prompt_step1_v2.md**
   - Changed: `<<<INPUT_SPEC>>>` → `{{nl_spec}}`
   - Matches config: `nl_spec` input from CLI

2. **prompt_step2_v2.md**
   - Changed: `<<<YAML_SPECIFICATION>>>` → `{{spec}}`
   - Matches config: `spec` input from step1 output

3. **prompt_step3_v2.md**
   - Changed: `<<<FORMAL_MARKDOWN_SPEC>>>` → `{{spec_formal}}`
   - Changed: `<<<OLD_YAML_SPEC>>>` → `{{spec}}`
   - Matches config: `spec_formal` from step2, `spec` from step1

4. **prompt_step_C3.md**
   - Added: `{{spec}}` tag in input section
   - Matches config: `spec` input from step1 output

5. **prompt_step_C4.md**
   - Added: `{{spec}}` and `{{concepts}}` tags in input sections
   - Matches config: `spec` from step1, `concepts` from stepC3

6. **prompt_step_C5.md**
   - Added: `{{spec}}`, `{{concepts}}`, and `{{aggregations}}` tags in input sections
   - Matches config: `spec` from step1, `concepts` from stepC3, `aggregations` from stepC4

7. **prompt_step_D1.md**
   - Added: `{{spec}}`, `{{concepts}}`, and `{{messages}}` tags in input sections
   - Matches config: `spec` from step1, `concepts` from stepC3, `messages` from stepC5

### Tag Replacement System

The updated prompts now use the `{{TAG}}` format which is compatible with the `TagReplacer` class in `prompt_pipeline/tag_replacement.py`. This system:

- Supports `{{tag_name}}` format for tag placeholders
- Automatically loads file content for tag replacements
- Validates that all required tags are present
- Handles missing tags gracefully with optional default values

### Verification

All prompts have been verified to:
- Use the new `{{TAG}}` format
- Match tag names with pipeline configuration labels
- Include all required input tags for their respective steps
- Follow consistent naming conventions

### Next Steps

The prompts are now ready for:
1. Tag replacement during step execution
2. Compression strategy integration
3. Testing with the actual prompt pipeline
