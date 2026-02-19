# JSON Validator Refactor Proposal

## Summary

The `json_validator.py` module needs to be refactored to use the `jsonschema` library for proper JSON schema validation. Currently, it implements custom validation logic that only partially validates against the schemas defined in `schemas/`.

## Current Issues

1. **No jsonschema library usage**: The validators implement custom validation logic instead of using the `jsonschema` library for schema validation.

2. **Incomplete schema validation**: The `_validate_schema` method only checks basic type validation and ignores all schema constraints like:
   - `required` fields
   - `properties` definitions
   - `pattern` regex constraints
   - `enum` values
   - `additionalProperties` constraints
   - Nested object/array validations

3. **Logic inconsistency**: Validators check if `self.schema` exists to decide whether to perform custom validations. This is backwards - when a schema is provided, the schema should be the source of truth.

4. **Code duplication**: Regex patterns and field requirements are hardcoded in validators but should be derived from schemas.

5. **Schema-file mismatch**: There are multiple schema definition issues:
   
   a. **Array vs Object type mismatch**: The schemas define single objects (e.g., `{"type": "object", ...}`) but the JSON files contain arrays of these objects. For example:
      - `concepts.json` is an array: `[{...}, {...}]`
      - `concepts.schema.json` defines a single object: `{"type": "object", ...}`
      - This means schema validation will fail for the array structure itself
   
   b. **Validator schemas don't match actual schemas**: The current validators check `self.schema` to decide whether to run custom validations, but when a schema is provided, the custom validations should be disabled and the schema should be the source of truth.
   
   c. **Enum value mismatches**: 
      - `MessagesValidator` uses types: `Command`, `Event`, `Query`, `Response`
      - Schema uses categories: `request`, `command`, `response`, `event`
   
   d. **Type value mismatches**:
      - `RequirementsValidator` uses: `Functional`, `Non-Functional`, `Interface`, `Business`
      - Schema uses: `functional`, `nonfunctional`, `ui`, `future-functional`, `excluded`
   
   e. **Missing schema fields in validator checks**:
      - `AggregationsValidator` requires `type` field
      - Schema requires `label`, `description`, `justification` (not checked by validator)
      - Schema has `category` field (not in validator)
   
   f. **Schema field requirements differ**:
      - Validator checks for `role` and `permissions` in Actor
      - Schema doesn't require these (no `required` field in schema for Actor-specific props)

## Proposed Solution

### 1. Add jsonschema Dependency

Add `jsonschema` to project dependencies in `pyproject.toml`:
```toml
dependencies = [
    "jsonschema>=4.17.0",
    ...
]
```

### 2. Refactor JSONValidator Base Class

The base class should:
- Use `jsonschema.validate()` or `jsonschema.Draft7Validator` for schema validation
- Only perform schema validation when a schema is provided
- Return all validation errors from the schema validator
- Remove all custom validation logic that duplicates schema definitions

### 3. Simplify Subclass Validators

The specific validators (ConceptsValidator, AggregationsValidator, etc.) should:
- Still support schema-based validation via the base class
- Remove hardcoded ID patterns (already in schemas)
- Remove hardcoded required fields (already in schemas)
- Remove hardcoded enum values (already in schemas)
- Keep only post-schema validation logic that can't be expressed in JSON Schema

### 4. Post-Schema Validation (What Remains)

Some validation may not be expressible in JSON Schema and should remain in validators:
- **Duplicate ID detection**: Cross-file duplicate checking (though you mentioned this is out of scope)
- **Complex cross-field dependencies**: If any exist (though schemas should handle most)
- **Type-specific logic**: Some type-specific validations may need custom code

However, for this proposal, we should aim to move **everything** possible to schema validation.

### 5. Architecture Changes

#### Current Architecture (Problematic)

**Schemas (*.schema.json):**
- Define single objects: `{"type": "object", ...}`
- Do not validate array structure
- Used inconsistently by validators

**JSON Files (e.g., concepts.json):**
- Contains array of objects: `[{...}, {...}]`
- Schema can't validate this structure

**JSONValidator (Base):**
- `_validate_schema()`: Only checks basic type (array vs object)
- Does not use jsonschema library
- Schema validation is minimal

**Subclass Validators (ConceptsValidator, etc.):**
- Hardcoded ID patterns: `re.compile(r"^A\d+$")`
- Hardcoded required fields: `["type", "id", "label", "description"]`
- Hardcoded enum values: `["Actor", "Action", "DataEntity"]`
- Custom validation logic in `_validate_concept()`, etc.
- Conditionally runs schema validation (backwards logic)
- Many fields in schema not validated by code

**Result:**
- Schema is NOT the source of truth
- Code and schema can diverge
- Incomplete validation
- Schema file structure doesn't match JSON file structure

