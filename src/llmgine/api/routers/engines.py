"""
Engine management router for the LLMGine API.

This router handles:
- Creating a new engine
- Listing all active engines
- Getting engine details and status
- Connecting to an engine
- Disconnecting from an engine
"""

from typing import Optional
from fastapi import APIRouter, Depends

from llmgine.api.services.engine_service import EngineService
from llmgine.llm import EngineID, SessionID
from llmgine.api.models import (EngineCreateResponse, 
                                ResponseStatus, 
                                EngineListResponse, 
                                EngineFetchResponse, 
                                EngineConnectResponse, 
                                EngineDisconnectResponse, 
                                EngineConnectRequest)
from llmgine.llm.engine.engine import Engine
from llmgine.api.routers.dependencies import get_engine_service

router = APIRouter(prefix="/api/sessions/{session_id}/engines", tags=["engines"])



@router.post("/create", response_model=EngineCreateResponse, status_code=201)
async def create_engine(
    engine: Engine,
    engine_service: EngineService = Depends(get_engine_service)
) -> EngineCreateResponse:
    """
    Create a new engine
    """
    engine_id : Optional[EngineID] = engine_service.create_engine(engine)

    if engine_id is None:
        return EngineCreateResponse(
            engine_id=str(engine_id),
            status=ResponseStatus.FAILED,
            error=f"Failed to create engine: Max engines reached"
        )
    else:
        return EngineCreateResponse(
            engine_id=str(engine_id),
            status=ResponseStatus.SUCCESS
        )

@router.get("/", response_model=EngineListResponse, status_code=200)
async def get_engines(
    engine_service: EngineService = Depends(get_engine_service)
) -> EngineListResponse:
    """
    Get all active engines
    """

    engines = engine_service.get_all_engines()
    return EngineListResponse(engines=engines, status=ResponseStatus.SUCCESS)

@router.get("/{engine_id}", response_model=EngineFetchResponse, status_code=200)
async def get_engine(
    engine_id: str,
    engine_service: EngineService = Depends(get_engine_service)
) -> EngineFetchResponse:
    """
    Get an engine by its id
    """
    engine : Optional[Engine] = engine_service.get_engine(EngineID(engine_id))

    if engine is None:
        return EngineFetchResponse(
            engine=None,
            status=ResponseStatus.FAILED,
            error=f"Engine {engine_id} not found"
        )
    else:
        return EngineFetchResponse(
            engine=engine,
            status=ResponseStatus.SUCCESS
        )
    
@router.post("/connect", response_model=EngineConnectResponse, status_code=200)
async def connect_engine(
    session_id: str,
    engine_connect_request: EngineConnectRequest,
    engine_service: EngineService = Depends(get_engine_service)
) -> EngineConnectResponse:
    """
    Connect to an engine
    """
    engine_id : Optional[EngineID] = engine_service.register_engine(SessionID(session_id), 
                                                                    EngineID(engine_connect_request.engine_id))
    if engine_id is None:
        return EngineConnectResponse(
            engine_id=str(engine_id),
            status=ResponseStatus.FAILED,
            error=f"Engine {engine_id} not found or already connected to a session"
        )
    else:
        return EngineConnectResponse(
            engine_id=str(engine_id),
            status=ResponseStatus.SUCCESS
        )
    
@router.post("/disconnect", response_model=EngineDisconnectResponse, status_code=200)
async def disconnect_engine(
    session_id: str,
    engine_service: EngineService = Depends(get_engine_service)
) -> EngineDisconnectResponse:
    """
    Disconnect from an engine
    """
    engine_id : Optional[EngineID] = engine_service.unregister_engine(SessionID(session_id))

    if engine_id is None:
        return EngineDisconnectResponse(
            engine_id=str(engine_id),
            status=ResponseStatus.FAILED,
            error=f"Engine {engine_id} not found or not connected to a session"
        )
    else:
        return EngineDisconnectResponse(
            engine_id=str(engine_id),
            status=ResponseStatus.SUCCESS
        )
