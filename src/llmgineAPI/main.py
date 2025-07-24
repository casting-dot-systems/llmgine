"""
FastAPI app initialization and configuration with extensibility and messaging support.

This module provides both a default app instance and factory functions
for creating customized apps with project-specific extensions and
server-initiated messaging capabilities.
"""

from typing import Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import time
from datetime import datetime
import atexit

from llmgineAPI.config import config_manager, APIConfig
from llmgineAPI.core.extensibility import ExtensibleAPIFactory
from llmgineAPI.routers import websocket
from llmgineAPI.services.engine_service import EngineService
from llmgineAPI.services.session_service import SessionService
from llmgineAPI.websocket.connection_registry import get_connection_registry
from llmgineAPI.core.messaging_api import MessagingAPIWithEvents
from llmgineAPI.services.connection_service import get_connection_service


def create_app(
    config: Optional[APIConfig] = None,
    api_factory: Optional[ExtensibleAPIFactory] = None
) -> FastAPI:
    """
    Create a FastAPI application with optional customizations and messaging support.
    
    Args:
        config: Custom configuration (uses defaults if None)
        api_factory: Factory with custom extensions (optional)
        
    Returns:
        Configured FastAPI application with server messaging capabilities
    """
    
    # Use provided config or load from config manager
    if config is None:
        config = config_manager.config
    
    # Create FastAPI app with configuration
    app = FastAPI(
        title=config.title,
        description=config.description,
        version=config.version,
        debug=config.debug
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=config.cors_credentials,
        allow_methods=config.cors_methods,
        allow_headers=config.cors_headers,
    )
    
    # Initialize messaging infrastructure
    connection_registry = get_connection_registry()
    messaging_api = MessagingAPIWithEvents(connection_registry)
    connection_service = get_connection_service()
    
    # Store components in app state for access by routers and custom code
    app.state.api_factory = api_factory
    app.state.connection_registry = connection_registry
    app.state.messaging_api = messaging_api
    app.state.connection_service = connection_service
    
    # Initialize messaging API with factory if provided
    if api_factory:
        api_factory._set_messaging_api(messaging_api)
    
    # Include core routers
    app.include_router(websocket.router)
    
    # Include custom routers if provided
    if api_factory:
        for custom_router in api_factory.custom_routers:
            app.include_router(custom_router)
    
    # Register cleanup on app shutdown
    @app.on_event("shutdown")
    async def cleanup_on_shutdown():
        """Clean up resources when app shuts down."""
        try:
            # Cancel any pending messaging requests
            messaging_api.cancel_pending_requests("Application shutdown")
            
            # Clean up stale connections
            await connection_service.cleanup_stale_connections(max_idle_seconds=0)
            
        except Exception as e:
            print(f"Error during shutdown cleanup: {e}")
    
    # Root endpoint with dynamic metadata
    @app.get("/")
    async def root(): # type: ignore
        """Root endpoint with API information."""
        base_info : dict[str, Any] = {
            "message": f"{config.title}",
            "version": config.version,
            "engine_type": "llmgine-based"
        }
        
        # Add custom engine info if available
        if api_factory:
            metadata = api_factory.get_api_metadata()
            base_info.update({
                "engine_name": metadata["engine_name"],
                "custom_features": {
                    "message_types": metadata["custom_message_types"],
                    "custom_routers": metadata["custom_routers_count"]
                }
            })
        
        return base_info
    
    @app.get("/health")
    async def health_check(): # type: ignore
        """Basic health check endpoint."""
        return {
            "status": "healthy", 
            "service": config.title.lower().replace(" ", "-"),
            "timestamp": datetime.now().isoformat(),
            "uptime": time.time()
        }
    
    @app.get("/health/ready")
    async def readiness_check(): # type: ignore
        """Readiness check - indicates if the service is ready to handle requests."""
        try:
            session_service = SessionService()
            engine_service = EngineService()
            
            # Check if monitor threads are running
            if not session_service.monitor_thread.is_alive():
                raise HTTPException(status_code=503, detail="Session monitor thread not running")
                
            if not engine_service.monitor_thread.is_alive():
                raise HTTPException(status_code=503, detail="Engine monitor thread not running")
            
            # Get messaging system health
            health_info = connection_service.get_health_summary()
            
            return {
                "status": "ready",
                "timestamp": datetime.now().isoformat(),
                "services": {
                    "sessions": {
                        "initialized": True,
                        "monitor_running": session_service.monitor_thread.is_alive(),
                        "count": len(session_service.sessions)
                    },
                    "engines": {
                        "initialized": True,
                        "monitor_running": engine_service.monitor_thread.is_alive(),
                        "count": len(engine_service.engines)
                    },
                    "websocket_connections": {
                        "initialized": True,
                        "total_connections": health_info["total_connections"],
                        "total_sessions": health_info["total_sessions"],
                        "pending_server_requests": health_info.get("pending_server_requests", 0)
                    }
                }
            }
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Service not ready: {str(e)}")
    
    @app.get("/health/live")
    async def liveness_check(): # type: ignore
        """Liveness check - indicates if the service is alive."""
        return {
            "status": "alive",
            "timestamp": datetime.now().isoformat(),
            "pid": None  # Could add os.getpid() if needed
        }
    
    @app.get("/api/info")
    async def api_info(): # type: ignore
        """Detailed API information including custom extensions."""
        info = {
            "api": {
                "title": config.title,
                "description": config.description,
                "version": config.version,
                "debug": config.debug
            },
            "config": {
                "max_sessions": config.max_sessions,
                "session_timeout": config.session_timeout,
                "websocket_heartbeat_interval": config.websocket_heartbeat_interval
            },
            "messaging": {
                "server_messaging_enabled": True,
                "connection_registry_available": True,
                "features": [
                    "server_initiated_messages",
                    "request_response_mapping", 
                    "connection_event_callbacks",
                    "broadcast_messaging"
                ]
            }
        }
        
        if api_factory:
            info["extensions"] = api_factory.get_api_metadata()
        
        return info
    
    @app.get("/api/connections")
    async def connection_info(): # type: ignore
        """Get information about active WebSocket connections."""
        health_info = connection_service.get_health_summary()
        return {
            "summary": health_info,
            "connected_apps": connection_service.get_connected_apps(),
            "messaging_capabilities": {
                "send_to_app": True,
                "send_to_session": True,
                "broadcast": True,
                "request_response": True,
                "event_callbacks": True
            }
        }
    
    return app


# Default app instance (for backwards compatibility)
app = create_app()


# Example of how projects would create their custom app:
def create_custom_app_example():
    """
    Example of how other projects would create a custom app.
    
    This would typically be in their own main.py file.
    """
    
    # Load custom configuration
    custom_config = APIConfig(
        title="My Custom Engine API",
        description="API for my specialized LLMGine-based engine",
        version="2.0.0",
        custom={
            "feature_flags": {"advanced_analysis": True},
            "model_settings": {"temperature": 0.7}
        }
    )
    
    # Create factory with extensions (see examples/custom_engine_example.py)
    # api_factory = create_translation_api()
    
    # Create customized app
    # return create_app(config=custom_config, api_factory=api_factory)
    return create_app(config=custom_config)
