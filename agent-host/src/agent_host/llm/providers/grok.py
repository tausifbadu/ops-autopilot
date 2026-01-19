"""xAI Grok provider implementation."""

import json
from typing import Optional

import httpx

from agent_host.llm.base import LLMProvider, LLMRequest, LLMResponse

# Default models
DEFAULT_MODEL = "grok-beta"  # Default Grok model
PREMIUM_MODEL = "grok-2"  # Latest Grok model


class GrokProvider(LLMProvider):
    """xAI Grok provider."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: str = "https://api.x.ai/v1",
    ):
        """Initialize Grok provider.

        Args:
            api_key: xAI API key
            model: Default model name
            base_url: API base URL
        """
        super().__init__(api_key=api_key, model=model or DEFAULT_MODEL)
        self.base_url = base_url
        self.api_key = api_key or self._get_api_key()

    def _get_api_key(self) -> str:
        """Get API key from environment."""
        import os
        return os.getenv("GROK_API_KEY", "")

    def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate response using Grok API.

        Args:
            request: LLM request

        Returns:
            LLM response
        """
        model = request.model or self.default_model

        # Prepare messages
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        # Prepare request body
        body = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
        }

        if request.max_tokens:
            body["max_tokens"] = request.max_tokens

        # Handle structured output (JSON mode)
        if request.response_format:
            body["response_format"] = {"type": "json_object"}

        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=body,
                )
                response.raise_for_status()
                data = response.json()

            content = data["choices"][0]["message"]["content"] or ""
            
            # Parse structured output
            structured_output = None
            if request.response_format:
                structured_output = self._parse_structured_output(content, request.response_format)

            usage = None
            if "usage" in data:
                usage = {
                    "prompt_tokens": data["usage"].get("prompt_tokens", 0),
                    "completion_tokens": data["usage"].get("completion_tokens", 0),
                    "total_tokens": data["usage"].get("total_tokens", 0),
                }

            return LLMResponse(
                content=content,
                structured_output=structured_output,
                model=model,
                usage=usage,
                finish_reason=data["choices"][0].get("finish_reason"),
            )

        except Exception as e:
            self.logger.error(f"Grok API error: {e}")
            raise


# Model presets
GROK_MODELS = {
    "grok-2": "grok-2",
    "grok-beta": "grok-beta",
}
