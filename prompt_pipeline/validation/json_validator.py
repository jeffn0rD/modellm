"""JSON Validator module for pipeline output validation."""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from prompt_pipeline.validation.yaml_validator import ValidationResult


class JSONValidator:
    """Base JSON validator with optional schema support.

    Provides common JSON validation functionality that can be
    extended by specific validators for different output types.
    """

    def __init__(self, schema_path: Optional[str] = None):
        """Initialize JSON validator.

        Args:
            schema_path: Optional path to JSON schema file.
        """
        self.schema: Optional[Dict[str, Any]] = None
        if schema_path and Path(schema_path).exists():
            with open(schema_path, "r", encoding="utf-8") as f:
                self.schema = json.load(f)

    def validate(self, json_content: str) -> ValidationResult:
        """Validate JSON structure.

        Args:
            json_content: The JSON content to validate.

        Returns:
            ValidationResult with errors and warnings.
        """
        result = ValidationResult()

        # Parse JSON
        try:
            data = json.loads(json_content)
        except json.JSONDecodeError as e:
            result.add_error(f"JSON parse error: {e}")
            return result

        if data is None:
            result.add_error("JSON content is empty")
            return result

        # Validate against schema if available
        if self.schema:
            self._validate_schema(data, result)

        result.passed = result.is_valid()
        return result

    def _validate_schema(self, data: Any, result: ValidationResult) -> None:
        """Validate against JSON schema.

        Args:
            data: Parsed JSON data.
            result: ValidationResult to append errors to.
        """
        # Simple schema validation - can be extended with jsonschema library
        if "type" in self.schema:
            expected_type = self.schema["type"]
            if expected_type == "array" and not isinstance(data, list):
                result.add_error(f"Expected array, got {type(data).__name__}")
            elif expected_type == "object" and not isinstance(data, dict):
                result.add_error(f"Expected object, got {type(data).__name__}")

    def validate_file(self, file_path: str) -> ValidationResult:
        """Validate JSON file.

        Args:
            file_path: Path to JSON file.

        Returns:
            ValidationResult with errors and warnings.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return self.validate(content)
        except FileNotFoundError:
            result = ValidationResult()
            result.add_error(f"File not found: {file_path}")
            return result
        except Exception as e:
            result = ValidationResult()
            result.add_error(f"Error reading file: {e}")
            return result


class ConceptsValidator(JSONValidator):
    """Validate concepts.json output.

    Validates:
    - Valid JSON array format
    - Required fields per concept (type, id, label, description)
    - ID patterns by type (A* for Actor, ACT* for Action, DE* for DataEntity)
    - No duplicate IDs
    - Required properties for each type
    """

    # ID patterns by concept type
    ID_PATTERNS = {
        "Actor": re.compile(r"^A\d+$"),
        "Action": re.compile(r"^ACT\d+$"),
        "DataEntity": re.compile(r"^DE\d+$"),
    }

    # Required fields for all concepts
    REQUIRED_FIELDS = ["type", "id", "label", "description"]

    # Required properties by type
    REQUIRED_PROPERTIES = {
        "Actor": ["role", "permissions"],
        "Action": ["inputs", "outputs"],
        "DataEntity": ["attributes"],
    }

    def __init__(self, schema_path: Optional[str] = None):
        """Initialize concepts validator.

        Args:
            schema_path: Optional path to JSON schema file.
        """
        super().__init__(schema_path)

    def validate(self, json_content: str) -> ValidationResult:
        """Validate concepts JSON.

        Args:
            json_content: The JSON content to validate.

        Returns:
            ValidationResult with errors and warnings.
        """
        result = ValidationResult()

        # Parse JSON
        try:
            data = json.loads(json_content)
        except json.JSONDecodeError as e:
            result.add_error(f"JSON parse error: {e}")
            return result

        # Check it's an array
        if not isinstance(data, list):
            result.add_error("concepts.json must be an array")
            return result

        if len(data) == 0:
            result.add_warning("No concepts defined")

        ids: Set[str] = set()
        for i, concept in enumerate(data):
            self._validate_concept(concept, i, ids, result)

        result.passed = result.is_valid()
        return result

    def _validate_concept(
        self,
        concept: Dict[str, Any],
        index: int,
        ids: Set[str],
        result: ValidationResult,
    ) -> None:
        """Validate a single concept.

        Args:
            concept: Concept dictionary.
            index: Index of concept in array.
            ids: Set of already seen IDs.
            result: ValidationResult to append errors to.
        """
        if not isinstance(concept, dict):
            result.add_error(f"Concept {index} is not a dictionary")
            return

        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in concept:
                result.add_error(f"Concept {index} missing required field: '{field}'")

        # Get type and ID
        concept_type = concept.get("type", "")
        concept_id = concept.get("id", "")

        # Validate ID pattern based on type
        if concept_type and concept_id:
            pattern = self.ID_PATTERNS.get(concept_type)
            if pattern and not pattern.match(concept_id):
                result.add_error(
                    f"Concept {index}: Invalid ID '{concept_id}' for type "
                    f"'{concept_type}'. Expected pattern: {pattern.pattern}"
                )

        # Check for duplicate IDs
        if concept_id in ids:
            result.add_error(f"Concept {index}: Duplicate ID: '{concept_id}'")
        ids.add(concept_id)

        # Validate required properties by type
        if concept_type in self.REQUIRED_PROPERTIES:
            for prop in self.REQUIRED_PROPERTIES[concept_type]:
                if prop not in concept:
                    result.add_error(
                        f"Concept {index} ({concept_type}): "
                        f"missing required property: '{prop}'"
                    )


class AggregationsValidator(JSONValidator):
    """Validate aggregations.json output.

    Validates:
    - Valid JSON array format
    - Required fields per aggregation (id, type, members)
    - ID pattern: AG followed by digits
    - Member references to valid concept IDs
    - No duplicate IDs
    """

    # ID pattern: AG followed by digits
    ID_PATTERN = re.compile(r"^AG\d+$")

    # Required fields
    REQUIRED_FIELDS = ["id", "type", "members"]

    # Valid aggregation types
    VALID_TYPES = ["CompositeActor", "CompositeAction", "CompositeDataEntity"]

    def __init__(self, schema_path: Optional[str] = None):
        """Initialize aggregations validator.

        Args:
            schema_path: Optional path to JSON schema file.
        """
        super().__init__(schema_path)

    def validate(self, json_content: str) -> ValidationResult:
        """Validate aggregations JSON.

        Args:
            json_content: The JSON content to validate.

        Returns:
            ValidationResult with errors and warnings.
        """
        result = ValidationResult()

        # Parse JSON
        try:
            data = json.loads(json_content)
        except json.JSONDecodeError as e:
            result.add_error(f"JSON parse error: {e}")
            return result

        # Check it's an array
        if not isinstance(data, list):
            result.add_error("aggregations.json must be an array")
            return result

        if len(data) == 0:
            result.add_warning("No aggregations defined")

        ids: Set[str] = set()
        known_member_ids: Set[str] = set()

        # First pass: collect all valid IDs
        for agg in data:
            if isinstance(agg, dict):
                member_id = agg.get("id")
                if member_id:
                    known_member_ids.add(member_id)

        # Second pass: validate
        for i, agg in enumerate(data):
            self._validate_aggregation(agg, i, ids, known_member_ids, result)

        result.passed = result.is_valid()
        return result

    def _validate_aggregation(
        self,
        aggregation: Dict[str, Any],
        index: int,
        ids: Set[str],
        known_member_ids: Set[str],
        result: ValidationResult,
    ) -> None:
        """Validate a single aggregation.

        Args:
            aggregation: Aggregation dictionary.
            index: Index of aggregation in array.
            ids: Set of already seen IDs.
            known_member_ids: Set of valid member IDs from all aggregations.
            result: ValidationResult to append errors to.
        """
        if not isinstance(aggregation, dict):
            result.add_error(f"Aggregation {index} is not a dictionary")
            return

        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in aggregation:
                result.add_error(
                    f"Aggregation {index} missing required field: '{field}'"
                )

        agg_id = aggregation.get("id", "")
        agg_type = aggregation.get("type", "")

        # Validate ID pattern
        if agg_id and not self.ID_PATTERN.match(agg_id):
            result.add_error(
                f"Aggregation {index}: Invalid ID '{agg_id}'. "
                f"Expected pattern: {self.ID_PATTERN.pattern}"
            )

        # Check for duplicate IDs
        if agg_id in ids:
            result.add_error(f"Aggregation {index}: Duplicate ID: '{agg_id}'")
        ids.add(agg_id)

        # Validate type
        if agg_type and agg_type not in self.VALID_TYPES:
            result.add_error(
                f"Aggregation {index}: Invalid type '{agg_type}'. "
                f"Valid types: {', '.join(self.VALID_TYPES)}"
            )

        # Validate members
        members = aggregation.get("members", [])
        if not isinstance(members, list):
            result.add_error(f"Aggregation {index}: 'members' must be an array")
        else:
            for j, member in enumerate(members):
                if isinstance(member, str):
                    # Reference by ID
                    if member not in known_member_ids:
                        result.add_warning(
                            f"Aggregation {index}, member {j}: "
                            f"Unknown member ID '{member}'"
                        )
                elif isinstance(member, dict):
                    # Inline member definition
                    if "id" not in member:
                        result.add_error(
                            f"Aggregation {index}, member {j}: "
                            f"missing 'id' field"
                        )


class MessagesValidator(JSONValidator):
    """Validate messages.json output.

    Validates:
    - Valid JSON array format
    - Required fields per message (id, type, producer, consumer, payload)
    - ID pattern: MSG followed by digits
    - Producer/consumer references to Actor IDs
    - Payload structure
    - No duplicate IDs
    """

    # ID pattern: MSG followed by digits
    ID_PATTERN = re.compile(r"^MSG\d+$")

    # Required fields
    REQUIRED_FIELDS = ["id", "type", "producer", "consumer", "payload"]

    # Valid message types
    VALID_TYPES = [
        "Command",
        "Event",
        "Query",
        "Response",
    ]

    def __init__(self, schema_path: Optional[str] = None):
        """Initialize messages validator.

        Args:
            schema_path: Optional path to JSON schema file.
        """
        super().__init__(schema_path)

    def validate(self, json_content: str) -> ValidationResult:
        """Validate messages JSON.

        Args:
            json_content: The JSON content to validate.

        Returns:
            ValidationResult with errors and warnings.
        """
        result = ValidationResult()

        # Parse JSON
        try:
            data = json.loads(json_content)
        except json.JSONDecodeError as e:
            result.add_error(f"JSON parse error: {e}")
            return result

        # Check it's an array
        if not isinstance(data, list):
            result.add_error("messages.json must be an array")
            return result

        if len(data) == 0:
            result.add_warning("No messages defined")

        ids: Set[str] = set()
        actor_ids: Set[str] = set()

        # First pass: collect all actor IDs from concepts if available
        # (would need to be passed in for full validation)

        for i, msg in enumerate(data):
            self._validate_message(msg, i, ids, actor_ids, result)

        result.passed = result.is_valid()
        return result

    def _validate_message(
        self,
        message: Dict[str, Any],
        index: int,
        ids: Set[str],
        actor_ids: Set[str],
        result: ValidationResult,
    ) -> None:
        """Validate a single message.

        Args:
            message: Message dictionary.
            index: Index of message in array.
            ids: Set of already seen IDs.
            actor_ids: Set of known Actor IDs.
            result: ValidationResult to append errors to.
        """
        if not isinstance(message, dict):
            result.add_error(f"Message {index} is not a dictionary")
            return

        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in message:
                result.add_error(f"Message {index} missing required field: '{field}'")

        msg_id = message.get("id", "")
        msg_type = message.get("type", "")

        # Validate ID pattern
        if msg_id and not self.ID_PATTERN.match(msg_id):
            result.add_error(
                f"Message {index}: Invalid ID '{msg_id}'. "
                f"Expected pattern: {self.ID_PATTERN.pattern}"
            )

        # Check for duplicate IDs
        if msg_id in ids:
            result.add_error(f"Message {index}: Duplicate ID: '{msg_id}'")
        ids.add(msg_id)

        # Validate type
        if msg_type and msg_type not in self.VALID_TYPES:
            result.add_error(
                f"Message {index}: Invalid type '{msg_type}'. "
                f"Valid types: {', '.join(self.VALID_TYPES)}"
            )

        # Validate producer/consumer (should be Actor IDs)
        producer = message.get("producer", "")
        consumer = message.get("consumer", "")
        if producer and not re.match(r"^A\d+$", producer):
            result.add_warning(f"Message {index}: Producer '{producer}' may not be valid Actor ID")
        if consumer and not re.match(r"^A\d+$", consumer):
            result.add_warning(f"Message {index}: Consumer '{consumer}' may not be valid Actor ID")

        # Validate payload
        payload = message.get("payload", {})
        if not isinstance(payload, dict):
            result.add_error(f"Message {index}: 'payload' must be an object")


class RequirementsValidator(JSONValidator):
    """Validate requirements.json output.

    Validates:
    - Valid JSON array format
    - Required fields per requirement (id, type, statement)
    - ID pattern: REQ- followed by digits
    - Types: Functional, Non-Functional, Interface, Business
    - Priority levels: Critical, High, Medium, Low
    - No duplicate IDs
    """

    # ID pattern: REQ- followed by digits
    ID_PATTERN = re.compile(r"^REQ-\d+$")

    # Required fields
    REQUIRED_FIELDS = ["id", "type", "statement"]

    # Valid requirement types
    VALID_TYPES = [
        "Functional",
        "Non-Functional",
        "Interface",
        "Business",
    ]

    # Valid priorities
    VALID_PRIORITIES = ["Critical", "High", "Medium", "Low"]

    def __init__(self, schema_path: Optional[str] = None):
        """Initialize requirements validator.

        Args:
            schema_path: Optional path to JSON schema file.
        """
        super().__init__(schema_path)

    def validate(self, json_content: str) -> ValidationResult:
        """Validate requirements JSON.

        Args:
            json_content: The JSON content to validate.

        Returns:
            ValidationResult with errors and warnings.
        """
        result = ValidationResult()

        # Parse JSON
        try:
            data = json.loads(json_content)
        except json.JSONDecodeError as e:
            result.add_error(f"JSON parse error: {e}")
            return result

        # Check it's an array
        if not isinstance(data, list):
            result.add_error("requirements.json must be an array")
            return result

        if len(data) == 0:
            result.add_warning("No requirements defined")

        ids: Set[str] = set()
        for i, req in enumerate(data):
            self._validate_requirement(req, i, ids, result)

        result.passed = result.is_valid()
        return result

    def _validate_requirement(
        self,
        requirement: Dict[str, Any],
        index: int,
        ids: Set[str],
        result: ValidationResult,
    ) -> None:
        """Validate a single requirement.

        Args:
            requirement: Requirement dictionary.
            index: Index of requirement in array.
            ids: Set of already seen IDs.
            result: ValidationResult to append errors to.
        """
        if not isinstance(requirement, dict):
            result.add_error(f"Requirement {index} is not a dictionary")
            return

        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in requirement:
                result.add_error(
                    f"Requirement {index} missing required field: '{field}'"
                )

        req_id = requirement.get("id", "")
        req_type = requirement.get("type", "")
        priority = requirement.get("priority", "")

        # Validate ID pattern
        if req_id and not self.ID_PATTERN.match(req_id):
            result.add_error(
                f"Requirement {index}: Invalid ID '{req_id}'. "
                f"Expected pattern: {self.ID_PATTERN.pattern}"
            )

        # Check for duplicate IDs
        if req_id in ids:
            result.add_error(f"Requirement {index}: Duplicate ID: '{req_id}'")
        ids.add(req_id)

        # Validate type
        if req_type and req_type not in self.VALID_TYPES:
            result.add_error(
                f"Requirement {index}: Invalid type '{req_type}'. "
                f"Valid types: {', '.join(self.VALID_TYPES)}"
            )

        # Validate priority (if present)
        if priority and priority not in self.VALID_PRIORITIES:
            result.add_warning(
                f"Requirement {index}: Invalid priority '{priority}'. "
                f"Valid priorities: {', '.join(self.VALID_PRIORITIES)}"
            )

        # Validate statement is not empty
        statement = requirement.get("statement", "")
        if not statement or not isinstance(statement, str):
            result.add_error(f"Requirement {index}: 'statement' must be a non-empty string")


# Convenience functions
def validate_concepts(
    json_content: str, schema_path: Optional[str] = None
) -> ValidationResult:
    """Validate concepts JSON.

    Args:
        json_content: The JSON content to validate.
        schema_path: Optional path to JSON schema file.

    Returns:
        ValidationResult with errors and warnings.
    """
    validator = ConceptsValidator(schema_path)
    return validator.validate(json_content)


def validate_aggregations(
    json_content: str, schema_path: Optional[str] = None
) -> ValidationResult:
    """Validate aggregations JSON.

    Args:
        json_content: The JSON content to validate.
        schema_path: Optional path to JSON schema file.

    Returns:
        ValidationResult with errors and warnings.
    """
    validator = AggregationsValidator(schema_path)
    return validator.validate(json_content)


def validate_messages(
    json_content: str, schema_path: Optional[str] = None
) -> ValidationResult:
    """Validate messages JSON.

    Args:
        json_content: The JSON content to validate.
        schema_path: Optional path to JSON schema file.

    Returns:
        ValidationResult with errors and warnings.
    """
    validator = MessagesValidator(schema_path)
    return validator.validate(json_content)


def validate_requirements(
    json_content: str, schema_path: Optional[str] = None
) -> ValidationResult:
    """Validate requirements JSON.

    Args:
        json_content: The JSON content to validate.
        schema_path: Optional path to JSON schema file.

    Returns:
        ValidationResult with errors and warnings.
    """
    validator = RequirementsValidator(schema_path)
    return validator.validate(json_content)
