# LLMGine API Module

This module provides a **WebSocket-only, extensible FastAPI-based API** with **bidirectional messaging capabilities** designed to serve as a foundation for LLMGine-based applications. The API module is designed to be imported and extended by other projects that use LLMGine as their core engine.

## 🎯 Design Philosophy

The API module serves as a **complementary library** to the core LLMGine module, providing:

- **WebSocket-first architecture** for real-time communication
- **Bidirectional messaging** with server-initiated requests and notifications
- **App-based session management** with automatic cleanup
- **Request-response mapping** using Futures for async operations
- **Extensible message system** for custom functionality
- **Framework integration API** for custom backends
- **Type-safe communication** with full Pydantic validation
- **Thread-safe operations** with proper resource management

## 🏗️ Architecture Overview

```
src/llmgineAPI/
├── core/                   # Extensibility framework
│   ├── extensibility.py    # Base classes for custom extensions
│   ├── messaging_api.py    # Server messaging API for custom backends
│   └── __init__.py
├── config.py              # Configuration system
├── examples/               # Usage examples for other projects
│   ├── custom_engine_example.py
│   └── __init__.py
├── main.py                # FastAPI app with messaging infrastructure
├── models/                # Pydantic models
│   ├── websocket.py       # WebSocket message schemas with server messages
│   ├── sessions.py        # Session management models
│   └── responses.py       # Standard response models
├── routers/               # FastAPI routers
│   └── websocket.py       # WebSocket-only endpoint with connection registry
├── services/              # Business logic services
│   ├── session_service.py # Session lifecycle management
│   ├── engine_service.py  # Engine lifecycle management
│   └── connection_service.py # WebSocket connection management
├── utils/                 # Utility functions
└── websocket/             # WebSocket infrastructure
    ├── base.py            # Base handler classes with server messaging
    ├── handlers.py        # Core message handlers
    ├── registry.py        # Handler registration system
    └── connection_registry.py # Connection tracking and management
```

## 🔧 Bidirectional WebSocket Communication

### Connection Flow

1. **Connect**: Client connects to `/api/ws`
2. **App Registration**: Server assigns unique `app_id` and sends connection confirmation
3. **Session Management**: Frontend creates sessions associated with the `app_id`
4. **Bidirectional Messaging**: Both client and server can initiate messages
5. **Future-Based Responses**: Server can send requests and wait for responses using asyncio Futures
6. **Cleanup**: On disconnect, all sessions, engines, and pending requests are automatically cleaned up

### Message Protocol

All WebSocket messages follow this structure with request-response mapping:

**Client-Initiated Request Format:**
```json
{
  "type": "message_type",
  "message_id": "unique-uuid-123",
  "data": {
    // Message-specific data
  }
}
```

**Server-Initiated Message Format:**
```json
{
  "type": "server_request",
  "message_id": "server-generated-uuid",
  "server_initiated": true,
  "data": {
    "request_type": "user_input",
    "prompt": "Please enter your name"
  }
}
```

**Response Format (works for both directions):**
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

#### Client-Initiated Messages

**Create Session:**
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

**Ping/Pong:**
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

#### Server-Initiated Messages

**Server Request (with response expected):**
```json
// Server sends
{
  "type": "server_request",
  "message_id": "server-uuid",
  "server_initiated": true,
  "data": {
    "request_type": "user_confirmation",
    "message": "Do you want to proceed?",
    "options": ["yes", "no"]
  }
}

// Client responds
{
  "type": "server_response",
  "message_id": "server-uuid",
  "data": {
    "response_type": "user_confirmation",
    "selection": "yes"
  }
}
```

**Server Notification (fire-and-forget):**
```json
{
  "type": "notification",
  "message_id": "server-uuid",
  "server_initiated": true,
  "data": {
    "notification_type": "process_complete",
    "message": "Your file has been processed successfully",
    "additional_data": {
      "file_id": "abc123",
      "download_url": "/api/files/abc123"
    }
  }
}
```

