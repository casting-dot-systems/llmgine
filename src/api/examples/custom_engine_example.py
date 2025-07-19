"""
Example: Creating a custom engine with specialized WebSocket messages.

This example shows how another project can extend the API module
to create custom message types and handlers for their specific engine.
"""

from typing import Optional, Dict, Any
from fastapi import WebSocket
import uvicorn

from api.models.websocket import WSMessage, WSResponse
from api.websocket.base import BaseHandler
from api.core.extensibility import (
    CustomMessageMixin, 
    ExtensibleAPIFactory, 
    EngineConfiguration
)
from llmgine.llm import SessionID


# 1. Define custom message types
class TranslateRequest(WSMessage, CustomMessageMixin):
    """Custom message for translation requests."""
    
    def __init__(self, text: str, target_language: str, source_language: str = "auto"):
        super().__init__(
            type="translate",
            data={
                "text": text,
                "target_language": target_language,
                "source_language": source_language
            }
        )


class TranslateResponse(WSResponse):
    """Custom response for translation results."""
    
    def __init__(self, original_text: str, translated_text: str, detected_language: Optional[str] = None):
        super().__init__(
            type="translate_res",
            data={
                "original_text": original_text,
                "translated_text": translated_text,
                "detected_language": detected_language
            }
        )


class AnalyzeTextRequest(WSMessage, CustomMessageMixin):
    """Custom message for text analysis requests."""
    
    def __init__(self, text: str, analysis_types: list[str]):
        super().__init__(
            type="analyze_text",
            data={
                "text": text,
                "analysis_types": analysis_types  # e.g., ["sentiment", "entities", "summary"]
            }
        )


class AnalyzeTextResponse(WSResponse):
    """Custom response for text analysis results."""
    
    def __init__(self, text: str, analysis_results: Dict[str, Any]):
        super().__init__(
            type="analyze_text_res",
            data={
                "text": text,
                "analysis_results": analysis_results
            }
        )


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
        message: WSMessage, 
        websocket: WebSocket, 
        session_id: SessionID
    ) -> Optional[WSResponse]:
        """Handle translation request."""
        # Extract data from message
        text = message.data["text"]
        target_lang = message.data["target_language"]
        source_lang = message.data.get("source_language", "auto")
        
        # TODO: Implement actual translation logic here
        # For demo purposes, we'll just return a mock translation
        translated_text = f"[{target_lang.upper()}] {text}"
        detected_language = "en" if source_lang == "auto" else source_lang
        
        return TranslateResponse(
            original_text=text,
            translated_text=translated_text,
            detected_language=detected_language
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
        message: WSMessage, 
        websocket: WebSocket, 
        session_id: SessionID
    ) -> Optional[WSResponse]:
        """Handle text analysis request."""
        text = message.data["text"]
        analysis_types = message.data["analysis_types"]
        
        # TODO: Implement actual analysis logic here
        # For demo purposes, return mock analysis results
        analysis_results = {}
        
        if "sentiment" in analysis_types:
            analysis_results["sentiment"] = {
                "score": 0.8,
                "label": "positive",
                "confidence": 0.95
            }
        
        if "entities" in analysis_types:
            analysis_results["entities"] = [
                {"text": "example", "label": "MISC", "start": 0, "end": 7}
            ]
        
        if "summary" in analysis_types:
            analysis_results["summary"] = f"Summary of: {text[:50]}..."
        
        return AnalyzeTextResponse(
            text=text,
            analysis_results=analysis_results
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
    from api.main import create_app
    app = create_app(api_factory=translation_api)
    uvicorn.run(app, host="127.0.0.1", port=8000)