#### Proposed Architecture (Fixed)

**Schemas (*.schema.json) - UPDATED:**
- Define array structure: `{"type": "array", "items": {...}}`
- Validates array of objects
- ALL constraints defined here:
  - Required fields
  - ID patterns (regex)
  - Enum values
  - Property types
  - AdditionalProperties restrictions

**JSON Files (e.g., concepts.json):**
- Contains array of objects: `[{...}, {...}]`
- Schema validates this structure ✓

**JSONValidator (Base):**
- `_validate_schema()`: Uses jsonschema library
- Validates data against schema
- Converts jsonschema errors to ValidationResult
- Schema validation is comprehensive

**Subclass Validators (ConceptsValidator, etc.):**
- MINIMAL custom logic
- Only for things not expressible in JSON Schema
- Or for structural checks before schema validation

**Result:**
- Schema IS the source of truth
- Code and schema always in sync
- Complete validation
- Schema file structure matches JSON file structure
- Less code to maintain

### 6. API Changes

The public API should remain unchanged:
- `validator.validate(json_content)` returns `ValidationResult`
- `validator.validate_file(file_path)` returns `ValidationResult`
- Convenience functions remain available

### 7. Error Reporting

Schema validation errors should be converted to `ValidationResult` format:
- `jsonschema.exceptions.ValidationError` → `ValidationResult.errors`
- Preserve error messages for user readability
- Maintain backward compatibility with error message format

## Implementation Plan

### Step 1: Add jsonschema Dependency

**File**: `pyproject.toml`
**Changes**: Add `jsonschema>=4.17.0` to dependencies

### Step 2: Fix Schema File Structure (Critical)

**Files**: `schemas/*.schema.json`

**Issue**: All schemas define single objects (type: "object") but JSON files contain arrays of objects. Schema validation will fail because:
- `concepts.json` is: `[{...}, {...}]` (array)
- `concepts.schema.json` expects: `{...}` (object)

**Solution Options**:
- **Option A**: Wrap schema in array type
  ```json
  {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "array",
    "items": {
      "type": "object",
      "required": [...],
      "properties": {...}
    }
  }
  ```
- **Option B**: Create wrapper schemas that use `items`
- **Option C**: Use schema with `oneOf` to handle both array and object (not recommended)

**Recommendation**: Option A - Update all schemas to be array schemas with `items` pointing to the current object definition.

### Step 3: Refactor JSONValidator Base Class

**File**: `prompt_pipeline/validation/json_validator.py`

**Changes**:
1. Remove all custom validation logic from `_validate_schema()`
2. Implement proper schema validation using `jsonschema`
3. Convert schema validation errors to `ValidationResult`
4. Remove conditional logic based on `self.schema` existence
5. Handle the array structure validation (if schemas are updated to array type)

**Example implementation**:
```python
import jsonschema

def _validate_schema(self, data: Any, result: ValidationResult) -> None:
    """Validate against JSON schema using jsonschema library."""
    if not self.schema:
        return
    
    try:
        jsonschema.validate(instance=data, schema=self.schema)
    except jsonschema.exceptions.ValidationError as e:
        result.add_error(f"Schema validation failed: {e.message}")
        # Optionally include path for more context
        if e.absolute_path:
            result.add_error(f"  at path: {'.'.join(str(p) for p in e.absolute_path)}")
```

### Step 4: Simplify Subclass Validators

**File**: `prompt_pipeline/validation/json_validator.py`

