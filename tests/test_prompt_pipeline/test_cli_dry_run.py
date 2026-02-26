"""Integration tests for CLI dry-run functionality."""

import subprocess
import pytest
from pathlib import Path


class TestCLIDryRun:
    """Integration tests for prompt-pipeline CLI dry-run options."""
    
    def test_dry_run_prompt_generates_prompt_without_api_calls(self):
        """Test that --dry-run-prompt shows the full prompt without making API calls."""
        result = subprocess.run([
            "python", "-m", "prompt_pipeline_cli.main",
            "run-step",
            "step1",
            "--input-file", "nl_spec:doc/todo_list_nl_spec.md",
            "--dry-run-prompt"
        ], capture_output=True, text=True, cwd=".")
        
        # Should exit successfully
        assert result.returncode == 0, f"Command failed with stderr: {result.stderr}"
        
        # Should show prompt header
        assert "FULL PROMPT" in result.stdout
        
        # Should show step info
        assert "Step: step1" in result.stdout
        assert "Persona: systems_architect" in result.stdout
        assert "Prompt file: prompt_step1_v2.md" in result.stdout
        
        # Should show the actual prompt content
        assert "You are a systems architect" in result.stdout
        assert "Given the inputs:" in result.stdout
        assert "nl_spec:" in result.stdout
        
        # Should NOT show API call messages
        assert "Executing step" not in result.stdout
        assert "Calling LLM" not in result.stdout
        
        # Should NOT have made any network calls (no API error)
        assert "401" not in result.stderr
        assert "400" not in result.stderr
        assert "Connection" not in result.stderr
        
    def test_dry_run_shows_metadata_without_api_calls(self):
        """Test that --dry-run shows metadata without making API calls."""
        result = subprocess.run([
            "python", "-m", "prompt_pipeline_cli.main",
            "run-step",
            "step1",
            "--input-file", "nl_spec:doc/todo_list_nl_spec.md",
            "--dry-run"
        ], capture_output=True, text=True, cwd=".")
        
        # Should exit successfully
        assert result.returncode == 0, f"Command failed with stderr: {result.stderr}"
        
        # Should show dry-run info
        assert "[DRY RUN]" in result.stdout
        assert "Would execute step: step1" in result.stdout
        
        # Should show prompt info
        assert "FULL PROMPT" in result.stdout
        assert "Step: step1" in result.stdout
        
        # Should NOT show API call messages
        assert "Calling LLM" not in result.stdout
        
    def test_dry_run_with_different_step(self):
        """Test that dry-run works with stepC3 (which uses label references)."""
        # First create a mock spec file
        spec_content = """specification:
  id: TEST
  title: "Test Specification"
"""
        
        with open("test_spec.yaml", "w") as f:
            f.write(spec_content)
        
        try:
            result = subprocess.run([
                "python", "-m", "prompt_pipeline_cli.main",
                "run-step",
                "stepC3",
                "--input-file", "spec:test_spec.yaml",
                "--dry-run-prompt"
            ], capture_output=True, text=True, cwd=".")
            
            # Should exit successfully
            assert result.returncode == 0, f"Command failed with stderr: {result.stderr}"
            
            # Should show prompt
            assert "FULL PROMPT" in result.stdout
            assert "Step: stepC3" in result.stdout
            
        finally:
            # Clean up
            if Path("test_spec.yaml").exists():
                Path("test_spec.yaml").unlink()
    
    def test_dry_run_missing_input_shows_error(self):
        """Test that dry-run shows error when required input is missing."""
        result = subprocess.run([
            "python", "-m", "prompt_pipeline_cli.main",
            "run-step",
            "step1"  # Missing --input-file
        ], capture_output=True, text=True, cwd=".")
        
        # Should exit with error
        assert result.returncode != 0
        
        # Should show missing input error (updated message format)
        assert "Missing required CLI inputs" in result.stderr or "Missing required CLI inputs" in result.stdout
    
    def test_dry_run_with_force_flag(self):
        """Test that --dry-run-prompt with --force works without all inputs."""
        result = subprocess.run([
            "python", "-m", "prompt_pipeline_cli.main",
            "run-step",
            "--dry-run-prompt",
            "--force",
            "step1"  # Missing --nl-spec but force mode should substitute empty string
        ], capture_output=True, text=True, cwd=".")
        
        # Should exit successfully with force mode
        assert result.returncode == 0, f"Command failed with stderr: {result.stderr}"
        
        # Should show prompt
        assert "FULL PROMPT" in result.stdout
