# Schema Transformation Example

## Current Schema (Object Definition)

**File**: `schemas/concepts.schema.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["type", "id", "label", "description"],
  "properties": {
    "type": {
      "type": "string",
      "enum": ["Actor", "Action", "DataEntity"]
    },
    "id": {
      "type": "string",
      "pattern": "^(A|ACT|DE)\\d+$"
    },
    ...
  },
  "additionalProperties": false
}
```

## Problem

**File**: `json/concepts.json`

```json
[
  {
    "type": "Actor",
    "id": "A1",
    "label": "EndUser",
    "description": "A single person...",
    ...
  },
  {
    "type": "Actor",
    "id": "A2",
    "label": "TodoApplication",
    "description": "The local browser...",
    ...
  }
]
```

The JSON file is an **array** of objects, but the schema expects a **single object**.

## Fixed Schema (Array Definition)

**File**: `schemas/concepts.schema.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["type", "id", "label", "description"],
    "properties": {
      "type": {
        "type": "string",
        "enum": ["Actor", "Action", "DataEntity"]
      },
      "id": {
        "type": "string",
        "pattern": "^(A|ACT|DE)\\d+$"
      },
      "label": {
        "type": "string",
        "minLength": 1
      },
      "categories": {
        "type": "array",
        "items": {
          "type": "string"
        },
        "default": []
      },
      "description": {
        "type": "string",
        "minLength": 1
      },
      "justification": {
        "type": "string",
        "minLength": 1
      },
      "anchors": {
        "type": "array",
        "items": {
          "type": "string",
          "pattern": "^AN\\d+$"
        },
        "default": []
      },
      "sourceConceptIds": {
        "type": "array",
        "items": {
          "type": "string"
        },
        "default": []
      }
    },
    "additionalProperties": false
  }
}
```

## Transformation Pattern

For all schema files, apply this transformation:

```json
// BEFORE
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": [...],
  "properties": {...},
  "additionalProperties": false
}

// AFTER
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "array",
  "items": {
    "type": "object",
    "required": [...],
    "properties": {...},
    "additionalProperties": false
  }
}
```

## Files to Transform

1. `schemas/concepts.schema.json`
2. `schemas/aggregations.schema.json`
3. `schemas/messages.schema.json`
4. `schemas/requirements.schema.json`
5. `schemas/messageAggregations.schema.json`

## Validation Logic Changes

### Before (Current - Incorrect)

```python
def validate(self, json_content: str) -> ValidationResult:
    result = ValidationResult()
    
    try:
        data = json.loads(json_content)
    except json.JSONDecodeError as e:
        result.add_error(f"JSON parse error: {e}")
        return result
    
    if data is None:
        result.add_error("JSON content is empty")
        return result
    
    # Basic type check only
    if self.schema:
        self._validate_schema(data, result)
    
    # Then custom validation
    self._validate_concepts(data, result)
    
    result.passed = result.is_valid()
    return result

def _validate_schema(self, data: Any, result: ValidationResult) -> None:
    # Only checks if it's an array
    if "type" in self.schema:
        expected_type = self.schema["type"]
        if expected_type == "array" and not isinstance(data, list):
            result.add_error(f"Expected array, got {type(data).__name__}")
        elif expected_type == "object" and not isinstance(data, dict):
            result.add_error(f"Expected object, got {type(data).__name__}")
```

### After (Proposed - Correct)

```python
import jsonschema

def validate(self, json_content: str) -> ValidationResult:
    result = ValidationResult()
    
    try:
        data = json.loads(json_content)
    except json.JSONDecodeError as e:
        result.add_error(f"JSON parse error: {e}")
        return result
    
    if data is None:
        result.add_error("JSON content is empty")
        return result
    
    # Validate against schema (which now includes array structure)
    if self.schema:
        self._validate_schema(data, result)
    
    result.passed = result.is_valid()
    return result

def _validate_schema(self, data: Any, result: ValidationResult) -> None:
    """Validate against JSON schema using jsonschema library."""
    if not self.schema:
        return
    
    try:
        jsonschema.validate(instance=data, schema=self.schema)
    except jsonschema.exceptions.ValidationError as e:
        result.add_error(f"Schema validation failed: {e.message}")
        if e.absolute_path:
            path = '.'.join(str(p) for p in e.absolute_path)
            result.add_error(f"  at path: {path}")
```

## Benefits of This Approach

1. **Schema is single source of truth**: All validation rules defined in schema
2. **Array structure validated**: Schema validates the array wrapper
3. **All constraints validated**: Required fields, patterns, enums, nested objects
4. **No code duplication**: No need to maintain validation logic in Python
5. **Easier to modify**: Update schema file, no code changes needed
6. **Standard JSON Schema**: Uses standard JSON Schema Draft 7 format

## Testing the Schema

### Valid JSON (Should Pass)

```json
[
  {
    "type": "Actor",
    "id": "A1",
    "label": "User",
    "description": "A user"
  }
]
```

### Invalid JSON (Should Fail - Missing Required Field)

```json
[
  {
    "type": "Actor",
    "id": "A1",
    "label": "User"
    // Missing "description" (required)
  }
]
```

### Invalid JSON (Should Fail - Invalid ID Pattern)

```json
[
  {
    "type": "Actor",
    "id": "InvalidID",
    "label": "User",
    "description": "A user"
    // ID doesn't match ^A\d+$ pattern
  }
]
```

### Invalid JSON (Should Fail - Invalid Type)

```json
[
  {
    "type": "InvalidType",
    "id": "A1",
    "label": "User",
    "description": "A user"
    // Type not in enum: ["Actor", "Action", "DataEntity"]
  }
]
```
