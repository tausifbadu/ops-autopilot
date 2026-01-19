"""Anthropic Claude provider implementation."""

import json
from typing import Optional

import anthropic

from agent_host.llm.base import LLMProvider, LLMRequest, LLMResponse

# Default models
DEFAULT_MODEL = "claude-3-5-sonnet-20241022"  # Cost-effective default
PREMIUM_MODEL = "claude-3-5-opus-20241022"  # For complex RCA


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key
            model: Default model name
        """
        super().__init__(api_key=api_key, model=model or DEFAULT_MODEL)
        
        self.client = anthropic.Anthropic(api_key=api_key or self._get_api_key())

    def _get_api_key(self) -> str:
        """Get API key from environment."""
        import os
        return os.getenv("ANTHROPIC_API_KEY", "")

    def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate response using Anthropic API.

        Args:
            request: LLM request

        Returns:
            LLM response
        """
        model = request.model or self.default_model

        # Build system prompt
        system_prompt = request.system_prompt or ""
        
        # Add JSON schema instruction if structured output requested
        if request.response_format:
            system_prompt += "\n\nIMPORTANT: You must respond with valid JSON only. Do not include any markdown formatting or explanatory text."
            # Add schema description
            schema_str = json.dumps(request.response_format, indent=2)
            system_prompt += f"\n\nResponse must match this JSON schema:\n{schema_str}"

        # Prepare parameters
        params = {
            "model": model,
            "max_tokens": request.max_tokens or 4096,
            "temperature": request.temperature,
            "system": system_prompt,
            "messages": [{"role": "user", "content": request.prompt}],
        }

        try:
            response = self.client.messages.create(**params)

            content = response.content[0].text if response.content else ""
            
            # Parse structured output
            structured_output = None
            if request.response_format:
                structured_output = self._parse_structured_output(content, request.response_format)

            usage = None
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                }

            return LLMResponse(
                content=content,
                structured_output=structured_output,
                model=model,
                usage=usage,
                finish_reason=response.stop_reason,
            )

        except Exception as e:
            self.logger.error(f"Anthropic API error: {e}")
            raise


# Model presets
ANTHROPIC_MODELS = {
    "claude-3-5-opus": "claude-3-5-opus-20241022",
    "claude-3-5-sonnet": "claude-3-5-sonnet-20241022",
    "claude-3-opus": "claude-3-opus-20240229",
    "claude-3-sonnet": "claude-3-sonnet-20240229",
    "claude-3-haiku": "claude-3-haiku-20240307",
}
