# Story 1.8: Standardize LLM Request Contract

## Story
As a developer,
I want a standardized LLMRequest contract across all providers,
so that I can switch providers without changing my application code.

## Context
Currently, each provider (OpenAI, Anthropic, Gemini) has its own request format. While LLMResponse is partially standardized, there's no unified LLMRequest contract, making it difficult to switch providers without code changes.

## Acceptance Criteria
1. Create `LLMRequest` base class in `src/llmgine/messages/`
2. Define common fields: messages, model, temperature, max_tokens, tools
3. Update all provider implementations to accept LLMRequest
4. Maintain backward compatibility with provider-specific requests
5. Create request transformation utilities for each provider
6. Update example programs to use standardized requests

## Integration Verification
- IV1: All existing provider calls continue to work with current interfaces
- IV2: Provider-specific features remain accessible through extensions
- IV3: No performance degradation in request processing

## Technical Details

### LLMRequest Contract Design
```python
@dataclass
class LLMRequest(Command):
    """Standardized LLM request across all providers"""
    messages: List[Message]
    model: str
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    tools: Optional[List[Tool]] = None
    stream: bool = False
    
    # Provider-specific extensions
    provider_options: Optional[Dict[str, Any]] = None
```

### Provider Updates Required
1. `src/llmgine/llm/providers/openai_provider.py`
2. `src/llmgine/llm/providers/anthropic_provider.py`
3. `src/llmgine/llm/providers/gemini_provider.py`
4. `src/llmgine/llm/providers/openrouter_provider.py`

### Backward Compatibility Strategy
- Keep existing provider-specific methods as deprecated
- Add new standardized methods alongside
- Use adapter pattern to transform requests internally
- Log deprecation warnings for old usage

## Testing Requirements
1. Unit tests for request transformation logic
2. Integration tests with each provider
3. Backward compatibility tests
4. Performance comparison tests
5. Test provider-specific extensions