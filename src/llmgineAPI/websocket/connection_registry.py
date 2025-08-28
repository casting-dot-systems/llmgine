"""
WebSocket connection registry for tracking active connections.

This module provides a thread-safe registry for managing WebSocket connections,
allowing the server to send messages to specific clients and track connection metadata.
"""

from typing import Dict, Set, Optional, List
from threading import RLock
from dataclasses import dataclass, field
from datetime import datetime
import logging
from fastapi import WebSocket

from llmgine.llm import SessionID

logger = logging.getLogger(__name__)


@dataclass
class ConnectionMetadata:
    """Metadata for a WebSocket connection."""
    app_id: str
    websocket: WebSocket
    session_ids: Set[SessionID] = field(default_factory=set)
    connected_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    
    def add_session(self, session_id: SessionID) -> None:
        """Add a session to this connection."""
        self.session_ids.add(session_id)
        self.last_activity = datetime.now()
    
    def remove_session(self, session_id: SessionID) -> None:
        """Remove a session from this connection."""
        self.session_ids.discard(session_id)
        self.last_activity = datetime.now()
    
    def update_activity(self) -> None:
        """Update the last activity timestamp."""
        self.last_activity = datetime.now()


class ConnectionRegistry:
    """
    Thread-safe registry for managing WebSocket connections.
    
    This registry allows the server to:
    - Track active WebSocket connections by app_id
    - Send messages to specific connections
    - Manage connection metadata and session associations
    - Provide connection health and diagnostic information
    """
    
    def __init__(self):
        self._connections: Dict[str, ConnectionMetadata] = {}
        self._session_to_app: Dict[SessionID, str] = {}
        self._lock = RLock()
    
    def register_connection(
        self, 
        app_id: str, 
        websocket: WebSocket
    ) -> None:
        """
        Register a new WebSocket connection.
        
        Args:
            app_id: Unique identifier for the frontend application
            websocket: The WebSocket connection object
        """
        with self._lock:
            if app_id in self._connections:
                logger.warning(f"App {app_id} already has a registered connection. Replacing.")
            
            metadata = ConnectionMetadata(app_id=app_id, websocket=websocket)
            self._connections[app_id] = metadata
            logger.info(f"Registered WebSocket connection for app {app_id}")
    
    def unregister_connection(self, app_id: str) -> Optional[ConnectionMetadata]:
        """
        Unregister a WebSocket connection.
        
        Args:
            app_id: The app ID to unregister
            
        Returns:
            The connection metadata if it existed, None otherwise
        """
        with self._lock:
            metadata = self._connections.pop(app_id, None)
            if metadata:
                # Clean up session mappings
                for session_id in metadata.session_ids.copy():
                    self._session_to_app.pop(session_id, None)
                logger.info(f"Unregistered WebSocket connection for app {app_id}")
            else:
                logger.warning(f"Attempted to unregister non-existent app {app_id}")
            return metadata
    
    def get_connection(self, app_id: str) -> Optional[ConnectionMetadata]:
        """
        Get connection metadata for an app ID.
        
        Args:
            app_id: The app ID to look up
            
        Returns:
            Connection metadata if found, None otherwise
        """
        with self._lock:
            metadata = self._connections.get(app_id)
            if metadata:
                metadata.update_activity()
            return metadata
    
    def get_connection_by_session(self, session_id: SessionID) -> Optional[ConnectionMetadata]:
        """
        Get connection metadata for a session ID.
        
        Args:
            session_id: The session ID to look up
            
        Returns:
            Connection metadata if found, None otherwise
        """
        with self._lock:
            app_id = self._session_to_app.get(session_id)
            if app_id:
                return self.get_connection(app_id)
            return None
    
    def get_all_connections(self) -> Dict[str, ConnectionMetadata]:
        """
        Get all active connections.
        
        Returns:
            Dictionary of app_id -> ConnectionMetadata
        """
        with self._lock:
            return self._connections.copy()
    
    def register_session_to_app(self, app_id: str, session_id: SessionID) -> bool:
        """
        Associate a session with an app connection.
        
        Args:
            app_id: The app ID
            session_id: The session ID to associate
            
        Returns:
            True if successful, False if app not found
        """
        with self._lock:
            metadata = self._connections.get(app_id)
            if metadata:
                metadata.add_session(session_id)
                self._session_to_app[session_id] = app_id
                logger.info(f"Associated session {session_id} with app {app_id}")
                return True
            else:
                logger.warning(f"Cannot associate session {session_id} - app {app_id} not found")
                return False
    
    def unregister_session_from_app(self, app_id: str, session_id: SessionID) -> bool:
        """
        Remove session association from an app connection.
        
        Args:
            app_id: The app ID
            session_id: The session ID to remove
            
        Returns:
            True if successful, False if app not found
        """
        with self._lock:
            metadata = self._connections.get(app_id)
            if metadata:
                metadata.remove_session(session_id)
                self._session_to_app.pop(session_id, None)
                logger.info(f"Removed session {session_id} from app {app_id}")
                return True
            else:
                logger.warning(f"Cannot remove session {session_id} - app {app_id} not found")
                return False
    
    def get_app_sessions(self, app_id: str) -> Set[SessionID]:
        """
        Get all session IDs associated with an app.
        
        Args:
            app_id: The app ID
            
        Returns:
            Set of session IDs (empty if app not found)
        """
        with self._lock:
            metadata = self._connections.get(app_id)
            return metadata.session_ids.copy() if metadata else set()
    
    def get_connection_count(self) -> int:
        """Get the total number of active connections."""
        with self._lock:
            return len(self._connections)
    
    def get_session_count(self) -> int:
        """Get the total number of active sessions across all connections."""
        with self._lock:
            return len(self._session_to_app)
    
    def get_health_info(self) -> Dict[str, any]:
        """
        Get health and diagnostic information about connections.
        
        Returns:
            Dictionary with connection health metrics
        """
        with self._lock:
            now = datetime.now()
            connections_info = []
            
            for app_id, metadata in self._connections.items():
                connection_age = (now - metadata.connected_at).total_seconds()
                idle_time = (now - metadata.last_activity).total_seconds()
                
                connections_info.append({
                    "app_id": app_id,
                    "session_count": len(metadata.session_ids),
                    "connected_at": metadata.connected_at.isoformat(),
                    "last_activity": metadata.last_activity.isoformat(),
                    "connection_age_seconds": connection_age,
                    "idle_time_seconds": idle_time
                })
            
            return {
                "total_connections": len(self._connections),
                "total_sessions": len(self._session_to_app),
                "connections": connections_info
            }
        
    def get_app_id_by_session(self, session_id: SessionID) -> Optional[str]:
        """
        Get the app ID for a session ID.
        """
        with self._lock:
            return self._session_to_app.get(session_id)
    
    def cleanup_stale_connections(self, max_idle_seconds: int = 3600) -> List[str]:
        """
        Clean up connections that have been idle for too long.
        
        Args:
            max_idle_seconds: Maximum idle time before considering connection stale
            
        Returns:
            List of app_ids that were cleaned up
        """
        with self._lock:
            now = datetime.now()
            stale_apps = []
            
            for app_id, metadata in list(self._connections.items()):
                idle_time = (now - metadata.last_activity).total_seconds()
                if idle_time > max_idle_seconds:
                    stale_apps.append(app_id)
                    logger.info(f"Cleaning up stale connection for app {app_id} (idle for {idle_time:.1f}s)")
                    self.unregister_connection(app_id)
            
            return stale_apps


# Global registry instance
_global_registry: Optional[ConnectionRegistry] = None
_registry_lock = RLock()


def get_connection_registry() -> ConnectionRegistry:
    """
    Get the global connection registry instance.
    
    Returns:
        The global ConnectionRegistry instance
    """
    global _global_registry
    with _registry_lock:
        if _global_registry is None:
            _global_registry = ConnectionRegistry()
            logger.info("Initialized global connection registry")
        return _global_registry


def reset_connection_registry() -> None:
    """Reset the global connection registry (for testing)."""
    global _global_registry
    with _registry_lock:
        _global_registry = None
        logger.info("Reset global connection registry")