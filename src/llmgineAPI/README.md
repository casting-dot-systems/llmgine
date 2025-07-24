# LLMGine API Module

This module provides a **WebSocket-only, extensible FastAPI-based API** designed to serve as a foundation for LLMGine-based applications. The API module is designed to be imported and extended by other projects that use LLMGine as their core engine.

## 🎯 Design Philosophy

The API module serves as a **complementary library** to the core LLMGine module, providing:

- **WebSocket-first architecture** for real-time communication
- **App-based session management** with automatic cleanup
- **Request-response mapping** for frontend applications
- **Extensible message system** for custom functionality
- **Type-safe communication** with full Pydantic validation
- **Thread-safe operations** with proper resource management

## 🏗️ Architecture Overview

```
src/llmgineAPI/
├── core/                   # Extensibility framework
│   ├── extensibility.py    # Base classes for custom extensions
│   └── __init__.py
├── config.py              # Configuration system
├── examples/               # Usage examples for other projects
│   ├── custom_engine_example.py
│   └── __init__.py
├── main.py                # FastAPI app with WebSocket support
├── models/                # Pydantic models
│   ├── websocket.py       # WebSocket message schemas with message IDs
│   ├── sessions.py        # Session management models
│   └── responses.py       # Standard response models
├── routers/               # FastAPI routers
│   └── websocket.py       # WebSocket-only endpoint
├── services/              # Business logic services
│   ├── session_service.py # Session lifecycle management
│   └── engine_service.py  # Engine lifecycle management
├── utils/                 # Utility functions
└── websocket/             # WebSocket infrastructure
    ├── base.py            # Base handler classes
    ├── handlers.py        # Core message handlers
    └── registry.py        # Handler registration system
```

## 🔧 WebSocket-Only Communication

### Connection Flow

1. **Connect**: Client connects to `/api/ws`
2. **App Registration**: Server assigns unique `app_id` and sends connection confirmation
3. **Session Management**: Frontend creates sessions associated with the `app_id`
4. **Message Exchange**: All communication happens through structured WebSocket messages
5. **Cleanup**: On disconnect, all sessions and engines are automatically cleaned up

### Message Protocol

All WebSocket messages follow this structure with request-response mapping:

**Request Format:**
```json
{
  "type": "message_type",
  "message_id": "unique-uuid-123",
  "data": {
    // Message-specific data
  }
}
```

**Response Format:**
```json
{
  "type": "response_type",
  "message_id": "unique-uuid-123",  // Same as request
  "data": {
    // Response-specific data
  }
}
```

### Core Message Types

#### Connection Establishment
When a WebSocket connects, the server automatically sends:

```json
{
  "type": "connected",
  "message_id": "auto-generated-uuid",
  "data": {
    "app_id": "unique-app-id",
    "status": "connected"
  }
}
```

#### Create Session
```json
// Request
{
  "type": "create_session",
  "message_id": "client-uuid",
  "data": {
    "app_id": "your-app-id"
  }
}

// Response
{
  "type": "create_session_res",
  "message_id": "client-uuid",
  "data": {
    "session_id": "new-session-uuid"
  }
}
```

#### Ping/Pong
```json
// Request
{
  "type": "ping",
  "message_id": "client-uuid",
  "data": {
    "timestamp": "2024-01-01T12:00:00.000Z"
  }
}

// Response
{
  "type": "ping_res",
  "message_id": "client-uuid",
  "data": {
    "timestamp": "2024-01-01T12:00:00.000Z"
  }
}
```

#### Session Status
```json
// Request
{
  "type": "status",
  "message_id": "client-uuid",
  "data": {
    "session_id": "session-uuid"
  }
}

// Response
{
  "type": "status_res",
  "message_id": "client-uuid",
  "data": {
    "session_id": "session-uuid",
    "status": "running",
    "created_at": "2024-01-01T12:00:00.000Z",
    "last_interaction_at": "2024-01-01T12:05:00.000Z"
  }
}
```

### Error Handling

