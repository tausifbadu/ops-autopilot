# LLM Integration Module

Multi-provider LLM integration with structured output support for ops-autopilot.

## Supported Providers

1. **OpenAI** - GPT-4, GPT-4o, GPT-3.5-turbo
2. **Anthropic** - Claude 3.5 Opus, Sonnet, Haiku
3. **Google Gemini** - Gemini 1.5 Pro, Flash
4. **xAI Grok** - Grok-2, Grok-beta
5. **AWS Bedrock** - Claude (via Bedrock), Llama, Titan

## Features

- **Structured Outputs**: JSON schema enforcement for all LLM responses
- **Multi-Provider**: Easy switching between providers
- **Automatic Parsing**: Extracts JSON from markdown-wrapped responses
- **Fallback Support**: Rule-based fallback if LLM fails
- **Cost Optimization**: Use cheaper models for simple tasks, premium for complex RCA

## Usage

### Basic Usage

```python
from agent_host.llm import get_llm_provider

# Get provider (uses config default)
llm = get_llm_provider()

# Generate structured output
result = llm.generate_structured(
    prompt="Analyze this pipeline failure...",
    response_schema={
        "type": "object",
        "properties": {
            "classification": {"type": "string"},
            "confidence": {"type": "number"},
        },
        "required": ["classification", "confidence"],
    }
)

print(result["classification"])
```

### Provider-Specific Usage

```python
from agent_host.llm import LLMFactory

# Use specific provider
llm = LLMFactory.create_provider(
    provider_name="openai",
    model="gpt-4o",
    api_key="sk-..."
)

# Or use different provider
llm = LLMFactory.create_provider(
    provider_name="anthropic",
    model="claude-3-5-sonnet-20241022"
)
```

### In Agents

```python
from agent_host.llm import get_llm_provider

class MyAgent:
    def __init__(self):
        self.llm = get_llm_provider(provider_name="bedrock", model="claude-3-5-sonnet")
    
    def analyze(self, evidence):
        result = self.llm.generate_structured(
            prompt=f"Analyze: {evidence}",
            response_schema=MY_SCHEMA,
        )
        return result
```

## Configuration

### Environment Variables

```bash
# Provider selection
LLM_PROVIDER=openai  # or bedrock, anthropic, gemini, grok

# API keys (provider-specific)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...
GROK_API_KEY=xai-...

# Model selection (optional)
LLM_MODEL=gpt-4o  # Override default model
```

### Default Models

- **OpenAI**: `gpt-4o-mini` (default), `gpt-4o` (premium)
- **Anthropic**: `claude-3-5-sonnet-20241022` (default), `claude-3-5-opus-20241022` (premium)
- **Gemini**: `gemini-1.5-flash` (default), `gemini-1.5-pro` (premium)
- **Grok**: `grok-beta` (default), `grok-2` (premium)
- **Bedrock**: `anthropic.claude-3-5-sonnet-20241022-v2:0` (default)

## Structured Output Schema

All LLM calls enforce JSON schema:

```python
schema = {
    "type": "object",
    "properties": {
        "field1": {"type": "string"},
        "field2": {"type": "number"},
    },
    "required": ["field1", "field2"],
}

result = llm.generate_structured(prompt="...", response_schema=schema)
# result is guaranteed to match schema
```

## Error Handling

- Automatic JSON parsing from markdown code blocks
- Fallback to rule-based classification if LLM fails
- Retry logic (handled by provider implementations)
- Detailed error logging

## Cost Optimization

Use different models for different tasks:

```python
# Simple classification - use cheaper model
llm_cheap = get_llm_provider(provider_name="openai", model="gpt-3.5-turbo")
classification = llm_cheap.generate_structured(...)

# Complex RCA - use premium model
llm_premium = get_llm_provider(provider_name="anthropic", model="claude-3-5-opus")
rca = llm_premium.generate_structured(...)
```

## Architecture

```
Agent
  ↓
LLMProvider (abstract)
  ↓
Concrete Provider (OpenAI/Anthropic/etc.)
  ↓
API Call
  ↓
Structured JSON Response
```

All providers implement the same interface, making it easy to switch providers without code changes.