**Changes**:
1. Remove all hardcoded ID patterns (they're in the schemas)
2. Remove all hardcoded required fields (they're in the schemas)
3. Remove all hardcoded enum validations (they're in the schemas)
4. Remove all hardcoded type-specific property validations
5. Remove the `_validate_concept`, `_validate_aggregation`, etc. methods entirely

**Keep only**:
- JSON parsing and basic structure checks
- Empty content validation
- Basic array structure validation

**Rationale**: When a schema is provided, it becomes the single source of truth. If the schema doesn't require a field, the validator shouldn't require it either.

**Important Note on Duplicate ID Detection**:
You mentioned "ID reference checks is beyond scope here because we are not validating all the files together" and "Invalid ID's *should* cause an error when importing to typedb". This is correct and aligns with the schema-as-source-of-truth approach:
- The schemas don't define uniqueness constraints (which can't be expressed in JSON Schema for cross-file validation)
- Duplicate ID detection is a business logic constraint, not a schema constraint
- This should remain out of scope (handled by TypeDB import)
- Validators should NOT check for duplicate IDs within a file either (though the current schemas don't enforce this either)

If you later want to add duplicate ID detection within a single file, it would need to be a separate validation step, not part of schema validation.

### Step 5: Update Tests

**File**: `tests/test_prompt_pipeline/test_json_validator.py`

**Changes**:
1. Update tests to verify schema validation works correctly
2. Ensure tests use schemas for validation
3. Add tests for schema validation errors
4. Remove tests that rely on custom validation when schema is disabled
5. Update tests to match the new array-based schema structure
6. Test all schema types: concepts, aggregations, messages, requirements

**Note**: Tests that relied on passing validation WITHOUT a schema (e.g., `schema_path=""`) will need to be updated or removed, as the base validator should require a schema for proper validation.

## Key Considerations

### Scope Boundaries (As Requested)

**IN SCOPE** (This fix):
- Schema validation using jsonschema library
- Schema is the source of truth
- Validation errors from schema constraints
- Proper error reporting

**OUT OF SCOPE** (Not addressed):
- ID reference validation across files
- Cross-file consistency checking
- TypeDB import validation
- Advanced features beyond basic schema validation

### Schema as Source of Truth

When a schema is provided:
1. All validation comes from the schema
2. No additional constraints are applied
3. The schema defines:
   - Required fields
   - Field types
   - ID patterns
   - Enum values
   - Array constraints
   - Object structure

When no schema is provided:
1. The validator should return an error or warning
2. Or use minimal structural validation only

### Backward Compatibility

The public API should remain unchanged:
- Validator classes remain the same
- Method signatures remain the same
- Return type (`ValidationResult`) remains the same

## Testing Strategy

### Unit Tests
- Test schema loading
- Test schema validation success
- Test schema validation failure
- Test error message format
- Test with each schema file

### Integration Tests
- Test with actual output files
- Verify schema files are valid JSON Schema
- Test with malformed JSON
- Test with valid JSON but invalid schema

### Schema Validation Tests
- Test `required` field validation
- Test `pattern` validation
- Test `enum` validation
- Test `additionalProperties` validation
- Test nested object/array validation

## Expected Benefits

1. **Single Source of Truth**: Schema files define all validation rules
2. **Consistency**: Validation rules match schema definitions exactly
3. **Maintainability**: Easier to update validation rules (just update schema)
4. **Standardization**: Uses standard JSON Schema format
5. **Error Reporting**: jsonschema provides detailed error messages
6. **Flexibility**: Schemas can be changed without code changes
7. **Less Code**: Removes duplicated validation logic

## Example Schema Validation

Before (custom validation):
```python
# Requires manual update if schema changes
ID_PATTERNS = {"Actor": re.compile(r"^A\d+$")}
REQUIRED_FIELDS = ["type", "id", "label", "description"]
```

After (schema-based validation):
```python
# Validation comes from schema file
# Schema: {"required": ["type", "id", "label", "description"], 
#          "properties": {"id": {"pattern": "^A\d+$"}}}
```

## Success Criteria

1. ✅ All existing tests pass
2. ✅ Schema validation works for all schema types
3. ✅ Schema files are the only source of validation rules
4. ✅ No custom validation logic in validator classes (except base class using jsonschema)
5. ✅ Error messages are clear and informative
6. ✅ Public API unchanged
7. ✅ No cross-file ID validation (as requested)

## Recommendation

### Immediate Action Required

The current state of the code has a **critical mismatch** between the schemas and the validation logic:

1. **Schema definition**: Each `*.schema.json` file defines a single object (e.g., `{"type": "object", ...}`)
2. **JSON file format**: Each `*.json` file contains an array of objects (e.g., `[{...}, {...}]`)
3. **Schema validation**: Will fail on array structure because schema expects object, not array

### Suggested Path Forward

**Option A: Fix the Schemas (Recommended)**
- Update all schema files to wrap the object definition in an array
- This is the cleanest solution and makes schemas the true source of truth
- Requires minimal code changes in validators (just remove custom logic)

**Option B: Create Array Wrappers**
- Create wrapper schemas that define the array structure
- Keep existing schemas as item definitions
- More complex but preserves existing schema files

**Option C: Keep Current Architecture (Not Recommended)**
- Keep schemas as object definitions
- Keep custom validation that checks array structure separately
- Does not achieve the goal of "schema as source of truth"

### Which Option to Choose?

**Choose Option A** because:
1. It's what the JSON files actually contain (arrays)
2. It makes schemas the true source of truth
3. It's the standard approach for JSON Schema (array with items)
4. It simplifies the validator code significantly
5. It aligns with your request for "schema is the source of truth"

### Implementation Priority

1. **High Priority**: Fix `concepts.schema.json` to be an array schema
2. **High Priority**: Update `json_validator.py` to use jsonschema library
3. **Medium Priority**: Fix remaining schema files (aggregations, messages, requirements)
4. **Low Priority**: Simplify validator classes after schemas are fixed
5. **Low Priority**: Update tests to match new architecture
