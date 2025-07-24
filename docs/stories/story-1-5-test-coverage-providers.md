# Story 1.4: Comprehensive Test Coverage - Providers and Tools

## Story
As a maintainer,
I want comprehensive test coverage for LLM providers and tools,
so that I can ensure reliable interactions with external services.

## Context
Provider implementations and tool management are critical components that interface with external services. They currently lack comprehensive testing, making it risky to refactor or add new features.

## Acceptance Criteria
1. Create unit tests for all provider implementations
2. Add mock-based tests for provider API calls
3. Test tool registration and execution flows
4. Create integration tests for tool + provider interactions
5. Test error handling for API failures and rate limits
6. Document testing patterns for community contributors

## Integration Verification
- IV1: Tests work with both real and mocked providers
- IV2: No API keys required for basic test execution
- IV3: Provider-specific features are properly tested

## Technical Details

### Provider Test Coverage
1. **OpenAI Provider**
   - Mock OpenAI client responses
   - Test streaming and non-streaming modes
   - Function calling tests
   - Error handling (rate limits, API errors)

2. **Anthropic Provider**
   - Mock Anthropic client responses
   - Tool use testing
   - Message formatting tests
   - Claude-specific features

3. **Gemini Provider**
   - Mock Gemini client responses
   - Multi-modal content tests
   - Safety settings tests

4. **OpenRouter Provider**
   - Route selection tests
   - Provider fallback tests

### Tool System Testing
1. **Tool Registration**
   - Schema generation from functions
   - Type validation tests
   - Async/sync function handling

2. **Tool Execution**
   - Argument parsing tests
   - Result serialization
   - Error handling in tool functions
   - MCP tool integration tests

### Mock Strategy
```python
# Example mock pattern for providers
@pytest.fixture
def mock_openai_client():
    with patch('openai.AsyncOpenAI') as mock:
        mock.return_value.chat.completions.create.return_value = ...
        yield mock

# VCR.py for recording/replaying real API calls
@vcr.use_cassette('openai_completion.yaml')
def test_real_api_call():
    # Test with real API (recorded)
    pass
```

## Testing Requirements
1. Use unittest.mock for provider mocking
2. Consider VCR.py for recording real API interactions
3. Create provider-agnostic test suites
4. Test rate limiting and retry logic
5. Document mock patterns for contributors