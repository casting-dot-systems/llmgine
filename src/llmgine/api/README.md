# LLMGine API Server

This directory contains the FastAPI backend server for the LLMGine system. The API provides a RESTful interface to the LLM engine, replacing the internal message bus communication with HTTP endpoints for frontend integration.

## Architecture Overview

The API server acts as a facade over the existing LLMGine architecture, providing HTTP endpoints for:
- Session management
- Command execution
- Event publishing and subscription
- Engine management
- Tool registration and execution
- Handler registration
- Observability and monitoring

### Key Components

```
src/llmgine/api/
├── main.py                 # FastAPI app initialization and configuration
├── dependencies.py         # Dependency injection and shared services
├── models/                 # Pydantic models for request/response validation
├── routers/               # FastAPI route handlers organized by domain
├── services/              # Business logic layer interfacing with core LLMGine
└── middleware/            # Custom middleware for logging, auth, CORS, etc.
```

## API Endpoints

### 1. Session Management

#### Create Session
```http
POST /api/sessions
Content-Type: application/json

{
  "name": "optional-session-name",
  "metadata": {
    "user_id": "user123",
    "project": "my-project"
  }
}
```

**Response:**
```json
{
  "session_id": "uuid-session-id",
  "created_at": "2024-01-01T00:00:00Z",
  "status": "active"
}
```

#### Get Session Status
```http
GET /api/sessions/{session_id}
```

#### Delete Session
```http
DELETE /api/sessions/{session_id}
```

### 2. Command Execution

#### Execute Command
```http
POST /api/sessions/{session_id}/commands
Content-Type: application/json

{
  "command_type": "DummyEngineCommand",
  "parameters": {
    "prompt": "Hello, world!"
  },
  "metadata": {
    "priority": "high",
    "timeout": 30
  }
}
```

**Response:**
```json
{
  "command_id": "uuid-command-id",
  "status": "executing",
  "result": null,
  "error": null,
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### Get Command Result
```http
GET /api/sessions/{session_id}/commands/{command_id}
```

#### Batch Command Execution
```http
POST /api/sessions/{session_id}/commands/batch
Content-Type: application/json

{
  "commands": [
    {
      "command_type": "DummyEngineCommand",
      "parameters": {"prompt": "First command"}
    },
    {
      "command_type": "DummyEngineCommand", 
      "parameters": {"prompt": "Second command"}
    }
  ]
}
```

### 3. Event Management

#### Publish Event
```http
POST /api/sessions/{session_id}/events
Content-Type: application/json

{
  "event_type": "DummyEngineStatusUpdate",
  "data": {
    "status": "processing"
  },
  "metadata": {
    "source": "engine",
    "priority": "normal"
  }
}
```

#### Get Events
```http
GET /api/sessions/{session_id}/events?limit=50&offset=0&event_type=StatusUpdate
```

#### Get Specific Event
```http
GET /api/sessions/{session_id}/events/{event_id}
```

### 4. Engine Management

#### Create Engine
```http
POST /api/engines
Content-Type: application/json

{
  "engine_type": "DummyEngine",
  "model_name": "gpt-4",
  "session_id": "session-uuid",
  "configuration": {
    "temperature": 0.7,
    "max_tokens": 1000
  }
}
```

**Response:**
```json
{
  "engine_id": "uuid-engine-id",
  "engine_type": "DummyEngine",
  "status": "initialized",
  "session_id": "session-uuid",
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### List Engines
```http
GET /api/engines?session_id={session_id}&status=active
```

#### Get Engine Details
```http
GET /api/engines/{engine_id}
```

#### Execute on Engine
```http
POST /api/engines/{engine_id}/execute
Content-Type: application/json

{
  "prompt": "Hello, world!",
  "parameters": {
    "temperature": 0.7
  }
}
```

#### Delete Engine
```http
DELETE /api/engines/{engine_id}
```

### 5. Tool Management

#### Register Tool
```http
POST /api/sessions/{session_id}/tools
Content-Type: application/json

{
  "name": "get_weather",
  "description": "Get weather information for a location",
  "parameters": {
    "location": {
      "type": "string",
      "description": "City name"
    }
  },
  "function_code": "async def get_weather(location: str): ..."
}
```

#### List Tools
```http
GET /api/sessions/{session_id}/tools
```

#### Execute Tool
```http
POST /api/sessions/{session_id}/tools/{tool_name}/execute
Content-Type: application/json

{
  "arguments": {
    "location": "Melbourne"
  }
}
```

#### Unregister Tool
```http
DELETE /api/sessions/{session_id}/tools/{tool_name}
```

### 6. Handler Registration

#### Register Command Handler
```http
POST /api/sessions/{session_id}/handlers/commands
Content-Type: application/json

{
  "command_type": "DummyEngineCommand",
  "handler_function": "async def handle_dummy_command(command): ..."
}
```

#### Register Event Handler
```http
POST /api/sessions/{session_id}/handlers/events
Content-Type: application/json

{
  "event_type": "DummyEngineStatusUpdate",
  "handler_function": "async def handle_status_update(event): ..."
}
```

#### Unregister Handlers
```http
DELETE /api/sessions/{session_id}/handlers/commands/{command_type}
DELETE /api/sessions/{session_id}/handlers/events/{event_type}
```

### 7. Observability

#### Get Logs
```http
GET /api/observability/logs?level=info&session_id={session_id}&limit=100
```

#### Get Metrics
```http
GET /api/observability/metrics?session_id={session_id}
```

#### Manual Logging
```http
POST /api/observability/logs
Content-Type: application/json

{
  "level": "info",
  "message": "User action completed",
  "metadata": {
    "user_id": "user123",
    "action": "command_execution"
  }
}
```

#### Get Trace
```http
GET /api/observability/traces/{trace_id}
```

### 8. System Management

#### Health Check
```http
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "version": "1.0.0",
  "uptime": 3600
}
```

#### System Status
```http
GET /api/status
```

#### Get Configuration
```http
GET /api/config
```

#### Graceful Shutdown
```http
POST /api/shutdown
```

## WebSocket Endpoints

### Real-time Event Streaming
```http
WS /api/sessions/{session_id}/events/stream
```

Subscribe to real-time events for a session:
```javascript
const ws = new WebSocket(`ws://localhost:8000/api/sessions/${sessionId}/events/stream`);
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received event:', data);
};
```

## Error Handling

All endpoints return consistent error responses:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": {
      "field": "prompt",
      "issue": "Field is required"
    }
  },
  "timestamp": "2024-01-01T00:00:00Z",
  "request_id": "uuid-request-id"
}
```

