# TypeDB Client3 Migration Plan

## Overview

This document outlines the plan to extract the `typedb_client3` library from the modellm project into its own separate repository for independent maintenance and distribution.

## What Was Moved

### New Repository: `typedb_client3`

The following files were moved to the new repository:

**Core Library Files:**
- `typedb_client3/__init__.py` - Package initialization
- `typedb_client3/auth.py` - Authentication with encryption
- `typedb_client3/client.py` - HTTP API client for TypeDB
- `typedb_client3/entities.py` - Entity/Relation dataclasses
- `typedb_client3/entity_manager.py` - High-level entity operations
- `typedb_client3/exceptions.py` - Custom exceptions
- `typedb_client3/query_builder.py` - Generic TypeQL query builder
- `typedb_client3/transactions.py` - Transaction context management
- `typedb_client3/validation.py` - Input validation utilities

**Test Files:**
- `tests/conftest.py` - Pytest fixtures
- `tests/test_auth.py` - Authentication tests
- `tests/test_client_integration.py` - Client integration tests
- `tests/test_database.py` - Database operations tests
- `tests/test_database_integration.py` - Database integration tests
- `tests/test_entities.py` - Entity tests
- `tests/test_entity_manager.py` - Entity manager tests
- `tests/test_queries.py` - Query execution tests
- `tests/test_queries_integration.py` - Query integration tests
- `tests/test_query_builder.py` - Query builder tests
- `tests/test_schema.py` - Schema loading tests
- `tests/test_transaction_type.py` - Transaction type tests
- `tests/test_validation.py` - Validation tests
- `tests/test_wipe.py` - Database wipe tests

### Retained in modellm

The following files were kept in modellm because they are specific to the modellm schema:

**Prompt Pipeline Importer:**
- `prompt_pipeline/importer/importer.py` - TypeDB importer for modellm schema
- `prompt_pipeline/importer/__init__.py` - Package initialization

**Query Patterns:**
- `prompt_pipeline/query_patterns.py` - Pre-built query patterns for modellm schema

**Debug Scripts:**
- `prompt_pipeline/debug_sql_injection.py` - Debug script for SQL injection testing
- `prompt_pipeline/debug_validation.py` - Debug script for validation testing

**CLI Tool:**
- `tools/typedb_import.py` - Unified TypeDB importer CLI tool (modellm-specific)

## Changes to modellm

### Updated Imports

All imports in modellm have been updated to use the external `typedb_client3` package:

**Before:**
```python
from typedb_client3 import TypeDBClient
from typedb_client3.importer import TypeDBImporter
```

**After:**
```python
from typedb_client3 import TypeDBClient
from prompt_pipeline.importer import TypeDBImporter
```

### Updated pyproject.toml

**Before:**
```toml
[project]
dependencies = [
    "requests>=2.25.0",
    "cryptography>=3.4.8",
    "urllib3>=1.26.0",
    "pyyaml>=6.0",
    "click>=8.0.0",
    "jsonschema>=4.17.0"
]

[tool.setuptools]
packages = ["typedb_client3", "prompt_pipeline", "prompt_pipeline_cli"]

[tool.setuptools.package-dir]
typedb_client3 = "tools/typedb_client3"
prompt_pipeline = "prompt_pipeline"
prompt_pipeline_cli = "prompt_pipeline_cli"
```

**After:**
```toml
[project]
dependencies = [
    "typedb-client3>=0.1.0",  # External dependency
    "requests>=2.25.0",
    "cryptography>=3.4.8",
    "urllib3>=1.26.0",
    "pyyaml>=6.0",
    "click>=8.0.0",
    "jsonschema>=4.17.0"
]

[tool.setuptools]
packages = ["prompt_pipeline", "prompt_pipeline_cli"]

[tool.setuptools.package-dir]
prompt_pipeline = "prompt_pipeline"
prompt_pipeline_cli = "prompt_pipeline_cli"
```

## Installation Instructions

### For typedb_client3 Library

1. Clone the new repository:
   ```bash
   git clone <repository-url> typedb_client3
   cd typedb_client3
   ```

2. Install in development mode:
   ```bash
   pip install -e ".[dev]"
   ```

3. Run tests:
   ```bash
   pytest tests/ -v
   ```

### For modellm Project

1. Install modellm with the new dependency:
   ```bash
   pip install -e ".[dev]"
   ```

   This will automatically install `typedb-client3` from PyPI (once published).

2. For development, you can install from the local repository:
   ```bash
   # First, install typedb_client3
   cd /path/to/typedb_client3
   pip install -e .
   
   # Then install modellm
   cd /path/to/modellm
   pip install -e ".[dev]"
   ```

## Dependency Resolution

### typedb_client3 Dependencies

The library requires:
- `requests>=2.25.0`
- `cryptography>=3.4.8`
- `urllib3>=1.26.0`
- `pyyaml>=6.0`

### modellm Dependencies

