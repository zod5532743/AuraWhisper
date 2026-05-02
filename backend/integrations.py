"""
AI Integration Module for AuraWhisper
Supports both Ollama (offline) and external API providers.
"""
import os
import json
import logging
import requests
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import httpx
from httpx import AsyncClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AIResponse:
    """AI response structure."""
    text: str
    usage: Optional[Dict[str, Any]] = None
    finish_reason: Optional[str] = None
    model: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseAIIntegration:
    """Base class for AI integrations."""

    async def generate(self, prompt: str, **kwargs) -> AIResponse:
        raise NotImplementedError


class OllamaIntegration(BaseAIIntegration):
    """Ollama integration for offline LLM access."""

    def __init__(
        self,
        model: str = 'llama3.2',
        base_url: str = 'http://localhost:11434',
        temperature: float = 0.7,
        max_tokens: int = 2048,
        keep_alive: str = '5m'
    ):
        self.model = model
        self.base_url = base_url.rstrip('/')
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.keep_alive = keep_alive

        logger.info(f"OllamaIntegration initialized [model={model}, url={base_url}]")
        # Verify Ollama is running
        self._check_ollama()

    def _check_ollama(self):
        """Check if Ollama is running."""
        try:
            import requests
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                available_models = [m.get('name', '') for m in data.get('models', [])]
                logger.info(f"Available Ollama models: {available_models}")
                if self.model not in available_models:
                    logger.warning(f"Requested model '{self.model}' not found. Available: {available_models}")
            else:
                logger.info(f"Could not verify Ollama: {response.status_code}")
        except Exception as e:
            logger.warning(f"Could not connect to Ollama: {e}. Continuing without AI capabilities.")
            raise ConnectionError("Ollama is not running or not accessible.")

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> AIResponse:
        """Generate text using Ollama."""
        try:
            # Prepare request payload
            payload = {
                "model": self.model,
                "prompt": prompt,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                    "system": system_prompt,
                    **kwargs.get('options', {})
                }
            }

            # Stream response
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", f"{self.base_url}/api/generate", json=payload) as response:
                    full_text = ""
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                full_text += data.get('response', '')
                            except json.JSONDecodeError:
                                pass

            if full_text:
                logger.info(f"Ollama response (truncated): {full_text[:200]}...")
                return AIResponse(
                    text=full_text,
                    usage={"total_tokens": 0},
                    metadata={"source": "ollama", "model": self.model}
                )
            else:
                logger.warning("Ollama returned empty response.")
                return AIResponse(text="")

        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to Ollama: {e}")
            return AIResponse(
                text=f"Error: Cannot connect to Ollama at {self.base_url}. Please ensure Ollama is running.",
                metadata={"source": "ollama", "error": "connection_failed"}
            )
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            return AIResponse(
                text=f"Error: {str(e)}",
                metadata={"source": "ollama", "error": "generation_failed"}
            )

    def list_models(self) -> List[str]:
        """List available Ollama models."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [m.get('name', '') for m in data.get('models', [])]
            return []
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            return []

    def pull_model(self, model: str) -> bool:
        """Pull a model from Ollama Hub."""
        try:
            response = requests.post(f"{self.base_url}/api/pull", json={"name": model}, timeout=60)
            if response.status_code == 200:
                logger.info(f"Started pulling model: {model}")
                return True
            else:
                logger.error(f"Failed to pull model: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error pulling model: {e}")
            return False


class OpenAIIntegration(BaseAIIntegration):
    """OpenAI API integration (requires API key)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = 'gpt-4o',
        base_url: Optional[str] = None
    ):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = model
        self.base_url = base_url or 'https://api.openai.com/v1'

        if not self.api_key:
            logger.warning("OpenAIIntegration initialized without API key. AI features will not work.")

    async def generate(self, prompt: str, **kwargs) -> AIResponse:
        """Generate text using OpenAI."""
        if not self.api_key:
            return AIResponse(
                text="Error: No API key provided. Configure OPENAI_API_KEY environment variable.",
                metadata={"source": "openai", "error": "no_api_key"}
            )

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        **kwargs
                    }
                )

            if response.status_code == 200:
                data = response.json()
                content = data['choices'][0]['message']['content']
                return AIResponse(
                    text=content,
                    usage={
                        "prompt_tokens": data.get('usage', {}).get('prompt_tokens', 0),
                        "completion_tokens": data.get('usage', {}).get('completion_tokens', 0),
                        "total_tokens": data.get('usage', {}).get('total_tokens', 0)
                    },
                    metadata={"source": "openai", "model": self.model}
                )
            else:
                logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                return AIResponse(
                    text=f"OpenAI API error: {response.status_code}",
                    metadata={"source": "openai", "error": "api_error"}
                )

        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            return AIResponse(text=f"Error: {str(e)}", metadata={"source": "openai", "error": "unknown"})


class LocalFallbackIntegration(BaseAIIntegration):
    """Simple local text generation fallback (for demo/testing)."""

    async def generate(self, prompt: str, **kwargs) -> AIResponse:
        """Simple echo-style response."""
        # This is just a placeholder for testing without AI
        responses = [
            "I'm running in offline mode without AI capabilities.",
            "This is a fallback response. For full functionality, use Ollama locally.",
            "Please ensure Ollama is installed and running for AI features."
        ]
        return AIResponse(
            text=responses[0],
            metadata={"source": "local_fallback"}
        )


# Singleton for easy access
_ai_instance: Optional[BaseAIIntegration] = None


def get_ai_instance() -> Optional[BaseAIIntegration]:
    """Get or create the AI integration instance."""
    global _ai_instance

    if _ai_instance is not None:
        return _ai_instance

    # Try to initialize based on configuration
    try:
        from server import OfflineServer
        server = OfflineServer()
        if server.ai_integration:
            _ai_instance = server.ai_integration
            return _ai_instance
    except Exception as e:
        logger.error(f"Failed to initialize AI instance: {e}")

    # Fallback to local mode
    logger.warning("No AI integration available. Falling back to offline mode.")
    _ai_instance = LocalFallbackIntegration()
    return _ai_instance


async def get_ai() -> BaseAIIntegration:
    """Get the AI integration instance."""
    return get_ai_instance()
