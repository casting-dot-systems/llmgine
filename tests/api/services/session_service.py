import asyncio
import pytest

from llmgine.api.services.session_service import SessionService, SessionStatus


def test_session_service_singleton():
    """Test that SessionService follows singleton pattern"""
    session_service = SessionService()
    session_service2 = SessionService()
    assert session_service is not None
    assert session_service is session_service2

def test_session_service_create_and_get_session():
    """Test creating and getting a session"""
    session_service = SessionService()
    session_id = session_service.create_session()
    assert session_id is not None
    assert session_service.get_session(session_id) is not None
    assert session_service.get_all_sessions() == {session_id: session_service.get_session(session_id)}

@pytest.mark.asyncio
async def test_session_service_update_session_last_interaction_at():
    """Test updating the last interaction time of a session"""
    session_service = SessionService()
    session_id = session_service.create_session()
    assert session_id is not None

    session = session_service.get_session(session_id)
    assert session is not None
    last_interaction_at = session.last_interaction_at
    await asyncio.sleep(1)
    session_service.update_session_last_interaction_at(session_id)
    session = session_service.get_session(session_id)
    assert session is not None
    assert session.last_interaction_at > last_interaction_at

def test_session_service_update_session_status():
    """Test updating the status of a session"""
    session_service = SessionService()
    session_id = session_service.create_session()
    assert session_id is not None
    session_service.update_session_status(session_id, SessionStatus.RUNNING)
    session = session_service.get_session(session_id)
    assert session is not None
    assert session.status == SessionStatus.RUNNING
    session_service.update_session_status(session_id, SessionStatus.IDLE)
    session = session_service.get_session(session_id)
    assert session is not None
    assert session.status == SessionStatus.IDLE

def test_session_service_delete_session():
    """Test deleting a session"""
    session_service = SessionService()
    session_id = session_service.create_session()
    assert session_service.get_session(session_id) is not None
    session_service.delete_session(session_id)
    assert session_service.get_session(session_id) is None

@pytest.mark.asyncio
async def test_session_service_monitor_sessions():
    """Test monitoring sessions"""
    session_service = SessionService()
    session_service.set_session_idle_timeout(1)
    session_service.set_session_delete_idle_timeout(5)

    session_id = session_service.create_session()
    assert session_id is not None

    session = session_service.get_session(session_id)
    assert session is not None
    assert session.status == SessionStatus.RUNNING

    await asyncio.sleep(3)
    session = session_service.get_session(session_id)
    assert session is not None
    assert session.status == SessionStatus.IDLE
    await asyncio.sleep(5)
    assert session_service.get_session(session_id) is None
    
