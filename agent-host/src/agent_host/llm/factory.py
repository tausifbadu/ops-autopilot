"""LLM factory for creating provider instances."""

from typing import Optional

from agent_host.config import config
from agent_host.logging import get_logger
from agent_host.llm.base import LLMProvider
from agent_host.llm.providers.anthropic import AnthropicProvider
from agent_host.llm.providers.bedrock import BedrockProvider
from agent_host.llm.providers.gemini import GeminiProvider
from agent_host.llm.providers.grok import GrokProvider
from agent_host.llm.providers.openai import OpenAIProvider

logger = get_logger(__name__)


class LLMFactory:
    """Factory for creating LLM provider instances."""

    @staticmethod
    def create_provider(
        provider_name: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> LLMProvider:
        """Create LLM provider instance.

        Args:
            provider_name: Provider name (bedrock, openai, anthropic, gemini, grok)
            model: Model name (optional, uses provider default)
            api_key: API key (optional, uses environment variable)

        Returns:
            LLM provider instance

        Raises:
            ValueError: If provider name is not supported
        """
        provider_name = provider_name or config.llm_provider.lower()

        logger.info(f"Creating LLM provider: {provider_name} (model: {model})")

        if provider_name == "bedrock":
            return BedrockProvider(model=model)
        elif provider_name == "openai":
            api_key = api_key or config.llm_api_key
            return OpenAIProvider(api_key=api_key, model=model)
        elif provider_name == "anthropic":
            api_key = api_key or config.llm_api_key
            return AnthropicProvider(api_key=api_key, model=model)
        elif provider_name == "gemini":
            api_key = api_key or config.llm_api_key
            return GeminiProvider(api_key=api_key, model=model)
        elif provider_name == "grok":
            api_key = api_key or config.llm_api_key
            return GrokProvider(api_key=api_key, model=model)
        else:
            raise ValueError(
                f"Unsupported LLM provider: {provider_name}. "
                f"Supported: bedrock, openai, anthropic, gemini, grok"
            )


def get_llm_provider(
    provider_name: Optional[str] = None,
    model: Optional[str] = None,
) -> LLMProvider:
    """Get LLM provider instance (convenience function).

    Args:
        provider_name: Provider name (optional, uses config default)
        model: Model name (optional)

    Returns:
        LLM provider instance
    """
    return LLMFactory.create_provider(provider_name=provider_name, model=model)