All errors return a standardized format:

```json
{
  "type": "error",
  "message_id": "original-request-id",
  "data": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": null
  }
}
```

**Error Codes:**
- `SESSION_NOT_FOUND` - Session does not exist or expired
- `ENGINE_NOT_FOUND` - Engine not found
- `INVALID_ENGINE_TYPE` - Invalid engine type requested
- `ENGINE_CREATION_FAILED` - Failed to create engine
- `INVALID_MESSAGE_TYPE` - Unknown message type
- `INVALID_JSON` - Invalid JSON in message
- `VALIDATION_ERROR` - Message validation failed
- `WEBSOCKET_ERROR` - Internal WebSocket error

## 🌟 App-Based Session Management

### Static App Mapping

The API maintains a static dictionary mapping `app_id` to multiple `session_id`s:

```python
# Thread-safe static mapping shared across all WebSocket connections
_app_session_mapping: Dict[str, Set[SessionID]] = {}
```

### Automatic Cleanup

When a WebSocket disconnects, the system automatically:

1. **Finds all sessions** associated with the `app_id`
2. **Stops and deletes engines** linked to those sessions
3. **Unregisters session handlers** from the message bus
4. **Deletes sessions** from the session service
5. **Removes app mapping** from the static dictionary

### Thread Safety

All operations on the app mapping use `RLock` for thread safety:

```python
def register_session_to_app(app_id: str, session_id: SessionID) -> None:
    with _app_mapping_lock:
        # Thread-safe session registration
```

## 🔧 How Other Projects Use This API

### 1. **Basic Usage (Default WebSocket API)**

```python
# In your project's main.py
from llmgineAPI.main import app

# Use the default WebSocket API as-is
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 2. **Extended Usage (Custom Message API)**

```python
# In your project's main.py
from llmgineAPI.main import create_app
from llmgineAPI.config import APIConfig
from llmgineAPI.core.extensibility import ExtensibleAPIFactory

# Create custom configuration
config = APIConfig(
    title="My Translation Engine API",
    description="WebSocket API for my specialized translation engine",
    version="2.0.0",
    custom={"supported_languages": ["en", "es", "fr"]}
)

# Create API factory with custom extensions
api_factory = ExtensibleAPIFactory(config)

# Register custom message handlers
api_factory.register_custom_handler("translate", TranslateHandler)
api_factory.register_custom_handler("analyze_sentiment", SentimentHandler)

# Create customized app
app = create_app(config=config, api_factory=api_factory)
```

### 3. **Custom WebSocket Messages**

```python
from llmgineAPI.models.websocket import WSMessage, WSResponse
from llmgineAPI.websocket.base import BaseHandler
from typing import Optional, Dict, Any
import uuid

# Define custom request
class TranslateRequest(WSMessage):
    def __init__(self, text: str, target_language: str, message_id: Optional[str] = None):
        super().__init__(
            type="translate",
            message_id=message_id or str(uuid.uuid4()),
            data={"text": text, "target_language": target_language}
        )

# Define custom response
class TranslateResponse(WSResponse):
    def __init__(self, original_text: str, translated_text: str, message_id: str):
        super().__init__(
            type="translate_res",
            message_id=message_id,
            data={"original_text": original_text, "translated_text": translated_text}
        )

# Create custom handler
class TranslateHandler(BaseHandler):
    @property
    def message_type(self) -> str:
        return "translate"
    
    @property
    def request_model(self) -> type[WSMessage]:
        return TranslateRequest
    
    async def handle(
        self, 
        message: Dict[str, Any], 
        websocket: WebSocket
    ) -> Optional[WSResponse]:
        # Validate and extract data
        req = TranslateRequest.model_validate(message)
        text = req.data["text"]
        target_lang = req.data["target_language"]
        
        # Your custom translation implementation
        translated = await your_translation_service.translate(text, target_lang)
        
        return TranslateResponse(
            original_text=text,
            translated_text=translated,
            message_id=req.message_id  # Maintain request-response mapping
        )
