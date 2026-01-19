"""AWS Bedrock provider implementation."""

import json
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from agent_host.llm.base import LLMProvider, LLMRequest, LLMResponse

# Default models (Bedrock model IDs)
DEFAULT_MODEL = "anthropic.claude-3-5-sonnet-20241022-v2:0"  # Claude via Bedrock
PREMIUM_MODEL = "anthropic.claude-3-5-opus-20241022-v1:0"  # Claude Opus via Bedrock


class BedrockProvider(LLMProvider):
    """AWS Bedrock provider (supports Claude, Llama, Titan, etc.)."""

    def __init__(
        self,
        region: Optional[str] = None,
        model: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ):
        """Initialize Bedrock provider.

        Args:
            region: AWS region
            model: Default model ID (Bedrock format)
            aws_access_key_id: AWS access key (optional, uses default credentials if not provided)
            aws_secret_access_key: AWS secret key (optional)
        """
        import os
        
        super().__init__(api_key=None, model=model or DEFAULT_MODEL)
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        
        # Initialize Bedrock client
        client_kwargs = {"region_name": self.region}
        if aws_access_key_id and aws_secret_access_key:
            client_kwargs["aws_access_key_id"] = aws_access_key_id
            client_kwargs["aws_secret_access_key"] = aws_secret_access_key
            
        self.client = boto3.client("bedrock-runtime", **client_kwargs)

    def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate response using Bedrock API.

        Args:
            request: LLM request

        Returns:
            LLM response
        """
        model = request.model or self.default_model

        # Determine model provider from model ID
        if model.startswith("anthropic.claude"):
            return self._generate_claude(request, model)
        elif model.startswith("meta.llama"):
            return self._generate_llama(request, model)
        elif model.startswith("amazon.titan"):
            return self._generate_titan(request, model)
        else:
            # Default to Claude format
            return self._generate_claude(request, model)

    def _generate_claude(self, request: LLMRequest, model: str) -> LLMResponse:
        """Generate using Claude model via Bedrock."""
        # Build system prompt
        system_prompt = request.system_prompt or ""
        
        # Add JSON schema instruction if structured output requested
        if request.response_format:
            system_prompt += "\n\nIMPORTANT: You must respond with valid JSON only. Do not include any markdown formatting or explanatory text."
            schema_str = json.dumps(request.response_format, indent=2)
            system_prompt += f"\n\nResponse must match this JSON schema:\n{schema_str}"

        # Prepare request body (Claude format)
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": request.max_tokens or 4096,
            "temperature": request.temperature,
            "system": system_prompt,
            "messages": [{"role": "user", "content": request.prompt}],
        }

        try:
            response = self.client.invoke_model(
                modelId=model,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json",
            )

            response_body = json.loads(response["body"].read())
            content = response_body["content"][0]["text"] if response_body.get("content") else ""
            
            # Parse structured output
            structured_output = None
            if request.response_format:
                structured_output = self._parse_structured_output(content, request.response_format)

            usage = None
            if "usage" in response_body:
                usage = {
                    "prompt_tokens": response_body["usage"].get("input_tokens", 0),
                    "completion_tokens": response_body["usage"].get("output_tokens", 0),
                    "total_tokens": response_body["usage"].get("input_tokens", 0) + response_body["usage"].get("output_tokens", 0),
                }

            return LLMResponse(
                content=content,
                structured_output=structured_output,
                model=model,
                usage=usage,
                finish_reason=response_body.get("stop_reason"),
            )

        except ClientError as e:
            self.logger.error(f"Bedrock API error: {e}")
            raise

    def _generate_llama(self, request: LLMRequest, model: str) -> LLMResponse:
        """Generate using Llama model via Bedrock."""
        # Llama format is different - implement if needed
        # For now, fall back to Claude
        self.logger.warning(f"Llama model {model} not fully implemented, using Claude format")
        return self._generate_claude(request, model)

    def _generate_titan(self, request: LLMRequest, model: str) -> LLMResponse:
        """Generate using Titan model via Bedrock."""
        # Titan format is different - implement if needed
        # For now, fall back to Claude
        self.logger.warning(f"Titan model {model} not fully implemented, using Claude format")
        return self._generate_claude(request, model)


# Model presets (Bedrock model IDs)
BEDROCK_MODELS = {
    "claude-3-5-opus": "anthropic.claude-3-5-opus-20241022-v1:0",
    "claude-3-5-sonnet": "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "claude-3-opus": "anthropic.claude-3-opus-20240229-v1:0",
    "claude-3-sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",
    "claude-3-haiku": "anthropic.claude-3-haiku-20240307-v1:0",
    "llama-3-70b": "meta.llama3-70b-instruct-v1:0",
    "llama-3-8b": "meta.llama3-8b-instruct-v1:0",
}
