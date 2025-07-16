from typing import Optional
from pydantic import BaseModel

from llmgine.api.models.responses import ResponseStatus
from llmgine.llm import EngineID
from llmgine.llm.engine.engine import Engine

class EngineCreateResponse(BaseModel):
    """Response model for engine creation"""
    engine_id: str
    status: ResponseStatus
    message: str
    error: Optional[str] = None

class EngineListResponse(BaseModel):
    """Response model for engine list"""
    engines: list[Engine]
    total: int
    limit: int
    offset: int
    status: ResponseStatus
    message: str
    error: Optional[str] = None

class EngineFetchResponse(BaseModel):
    """Response model for engine fetch"""
    engine: Optional[Engine]
    status: ResponseStatus
    message: str
    error: Optional[str] = None

class EngineConnectRequest(BaseModel):
    """Request model for engine connect"""
    engine_id: str

class EngineConnectResponse(BaseModel):
    """Response model for engine connect"""
    engine_id: str
    status: ResponseStatus
    message: str
    error: Optional[str] = None

class EngineDisconnectResponse(BaseModel):
    """Response model for engine disconnect"""
    engine_id: str
    status: ResponseStatus
    message: str
    error: Optional[str] = None