### Common Error Codes
- `VALIDATION_ERROR`: Request validation failed
- `SESSION_NOT_FOUND`: Session does not exist
- `ENGINE_NOT_FOUND`: Engine does not exist
- `COMMAND_EXECUTION_FAILED`: Command execution failed
- `TOOL_NOT_FOUND`: Tool not registered
- `HANDLER_NOT_FOUND`: Handler not registered
- `INTERNAL_ERROR`: Server internal error

## Authentication & Security

### API Key Authentication
```http
Authorization: Bearer your-api-key-here
```

### Session-based Authentication
```http
X-Session-Token: session-token-here
```

## Rate Limiting

- **Default**: 100 requests per minute per IP
- **Authenticated**: 1000 requests per minute per user
- **WebSocket**: 10 connections per minute per IP

## Configuration

### Environment Variables
```bash
# Server Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Database
DATABASE_URL=sqlite:///./llmgine.db

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/api.log

# Security
API_KEY_SECRET=your-secret-key
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com

# Observability
ENABLE_METRICS=true
ENABLE_TRACING=true
```

### Configuration File
```yaml
# config/api.yaml
server:
  host: 0.0.0.0
  port: 8000
  workers: 4

database:
  url: sqlite:///./llmgine.db

logging:
  level: INFO
  file: logs/api.log

security:
  api_key_secret: your-secret-key
  cors_origins:
    - http://localhost:3000
    - https://yourdomain.com

observability:
  enable_metrics: true
  enable_tracing: true
```

## Development

### Running the Development Server
```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn src.llmgine.api.main:app --reload --host 0.0.0.0 --port 8000

# Run with custom config
uvicorn src.llmgine.api.main:app --reload --env-file .env
```

### Running Tests
```bash
# Run all tests
pytest tests/api/

# Run specific test file
pytest tests/api/test_sessions.py

# Run with coverage
pytest tests/api/ --cov=src.llmgine.api --cov-report=html
```

### API Documentation

Once the server is running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Deployment

### Docker
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
COPY config/ ./config/

EXPOSE 8000
CMD ["uvicorn", "src.llmgine.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose
```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/llmgine
    depends_on:
      - db
  
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=llmgine
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## Migration from Message Bus

### Before (Message Bus)
```python
# Register command handler
bus.register_command_handler(DummyEngineCommand, handle_command, session_id)

# Execute command
result = await bus.execute(DummyEngineCommand(prompt="Hello"))

# Publish event
await bus.publish(DummyEngineStatusUpdate(status="processing"))
```

### After (API)
```python
# Register command handler
response = requests.post(f"/api/sessions/{session_id}/handlers/commands", json={
    "command_type": "DummyEngineCommand",
    "handler_function": "async def handle_command(command): ..."
})

# Execute command
response = requests.post(f"/api/sessions/{session_id}/commands", json={
    "command_type": "DummyEngineCommand",
    "parameters": {"prompt": "Hello"}
})

# Publish event
response = requests.post(f"/api/sessions/{session_id}/events", json={
    "event_type": "DummyEngineStatusUpdate",
    "data": {"status": "processing"}
})
```