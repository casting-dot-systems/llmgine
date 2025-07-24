"""
Connection management service for WebSocket connections.

This service provides high-level operations for managing WebSocket connections,
sending messages, and monitoring connection health.
"""

from typing import Dict, Set, List, Optional, Any
import logging
from datetime import datetime, timedelta

from llmgine.llm import SessionID
from llmgineAPI.websocket.connection_registry import ConnectionRegistry, get_connection_registry
from llmgineAPI.core.messaging_api import (
    ServerMessagingAPI, MessagingAPIWithEvents, 
    MessagingError, ConnectionNotFoundError
)
from llmgineAPI.models.websocket import NotificationMessage, ServerRequest

logger = logging.getLogger(__name__)


class ConnectionService:
    """
    High-level service for managing WebSocket connections and messaging.
    
    This service provides convenient methods for:
    - Sending messages to individual connections or groups
    - Broadcasting messages
    - Monitoring connection health
    - Managing connection lifecycle
    """
    
    def __init__(
        self, 
        connection_registry: Optional[ConnectionRegistry] = None,
        messaging_api: Optional[MessagingAPIWithEvents] = None
    ):
        self.connection_registry = connection_registry or get_connection_registry()
        self.messaging_api = messaging_api or MessagingAPIWithEvents(self.connection_registry)
    
    # Connection Management
    
    def get_connection_count(self) -> int:
        """Get the total number of active connections."""
        return self.connection_registry.get_connection_count()
    
    def get_session_count(self) -> int:
        """Get the total number of active sessions."""
        return self.connection_registry.get_session_count()
    
    def get_connected_apps(self) -> List[str]:
        """Get list of all connected app IDs."""
        return self.messaging_api.get_connected_apps()
    
    def is_app_connected(self, app_id: str) -> bool:
        """Check if a specific app is connected."""
        return self.messaging_api.is_app_connected(app_id)
    
    def get_app_sessions(self, app_id: str) -> Set[SessionID]:
        """Get all sessions for a specific app."""
        return self.messaging_api.get_app_sessions(app_id)
    
    def get_app_info(self, app_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific app connection.
        
        Args:
            app_id: The app identifier
            
        Returns:
            Dictionary with app information or None if not found
        """
        connection = self.connection_registry.get_connection(app_id)
        if not connection:
            return None
        
        return {
            "app_id": app_id,
            "connected_at": connection.connected_at.isoformat(),
            "last_activity": connection.last_activity.isoformat(),
            "session_count": len(connection.session_ids),
            "session_ids": [str(sid) for sid in connection.session_ids],
            "connection_age_seconds": (datetime.now() - connection.connected_at).total_seconds(),
            "idle_time_seconds": (datetime.now() - connection.last_activity).total_seconds()
        }
    
    # Messaging Operations
    
    async def send_notification(
        self,
        app_id: str,
        notification_type: str,
        message: str,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send a notification to a specific app.
        
        Args:
            app_id: Target app identifier
            notification_type: Type of notification
            message: Notification message
            additional_data: Optional additional data
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            await self.messaging_api.send_to_app(
                app_id=app_id,
                message_type="notification",
                data={
                    "notification_type": notification_type,
                    "message": message,
                    "additional_data": additional_data or {}
                }
            )
            logger.info(f"Sent notification to app {app_id}: {notification_type}")
            return True
        except ConnectionNotFoundError:
            logger.warning(f"Cannot send notification - app {app_id} not connected")
            return False
        except Exception as e:
            logger.error(f"Failed to send notification to app {app_id}: {e}")
            return False
    
    async def send_notification_to_session(
        self,
        session_id: SessionID,
        notification_type: str,
        message: str,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send a notification to a specific session.
        
        Args:
            session_id: Target session identifier
            notification_type: Type of notification
            message: Notification message
            additional_data: Optional additional data
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            await self.messaging_api.send_to_session(
                session_id=session_id,
                message_type="notification",
                data={
                    "notification_type": notification_type,
                    "message": message,
                    "additional_data": additional_data or {}
                }
            )
            logger.info(f"Sent notification to session {session_id}: {notification_type}")
            return True
        except ConnectionNotFoundError:
            logger.warning(f"Cannot send notification - session {session_id} not connected")
            return False
        except Exception as e:
            logger.error(f"Failed to send notification to session {session_id}: {e}")
            return False
    
    async def broadcast_notification(
        self,
        notification_type: str,
        message: str,
        additional_data: Optional[Dict[str, Any]] = None,
        exclude_apps: Optional[Set[str]] = None
    ) -> int:
        """
        Broadcast a notification to all connected apps.
        
        Args:
            notification_type: Type of notification
            message: Notification message
            additional_data: Optional additional data
            exclude_apps: Optional set of app IDs to exclude
            
        Returns:
            Number of apps the notification was sent to
        """
        try:
            sent_count = await self.messaging_api.broadcast(
                message_type="notification",
                data={
                    "notification_type": notification_type,
                    "message": message,
                    "additional_data": additional_data or {}
                },
                exclude_apps=exclude_apps
            )
            logger.info(f"Broadcast notification '{notification_type}' to {sent_count} apps")
            return sent_count
        except Exception as e:
            logger.error(f"Failed to broadcast notification: {e}")
            return 0
    
    async def request_from_app(
        self,
        app_id: str,
        request_type: str,
        data: Dict[str, Any],
        timeout: float = 30.0
    ) -> Optional[Dict[str, Any]]:
        """
        Send a request to an app and wait for response.
        
        Args:
            app_id: Target app identifier
            request_type: Type of request
            data: Request data
            timeout: Timeout in seconds
            
        Returns:
            Response data if successful, None otherwise
        """
        try:
            response = await self.messaging_api.send_to_app_and_wait(
                app_id=app_id,
                message_type="server_request",
                data={
                    "request_type": request_type,
                    **data
                },
                timeout=timeout
            )
            logger.info(f"Received response from app {app_id} for request {request_type}")
            return response.data
        except ConnectionNotFoundError:
            logger.warning(f"Cannot send request - app {app_id} not connected")
            return None
        except Exception as e:
            logger.error(f"Failed to get response from app {app_id}: {e}")
            return None
    
    async def request_from_session(
        self,
        session_id: SessionID,
        request_type: str,
        data: Dict[str, Any],
        timeout: float = 30.0
    ) -> Optional[Dict[str, Any]]:
        """
        Send a request to a session and wait for response.
        
        Args:
            session_id: Target session identifier
            request_type: Type of request
            data: Request data
            timeout: Timeout in seconds
            
        Returns:
            Response data if successful, None otherwise
        """
        try:
            response = await self.messaging_api.send_to_session_and_wait(
                session_id=session_id,
                message_type="server_request",
                data={
                    "request_type": request_type,
                    **data
                },
                timeout=timeout
            )
            logger.info(f"Received response from session {session_id} for request {request_type}")
            return response.data
        except ConnectionNotFoundError:
            logger.warning(f"Cannot send request - session {session_id} not connected")
            return None
        except Exception as e:
            logger.error(f"Failed to get response from session {session_id}: {e}")
            return None
    
    # Health and Monitoring
    
    def get_health_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive health summary of all connections.
        
        Returns:
            Dictionary with health information
        """
        health_info = self.connection_registry.get_health_info()
        
        # Add messaging API statistics
        if self.messaging_api:
            pending_requests = self.messaging_api.get_pending_request_count()
            health_info["pending_server_requests"] = pending_requests
        
        # Calculate averages
        if health_info["connections"]:
            total_idle = sum(conn["idle_time_seconds"] for conn in health_info["connections"])
            total_age = sum(conn["connection_age_seconds"] for conn in health_info["connections"])
            health_info["average_idle_time_seconds"] = total_idle / len(health_info["connections"])
            health_info["average_connection_age_seconds"] = total_age / len(health_info["connections"])
        else:
            health_info["average_idle_time_seconds"] = 0
            health_info["average_connection_age_seconds"] = 0
        
        return health_info
    
    def get_stale_connections(self, max_idle_seconds: int = 3600) -> List[Dict[str, Any]]:
        """
        Get list of connections that have been idle for too long.
        
        Args:
            max_idle_seconds: Maximum idle time before considering stale
            
        Returns:
            List of connection info dictionaries for stale connections
        """
        health_info = self.connection_registry.get_health_info()
        stale_connections = []
        
        for conn_info in health_info["connections"]:
            if conn_info["idle_time_seconds"] > max_idle_seconds:
                stale_connections.append(conn_info)
        
        return stale_connections
    
    async def cleanup_stale_connections(self, max_idle_seconds: int = 3600) -> List[str]:
        """
        Clean up connections that have been idle for too long.
        
        Args:
            max_idle_seconds: Maximum idle time before cleanup
            
        Returns:
            List of app_ids that were cleaned up
        """
        cleaned_apps = self.connection_registry.cleanup_stale_connections(max_idle_seconds)
        
        # Send cleanup notifications if any apps were cleaned up
        if cleaned_apps:
            logger.info(f"Cleaned up {len(cleaned_apps)} stale connections: {cleaned_apps}")
            
            # Cancel any pending requests for cleaned up apps
            if self.messaging_api:
                self.messaging_api.cancel_pending_requests("Stale connection cleanup")
        
        return cleaned_apps
    
    async def ping_all_connections(self) -> Dict[str, bool]:
        """
        Send ping to all connected apps to test connectivity.
        
        Returns:
            Dictionary mapping app_id to ping success status
        """
        connected_apps = self.get_connected_apps()
        ping_results = {}
        
        for app_id in connected_apps:
            try:
                response = await self.messaging_api.send_to_app_and_wait(
                    app_id=app_id,
                    message_type="server_ping",
                    data={"timestamp": datetime.now().isoformat()},
                    timeout=10.0
                )
                ping_results[app_id] = True
                logger.debug(f"Ping successful for app {app_id}")
            except Exception as e:
                ping_results[app_id] = False
                logger.warning(f"Ping failed for app {app_id}: {e}")
        
        return ping_results
    
    # Event Callbacks
    
    def register_connection_callback(self, event: str, callback) -> None:
        """Register callback for connection events."""
        if hasattr(self.messaging_api, 'register_connection_callback'):
            self.messaging_api.register_connection_callback(event, callback)
    
    def register_session_callback(self, event: str, callback) -> None:
        """Register callback for session events."""
        if hasattr(self.messaging_api, 'register_session_callback'):
            self.messaging_api.register_session_callback(event, callback)


# Global service instance
_global_service: Optional[ConnectionService] = None


def get_connection_service() -> ConnectionService:
    """
    Get the global connection service instance.
    
    Returns:
        The global ConnectionService instance
    """
    global _global_service
    if _global_service is None:
        _global_service = ConnectionService()
        logger.info("Initialized global connection service")
    return _global_service


def reset_connection_service() -> None:
    """Reset the global connection service (for testing)."""
    global _global_service
    _global_service = None
    logger.info("Reset global connection service")