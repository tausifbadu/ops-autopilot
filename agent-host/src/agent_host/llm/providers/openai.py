"""OpenAI provider implementation."""

import json
from typing import Optional

import openai
from openai import OpenAI

from agent_host.llm.base import LLMProvider, LLMRequest, LLMResponse

# Default models
DEFAULT_MODEL = "gpt-4o-mini"  # Cost-effective default
PREMIUM_MODEL = "gpt-4o"  # For complex RCA


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            model: Default model name
            base_url: Custom base URL (for OpenAI-compatible APIs)
        """
        super().__init__(api_key=api_key, model=model or DEFAULT_MODEL)
        
        self.client = OpenAI(
            api_key=api_key or self._get_api_key(),
            base_url=base_url,
        )

    def _get_api_key(self) -> str:
        """Get API key from environment."""
        import os
        return os.getenv("OPENAI_API_KEY", "")

    def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate response using OpenAI API.

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

        # Prepare parameters
        params = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
        }

        if request.max_tokens:
            params["max_tokens"] = request.max_tokens

        # Handle structured output (JSON mode)
        if request.response_format:
            # OpenAI supports JSON mode
            params["response_format"] = {"type": "json_object"}

        try:
            response = self.client.chat.completions.create(**params)

            content = response.choices[0].message.content or ""
            
            # Parse structured output
            structured_output = None
            if request.response_format:
                structured_output = self._parse_structured_output(content, request.response_format)

            usage = None
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            return LLMResponse(
                content=content,
                structured_output=structured_output,
                model=model,
                usage=usage,
                finish_reason=response.choices[0].finish_reason,
            )

        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            raise


# Model presets
OPENAI_MODELS = {
    "gpt-4o": "gpt-4o",
    "gpt-4o-mini": "gpt-4o-mini",
    "gpt-4-turbo": "gpt-4-turbo",
    "gpt-4": "gpt-4",
    "gpt-3.5-turbo": "gpt-3.5-turbo",
}
