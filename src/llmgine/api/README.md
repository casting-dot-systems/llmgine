# LLMGine API Server

This directory contains the FastAPI backend server for the LLMGine system. The API provides a RESTful interface to the LLM engine, replacing the internal message bus communication with HTTP endpoints for frontend integration.

## Architecture Overview

The API server acts as a facade over the existing LLMGine architecture, providing HTTP endpoints for:
- Session management
- Command execution
- Event publishing
- Engine management
- Observability and monitoring

### Key Components

```
src/llmgine/api/
├── main.py                 # FastAPI app initialization and configuration
├── models/                 # Pydantic models for request/response validation
├── routers/               # FastAPI route handlers organized by domain
├── services/              # Business logic layer interfacing with core LLMGine
└── middleware/            # Custom middleware for logging, auth, CORS, etc.
```