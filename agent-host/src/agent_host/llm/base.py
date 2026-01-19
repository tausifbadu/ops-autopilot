"""Base LLM provider interface with structured output support."""

import json
from abc import ABC, abstractmethod
from typing import Any, Optional

from pydantic import BaseModel, Field

from agent_host.logging import get_logger

logger = get_logger(__name__)


class LLMRequest(BaseModel):
    """LLM request with structured output schema."""

    prompt: str = Field(..., description="Prompt text")
    system_prompt: Optional[str] = Field(None, description="System prompt")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Temperature")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens")
    response_format: Optional[dict[str, Any]] = Field(
        None, description="Structured output schema (JSON schema)"
    )
    model: Optional[str] = Field(None, description="Model name (provider-specific)")


class LLMResponse(BaseModel):
    """LLM response with structured output."""

    content: str = Field(..., description="Response content")
    structured_output: Optional[dict[str, Any]] = Field(
        None, description="Parsed structured output (JSON)"
    )
    model: str = Field(..., description="Model used")
    usage: Optional[dict[str, int]] = Field(
        None, description="Token usage (prompt_tokens, completion_tokens, total_tokens)"
    )
    finish_reason: Optional[str] = Field(None, description="Finish reason")


class LLMProvider(ABC):
    """Base class for LLM providers."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize LLM provider.

        Args:
            api_key: API key for the provider
            model: Default model name
        """
        self.api_key = api_key
        self.default_model = model
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate response from LLM.

        Args:
            request: LLM request

        Returns:
            LLM response with structured output

        Raises:
            Exception: If generation fails
        """
        pass

    def generate_structured(
        self,
        prompt: str,
        response_schema: dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        model: Optional[str] = None,
    ) -> dict[str, Any]:
        """Generate structured JSON output from LLM.

        This is a convenience method that enforces JSON schema.

        Args:
            prompt: User prompt
            response_schema: JSON schema for response
            system_prompt: Optional system prompt
            temperature: Temperature (0.0-2.0)
            model: Model name (uses default if not provided)

        Returns:
            Parsed structured output as dict

        Raises:
            ValueError: If response doesn't match schema
            Exception: If generation fails
        """
        request = LLMRequest(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            response_format=response_schema,
            model=model or self.default_model,
        )

        response = self.generate(request)

        if response.structured_output:
            return response.structured_output

        # Try to parse JSON from content
        try:
            parsed = json.loads(response.content)
            return parsed
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON from LLM response: {e}")
            self.logger.error(f"Response content: {response.content[:500]}")
            raise ValueError(f"LLM response is not valid JSON: {e}")

    def _parse_structured_output(
        self, content: str, schema: Optional[dict[str, Any]] = None
    ) -> Optional[dict[str, Any]]:
        """Parse structured output from response content.

        Args:
            content: Response content
            schema: Optional JSON schema for validation

        Returns:
            Parsed dict or None if parsing fails
        """
        try:
            # Try to extract JSON from content (may be wrapped in markdown)
            content_clean = content.strip()

            # Remove markdown code blocks if present
            if content_clean.startswith("```json"):
                content_clean = content_clean[7:]
            if content_clean.startswith("```"):
                content_clean = content_clean[3:]
            if content_clean.endswith("```"):
                content_clean = content_clean[:-3]
            content_clean = content_clean.strip()

            parsed = json.loads(content_clean)
            return parsed

        except json.JSONDecodeError:
            self.logger.warning("Failed to parse JSON from response content")
            return None
