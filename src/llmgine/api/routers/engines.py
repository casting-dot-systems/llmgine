"""
Engine management router for the LLMGine API.

This router handles engine lifecycle and session association including:
- Creating new engines
- Listing all active engines 
- Retrieving engine details and status
- Connecting engines to sessions
- Disconnecting engines from sessions
"""

from typing import Optional
from fastapi import APIRouter, Depends, Path, Query

from llmgine.api.services.engine_service import EngineService
from llmgine.api.utils.error_handler import (
    EngineNotFoundError,
    EngineConnectionError,
    ResourceLimitError,
    ValidationError,
    handle_api_error,
    handle_unexpected_error
)
from llmgine.llm import EngineID, SessionID
from llmgine.api.models import (EngineCreateResponse, 
                                ResponseStatus, 
                                EngineListResponse, 
                                EngineFetchResponse, 
                                EngineConnectResponse, 
                                EngineDisconnectResponse, 
                                EngineConnectRequest)
from llmgine.llm.engine.engine import Engine
from llmgine.api.routers.dependencies import get_engine_service, validate_session

router = APIRouter(prefix="/api/sessions/{session_id}/engines", tags=["engines"])



@router.post("/", response_model=EngineCreateResponse, status_code=201)
async def create_engine(
    engine: Engine,
    session_id: str = Path(..., description="Session ID to associate with the engine"),
    engine_service: EngineService = Depends(get_engine_service),
    _: SessionID = Depends(validate_session)
) -> EngineCreateResponse:
    """
    Create a new engine for the specified session.
    
    Creates a new engine instance and associates it with the session.
    The engine will be available for connection and command execution.
    
    Args:
        session_id: The session ID to associate with the engine
        engine: The engine configuration and instance
        
    Returns:
        EngineCreateResponse: Contains the new engine ID and status
        
    Raises:
        ResourceLimitError: When maximum engine limit is reached
    """

    try:
        engine_id: Optional[EngineID] = engine_service.create_engine(engine)

        if engine_id is None:
            raise ResourceLimitError("engines", engine_service.max_engines)
        
        return EngineCreateResponse(
            engine_id=str(engine_id),
            status=ResponseStatus.SUCCESS,
            message="Engine created successfully"
        )
        
    except ResourceLimitError as e:
        raise handle_api_error(e)
    except Exception as e:
        raise handle_unexpected_error(e, {"operation": "create_engine", "session_id": session_id})

