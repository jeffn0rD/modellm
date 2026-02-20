"""
OpenRouter API client for the prompt pipeline.

This module provides the OpenRouterClient class for making LLM calls
with retry logic, exponential backoff, and model selection based on
configuration.
"""

import os
import time
import asyncio
from typing import Optional, Dict, Any, List
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Load environment variables from .env file if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not installed, continue without it
    pass

# Environment variable for API key
OPENROUTER_API_KEY_ENV = "OPENROUTER_API_KEY"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Default configuration
DEFAULT_MODEL = "minimax/minimax-m2.5"
DEFAULT_MAX_TOKENS = 4000
DEFAULT_TIMEOUT = 120  # seconds

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF_FACTORS = [1, 2, 4]  # seconds


class LLMCallError(Exception):
    """Exception raised for LLM call failures."""
    
    def __init__(self, message: str, retry_count: int = 0, last_status_code: Optional[int] = None):
        super().__init__(message)
        self.retry_count = retry_count
        self.last_status_code = last_status_code


class OpenRouterClient:
    """
    OpenRouter API client for LLM calls.
    
    Provides model selection, retry logic with exponential backoff,
    and partial state saving on failure.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        timeout: int = DEFAULT_TIMEOUT,
        config_path: Optional[str] = None
    ):
        """
        Initialize the OpenRouter client.
        
        Args:
            api_key: OpenRouter API key. If None, reads from OPENROUTER_API_KEY env var.
            default_model: Default model to use for LLM calls.
            max_tokens: Maximum tokens in response.
            timeout: Request timeout in seconds.
            config_path: Optional path to pipeline config for model selection.
        """
        self.api_key = api_key or os.environ.get(OPENROUTER_API_KEY_ENV)
        if not self.api_key:
            raise ValueError(
                f"API key not provided. Set {OPENROUTER_API_KEY_ENV} environment variable "
                "or pass api_key parameter."
            )
        
        self.default_model = default_model
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.config_path = config_path
        
        # Load model levels from config if available
        self.model_levels: Dict[str, Dict[int, str]] = {}
        if config_path:
            self._load_model_levels()
        
        # Create session with retry strategy
        self.session = self._create_session()
    
    def _load_model_levels(self) -> None:
        """Load model level mappings from config file."""
        try:
            import yaml
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            model_levels = config.get('model_levels', {})
            self.model_levels = model_levels
        except Exception:
            # If config loading fails, use empty dict
            pass
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy."""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=0,  # We handle retries ourselves
            backoff_factor=0,
            status_forcelist=None,
            raise_on_status=False
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def get_model_for_step(
        self,
        step_name: str,
        model_level: int = 1
    ) -> str:
        """
        Get model name for step based on level.
        
        Args:
            step_name: Name of the pipeline step.
            model_level: Model level (1=cheapest, 2=balanced, 3=best).
        
        Returns:
            Model name string.
        """
        # Check if we have config for this step
        if step_name in self.model_levels:
            level_key = str(model_level)
            if level_key in self.model_levels[step_name]:
                return self.model_levels[step_name][level_key]
        
        # Fall back to default model
        return self.default_model
    
    def _build_headers(self) -> Dict[str, str]:
        """Build request headers."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/modellm/prompt-pipeline",
            "X-Title": "ModelLM Prompt Pipeline"
        }
    
    def _build_payload(
        self,
        prompt: str,
        model: str,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """Build request payload."""
        return {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": 0.7,
            "top_p": 0.9
        }
    
    def _parse_response(self, response: requests.Response) -> str:
        """Parse response and extract content."""
        try:
            data = response.json()
        except ValueError as e:
            raise LLMCallError(f"Failed to parse response as JSON: {e}")
        
        # Check for errors in response
        if 'error' in data:
            error_msg = data['error'].get('message', str(data['error']))
            raise LLMCallError(f"API error: {error_msg}")
        
        # Extract content from response
        try:
            choices = data.get('choices', [])
            if not choices:
                raise LLMCallError("No choices in response")
            
            message = choices[0].get('message', {})
            content = message.get('content', '')
            
            if not content:
                raise LLMCallError("Empty content in response")
            
            return content
        
        except (KeyError, IndexError) as e:
            raise LLMCallError(f"Failed to parse response structure: {e}")
    
    def call_prompt(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        retry_count: int = 0
    ) -> str:
        """
        Call LLM with prompt and return response.
        
        Implements retry logic with exponential backoff.
        
        Args:
            prompt: The prompt to send to the LLM.
            model: Model to use. If None, uses default_model.
            max_tokens: Maximum tokens in response. If None, uses default.
            retry_count: Current retry attempt (internal use).
        
        Returns:
            LLM response content as string.
        
        Raises:
            LLMCallError: If all retries fail.
        """
        model = model or self.default_model
        max_tokens = max_tokens or self.max_tokens
        
        headers = self._build_headers()
        payload = self._build_payload(prompt, model, max_tokens)
        
        try:
            response = self.session.post(
                OPENROUTER_API_URL,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            # Check for HTTP errors
            if response.status_code != 200:
                # Try to get error details from response
                error_details = ""
                try:
                    error_data = response.json()
                    if 'error' in error_data:
                        error_details = error_data['error'].get('message', str(error_data['error']))
                except ValueError:
                    # If we can't parse JSON, use the raw text
                    error_details = response.text[:200] if response.text else "No error details"
                
                # Check if we should retry
                if retry_count < MAX_RETRIES and response.status_code in [429, 500, 502, 503, 504]:
                    backoff_time = RETRY_BACKOFF_FACTORS[retry_count]
                    time.sleep(backoff_time)
                    return self.call_prompt(prompt, model, max_tokens, retry_count + 1)
                
                raise LLMCallError(
                    f"HTTP error: {response.status_code} - {error_details}",
                    retry_count=retry_count,
                    last_status_code=response.status_code
                )
            
            return self._parse_response(response)
        
        except requests.exceptions.Timeout:
            if retry_count < MAX_RETRIES:
                backoff_time = RETRY_BACKOFF_FACTORS[retry_count]
                time.sleep(backoff_time)
                return self.call_prompt(prompt, model, max_tokens, retry_count + 1)
            raise LLMCallError("Request timeout after all retries")
        
        except requests.exceptions.RequestException as e:
            if retry_count < MAX_RETRIES:
                backoff_time = RETRY_BACKOFF_FACTORS[retry_count]
                time.sleep(backoff_time)
                return self.call_prompt(prompt, model, max_tokens, retry_count + 1)
            raise LLMCallError(f"Request failed: {e}", retry_count=retry_count)
    
    async def call_prompt_async(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        retry_count: int = 0
    ) -> str:
        """
        Async version of call_prompt.
        
        Args:
            prompt: The prompt to send to the LLM.
            model: Model to use. If None, uses default_model.
            max_tokens: Maximum tokens in response. If None, uses default.
            retry_count: Current retry attempt (internal use).
        
        Returns:
            LLM response content as string.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.call_prompt,
            prompt,
            model,
            max_tokens,
            retry_count
        )
    
    def call_prompt_with_state_save(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        state_file: Optional[str] = None
    ) -> str:
        """
        Call LLM with automatic partial state saving on failure.
        
        If the call fails after retries, attempts to save partial state
        to the specified file.
        
        Args:
            prompt: The prompt to send to the LLM.
            model: Model to use. If None, uses default_model.
            max_tokens: Maximum tokens in response. If None, uses default.
            state_file: Optional path to save partial state on failure.
        
        Returns:
            LLM response content as string.
        
        Raises:
            LLMCallError: If all retries fail.
        """
        try:
            return self.call_prompt(prompt, model, max_tokens)
        except LLMCallError as e:
            # Try to save partial state
            if state_file:
                try:
                    import json
                    partial_state = {
                        "error": str(e),
                        "retry_count": e.retry_count,
                        "last_status_code": e.last_status_code,
                        "prompt_length": len(prompt),
                        "model": model or self.default_model
                    }
                    with open(state_file, 'w') as f:
                        json.dump(partial_state, f, indent=2)
                except Exception:
                    pass  # Ignore errors in state saving
            raise
    
    def close(self) -> None:
        """Close the HTTP session."""
        self.session.close()
    
    def __enter__(self) -> 'OpenRouterClient':
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


# Convenience function for simple usage
def create_client(
    api_key: Optional[str] = None,
    default_model: str = DEFAULT_MODEL,
    config_path: Optional[str] = None
) -> OpenRouterClient:
    """
    Create an OpenRouter client with optional config.
    
    Args:
        api_key: OpenRouter API key.
        default_model: Default model to use.
        config_path: Path to pipeline config.
    
    Returns:
        Configured OpenRouterClient instance.
    """
    return OpenRouterClient(
        api_key=api_key,
        default_model=default_model,
        config_path=config_path
    )
