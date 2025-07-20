# LLMgine API Documentation

## Overview

The LLMgine API is a FastAPI-based REST and WebSocket API for managing LLM engine sessions and real-time communication. It provides a solid foundation that can be extended with custom functionality.

## Architecture

### Core Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   REST API      │    │   WebSocket     │    │   Extensions    │
│   (Sessions)    │    │   (Real-time)   │    │   (Custom)      │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ • Create        │    │ • Message       │    │ • Custom        │
│ • List          │    │   Handling      │    │   Messages      │
│ • Get Status    │    │ • Engine Ops    │    │ • Custom        │
│ • Delete        │    │ • Events        │    │   Handlers      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Core Services │
                    │                 │
                    │ • SessionService│
                    │ • EngineService │
                    │ • Extensibility │
                    └─────────────────┘
```

### Service Layer

- **SessionService**: Manages session lifecycle, status, and cleanup
- **EngineService**: Manages LLM engines, registration, and monitoring
- **ExtensibilityFramework**: Enables custom message types and handlers

## REST API Endpoints

### Health Checks

#### `GET /health`
Basic health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "llmgine-api",
  "timestamp": "2024-01-01T12:00:00.000Z",
  "uptime": 1704110400.0
}
```

#### `GET /health/ready`
Readiness check for Kubernetes deployments.

**Response:**
```json
{
  "status": "ready",
  "timestamp": "2024-01-01T12:00:00.000Z",
  "services": {
    "sessions": {
      "initialized": true,
      "monitor_running": true,
      "count": 5
    },
    "engines": {
      "initialized": true,
      "monitor_running": true,
      "count": 3
    }
  }
}
```

#### `GET /health/live`
Liveness check for Kubernetes deployments.

**Response:**
```json
{
  "status": "alive",
  "timestamp": "2024-01-01T12:00:00.000Z",
  "pid": null
}
```

### Session Management

#### `POST /api/sessions`
Create a new session.

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "success"
}
```

#### `GET /api/sessions`
List all active sessions.

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "running",
      "created_at": "2024-01-01T12:00:00.000Z",
      "last_interaction_at": "2024-01-01T12:05:00.000Z"
    }
  ],
  "total": 1
}
```

#### `GET /api/sessions/{session_id}`
Get session details.

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "created_at": "2024-01-01T12:00:00.000Z",
  "last_interaction_at": "2024-01-01T12:05:00.000Z",
  "linked_engine": "engine_123"
}
```

#### `DELETE /api/sessions/{session_id}`
Delete a session.

**Response:**
```json
{
  "message": "Session deleted successfully"
}
```

## WebSocket API

### Connection

Connect to a session's WebSocket endpoint:
```
ws://localhost:8000/api/sessions/{session_id}/ws
```

### Message Format

All WebSocket messages follow this structure:

**Request:**
```json
{
  "type": "message_type",
  "data": {
    // Message-specific data
  }
}
```

**Response:**
```json
{
  "type": "response_type", 
  "data": {
    // Response-specific data
  }
}
```

**Error:**
```json
{
  "type": "error",
  "data": {
    "code": "ERROR_CODE",
    "message": "Error description"
  }
}
```

### Core Message Types

#### Ping
Test WebSocket connection.

**Request:**
```json
{
  "type": "ping",
  "data": {
    "timestamp": "2024-01-01T12:00:00.000Z"
  }
}
```

**Response:**
```json
{
  "type": "pong",
  "data": {
    "timestamp": "2024-01-01T12:00:00.000Z",
    "server_timestamp": "2024-01-01T12:00:00.001Z"
  }
}
```

#### Get Engine Types
List available engine types.

**Request:**
```json
{
  "type": "get_engine_types",
  "data": {}
}
```

**Response:**
```json
{
  "type": "engine_types",
  "data": {
    "engine_types": ["SinglePassEngine", "ToolChatEngine", "VoiceProcessingEngine"]
  }
}
```

#### Link Engine
Create and link an engine to the session.

**Request:**
```json
{
  "type": "link_engine",
  "data": {
    "engine_type": "ToolChatEngine"
  }
}
```

**Response:**
```json
{
  "type": "engine_linked",
  "data": {
    "engine_id": "engine_123",
    "engine_type": "ToolChatEngine",
    "status": "running"
  }
}
```

#### Status
Get session status.

**Request:**
```json
{
  "type": "status",
  "data": {}
}
```

**Response:**
```json
{
  "type": "status_response",
  "data": {
    "session_status": "running",
    "engine_status": "running",
    "engine_id": "engine_123"
  }
}
```

### Error Codes

| Code | Description |
|------|-------------|
| `SESSION_NOT_FOUND` | Session does not exist or has expired |
| `INVALID_ENGINE_TYPE` | Requested engine type is not available |
| `ENGINE_CREATION_FAILED` | Failed to create engine |
| `INVALID_MESSAGE_TYPE` | Unknown message type |
| `INVALID_JSON` | Message is not valid JSON |
| `VALIDATION_ERROR` | Message failed validation |
| `WEBSOCKET_ERROR` | Internal WebSocket error |

## Extensibility

### Creating Custom Messages

1. **Define Message Types:**
```python
from llmgineAPI.models.websocket import WSMessage, WSResponse
from llmgineAPI.core.extensibility import CustomMessageMixin

