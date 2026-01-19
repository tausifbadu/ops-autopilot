"""Google Gemini provider implementation."""

import json
from typing import Optional

import google.generativeai as genai

from agent_host.llm.base import LLMProvider, LLMRequest, LLMResponse

# Default models
DEFAULT_MODEL = "gemini-1.5-flash"  # Cost-effective default
PREMIUM_MODEL = "gemini-1.5-pro"  # For complex RCA


class GeminiProvider(LLMProvider):
    """Google Gemini provider."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize Gemini provider.

        Args:
            api_key: Google API key
            model: Default model name
        """
        super().__init__(api_key=api_key, model=model or DEFAULT_MODEL)
        
        api_key = api_key or self._get_api_key()
        genai.configure(api_key=api_key)

    def _get_api_key(self) -> str:
        """Get API key from environment."""
        import os
        return os.getenv("GEMINI_API_KEY", "")

    def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate response using Gemini API.

        Args:
            request: LLM request

        Returns:
            LLM response
        """
        model = request.model or self.default_model

        # Build prompt with system instruction
        full_prompt = request.prompt
        if request.system_prompt:
            full_prompt = f"{request.system_prompt}\n\n{request.prompt}"

        # Add JSON schema instruction if structured output requested
        if request.response_format:
            schema_str = json.dumps(request.response_format, indent=2)
            full_prompt += f"\n\nIMPORTANT: Respond with valid JSON only. Response must match this schema:\n{schema_str}"

        try:
            # Configure generation config
            generation_config = genai.types.GenerationConfig(
                temperature=request.temperature,
                max_output_tokens=request.max_tokens or 8192,
            )

            # Get model
            gemini_model = genai.GenerativeModel(model)

            # Generate
            response = gemini_model.generate_content(
                full_prompt,
                generation_config=generation_config,
            )

            content = response.text or ""
            
            # Parse structured output
            structured_output = None
            if request.response_format:
                structured_output = self._parse_structured_output(content, request.response_format)

            # Gemini doesn't provide detailed usage in the same way
            usage = {
                "prompt_tokens": len(full_prompt.split()),  # Approximate
                "completion_tokens": len(content.split()),  # Approximate
            }

            return LLMResponse(
                content=content,
                structured_output=structured_output,
                model=model,
                usage=usage,
                finish_reason=None,  # Gemini doesn't provide this
            )

        except Exception as e:
            self.logger.error(f"Gemini API error: {e}")
            raise


# Model presets
GEMINI_MODELS = {
    "gemini-1.5-pro": "gemini-1.5-pro",
    "gemini-1.5-flash": "gemini-1.5-flash",
    "gemini-pro": "gemini-pro",
}