**Server Ping:**
```json
// Server sends
{
  "type": "server_ping",
  "message_id": "server-uuid",
  "server_initiated": true,
  "data": {
    "timestamp": "2024-01-01T12:00:00.000Z"
  }
}

// Client responds
{
  "type": "server_pong",
  "message_id": "server-uuid",
  "data": {
    "timestamp": "2024-01-01T12:00:00.000Z",
    "server_timestamp": "2024-01-01T12:00:00.001Z"
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

## 🌟 Connection Registry & Resource Management

### Connection Registry System

The API uses a sophisticated connection registry for tracking WebSocket connections:

```python
# Thread-safe connection registry with metadata
@dataclass
class ConnectionMetadata:
    app_id: str
    websocket: WebSocket
    session_ids: Set[SessionID]
    connected_at: datetime
    last_activity: datetime
```

### Automatic Resource Management

When a WebSocket disconnects, the system automatically:

1. **Cancels pending server requests** using Future cancellation
2. **Finds all sessions** associated with the `app_id`
3. **Stops and deletes engines** linked to those sessions
4. **Unregisters session handlers** from the message bus
5. **Deletes sessions** from the session service
6. **Removes connection** from the registry
7. **Triggers cleanup callbacks** for custom backends

### Thread Safety

All operations use proper locking mechanisms:
- Connection registry operations use `RLock`
- Pending request management is atomic
- Session and engine cleanup is synchronized

## 🔧 Framework Integration for Custom Backends

### 1. **Basic Usage (Default WebSocket API)**

```python
# In your project's main.py
from llmgineAPI.main import app

# Use the default WebSocket API as-is
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 2. **Extended Usage with Server Messaging**

```python
# In your project's main.py
from llmgineAPI.main import create_app
from llmgineAPI.config import APIConfig
from llmgineAPI.core.extensibility import ExtensibleAPIFactory, EngineConfiguration

class MyCustomBackend:
    def __init__(self, messaging_api):
        self.messaging = messaging_api
    
    async def send_user_notification(self, app_id: str, message: str):
        """Send notification to specific frontend app"""
        await self.messaging.send_to_app(
            app_id=app_id,
            message_type="notification", 
            data={
                "notification_type": "info",
                "message": message
            }
        )
    
    async def request_user_input(self, app_id: str, prompt: str) -> str:
        """Request input from user and wait for response"""
        try:
            response = await self.messaging.send_to_app_and_wait(
                app_id=app_id,
                message_type="server_request",
                data={
                    "request_type": "user_input",
                    "prompt": prompt
                },
                timeout=30.0
            )
            return response.data.get("user_input", "")
        except Exception as e:
            print(f"Error getting user input: {e}")
            return ""

# Setup
config = EngineConfiguration(engine_name="MyCustomEngine")
api_factory = ExtensibleAPIFactory(config)

# Register custom message handlers
api_factory.register_custom_handler("translate", TranslateHandler)

# Register connection event callbacks
async def on_user_connected(app_id: str):
    print(f"User connected: {app_id}")

async def on_user_disconnected(app_id: str):
    print(f"User disconnected: {app_id}")

api_factory.register_connection_callback("connect", on_user_connected)
api_factory.register_connection_callback("disconnect", on_user_disconnected)

# Create app
app = create_app(api_factory=api_factory)

# Get messaging API after app creation
messaging_api = api_factory.get_messaging_api()
backend = MyCustomBackend(messaging_api)

# Store in app state for use in handlers
app.state.custom_backend = backend
```

### 3. **Server Messaging API Methods**

The messaging API provides comprehensive methods for server-initiated communication:

