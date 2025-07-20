"""
Configuration system for the API module.

This module provides a flexible configuration system that can be
extended by projects using the API as a base.
"""

from typing import Dict, Any, Optional, Type
from pydantic import BaseModel, Field
from pathlib import Path
import json
import os
import logging

logger = logging.getLogger(__name__)

class APIConfig(BaseModel):
    """
    Base API configuration with extensible settings.
    """
    
    # Core API settings
    title: str = "LLMGine API"
    description: str = "API server for LLMGine-based applications"
    version: str = "1.0.0"
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # CORS settings
    cors_origins: list[str] = ["*"]
    cors_credentials: bool = True
    cors_methods: list[str] = ["*"]
    cors_headers: list[str] = ["*"]
    
    # Session settings
    max_sessions: int = 100
    session_timeout: int = 3600  # seconds
    
    # WebSocket settings
    websocket_heartbeat_interval: int = 30  # seconds
    websocket_max_message_size: int = 1024 * 1024  # 1MB
    
    # Custom settings (for extending projects)
    custom: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        extra = "allow"  # Allow additional fields for extensibility


class ConfigManager:
    """
    Configuration manager that supports environment variables,
    config files, and programmatic configuration.
    """
    
    def __init__(self, config_class: Type[APIConfig] = APIConfig):
        self.config_class = config_class
        self._config: Optional[APIConfig] = None
    
    def load_from_file(self, file_path: str) -> APIConfig:
        """Load configuration from a JSON file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {file_path}")
        
        with open(path, 'r') as f:
            config_data = json.load(f)
        
        return self.config_class(**config_data)
    
    def load_from_env(self, prefix: str = "LLMGINE_API_") -> APIConfig:
        """Load configuration from environment variables."""
        config_data : dict[str, Any] = {}
        
        # Map environment variables to config fields
        env_mapping = {
            f"{prefix}TITLE": "title",
            f"{prefix}DESCRIPTION": "description",
            f"{prefix}VERSION": "version",
            f"{prefix}HOST": "host",
            f"{prefix}PORT": "port",
            f"{prefix}DEBUG": "debug",
            f"{prefix}MAX_SESSIONS": "max_sessions",
            f"{prefix}SESSION_TIMEOUT": "session_timeout",
        }
        
        for env_var, field_name in env_mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                # Convert types as needed
                if field_name in ["port", "max_sessions", "session_timeout"]:
                    value = int(value)
                elif field_name == "debug":
                    value = value.lower() in ("true", "1", "yes", "on")
                
                config_data[field_name] = value
        
        return self.config_class(**config_data)
    
    def load_config(
        self, 
        config_file: Optional[str] = None,
        env_prefix: str = "LLMGINE_API_",
        override: Optional[Dict[str, Any]] = None
    ) -> APIConfig:
        """
        Load configuration from multiple sources with precedence:
        1. Override parameters (highest priority)
        2. Environment variables
        3. Config file
        4. Default values (lowest priority)
        """
        
        # Start with defaults
        config_data : dict[str, Any] = {}
        
        # Load from file if provided
        if config_file:
            try:
                file_config = self.load_from_file(config_file)
                config_data.update(file_config.model_dump())
            except FileNotFoundError:
                logger.warning(f"Config file not found: {config_file}, using defaults")
        
        # Override with environment variables
        try:
            env_config = self.load_from_env(env_prefix)
            # Only update with non-default env values
            env_dict = env_config.model_dump()
            default_dict = self.config_class().model_dump()
            
            for key, value in env_dict.items():
                if value != default_dict.get(key):
                    config_data[key] = value
        except Exception as e:
            logger.warning(f"Error loading environment config: {e}")
        
        # Apply final overrides
        if override:
            config_data.update(override)
        
        self._config = self.config_class(**config_data)
        return self._config
    
    @property
    def config(self) -> APIConfig:
        """Get the current configuration."""
        if self._config is None:
            self._config = self.load_config()
        return self._config


# Global config manager instance
config_manager = ConfigManager()