@router.get("/", response_model=EngineListResponse, status_code=200)
async def list_engines(
    session_id: str = Path(..., description="Session ID to filter engines"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of engines to return"),
    offset: int = Query(0, ge=0, description="Number of engines to skip"),
    engine_service: EngineService = Depends(get_engine_service),
    _: SessionID = Depends(validate_session)
) -> EngineListResponse:
    """
    List all active engines with pagination.
    
    Retrieves all engines in the system with optional pagination.
    Note: This returns all engines, not just those associated with the session.
    
    Args:
        session_id: The session ID (for validation)
        limit: Maximum number of engines to return (1-100)
        offset: Number of engines to skip for pagination
        
    Returns:
        EngineListResponse: List of engines with pagination metadata
    """
    try:
        # Check limit and offset range
        if limit < 1 or limit > 100:
            raise ValidationError("limit", "Limit must be between 1 and 100", limit)
        if offset < 0:
            raise ValidationError("offset", "Offset must be greater than or equal to 0", offset)


        all_engines = engine_service.get_all_engines()
        
        # Convert to list for pagination
        engines_list = list(all_engines.values())
        
        # Apply pagination
        total = len(engines_list)
        paginated_engines = engines_list[offset:offset + limit]
        
        return EngineListResponse(
            engines=paginated_engines,
            total=total,
            limit=limit,
            offset=offset,
            status=ResponseStatus.SUCCESS,
            message=f"Engines listed successfully, from {offset} to {offset + limit} of {total}"
        )
        
    except Exception as e:
        raise handle_unexpected_error(e, {"operation": "list_engines", "session_id": session_id})

@router.get("/{engine_id}", response_model=EngineFetchResponse, status_code=200)
async def get_engine(
    session_id: str = Path(..., description="Session ID for validation"),
    engine_id: str = Path(..., description="Engine ID to retrieve"),
    engine_service: EngineService = Depends(get_engine_service),
    _: SessionID = Depends(validate_session),
) -> EngineFetchResponse:
    """
    Get detailed information about a specific engine.
    
    Args:
        session_id: The session ID (for validation)
        engine_id: Unique identifier of the engine to retrieve
        
    Returns:
        EngineFetchResponse: Engine details and status
        
    Raises:
        EngineNotFoundError: When engine doesn't exist
    """
    try:
        engine: Optional[Engine] = engine_service.get_engine(EngineID(engine_id))

        if engine is None:
            raise EngineNotFoundError(engine_id)
        
        return EngineFetchResponse(
            engine=engine,
            status=ResponseStatus.SUCCESS,
            message="Engine fetched successfully"
        )
        
    except EngineNotFoundError as e:
        raise handle_api_error(e)
    except Exception as e:
        raise handle_unexpected_error(e, {"operation": "get_engine", "session_id": session_id, "engine_id": engine_id})
    
@router.post("/connect", response_model=EngineConnectResponse, status_code=200)
async def connect_engine(
    engine_connect_request: EngineConnectRequest,
    session_id: str = Path(..., description="Session ID to connect the engine to"),
    engine_service: EngineService = Depends(get_engine_service),
    _: SessionID = Depends(validate_session)
) -> EngineConnectResponse:
    """
    Connect an engine to the specified session.
    
    Associates an existing engine with a session, allowing the session
    to send commands to the engine and receive responses.
    
    Args:
        session_id: The session ID to connect the engine to
        engine_connect_request: Request containing the engine ID to connect
        
    Returns:
        EngineConnectResponse: Confirmation of engine connection
        
    Raises:
        EngineNotFoundError: When engine doesn't exist
        EngineConnectionError: When engine connection fails
    """
    try:
        engine_id: Optional[EngineID] = engine_service.register_engine(
            SessionID(session_id), 
            EngineID(engine_connect_request.engine_id)
        )
        
        if engine_id is None:
            raise EngineConnectionError(
                engine_connect_request.engine_id,
                "Engine not found or already connected to another session"
            )
        
        return EngineConnectResponse(
            engine_id=str(engine_id),
            status=ResponseStatus.SUCCESS,
            message="Engine connected successfully"
        )
        
    except EngineConnectionError as e:
        raise handle_api_error(e)
    except Exception as e:
        raise handle_unexpected_error(e, {
            "operation": "connect_engine",
            "session_id": session_id,
            "engine_id": engine_connect_request.engine_id
        })
    
@router.delete("/disconnect", response_model=EngineDisconnectResponse, status_code=200)
async def disconnect_engine(
    session_id: str = Path(..., description="Session ID to disconnect the engine from"),
    engine_service: EngineService = Depends(get_engine_service),
    _: SessionID = Depends(validate_session)
) -> EngineDisconnectResponse:
    """
    Disconnect the engine from the specified session.
    
    Removes the association between the session and its connected engine.
    The engine remains available for connection to other sessions.
    
    Args:
        session_id: The session ID to disconnect the engine from
        
    Returns:
        EngineDisconnectResponse: Confirmation of engine disconnection
        
    Raises:
        EngineConnectionError: When no engine is connected to the session
    """
    try:
        engine_id: Optional[EngineID] = engine_service.unregister_engine(SessionID(session_id))

        if engine_id is None:
            raise EngineConnectionError(
                "unknown",
                f"No engine is connected to session {session_id}"
            )
        
        return EngineDisconnectResponse(
            engine_id=str(engine_id),
            status=ResponseStatus.SUCCESS,
            message="Engine disconnected successfully"
        )
        
    except EngineConnectionError as e:
        raise handle_api_error(e)
    except Exception as e:
        raise handle_unexpected_error(e, {"operation": "disconnect_engine", "session_id": session_id})