```python
# Fire-and-forget messaging
await messaging_api.send_to_app(app_id, "notification", {"message": "Hello!"})
await messaging_api.send_to_session(session_id, "notification", {"message": "Hello!"})

# Request-response messaging with Future-based waiting
response = await messaging_api.send_to_app_and_wait(
    app_id, 
    "server_request", 
    {"request_type": "confirmation", "message": "Proceed?"},
    timeout=30.0
)

# Broadcasting
sent_count = await messaging_api.broadcast(
    "notification", 
    {"message": "System maintenance in 5 minutes"},
    exclude_apps={"admin-app-123"}
)

# Connection management
connected_apps = messaging_api.get_connected_apps()
is_connected = messaging_api.is_app_connected("some-app-id")
app_sessions = messaging_api.get_app_sessions("some-app-id")
```

### 4. **Custom Server-Initiated Messages**

```python
from llmgineAPI.models.websocket import ServerMessage, ServerInitiatedMixin

# Define custom server message
class CustomServerMessage(ServerMessage, ServerInitiatedMixin):
    def __init__(self, custom_data: str, message_id: Optional[str] = None):
        super().__init__(
            type="custom_server_message",
            message_id=message_id or str(uuid.uuid4()),
            data={"custom_data": custom_data}
        )

# Use in your backend
custom_message = CustomServerMessage("Hello from server!")
await connection.websocket.send_text(custom_message.model_dump_json())
```

## 📱 Frontend Integration

The bidirectional messaging makes frontend integration powerful and flexible:

```typescript
// TypeScript frontend example with server message handling
interface WebSocketMessage {
  type: string;
  message_id: string;
  data: any;
  server_initiated?: boolean;
}

class WebSocketClient {
  private pendingRequests = new Map<string, (response: any) => void>();
  private serverMessageHandlers = new Map<string, (message: any) => Promise<void>>();
  
  // Client-initiated request-response
  async sendMessage(type: string, data: any): Promise<any> {
    const message_id = crypto.randomUUID();
    
    return new Promise((resolve) => {
      this.pendingRequests.set(message_id, resolve);
      
      this.websocket.send(JSON.stringify({
        type,
        message_id,
        data
      }));
    });
  }
  
  // Register handler for server-initiated messages
  registerServerMessageHandler(type: string, handler: (message: any) => Promise<void>) {
    this.serverMessageHandlers.set(type, handler);
  }
  
  private async handleMessage(message: WebSocketMessage) {
    // Handle client request responses
    const resolver = this.pendingRequests.get(message.message_id);
    if (resolver) {
      resolver(message);
      this.pendingRequests.delete(message.message_id);
      return;
    }
    
    // Handle server-initiated messages
    if (message.server_initiated) {
      if (message.type === "server_request") {
        await this.handleServerRequest(message);
      } else if (message.type === "notification") {
        await this.handleNotification(message);
      } else if (message.type === "server_ping") {
        await this.handleServerPing(message);
      }
    }
  }
  
  private async handleServerRequest(message: WebSocketMessage) {
    const { request_type } = message.data;
    const handler = this.serverMessageHandlers.get(request_type);
    
    if (handler) {
      try {
        await handler(message);
      } catch (error) {
        // Send error response
        this.websocket.send(JSON.stringify({
          type: "server_response",
          message_id: message.message_id,
          data: {
            response_type: request_type,
            error: error.message
          }
        }));
      }
    }
  }
  
  private async handleServerPing(message: WebSocketMessage) {
    // Auto-respond to server ping
    this.websocket.send(JSON.stringify({
      type: "server_pong",
      message_id: message.message_id,
      data: {
        timestamp: message.data.timestamp,
        server_timestamp: new Date().toISOString()
      }
    }));
  }
  
  // Send response to server request
  sendServerResponse(message_id: string, response_type: string, data: any) {
    this.websocket.send(JSON.stringify({
      type: "server_response",
      message_id,
      data: {
        response_type,
        ...data
      }
    }));
  }
}

// Usage
const client = new WebSocketClient();

// Handle server requests for user input
client.registerServerMessageHandler("user_input", async (message) => {
  const userInput = await showInputDialog(message.data.prompt);
  client.sendServerResponse(message.message_id, "user_input", {
    user_input: userInput
  });
});

// Handle notifications
client.registerServerMessageHandler("notification", async (message) => {
  showNotification(message.data.message);
});

// Client-initiated requests still work
const sessionResponse = await client.sendMessage("create_session", {
  app_id: "my-frontend-app"
});
```

