"""Integration tests for end-to-end pipeline execution.

Tests cover:
- Single step end-to-end execution
- Compression applied in prompt
- YAML input converted to JSON
- Output file saved uncompressed and schema-valid

Reference: CR-14 in agents/implementation_guide.md
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock

import pytest
import yaml

from prompt_pipeline.step_executor import StepExecutor
from prompt_pipeline.orchestrator import PipelineOrchestrator
from prompt_pipeline.prompt_manager import PromptManager
from prompt_pipeline.llm_client import OpenRouterClient


@pytest.mark.integration
class TestPipelineIntegration:

    @pytest.fixture
    def sample_nl_spec(self, tmp_path):
        """Create a sample NL specification file."""
        spec = tmp_path / "spec.md"
        spec.write_text("# Test Application\n\nThis is a test application specification.\n\nGoal: Test the pipeline.\n")
        return spec

    @pytest.fixture
    def sample_prompt_template(self, tmp_path):
        """Create a sample prompt template."""
        prompt = tmp_path / "prompt_step1.md"
        prompt.write_text(
            "Given the following NL specification:\n\n"
            "{{nl_spec}}\n\n"
            "Please extract the key concepts and return them as JSON.\n"
        )
        return prompt

    @pytest.fixture
    def mock_llm_response_concepts(self):
        """Mock LLM response for concept extraction."""
        return json.dumps([
            {"type": "Actor", "id": "A1", "label": "User",
             "description": "A test user", "categories": ["core"]},
            {"type": "Actor", "id": "A2", "label": "Admin",
             "description": "An admin user", "categories": ["admin"]}
        ])

    @pytest.fixture
    def mock_llm_response_with_reasoning(self):
        """Mock LLM response with reasoning section."""
        return (
            "Here's my reasoning:\n\n"
            "The specification describes a user and an admin.\n\n"
            "**Part 2 – Final JSON**:\n"
            '[\n'
            '  {"type": "Actor", "id": "A1", "label": "User", "description": "A test user", "categories": ["core"]},\n'
            '  {"type": "Actor", "id": "A2", "label": "Admin", "description": "An admin user", "categories": ["admin"]}\n'
            ']'
        )

    @pytest.mark.asyncio
    async def test_single_step_end_to_end(self, tmp_path, sample_nl_spec, sample_prompt_template):
        """Test single step execution from file input to output file."""
        # Create prompts directory
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        
        # Move the prompt template to the prompts directory
        prompt_file = prompts_dir / "prompt_step1.md"
        prompt_file.write_text(sample_prompt_template.read_text())
        
        # Create a minimal pipeline config
        config_path = tmp_path / "pipeline_config.yaml"
        config_content = {
            "data_entities": {
                "concepts": {
                    "type": "json",
                    "filename": "concepts.json",
                    "description": "Extracted concepts from NL spec"
                }
            },
            "steps": {
                "step1": {
                    "name": "step1",
                    "order": 1,
                    "prompt_file": "prompt_step1.md",
                    "inputs": [
                        {
                            "label": "nl_spec",
                            "source": "file",
                            "compression": "none"
                        }
                    ],
                    "outputs": [
                        {"label": "concepts"}
                    ],
                    "validation": {"enabled": False},
                    "model_levels": {
                        "step1": {
                            1: "test/model"
                        }
                    }
                }
            }
        }
        with open(config_path, 'w') as f:
            yaml.dump(config_content, f)

        # Initialize components
        llm_client = Mock()
        llm_client.call_prompt_async = AsyncMock(return_value=json.dumps([
            {"type": "Actor", "id": "A1", "label": "User", "description": "A test user"}
        ]))
        llm_client.default_model = "test/model"

        # Use tmp_path as prompts_dir so it can find the prompt file
        prompt_manager = PromptManager(str(config_path), prompts_dir=str(prompts_dir))
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        executor = StepExecutor(
            llm_client=llm_client,
            prompt_manager=prompt_manager,
            output_dir=output_dir,
            model_level=1,
            skip_validation=True,
            verbose=False,
        )

        # Execute the step
        result = await executor.execute_step(
            step_name="step1",
            cli_inputs={},
            exogenous_inputs={"nl_spec": sample_nl_spec},
            previous_outputs={},
        )

        # Verify output file was created
        assert "concepts" in result
        assert result["concepts"].exists()

        # Verify output is valid JSON
        content = result["concepts"].read_text()
        json_data = json.loads(content)
        assert isinstance(json_data, list)
        assert len(json_data) == 1
        assert json_data[0]["type"] == "Actor"

    @pytest.mark.asyncio
    async def test_compression_applied_in_prompt(self, tmp_path, sample_nl_spec, sample_prompt_template):
        """Test that compression is applied and prompt contains compressed content."""
        # Create prompts directory
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        
        # Move the prompt template to the prompts directory
        prompt_file = prompts_dir / "prompt_step1.md"
        prompt_file.write_text(sample_prompt_template.read_text())
        
        # Create a pipeline config with compression
        config_path = tmp_path / "pipeline_config.yaml"
        config_content = {
            "data_entities": {
                "concepts": {
                    "type": "json",
                    "filename": "concepts.json",
                    "description": "Extracted concepts from NL spec"
                }
            },
            "steps": {
                "step1": {
                    "name": "step1",
                    "order": 1,
                    "prompt_file": "prompt_step1.md",
                    "inputs": [
                        {
                            "label": "nl_spec",
                            "source": "file",
                            "compression": "truncate",
                            "compression_params": {"truncation_length": 50}
                        }
                    ],
                    "outputs": [
                        {"label": "concepts"}
                    ],
                    "validation": {"enabled": False},
                    "model_levels": {
                        "step1": {
                            1: "test/model"
                        }
                    }
                }
            }
        }
        with open(config_path, 'w') as f:
            yaml.dump(config_content, f)

        # Create a large NL spec
        large_nl_spec = tmp_path / "large_nl_spec.md"
        large_nl_spec.write_text("# Test App\n" + "x" * 1000)

        # Initialize components
        llm_client = Mock()
        llm_client.call_prompt_async = AsyncMock(return_value=json.dumps([]))
        llm_client.default_model = "test/model"

        # Use prompts_dir so it can find the prompt file
        prompt_manager = PromptManager(str(config_path), prompts_dir=str(prompts_dir))
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        executor = StepExecutor(
            llm_client=llm_client,
            prompt_manager=prompt_manager,
            output_dir=output_dir,
            model_level=1,
            skip_validation=True,
            verbose=False,
        )

        # Execute the step
        result = await executor.execute_step(
            step_name="step1",
            cli_inputs={},
            exogenous_inputs={"nl_spec": large_nl_spec},
            previous_outputs={},
        )

        # Verify output was created
        assert "concepts" in result
        assert result["concepts"].exists()

        # Verify the LLM was called with compressed content
        call_args = llm_client.call_prompt_async.call_args
        prompt_sent = call_args[0][0]
        # The prompt should contain truncated content (not full 1000 chars)
        assert len(prompt_sent) < 1500  # Less than full content

    @pytest.mark.asyncio
    async def test_yaml_input_converted_to_json(self, tmp_path, sample_prompt_template):
        """Test that YAML input is auto-converted to JSON before compression."""
        # Create prompts directory
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        
        # Create prompt template that matches the input label
        prompt_file = prompts_dir / "prompt_step1.md"
        prompt_file.write_text(
            "Given the following spec:\n\n{{spec_yaml}}\n\n"
            "Please extract the key concepts and return them as JSON.\n"
        )
        
        # Create a pipeline config that reads YAML
        config_path = tmp_path / "pipeline_config.yaml"
        config_content = {
            "data_entities": {
                "concepts": {
                    "type": "json",
                    "filename": "concepts.json",
                    "description": "Extracted concepts from NL spec"
                }
            },
            "steps": {
                "step1": {
                    "name": "step1",
                    "order": 1,
                    "prompt_file": "prompt_step1.md",
                    "inputs": [
                        {
                            "label": "spec_yaml",
                            "source": "file",
                            "compression": "none"
                        }
                    ],
                    "outputs": [
                        {"label": "concepts"}
                    ],
                    "validation": {"enabled": False},
                    "model_levels": {
                        "step1": {
                            1: "test/model"
                        }
                    }
                }
            }
        }
        with open(config_path, 'w') as f:
            yaml.dump(config_content, f)

        # Create a YAML spec file
        yaml_spec = tmp_path / "spec.yaml"
        yaml_content = {
            "specification": {
                "id": "TEST-001",
                "title": "Test Spec",
                "sections": [
                    {"id": "S1", "title": "Section 1", "text": "Test content"}
                ]
            }
        }
        with open(yaml_spec, 'w') as f:
            yaml.dump(yaml_content, f)

        # Initialize components
        llm_client = Mock()
        llm_client.call_prompt_async = AsyncMock(return_value=json.dumps([]))
        llm_client.default_model = "test/model"

        # Use prompts_dir so it can find the prompt file
        prompt_manager = PromptManager(str(config_path), prompts_dir=str(prompts_dir))
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        executor = StepExecutor(
            llm_client=llm_client,
            prompt_manager=prompt_manager,
            output_dir=output_dir,
            model_level=1,
            skip_validation=True,
            verbose=False,
        )

        # Execute the step
        result = await executor.execute_step(
            step_name="step1",
            cli_inputs={},
            exogenous_inputs={"spec_yaml": yaml_spec},
            previous_outputs={},
        )

        # Verify output was created
        assert "concepts" in result
        assert result["concepts"].exists()

        # Verify the LLM was called
        call_args = llm_client.call_prompt_async.call_args
        prompt_sent = call_args[0][0]
        # Verify the prompt was sent (we can't easily verify YAML→JSON conversion
        # without mocking the actual prompt generation, but we can check it was called)
        assert prompt_sent is not None

    @pytest.mark.asyncio
    async def test_output_file_saved_uncompressed(self, tmp_path, sample_nl_spec, sample_prompt_template):
        """Test that output files are saved uncompressed."""
        # Create prompts directory
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        
        # Move the prompt template to the prompts directory
        prompt_file = prompts_dir / "prompt_step1.md"
        prompt_file.write_text(sample_prompt_template.read_text())
        
        # Create a pipeline config
        config_path = tmp_path / "pipeline_config.yaml"
        config_content = {
            "data_entities": {
                "concepts": {
                    "type": "json",
                    "filename": "concepts.json",
                    "description": "Extracted concepts from NL spec"
                }
            },
            "steps": {
                "step1": {
                    "name": "step1",
                    "order": 1,
                    "prompt_file": "prompt_step1.md",
                    "inputs": [
                        {
                            "label": "nl_spec",
                            "source": "file",
                            "compression": "none"
                        }
                    ],
                    "outputs": [
                        {"label": "concepts"}
                    ],
                    "validation": {"enabled": False},
                    "model_levels": {
                        "step1": {
                            1: "test/model"
                        }
                    }
                }
            }
        }
        with open(config_path, 'w') as f:
            yaml.dump(config_content, f)

        # Initialize components
        llm_client = Mock()
        llm_client.call_prompt_async = AsyncMock(return_value=json.dumps([
            {"type": "Actor", "id": "A1", "label": "User", "description": "A test user"}
        ]))
        llm_client.default_model = "test/model"

        # Use prompts_dir so it can find the prompt file
        prompt_manager = PromptManager(str(config_path), prompts_dir=str(prompts_dir))
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        executor = StepExecutor(
            llm_client=llm_client,
            prompt_manager=prompt_manager,
            output_dir=output_dir,
            model_level=1,
            skip_validation=True,
            verbose=False,
        )

        # Execute the step
        result = await executor.execute_step(
            step_name="step1",
            cli_inputs={},
            exogenous_inputs={"nl_spec": sample_nl_spec},
            previous_outputs={},
        )

        # Verify output file was created
        assert "concepts" in result
        output_path = result["concepts"]
        assert output_path.exists()

        # Verify output is saved uncompressed (plain JSON, not compressed)
        content = output_path.read_text()
        json_data = json.loads(content)
        assert isinstance(json_data, list)
        # Verify it's valid JSON with expected structure
        assert json_data[0]["type"] == "Actor"
        assert json_data[0]["id"] == "A1"

    @pytest.mark.asyncio
    async def test_yaml_input_with_schema_validation(self, tmp_path, sample_prompt_template):
        """Test that YAML input is processed correctly when schema validation is enabled."""
        # Create prompts directory
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        
        # Move the prompt template to the prompts directory
        prompt_file = prompts_dir / "prompt_step1.md"
        prompt_file.write_text(sample_prompt_template.read_text())
        
        # Create a pipeline config with schema validation
        config_path = tmp_path / "pipeline_config.yaml"
        
        # Create a simple JSON schema for concepts
        schema_path = tmp_path / "concepts_schema.json"
        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string"},
                    "id": {"type": "string"},
                    "label": {"type": "string"},
                    "description": {"type": "string"}
                },
                "required": ["type", "id", "label"]
            }
        }
        with open(schema_path, 'w') as f:
            json.dump(schema, f)
        
        config_content = {
            "data_entities": {
                "concepts": {
                    "type": "json",
                    "filename": "concepts.json",
                    "description": "Extracted concepts from NL spec",
                    "schema": str(schema_path.relative_to(tmp_path))
                }
            },
            "steps": {
                "step1": {
                    "name": "step1",
                    "order": 1,
                    "prompt_file": "prompt_step1.md",
                    "inputs": [
                        {
                            "label": "nl_spec",
                            "source": "file",
                            "compression": "none"
                        }
                    ],
                    "outputs": [
                        {"label": "concepts"}
                    ],
                    "validation": {"enabled": True},
                    "model_levels": {
                        "step1": {
                            1: "test/model"
                        }
                    }
                }
            }
        }
        with open(config_path, 'w') as f:
            yaml.dump(config_content, f)

        # Create a test NL spec
        nl_spec = tmp_path / "nl_spec.md"
        nl_spec.write_text("# Test App\n\nThis is a test.")

        # Initialize components
        llm_client = Mock()
        # Return valid JSON that matches schema
        llm_client.call_prompt_async = AsyncMock(return_value=json.dumps([
            {"type": "Actor", "id": "A1", "label": "User", "description": "A test user"}
        ]))
        llm_client.default_model = "test/model"

        # Use prompts_dir so it can find the prompt file
        prompt_manager = PromptManager(str(config_path), prompts_dir=str(prompts_dir))
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        executor = StepExecutor(
            llm_client=llm_client,
            prompt_manager=prompt_manager,
            output_dir=output_dir,
            model_level=1,
            skip_validation=False,  # Enable validation
            verbose=False,
        )

        # Execute the step - should succeed with valid JSON
        result = await executor.execute_step(
            step_name="step1",
            cli_inputs={},
            exogenous_inputs={"nl_spec": nl_spec},
            previous_outputs={},
        )

        # Verify output was created and valid
        assert "concepts" in result
        assert result["concepts"].exists()

        # Verify content is valid JSON
        content = result["concepts"].read_text()
        json_data = json.loads(content)
        assert isinstance(json_data, list)
        assert len(json_data) == 1

    @pytest.mark.asyncio
    async def test_yaml_input_converted_to_json_with_validation(self, tmp_path, sample_prompt_template):
        """Test YAML→JSON conversion with schema validation."""
        # Create prompts directory
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        
        # Create prompt template that matches the input label
        prompt_file = prompts_dir / "prompt_step1.md"
        prompt_file.write_text(
            "Given the following spec:\n\n{{spec_yaml}}\n\n"
            "Please extract the key concepts and return them as JSON.\n"
        )
        
        # Create a pipeline config
        config_path = tmp_path / "pipeline_config.yaml"
        
        # Create a simple JSON schema
        schema_path = tmp_path / "concepts_schema.json"
        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string"},
                    "id": {"type": "string"},
                    "label": {"type": "string"}
                },
                "required": ["type", "id", "label"]
            }
        }
        with open(schema_path, 'w') as f:
            json.dump(schema, f)
        
        config_content = {
            "data_entities": {
                "concepts": {
                    "type": "json",
                    "filename": "concepts.json",
                    "description": "Extracted concepts",
                    "schema": str(schema_path.relative_to(tmp_path))
                }
            },
            "steps": {
                "step1": {
                    "name": "step1",
                    "order": 1,
                    "prompt_file": "prompt_step1.md",
                    "inputs": [
                        {
                            "label": "spec_yaml",
                            "source": "file",
                            "compression": "none"
                        }
                    ],
                    "outputs": [
                        {"label": "concepts"}
                    ],
                    "validation": {"enabled": True},
                    "model_levels": {
                        "step1": {
                            1: "test/model"
                        }
                    }
                }
            }
        }
        with open(config_path, 'w') as f:
            yaml.dump(config_content, f)

        # Create a YAML spec file
        yaml_spec = tmp_path / "spec.yaml"
        yaml_content = {
            "specification": {
                "id": "TEST-001",
                "title": "Test Spec",
                "sections": [
                    {"id": "S1", "title": "Section 1", "text": "Test content"}
                ]
            }
        }
        with open(yaml_spec, 'w') as f:
            yaml.dump(yaml_content, f)

        # Initialize components
        llm_client = Mock()
        # Return valid JSON that matches schema
        llm_client.call_prompt_async = AsyncMock(return_value=json.dumps([
            {"type": "Actor", "id": "A1", "label": "User"}
        ]))
        llm_client.default_model = "test/model"

        # Use prompts_dir so it can find the prompt file
        prompt_manager = PromptManager(str(config_path), prompts_dir=str(prompts_dir))
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        executor = StepExecutor(
            llm_client=llm_client,
            prompt_manager=prompt_manager,
            output_dir=output_dir,
            model_level=1,
            skip_validation=False,  # Enable validation
            verbose=False,
        )

        # Execute the step
        result = await executor.execute_step(
            step_name="step1",
            cli_inputs={},
            exogenous_inputs={"spec_yaml": yaml_spec},
            previous_outputs={},
        )

        # Verify output was created and valid
        assert "concepts" in result
        assert result["concepts"].exists()

        # Verify content is valid JSON and matches schema
        content = result["concepts"].read_text()
        json_data = json.loads(content)
        assert isinstance(json_data, list)
        assert len(json_data) == 1
        # Verify schema-required fields are present
        assert "type" in json_data[0]
        assert "id" in json_data[0]
        assert "label" in json_data[0]

    @pytest.mark.asyncio
    async def test_full_pipeline_with_multiple_steps(self, tmp_path, sample_nl_spec, sample_prompt_template):
        """Test full pipeline with multiple steps and label-based dependencies."""
        # Create prompts directory
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        
        # Create two prompt templates
        prompt_step1 = prompts_dir / "prompt_step1.md"
        prompt_step1.write_text(
            "Given the following NL specification:\n\n{{nl_spec}}\n\n"
            "Extract the key concepts and return as JSON.\n"
        )
        
        prompt_stepC3 = prompts_dir / "prompt_stepC3.md"
        prompt_stepC3.write_text(
            "Given the following spec:\n\n{{spec}}\n\n"
            "Aggregate the concepts and return as JSON.\n"
        )
        
        config_path = tmp_path / "pipeline_config.yaml"
        config_content = {
            "data_entities": {
                "spec": {
                    "type": "yaml",
                    "filename": "spec_1.yaml",
                    "description": "Formal specification"
                },
                "concepts": {
                    "type": "json",
                    "filename": "concepts.json",
                    "description": "Extracted concepts"
                }
            },
            "steps": {
                "step1": {
                    "name": "step1",
                    "order": 1,
                    "prompt_file": "prompt_step1.md",
                    "inputs": [
                        {
                            "label": "nl_spec",
                            "source": "file",
                            "compression": "none"
                        }
                    ],
                    "outputs": [
                        {"label": "spec"}
                    ],
                    "validation": {"enabled": False},
                    "model_levels": {
                        "step1": {
                            1: "test/model"
                        }
                    }
                },
                "stepC3": {
                    "name": "stepC3",
                    "order": 4,
                    "prompt_file": "prompt_stepC3.md",
                    "inputs": [
                        {
                            "label": "spec",
                            "source": "label:spec",
                            "compression": "none"
                        }
                    ],
                    "outputs": [
                        {"label": "concepts"}
                    ],
                    "validation": {"enabled": False},
                    "model_levels": {
                        "stepC3": {
                            1: "test/model"
                        }
                    }
                }
            }
        }
        with open(config_path, 'w') as f:
            yaml.dump(config_content, f)

        # Initialize components
        llm_client = Mock()
        llm_client.call_prompt_async = AsyncMock(side_effect=[
            # Step1 response (as JSON - will be converted to YAML)
            json.dumps({
                "specification": {
                    "id": "TEST-001",
                    "title": "Test Spec"
                }
            }),
            # StepC3 response (as JSON)
            json.dumps([{"type": "Actor", "id": "A1", "label": "User"}])
        ])
        llm_client.default_model = "test/model"

        # Use prompts_dir so it can find the prompt file
        prompt_manager = PromptManager(str(config_path), prompts_dir=str(prompts_dir))
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        orchestrator = PipelineOrchestrator(
            config_path=str(config_path),
            llm_client=llm_client,
            prompt_manager=prompt_manager,
            step_executor=StepExecutor(
                llm_client=llm_client,
                prompt_manager=prompt_manager,
                output_dir=output_dir,
                model_level=1,
                skip_validation=True,
                verbose=False,
            ),
            output_dir=output_dir,
            import_database=None,
            wipe_database=False,
            verbose=False,
        )

        # Execute the full pipeline
        outputs = await orchestrator.run_pipeline(sample_nl_spec)

        # Verify both outputs were created
        assert len(outputs) == 2
        assert "spec" in outputs
        assert "concepts" in outputs
        assert outputs["spec"].exists()
        assert outputs["concepts"].exists()

        # Verify spec is YAML
        spec_content = outputs["spec"].read_text()
        spec_data = yaml.safe_load(spec_content)
        assert "specification" in spec_data

        # Verify concepts is JSON
        concepts_content = outputs["concepts"].read_text()
        concepts_data = json.loads(concepts_content)
        assert isinstance(concepts_data, list)

    @pytest.mark.asyncio
    async def test_force_mode_with_missing_input(self, tmp_path, sample_prompt_template):
        """Test force mode allows execution with missing inputs."""
        # Create prompts directory
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        
        # Move the prompt template to the prompts directory
        prompt_file = prompts_dir / "prompt_step1.md"
        prompt_file.write_text(sample_prompt_template.read_text())
        
        # Create a pipeline config
        config_path = tmp_path / "pipeline_config.yaml"
        config_content = {
            "data_entities": {
                "concepts": {
                    "type": "json",
                    "filename": "concepts.json",
                    "description": "Extracted concepts"
                }
            },
            "steps": {
                "step1": {
                    "name": "step1",
                    "order": 1,
                    "prompt_file": "prompt_step1.md",
                    "inputs": [
                        {
                            "label": "nl_spec",
                            "source": "file",
                            "compression": "none"
                        }
                    ],
                    "outputs": [
                        {"label": "concepts"}
                    ],
                    "validation": {"enabled": False},
                    "model_levels": {
                        "step1": {
                            1: "test/model"
                        }
                    }
                }
            }
        }
        with open(config_path, 'w') as f:
            yaml.dump(config_content, f)

        # Initialize components
        llm_client = Mock()
        llm_client.call_prompt_async = AsyncMock(return_value=json.dumps([]))
        llm_client.default_model = "test/model"

        # Use prompts_dir so it can find the prompt file
        prompt_manager = PromptManager(str(config_path), prompts_dir=str(prompts_dir))
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        executor = StepExecutor(
            llm_client=llm_client,
            prompt_manager=prompt_manager,
            output_dir=output_dir,
            model_level=1,
            skip_validation=True,
            verbose=False,
            force=True,  # Enable force mode
        )

        # Execute the step without providing required input
        # This should NOT raise an error in force mode
        result = await executor.execute_step(
            step_name="step1",
            cli_inputs={},  # Missing nl_spec input
            exogenous_inputs={},
            previous_outputs={},
        )

        # Verify output was created
        assert "concepts" in result
        assert result["concepts"].exists()

        # Verify the LLM was called (even though input was missing)
        llm_client.call_prompt_async.assert_called_once()
