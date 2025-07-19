# LLMGine API Module

This module provides a **general-purpose, extensible FastAPI-based REST and WebSocket API** designed to serve as a foundation for LLMGine-based applications. The API module is designed to be imported and extended by other projects that use LLMGine as their core engine.

## 🎯 Design Philosophy

The API module serves as a **complementary library** to the core LLMGine module, providing:

- **Base API structure** that other projects can build upon
- **Extensible WebSocket message system** for real-time communication
- **Pluggable handler architecture** for custom message types
- **Configuration system** that supports project-specific settings
- **Type-safe communication** with full Pydantic validation

## 🏗️ Architecture Overview

```
src/api/
├── core/                   # Extensibility framework
│   ├── extensibility.py    # Base classes for custom extensions
│   └── __init__.py
├── config.py              # Configuration system
├── examples/               # Usage examples for other projects
│   ├── custom_engine_example.py
│   └── __init__.py
├── main.py                # App factory with extension support
├── models/                # Pydantic models
│   ├── websocket.py       # WebSocket message schemas
│   ├── sessions.py        # Session management models
│   └── responses.py       # Standard response models
├── routers/               # FastAPI routers
│   ├── websocket.py       # WebSocket endpoints
│   ├── sessions.py        # Session management
│   └── ...
├── services/              # Business logic services
├── utils/                 # Utility functions
└── websocket/             # WebSocket infrastructure
    ├── base.py            # Base handler classes
    ├── handlers.py        # Core message handlers
    └── registry.py        # Handler registration system
```

## 🔧 How Other Projects Use This API

### 1. **Basic Usage (Default LLMGine API)**

```python
# In your project's main.py
from api.main import app

# Use the default LLMGine API as-is
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 2. **Extended Usage (Custom Engine API)**

```python
# In your project's main.py
from api.main import create_app
from api.config import APIConfig
from api.core.extensibility import ExtensibleAPIFactory

# Create custom configuration
config = APIConfig(
    title="My Translation Engine API",
    description="API for my specialized translation engine",
    version="2.0.0",
    custom={"supported_languages": ["en", "es", "fr"]}
)

# Create API factory with custom extensions
api_factory = ExtensibleAPIFactory(config)

# Register custom message handlers
api_factory.register_custom_handler("translate", TranslateHandler)
api_factory.register_custom_handler("analyze_sentiment", SentimentHandler)

# Add custom routers
api_factory.register_custom_router(translation_router)

# Create customized app
app = create_app(config=config, api_factory=api_factory)
```

### 3. **Custom WebSocket Messages**

```python
from api.models.websocket import WSMessage, WSResponse
from api.core.extensibility import CustomMessageMixin

# Define custom request
class TranslateRequest(WSMessage, CustomMessageMixin):
    def __init__(self, text: str, target_language: str):
        super().__init__(
            type="translate",
            data={"text": text, "target_language": target_language}
        )

# Define custom response
class TranslateResponse(WSResponse):
    def __init__(self, original_text: str, translated_text: str):
        super().__init__(
            type="translate_res",
            data={"original_text": original_text, "translated_text": translated_text}
        )

# Create custom handler
class TranslateHandler(BaseHandler):
    @property
    def message_type(self) -> str:
        return "translate"
    
    @property
    def request_model(self) -> type[BaseModel]:
        return TranslateRequest
    
    async def handle(self, message: TranslateRequest, websocket: WebSocket, session_id: SessionID) -> Optional[WSResponse]:
        # Implement your translation logic here
        text = message.data["text"]
        target_lang = message.data["target_language"]
        
        # Your custom translation implementation
        translated = await your_translation_service.translate(text, target_lang)
        
        return TranslateResponse(
            original_text=text,
            translated_text=translated
        )
```

## 🌟 Key Features for Extensibility

### **1. Pluggable Handler System**
- Register custom WebSocket message handlers
- Type-safe message validation with Pydantic
- Automatic message routing and error handling

### **2. Configuration Management**
- Environment variable support
- JSON configuration files
- Programmatic configuration with custom fields

### **3. Factory Pattern**
- `ExtensibleAPIFactory` for creating customized API instances
- Support for custom routers and middleware
- Metadata tracking for custom extensions

### **4. Type Safety**
- Full Pydantic validation for all messages
- Custom message base classes with validation
- Structured error responses

## 📋 WebSocket Message Protocol

### **Base Message Format**
```json
{
    "type": "message_type",
    "data": { ... }
}
```

### **Core Message Types**
- `ping` - Connection testing
- `get_engine_types` - Get available engines
- `link_engine` - Create and link engine to session
- `status` - Get session status
- `command` - Execute commands (extensible)
- `event` - Publish events (extensible)

### **Custom Message Types**
Projects can define unlimited custom message types by:
1. Extending `WSMessage` and `WSResponse` base classes
2. Creating corresponding handler classes
3. Registering handlers with the API factory

## 📦 Frontend Integration

The structured message system makes it easy for frontends to:

```typescript
// TypeScript frontend example
interface PingRequest {
    type: "ping";
    data: { timestamp: string };
}

interface PingResponse {
    type: "ping_res";
    data: { timestamp: string };
}

// Send structured messages
const pingMessage: PingRequest = {
    type: "ping",
    data: { timestamp: new Date().toISOString() }
};

websocket.send(JSON.stringify(pingMessage));
```

## 🚀 Getting Started

1. **Use as-is**: Import the default app for standard LLMGine functionality
2. **Extend configuration**: Create custom `APIConfig` with your settings
3. **Add custom messages**: Define new request/response models
4. **Create handlers**: Implement handlers for your custom messages
5. **Register extensions**: Use `ExtensibleAPIFactory` to combine everything
6. **Deploy**: Create your customized app and deploy

See `examples/custom_engine_example.py` for a complete implementation example.

This architecture ensures that the API module serves as a **solid foundation** while remaining **completely extensible** for specialized use cases.