The project now requires:
- `typedb-client3>=0.1.0` (external)
- `requests>=2.25.0`
- `cryptography>=3.4.8`
- `urllib3>=1.26.0`
- `pyyaml>=6.0`
- `click>=8.0.0`
- `jsonschema>=4.17.0`

## File Structure

### New typedb_client3 Repository Structure (CORRECTED)

```
typedb_client3/                    # Repository root (typedb_client3/)
├── pyproject.toml                 # Package configuration
├── README.md
├── .gitignore
├── __init__.py                    # Package root (typedb_client3 package)
├── auth.py                        # Core library files in root
├── client.py
├── entities.py
├── entity_manager.py
├── exceptions.py
├── query_builder.py
├── transactions.py
├── validation.py
└── tests/                         # Test files
    ├── __init__.py
    ├── conftest.py
    ├── test_auth.py
    ├── test_client_integration.py
    ├── test_database.py
    ├── test_database_integration.py
    ├── test_entities.py
    ├── test_entity_manager.py
    ├── test_queries.py
    ├── test_queries_integration.py
    ├── test_query_builder.py
    ├── test_schema.py
    ├── test_transaction_type.py
    ├── test_validation.py
    └── test_wipe.py
```

**Important Note**: The package files (`__init__.py`, `auth.py`, `client.py`, etc.) are directly in the `typedb_client3/` directory, NOT in a subdirectory. This is the correct Python package structure.

### modellm Updated Structure

```
modellm/
├── pyproject.toml (updated)
├── prompt_pipeline/
│   ├── importer/
│   │   ├── __init__.py
│   │   └── importer.py (refactored to use external typedb_client3)
│   ├── query_patterns.py (refactored to use external typedb_client3)
│   ├── debug_sql_injection.py (refactored to use external typedb_client3)
│   ├── debug_validation.py (refactored to use external typedb_client3)
│   ├── typedb_integration.py (refactored to use external typedb_client3)
│   └── ... (other prompt_pipeline files)
├── tools/
│   ├── typedb_import.py (refactored to use external typedb_client3)
│   └── typedb_client3/ (removed - moved to new repository)
└── tests/
    ├── test_prompt_pipeline/
    │   └── ... (unchanged)
    └── test_*.py (unchanged - still import from typedb_client3)
```

## Testing Strategy

### typedb_client3 Tests

All tests in the new repository should pass:
```bash
cd typedb_client3
pytest tests/ -v
```

### modellm Tests

All tests in modellm should pass with the new dependency:
```bash
cd modellm
pytest tests/ -v
```

### Integration Testing

1. **Unit Tests**: Test individual components
2. **Integration Tests**: Test with TypeDB test server at `http://localhost:8000`
3. **Security Tests**: Test input validation and SQL injection prevention

## Migration Checklist

- [x] Create new repository structure for typedb_client3
- [x] Copy core library files to new repository
- [x] Update typedb_client3 __init__.py (remove importer/query_patterns references)
- [x] Update typedb_client3 pyproject.toml
- [x] Update typedb_client3 README.md
- [x] Copy test files to new repository
- [x] Update modellm pyproject.toml (add typedb-client3 dependency, remove internal reference)
- [x] Update modellm imports in prompt_pipeline files
- [x] Update modellm imports in tools/typedb_import.py
- [x] Create prompt_pipeline/importer package
- [ ] Run tests in typedb_client3 repository
- [ ] Run tests in modellm project
- [ ] Verify all imports work correctly
- [ ] Test TypeDB integration with external dependency
- [ ] Document the migration in project documentation

## Next Steps

1. **Publish typedb_client3 to PyPI** (optional):
   ```bash
   cd typedb_client3
   python -m build
   twine upload dist/*
   ```

2. **Update CI/CD pipelines** for both repositories

3. **Create GitHub releases** for version tracking

4. **Update project documentation** (README, AGENTS.md)

## Common Issues and Solutions

### Issue: Import errors after migration

**Solution**: Ensure `typedb-client3` is installed:
```bash
pip install -e /path/to/typedb_client3
```

### Issue: Version conflicts

**Solution**: Use consistent versioning:
- Update `typedb_client3/pyproject.toml` version
- Update modellm dependency version
- Use version constraints (e.g., `>=0.1.0,<0.2.0`)

### Issue: Test failures

**Solution**: Check that:
1. All imports use the external package
2. The test server is running at `http://localhost:8000`
3. Credentials match (`admin`/`password`)

## Benefits of Separation

1. **Independent maintenance**: The TypeDB client can be developed and maintained separately
2. **Reusability**: Other projects can use the typedb_client3 library
3. **Clear boundaries**: Modellm focuses on prompt pipeline logic, not low-level TypeDB API
4. **Better testing**: Each project has its own test suite
5. **Semantic versioning**: The library can version independently of the main application

## Contact

For questions or issues with the migration, please open an issue in the respective repository.
