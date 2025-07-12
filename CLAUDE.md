# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LLMgine is a pattern-driven framework for building production-grade, tool-augmented LLM applications in Python. It provides a clean separation between engines (conversation logic), models/providers (LLM backends), and tools (function calling), with a streaming message-bus for commands & events.

## Development Commands

### Package Management
This project uses `uv` as the package manager:
```bash
uv pip install -e ".[dev]"     # Install with development dependencies
uv pip install -e ".[openai]"  # Install with OpenAI provider
uv sync                         # Install from uv.lock (recommended)
```

### Testing
```bash
pytest                      # Run all tests
pytest -sv --log-cli-level=0  # Verbose output with logging (default config)
```

### Code Quality
```bash
ruff check src/             # Lint source code
ruff format src/            # Format source code
ruff check --fix src/       # Auto-fix lint issues
mypy                        # Type checking (strict mode enabled)
```

### Convenience Commands
```bash
make help                   # Show all available make commands
make check                  # Run all quality checks (lint, format, typecheck, test)
make clean                  # Clean build artifacts and cache
make demo                   # Show available demo commands
python scripts/dev.py check # Alternative comprehensive check script
./setup-dev.sh             # One-time development environment setup
```

### Pre-commit Hooks
```bash
pre-commit install          # Install git hooks
pre-commit run --all-files  # Run hooks on all files
```

### Running Examples
```bash
python -m llmgine.engines.single_pass_engine  # Pirate translator demo
python -m llmgine.engines.tool_chat_engine    # Tool-enabled chat demo
```


## Architecture Overview

### Message Bus Pattern
All components communicate through a central `MessageBus` using Commands and Events:
- **Commands**: 1 handler per command (strict routing)
- **Events**: N listeners per event (broadcast)
- **Sessions**: Automatic cleanup and isolation

Key files:
- `src/llmgine/bus/bus.py` - Core message bus implementation
- `src/llmgine/messages/` - Command and event definitions

### Engine System
Engines handle conversation logic by processing commands and emitting events:
- Base class: `src/llmgine/llm/engine/base.py`
- Built-in engines: `SinglePassEngine`, `ToolChatEngine`, `VoiceProcessingEngine`
- Custom engines should extend `Engine` and implement command handlers

### Provider Abstraction
LLM providers are abstracted through standardized interfaces:
- `src/llmgine/llm/providers/` - Provider implementations (OpenAI, Anthropic, Gemini)
- `src/llmgine/llm/models/` - Model wrappers
- Environment variables required: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.

### Tool System
Function calling is handled through declarative registration:
- `src/llmgine/llm/tools/` - Tool execution and schema generation
- Tools are registered as async functions with type hints
- Automatic JSON schema generation for different providers

## Key Directories

- `src/llmgine/` - Core library code
- `programs/` - Example applications and tools
- `programs/engines/` - Example engine implementations
- `programs/observability-gui/` - React-based log viewer
- `tests/` - Test suite
- `logs/` - Event logs (gitignored)

## Development Notes

- Python 3.11+ required
- All operations are async by default
- Events are automatically logged for observability
- Session-based handler management with automatic cleanup
- Type safety enforced with Pydantic models and MyPy
- Uses Rich for CLI interfaces and console output

## Configuration

- Package: `pyproject.toml` with hatchling build system
- Testing: pytest with asyncio support
- Linting: Ruff with 90-character line limit
- Type checking: MyPy in strict mode
- Frontend: Vite + TypeScript + React