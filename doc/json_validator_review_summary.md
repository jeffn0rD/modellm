# JSON Validator Review Summary

## Executive Summary

The `prompt_pipeline/validation/json_validator.py` module has several issues that prevent it from properly validating JSON output against the schemas defined in the `schemas/` directory.

**Key Finding**: The schemas define **single objects** but the JSON files contain **arrays of objects**. This is a critical mismatch that prevents proper schema validation.

## Current State

### Problems Identified

1. **No jsonschema library usage**: The code uses custom validation logic instead of the `jsonschema` library for schema validation.

2. **Incomplete validation**: The `_validate_schema()` method only checks basic type (array vs object) and ignores all schema constraints:
   - Required fields
   - Property definitions
   - Pattern regex constraints
   - Enum values
   - AdditionalProperties restrictions
   - Nested object/array validations

3. **Schema-file mismatch**: 
   - Schemas: Define single objects (`{"type": "object", ...}`)
   - JSON files: Contain arrays (`[{...}, {...}]`)

4. **Logic inconsistency**: Validators check `if self.schema` to decide whether to run custom validations. This is backwards - when a schema is provided, the schema should be the source of truth.

5. **Code duplication**: Hardcoded patterns and field requirements that should come from schemas.

## Recommendations

### Priority 1: Fix Schema Structure (Critical)

Update all `*.schema.json` files to use array type with `items`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["type", "id", "label", "description"],
    "properties": {...}
  }
}
```

### Priority 2: Use jsonschema Library

Refactor `JSONValidator` base class to use `jsonschema.validate()`:

```python
import jsonschema

def _validate_schema(self, data: Any, result: ValidationResult) -> None:
    if not self.schema:
        return
    
    try:
        jsonschema.validate(instance=data, schema=self.schema)
    except jsonschema.exceptions.ValidationError as e:
        result.add_error(f"Schema validation failed: {e.message}")
```

### Priority 3: Simplify Validators

Remove all custom validation logic from subclasses:
- Remove hardcoded ID patterns
- Remove hardcoded required fields
- Remove hardcoded enum validations
- Keep only structural checks that can't be expressed in JSON Schema

### Priority 4: Update Tests

- Tests must use actual schemas (not `schema_path=""` to disable)
- Test all schema types: concepts, aggregations, messages, requirements
- Remove tests that rely on custom validation

## Scope Boundaries

### IN SCOPE ✅
- Schema validation using jsonschema library
- Schema is the source of truth
- Validation errors from schema constraints
- Proper error reporting

### OUT OF SCOPE ❌
- ID reference validation across files
- Cross-file consistency checking
- TypeDB import validation
- Duplicate ID detection (current schemas don't enforce this)

## Implementation Path

1. **Phase 1**: Fix `concepts.schema.json` to be an array schema
2. **Phase 2**: Update `json_validator.py` to use jsonschema
3. **Phase 3**: Fix remaining schema files (aggregations, messages, requirements)
4. **Phase 4**: Simplify validator classes
5. **Phase 5**: Update tests

## Expected Benefits

1. **Single Source of Truth**: Schema files define all validation rules
2. **Consistency**: Validation rules match schema definitions exactly
3. **Maintainability**: Update schemas without changing code
4. **Standardization**: Uses standard JSON Schema format
5. **Better Error Reporting**: jsonschema provides detailed error messages
6. **Less Code**: Removes duplicated validation logic

## Files to Modify

1. `pyproject.toml` - Add jsonschema dependency
2. `schemas/*.schema.json` - Update to array schema structure
3. `prompt_pipeline/validation/json_validator.py` - Refactor to use jsonschema
4. `tests/test_prompt_pipeline/test_json_validator.py` - Update tests

## Note on Current Tests

Some tests currently pass by disabling schema validation (`schema_path=""`), which then relies on custom validation logic. These tests will need to be updated or removed, as the validator should always validate against a schema when one is provided.

## Reference Documents

- Full proposal: `doc/json_validator_refactor_proposal.md`
- Current schemas: `schemas/*.schema.json`
- Current validator: `prompt_pipeline/validation/json_validator.py`
- Current tests: `tests/test_prompt_pipeline/test_json_validator.py`
