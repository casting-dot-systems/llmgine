"""
Example: Creating a custom engine with specialized WebSocket messages.

This example shows how another project can extend the API module
to create custom message types and handlers for their specific engine.
"""

from typing import Optional, Dict, Any
from fastapi import WebSocket
import uvicorn
from pydantic import BaseModel

from llmgineAPI.models.websocket import WSMessage, WSResponse
from llmgineAPI.websocket.base import BaseHandler
from llmgineAPI.core.extensibility import (
    ExtensibleAPIFactory, 
    EngineConfiguration
)



# 1. Define custom message types
class TranslateRequest(WSMessage):
    """Custom message for translation requests."""
    class TranslateRequestData(BaseModel):
        text: str
        target_language: str
        source_language: str = "auto"

    type: str = "translate"
    message_id: str
    data: TranslateRequestData



class TranslateResponse(WSResponse):
    """Custom response for translation results."""
    
    class TranslateResponseData(BaseModel):
        original_text: str
        translated_text: str
        detected_language: Optional[str] = None

    type: str = "translate_res"
    message_id: str
    data: TranslateResponseData


class AnalyzeTextRequest(WSMessage):
    """Custom message for text analysis requests."""
    
    class AnalyzeTextRequestData(BaseModel):
        text: str
        analysis_types: list[str]

    type: str = "analyze_text"
    message_id: str
    data: AnalyzeTextRequestData


class AnalyzeTextResponse(WSResponse):
    """Custom response for text analysis results."""
    
    class AnalyzeTextResponseData(BaseModel):
        text: str
        analysis_results: Dict[str, Any]

    type: str = "analyze_text_res"
    message_id: str
    data: AnalyzeTextResponseData


# 2. Define custom handlers
class TranslateHandler(BaseHandler):
    """Handler for translation requests."""
    
    @property
    def message_type(self) -> str:
        return "translate"
    
    @property
    def request_model(self) -> type[WSMessage]:
        return TranslateRequest
    
    async def handle(
        self, 
        message: Dict[str, Any], 
        websocket: WebSocket, 
    ) -> Optional[WSResponse]:
        """Handle translation request."""

        
        return TranslateResponse(
            type="translate_res",
            message_id=message["message_id"],
            data=TranslateResponse.TranslateResponseData(
                original_text=message["data"]["text"],
                translated_text=message["data"]["target_language"],
                detected_language=message["data"]["source_language"]
            )
        )


class AnalyzeTextHandler(BaseHandler):
    """Handler for text analysis requests."""
    
    @property
    def message_type(self) -> str:
        return "analyze_text"
    
    @property
    def request_model(self) -> type[WSMessage]:
        return AnalyzeTextRequest
    
    async def handle(
        self, 
        message: Dict[str, Any], 
        websocket: WebSocket, 
    ) -> Optional[WSResponse]:
        """Handle text analysis request."""
        
        return AnalyzeTextResponse(
            type="analyze_text_res",
            message_id=message["message_id"],
            data=AnalyzeTextResponse.AnalyzeTextResponseData(
                text=message["data"]["text"],
                analysis_results=message["data"]["analysis_types"]
            )
        )


# 3. Create custom engine configuration
class TranslationEngineConfig(EngineConfiguration):
    """Configuration for a translation engine."""
    
    engine_name: str = "TranslationEngine"
    supported_languages: list[str] = ["en", "es", "fr", "de", "it", "pt"]
    default_target_language: str = "en"
    enable_text_analysis: bool = True
    max_text_length: int = 5000


# 4. Factory function to create custom API
def create_translation_api():
    """
    Create a customized API instance for a translation engine.
    
    This is how other projects would use the API module:
    """
    
    # Create configuration
    config = TranslationEngineConfig(
        custom_settings={
            "translation_service_url": "https://api.translator.com",
            "api_key_env_var": "TRANSLATION_API_KEY"
        }
    )
    
    # Create API factory
    api_factory = ExtensibleAPIFactory(config)
    
    # Register custom handlers
    api_factory.register_custom_handler("translate", TranslateHandler)
    api_factory.register_custom_handler("analyze_text", AnalyzeTextHandler)
    
    # Get API metadata
    metadata = api_factory.get_api_metadata()
    print(f"Created API for {metadata['engine_name']}")
    print(f"Custom message types: {metadata['custom_message_types']}")
    
    return api_factory


# Usage example:
if __name__ == "__main__":
    # This is how another project would extend the API
    translation_api = create_translation_api()
    
    # The project would then use this in their main.py:
    from llmgineAPI.main import create_app
    app = create_app(api_factory=translation_api)
    uvicorn.run(app, host="127.0.0.1", port=8000)