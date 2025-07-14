import asyncio
import pytest

from llmgine.llm import SessionID, EngineID
from llmgine.llm.engine.engine import DummyEngine, EngineStatus
from llmgine.api.services.engine_service import EngineService


def test_engine_service_singleton():
    """Test that EngineService follows singleton pattern"""
    engine_service = EngineService()
    engine_service2 = EngineService()
    assert engine_service is not None
    assert engine_service is engine_service2


@pytest.mark.asyncio
async def test_engine_service_get_all_engines():
    """Test getting all engines from the service"""
    engine_service = EngineService()
    engine = DummyEngine(EngineID("123"), SessionID("123"))
    engine_id = engine_service.create_engine(engine)
    assert engine_id is not None
    assert engine_service.get_engine(engine_id) is not None
    assert engine_service.get_all_engines() == {engine_id: engine}
    assert engine_service.get_engine(engine_id) == engine


@pytest.mark.asyncio
async def test_engine_service_create_and_delete_engine():
    """Test creating and deleting an engine"""
    engine_service = EngineService()
    engine = DummyEngine(EngineID("456"), SessionID("456"))
    
    # Create engine
    engine_id = engine_service.create_engine(engine)
    assert engine_id is not None
    assert engine_service.get_engine(engine_id) == engine
    
    # Delete engine
    engine_service.delete_engine(engine_id)
    assert engine_service.get_engine(engine_id) is None


@pytest.mark.asyncio
async def test_engine_service_register_and_unregister_engine():
    """Test registering an engine with a session"""
    engine_service = EngineService()
    engine = DummyEngine(EngineID("789"), SessionID("789"))
    engine_id = engine_service.create_engine(engine)
    session_id = "test-session-123"
    
    # Register engine with session
    engine_service.register_engine(session_id, engine_id)
    registered_engine = engine_service.get_registered_engine(session_id)
    assert registered_engine == engine
    
    # Unregister engine
    engine_service.unregister_engine(session_id)
    assert engine_service.get_registered_engine(session_id) is None

@pytest.mark.asyncio
async def test_engine_service_monitor_engines():
    """Test monitoring engines"""
    engine_service = EngineService()
    engine_service.set_engine_idle_timeout(1)
    engine_service.set_engine_delete_idle_timeout(5)

    engine_id = engine_service.create_engine(DummyEngine(EngineID("123"), SessionID("123")))
    assert engine_service.get_engine(engine_id) is not None
    assert engine_service.get_engine(engine_id).status == EngineStatus.RUNNING
    await asyncio.sleep(3)
    assert engine_service.get_engine(engine_id).status == EngineStatus.IDLE
    await asyncio.sleep(5)
    assert engine_service.get_engine(engine_id) is None