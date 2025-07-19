"""
FastAPI app initialization and configuration with extensibility support.

This module provides both a default app instance and factory functions
for creating customized apps with project-specific extensions.
"""

from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import config_manager, APIConfig
from api.core.extensibility import ExtensibleAPIFactory
from api.routers import sessions, websocket


def create_app(
    config: Optional[APIConfig] = None,
    api_factory: Optional[ExtensibleAPIFactory] = None
) -> FastAPI:
    """
    Create a FastAPI application with optional customizations.
    
    Args:
        config: Custom configuration (uses defaults if None)
        api_factory: Factory with custom extensions (optional)
        
    Returns:
        Configured FastAPI application
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
    
    # Include core routers
    app.include_router(sessions.router)
    app.include_router(websocket.router)
    
    # Include custom routers if provided
    if api_factory:
        for custom_router in api_factory.custom_routers:
            app.include_router(custom_router)
    
    # Root endpoint with dynamic metadata
    @app.get("/")
    async def root():
        """Root endpoint with API information."""
        base_info = {
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
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": config.title.lower().replace(" ", "-")}
    
    @app.get("/api/info")
    async def api_info():
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
            }
        }
        
        if api_factory:
            info["extensions"] = api_factory.get_api_metadata()
        
        return info
    
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