## 🚀 Key Features

### **1. Bidirectional Communication**
- Server can initiate messages to clients
- Future-based async/await pattern for server requests
- Fire-and-forget notifications
- Connection health monitoring with server pings

### **2. Request-Response Mapping**
- Every message has a unique `message_id` (UUID4)
- Responses include the same `message_id` for matching
- Works for both client-initiated and server-initiated messages
- Automatic timeout handling with configurable timeouts

### **3. Connection Registry & Management**
- Thread-safe connection tracking with metadata
- Health monitoring and diagnostics
- Automatic cleanup of stale connections
- Connection event callbacks for custom backends

### **4. Framework Integration API**
- Clean messaging API for custom backends
- Event callback system for connection/session lifecycle
- Convenience methods for common messaging patterns
- Type-safe interfaces with comprehensive error handling

### **5. Production-Ready Features**
- Thread-safe operations with proper locking
- Graceful shutdown with Future cancellation
- Health check endpoints with connection metrics
- Comprehensive error handling and logging
- Automatic resource cleanup and monitoring

## 📋 API Endpoints

### Health Check Endpoints

**`GET /health`** - Basic health check endpoint

**`GET /health/ready`** - Readiness check for Kubernetes deployments. Validates:
- Service initialization status
- Monitor thread status
- Active session/engine counts
- WebSocket connection health
- Pending server request counts

**`GET /health/live`** - Liveness check for Kubernetes deployments

### Information Endpoints

**`GET /api/info`** - Detailed API information including:
- API configuration
- Messaging capabilities
- Custom extensions metadata
- Server messaging features

**`GET /api/connections`** - WebSocket connection information:
- Active connections summary
- Connected app IDs
- Messaging capabilities overview
- Connection health metrics

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
    title="My Custom Messaging API",
    version="2.0.0",
    max_sessions=50,
    custom={
        "messaging_features": {
            "server_requests": True,
            "notifications": True,
            "broadcasting": True
        },
        "timeouts": {
            "server_request_timeout": 30,
            "connection_cleanup_interval": 300
        }
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
- Request timeout handling
- Connection health monitoring

**Missing Security Features:**
- Authentication/authorization for WebSocket connections
- Rate limiting for server-initiated messages
- Message encryption
- Request logging/audit trail for server messages

### Recommended Security Enhancements

1. **Authentication:**
   - WebSocket authentication during handshake
   - JWT token validation for server requests
   - API key support for backend services

2. **Rate Limiting:**
   - Message rate limiting per connection
   - Server request frequency limits
   - Connection limits per IP
   - Broadcast throttling

3. **Message Security:**
   - Message payload encryption
   - Request signing for server messages
   - Content filtering and validation
   - Size limits for all message types

## 🚀 Getting Started

1. **Use as-is**: Import the default app for standard WebSocket functionality with server messaging
2. **Extend configuration**: Create custom `APIConfig` with messaging settings
3. **Add custom handlers**: Define new request/response models and server message types
4. **Implement backend**: Create custom backend class using the messaging API
5. **Register callbacks**: Set up connection and session event handlers
6. **Deploy**: Create your customized app with bidirectional messaging and deploy

See `examples/custom_engine_example.py` for a complete implementation example with server messaging.

This architecture ensures that the API module serves as a **powerful bidirectional WebSocket foundation** with **comprehensive server messaging capabilities** while remaining **completely extensible** for specialized use cases.