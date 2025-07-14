"""
Service for managing sessions, singleton pattern
"""

from datetime import datetime, timedelta
from enum import Enum
import threading
import time
from typing import Optional
import uuid

from llmgine.llm import SessionID

#TODO Add logging

class SessionStatus(Enum):
    RUNNING = "running"
    FAILED = "failed"
    IDLE = "idle"

class Session:
    def __init__(self):
        self.session_id: SessionID = SessionID(str(uuid.uuid4()))
        self.status: SessionStatus = SessionStatus.RUNNING
        self.created_at: datetime = datetime.now()
        self.last_interaction_at: datetime = datetime.now()

    def update_last_interaction_at(self):
        self.last_interaction_at = datetime.now()

    def get_session_id(self) -> SessionID:
        return self.session_id

    def get_status(self) -> SessionStatus:
        return self.status

    def update_status(self, status: SessionStatus):
        self.status = status

class SessionService:
    """
    Service for managing sessions, singleton pattern
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SessionService, cls).__new__(cls)
            cls._instance.__init__()
        return cls._instance
    
    def __init__(self):
        """
        Initialize the session service
        - sessions: dictionary of session_id to session
        - idle_timeout: time in seconds after which a session is marked as idle
        - delete_idle_timeout: time in seconds after which an idle session is deleted
        - monitor_thread: thread for monitoring sessions
        """
        self.sessions : dict[SessionID, Session] = {}
        self.max_sessions = 100
        self.idle_timeout = 300 # 5 minutes
        self.delete_idle_timeout = 600 # 10 minutes
        self.monitor_thread = threading.Thread(target=self.monitor_sessions)
        self.monitor_thread.start()

    def create_session(self):
        """
        Create a session
        """
        if len(self.sessions) >= self.max_sessions:
            raise ValueError(f"Max sessions reached: {self.max_sessions}")
        session = Session()
        self.sessions[session.get_session_id()] = session
        return session.get_session_id()

    def update_session_last_interaction_at(self, session_id: SessionID):
        """
        Update the last interaction time of a session
        """
        if session_id in self.sessions:
            self.sessions[session_id].update_last_interaction_at()

    def get_session(self, session_id: SessionID) -> Optional[Session]:
        """
        Get a session by its id
        """
        if session_id in self.sessions:
            return self.sessions[session_id]
        return None

    def get_all_sessions(self) -> dict[SessionID, Session]:
        """
        Get all sessions
        """
        return self.sessions
    
    def delete_session(self, session_id: SessionID):
        """
        Delete a session
        """
        if session_id in self.sessions:
            self.sessions.pop(session_id)

    def update_session_status(self, session_id: SessionID, status: SessionStatus):
        """
        Update the status of a session
        """
        if session_id in self.sessions:
            self.sessions[session_id].update_status(status)

    def set_session_idle_timeout(self, idle_timeout: int):
        """
        Set the idle timeout for a session
        """
        self.idle_timeout = idle_timeout

    def set_session_delete_idle_timeout(self, delete_idle_timeout: int):
        """
        Set the delete idle timeout for a session
        """
        self.delete_idle_timeout = delete_idle_timeout

    def monitor_sessions(self):
        """
        Monitor sessions and update their status to IDLE if they have not been interacted with in the last idle_timeout seconds
        and delete them if they have been idle for delete_idle_timeout seconds
        """
        while True:
            session_ids = list(self.sessions.keys())
            
            for session_id in session_ids:
                session = self.sessions[session_id]

                # Check if session should be marked as idle
                if session.get_status() == SessionStatus.RUNNING and session.last_interaction_at < datetime.now() - timedelta(seconds=self.idle_timeout):
                    session.update_status(SessionStatus.IDLE)
                
                # Check if session should be deleted
                if session.get_status() == SessionStatus.IDLE and session.last_interaction_at < datetime.now() - timedelta(seconds=self.delete_idle_timeout):
                    self.delete_session(session_id)
                    
            time.sleep(1)
