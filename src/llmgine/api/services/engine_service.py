"""
Service for managing the engine, singleton pattern
"""

from datetime import datetime, timedelta
import threading
import time
from typing import Optional

from llmgine.llm import EngineID, SessionID
from llmgine.llm.engine.engine import Engine, EngineStatus

#TODO Add logging

class EngineService:
    """
    Service for managing the engine, singleton pattern
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EngineService, cls).__new__(cls)
            cls._instance.__init__()
        return cls._instance

    def __init__(self):
        """
        Initialize the engine service
        - engines: dictionary of engine_id to engine
        - engine_registry: dictionary of session_id to engine_id
        - max_engines: maximum number of engines
        - idle_timeout: time in seconds after which an engine is marked as idle
        - delete_idle_timeout: time in seconds after which an idle engine is deleted
        - monitor_thread: thread for monitoring engines
        """
        # key: engine_id, value: engine
        self.engines : dict[EngineID, Engine] = {}
        # key: session_id, value: engine_id
        self.engine_registry : dict[SessionID, EngineID] = {}
        self.max_engines = 10
        self.idle_timeout = 3000 # 30 minutes
        self.delete_idle_timeout = 6000 # 60 minutes
        self.monitor_thread = threading.Thread(target=self.monitor_engines)
        self.monitor_thread.start()

    # --- Engine Management ---

    def get_all_engines(self) -> dict[EngineID, Engine]:
        """
        Get all engines
        """
        return self.engines


    def get_engine(self, engine_id: EngineID) -> Optional[Engine]:
        """
        Get an engine by its id
        """
        return self.engines.get(engine_id, None)


    def create_engine(self, engine: Engine) -> Optional[EngineID]:
        """
        Create an engine
        None is returned if the max number of engines is reached
        """
        if len(self.engines) >= self.max_engines:
            return None

        self.engines[engine.engine_id] = engine
        return engine.engine_id

    def delete_engine(self, engine_id: EngineID) -> None:
        """
        Delete an engine
        """
        self.engines.pop(engine_id, None)

    def update_engine_status(self, engine_id: EngineID, status: EngineStatus) -> None:
        """
        Update the status of an engine
        """
        if engine_id in self.engines:
            self.engines[engine_id].status = status

    def update_engine_last_interaction_at(self, engine_id: EngineID) -> None:
        """
        Update the last interaction time of an engine
        """
        if engine_id in self.engines:
            self.update_engine_status(engine_id, EngineStatus.RUNNING)
            self.engines[engine_id].updated_at = datetime.now()

    def set_engine_idle_timeout(self, idle_timeout: int) -> None:
        """
        Set the idle timeout for an engine
        """
        self.idle_timeout = idle_timeout

    def set_engine_delete_idle_timeout(self, delete_idle_timeout: int) -> None:
        """
        Set the delete idle timeout for an engine
        """
        self.delete_idle_timeout = delete_idle_timeout

    # --- Engine Registration ---

    def get_registered_engine(self, session_id: SessionID) -> Optional[Engine]:
        """
        Get the engine registered to a session
        """
        engine_id = self.engine_registry.get(session_id, None)
        if engine_id:
            return self.engines.get(engine_id)
        return None

    # TODO: Emit events when an engine is registered or unregistered, switched to another session or deleted
    def register_engine(self, session_id: SessionID, engine_id: EngineID) -> Optional[EngineID]:
        """
        Register an engine to a session
        """
        if engine_id not in self.engines:
            return None
        self.engine_registry[session_id] = engine_id
        return engine_id

    def unregister_engine(self, session_id: SessionID) -> Optional[EngineID]:
        """
        Unregister an engine from a session
        """
        return self.engine_registry.pop(session_id, None)

    # --- Engine Monitoring ---

    def monitor_engines(self) -> None:
        """
        Monitor engines and update their status to IDLE if they have not been interacted with in the last idle_timeout seconds
        and delete them if they have been idle for delete_idle_timeout seconds
        """
        while True:
            engine_ids = list(self.engines.keys())
            for engine_id in engine_ids:
                engine = self.engines[engine_id]
                if engine.status == EngineStatus.RUNNING and engine.updated_at < datetime.now() - timedelta(seconds=self.idle_timeout):
                    self.update_engine_status(engine_id, EngineStatus.IDLE)
                if engine.status == EngineStatus.IDLE and engine.updated_at < datetime.now() - timedelta(seconds=self.delete_idle_timeout):
                    self.delete_engine(engine_id)
            time.sleep(1)