```

## 📱 Frontend Integration

The request-response mapping makes it easy for frontends to track messages:

```typescript
// TypeScript frontend example
interface WebSocketMessage {
  type: string;
  message_id: string;
  data: any;
}

class WebSocketClient {
  private pendingRequests = new Map<string, (response: any) => void>();
  
  async sendMessage(type: string, data: any): Promise<any> {
    const message_id = crypto.randomUUID();
    
    return new Promise((resolve) => {
      // Store resolver for this message ID
      this.pendingRequests.set(message_id, resolve);
      
      // Send message
      this.websocket.send(JSON.stringify({
        type,
        message_id,
        data
      }));
    });
  }
  
  private handleMessage(message: WebSocketMessage) {
    const resolver = this.pendingRequests.get(message.message_id);
    if (resolver) {
      resolver(message);
      this.pendingRequests.delete(message.message_id);
    }
  }
}

// Usage
const client = new WebSocketClient();

// Create session and wait for response
const sessionResponse = await client.sendMessage("create_session", {
  app_id: "my-frontend-app"
});

// Use the session
const statusResponse = await client.sendMessage("status", {
  session_id: sessionResponse.data.session_id
});
```

## 🚀 Key Features

### **1. Request-Response Mapping**
- Every message has a unique `message_id` (UUID4)
- Responses include the same `message_id` for client matching
- Automatic ID generation if not provided
- Frontend can track requests and match responses

### **2. App-Based Resource Management**
- One `app_id` per WebSocket connection
- Multiple sessions per `app_id`
- Automatic cleanup on disconnect
- Thread-safe resource tracking

### **3. Extensible Handler System**
- Register custom WebSocket message handlers
- Type-safe message validation with Pydantic
- Automatic message routing and error handling
- Support for unlimited custom message types

### **4. Production-Ready Features**
- Thread-safe operations with proper locking
- Graceful shutdown handling
- Health check endpoints for Kubernetes
- Comprehensive error handling and logging
- Automatic resource cleanup

## 📋 Health Check Endpoints

The API provides health check endpoints for production deployment:

### `GET /health`
Basic health check endpoint.

### `GET /health/ready`
Readiness check for Kubernetes deployments. Validates:
- Service initialization status
- Monitor thread status
- Active session/engine counts

### `GET /health/live`
Liveness check for Kubernetes deployments.

## 🔧 Configuration

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
    title="My Custom WebSocket API",
    version="2.0.0",
    max_sessions=50,
    custom={
        "my_setting": "value",
        "feature_flags": {"advanced_mode": True}
    }
)

app = create_app(config=config)
```

## 🚀 Deployment

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

## 🔒 Security Considerations

### Current Status

⚠️ **Warning**: This API requires additional security measures for production use.

**Current Security Features:**
- Input validation with Pydantic
- Type-safe message handling
- Resource cleanup and management
- Thread-safe operations

**Missing Security Features:**
- Authentication/authorization
- Rate limiting
- CORS restrictions
- Request logging/audit trail

### Recommended Security Enhancements

1. **Authentication:**
   - WebSocket authentication during handshake
   - JWT token validation
   - API key support

2. **Rate Limiting:**
   - Message rate limiting per connection
   - Session creation limits
   - Connection limits per IP

3. **Input Validation:**
   - Enhanced message size limits
   - Content filtering
   - XSS/injection prevention

## 🚀 Getting Started

1. **Use as-is**: Import the default app for standard WebSocket functionality
2. **Extend configuration**: Create custom `APIConfig` with your settings
3. **Add custom messages**: Define new request/response models with message IDs
4. **Create handlers**: Implement handlers for your custom messages
5. **Register extensions**: Use `ExtensibleAPIFactory` to combine everything
6. **Deploy**: Create your customized app and deploy

See `examples/custom_engine_example.py` for a complete implementation example.

This architecture ensures that the API module serves as a **solid WebSocket foundation** while remaining **completely extensible** for specialized use cases.