class CustomRequest(WSMessage, CustomMessageMixin):
    def __init__(self, custom_data: str):
        super().__init__(
            type="custom_request",
            data={"custom_data": custom_data}
        )

class CustomResponse(WSResponse):
    def __init__(self, result: str):
        super().__init__(
            type="custom_response",
            data={"result": result}
        )
```

2. **Create Handler:**
```python
from llmgineAPI.websocket.base import BaseHandler

class CustomHandler(BaseHandler):
    @property
    def message_type(self) -> str:
        return "custom_request"
    
    @property
    def request_model(self) -> type[WSMessage]:
        return CustomRequest
    
    async def handle(self, message, websocket, session_id):
        # Process custom logic
        custom_data = message.data["custom_data"]
        result = f"Processed: {custom_data}"
        
        return CustomResponse(result=result)
```

3. **Register with API Factory:**
```python
from llmgineAPI.core.extensibility import ExtensibleAPIFactory, EngineConfiguration

config = EngineConfiguration(engine_name="CustomEngine")
factory = ExtensibleAPIFactory(config)
factory.register_custom_handler("custom_request", CustomHandler)
```

4. **Create Application:**
```python
from llmgineAPI.main import create_app

app = create_app(api_factory=factory)
```

### Example: Translation Engine

See `examples/custom_engine_example.py` for a complete implementation of a translation engine with custom message types and handlers.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLMGINE_API_TITLE` | "LLMgine API" | API title |
| `LLMGINE_API_HOST` | "0.0.0.0" | Host to bind to |
| `LLMGINE_API_PORT` | 8000 | Port to bind to |
| `LLMGINE_API_DEBUG` | false | Enable debug mode |
| `LLMGINE_API_MAX_SESSIONS` | 100 | Maximum concurrent sessions |
| `LLMGINE_API_SESSION_TIMEOUT` | 3600 | Session timeout in seconds |

### Custom Configuration

```python
from llmgineAPI.config import APIConfig

config = APIConfig(
    title="My Custom API",
    version="2.0.0",
    max_sessions=50,
    custom={
        "my_setting": "value",
        "feature_flags": {"advanced_mode": True}
    }
)

app = create_app(config=config)
```

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ .
EXPOSE 8000

CMD ["uvicorn", "llmgineAPI.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: llmgine-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: llmgine-api
  template:
    metadata:
      labels:
        app: llmgine-api
    spec:
      containers:
      - name: api
        image: llmgine-api:latest
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        env:
        - name: LLMGINE_API_MAX_SESSIONS
          value: "50"
```

## Security Considerations

### Current Limitations

⚠️ **Warning**: This API is not production-ready without additional security measures.

**Missing Security Features:**
- No authentication/authorization
- CORS allows all origins by default
- No rate limiting
- No input sanitization beyond Pydantic validation
- No request logging or audit trail

### Recommended Security Enhancements

1. **Authentication:**
   - Implement JWT token validation
   - Add API key support
   - Role-based access control

2. **Network Security:**
   - Restrict CORS origins
   - Add rate limiting middleware
   - Implement request size limits

3. **Input Validation:**
   - Enhanced message validation
   - SQL injection prevention
   - XSS protection

4. **Monitoring:**
   - Request/response logging
   - Security event logging
   - Intrusion detection

## Performance Considerations

### Current Limitations

- Memory-only storage (data lost on restart)
- Polling-based monitoring (1-second intervals)
- No connection pooling
- No caching layer

### Optimization Recommendations

1. **Persistence:**
   - Add database backend (PostgreSQL/Redis)
   - Implement session persistence

2. **Performance:**
   - Event-driven monitoring instead of polling
   - Connection pooling for external services
   - Caching layer for frequently accessed data

3. **Scalability:**
   - Horizontal scaling with shared storage
   - Load balancing for WebSocket connections
   - Message queue for background processing

## Troubleshooting

### Common Issues

#### WebSocket Connection Fails
- Verify session exists: `GET /api/sessions/{session_id}`
- Check WebSocket URL format: `ws://host:port/api/sessions/{session_id}/ws`
- Ensure session hasn't expired

#### Custom Handler Not Working
- Verify handler is registered with factory
- Check message type matches handler's `message_type` property
- Ensure factory is passed to `create_app()`

#### Health Checks Fail
- Check if services are initialized
- Verify monitor threads are running
- Review application logs for errors

### Debug Mode

Enable debug mode for detailed error information:

```python
config = APIConfig(debug=True)
app = create_app(config=config)
```

Or via environment variable:
```bash
export LLMGINE_API_DEBUG=true
```

## Contributing

### Development Setup

1. Install dependencies:
```bash
pip install -e ".[dev]"
```

2. Run tests:
```bash
pytest
```

3. Code quality checks:
```bash
ruff check src/
mypy src/
```

### Adding New Features

1. Follow existing patterns for message types and handlers
2. Add comprehensive docstrings
3. Include type hints
4. Write tests for new functionality
5. Update documentation

See `CONTRIBUTING.md` for detailed guidelines.