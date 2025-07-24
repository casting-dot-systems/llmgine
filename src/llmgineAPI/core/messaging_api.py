"""
Messaging API for custom backends to send server-initiated messages.

This module provides a clean, type-safe interface that custom backends can use
to send messages to WebSocket clients and wait for responses using asyncio Futures.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Set, Callable, Awaitable
from dataclasses import dataclass
import asyncio
import uuid
import logging
from datetime import datetime, timedelta

from llmgine.llm import SessionID
from llmgineAPI.models.websocket import WSResponse, WSMessage
from llmgineAPI.websocket.connection_registry import ConnectionRegistry, get_connection_registry

logger = logging.getLogger(__name__)


@dataclass
class MessageResponse:
    """Response from a server-initiated message."""
    message_id: str
    type: str
    data: Dict[str, Any]
    received_at: datetime
    
    @classmethod
    def from_ws_response(cls, response: WSResponse) -> 'MessageResponse':
        """Create MessageResponse from WSResponse."""
        return cls(
            message_id=response.message_id,
            type=response.type,
            data=response.data,
            received_at=datetime.now()
        )


class MessagingError(Exception):
    """Base exception for messaging operations."""
    pass


class ConnectionNotFoundError(MessagingError):
    """Raised when trying to send to a non-existent connection."""
    pass


class MessageTimeoutError(MessagingError):
    """Raised when a message request times out."""
    pass


class BackendMessagingInterface(ABC):
    """
    Abstract interface for backend messaging capabilities.
    
    This interface defines the contract that custom backends can use
    to send server-initiated messages to WebSocket clients.
    """
    
    @abstractmethod
    async def send_to_app(
        self, 
        app_id: str, 
        message_type: str, 
        data: Dict[str, Any]
    ) -> None:
        """
        Send a fire-and-forget message to a specific app.
        
        Args:
            app_id: Target app identifier
            message_type: Type of message to send
            data: Message payload
            
        Raises:
            ConnectionNotFoundError: If app_id not found
        """
        pass
    
    @abstractmethod
    async def send_to_app_and_wait(
        self,
        app_id: str,
        message_type: str,
        data: Dict[str, Any],
        timeout: float = 30.0
    ) -> MessageResponse:
        """
        Send a message to a specific app and wait for response.
        
        Args:
            app_id: Target app identifier
            message_type: Type of message to send
            data: Message payload
            timeout: Maximum time to wait for response in seconds
            
        Returns:
            The response message
            
        Raises:
            ConnectionNotFoundError: If app_id not found
            MessageTimeoutError: If response not received within timeout
        """
        pass
    
    @abstractmethod
    async def send_to_session(
        self,
        session_id: SessionID,
        message_type: str,
        data: Dict[str, Any]
    ) -> None:
        """
        Send a fire-and-forget message to a specific session.
        
        Args:
            session_id: Target session identifier
            message_type: Type of message to send
            data: Message payload
            
        Raises:
            ConnectionNotFoundError: If session not found
        """
        pass
    
    @abstractmethod
    async def send_to_session_and_wait(
        self,
        session_id: SessionID,
        message_type: str,
        data: Dict[str, Any],
        timeout: float = 30.0
    ) -> MessageResponse:
        """
        Send a message to a specific session and wait for response.
        
        Args:
            session_id: Target session identifier
            message_type: Type of message to send
            data: Message payload
            timeout: Maximum time to wait for response in seconds
            
        Returns:
            The response message
            
        Raises:
            ConnectionNotFoundError: If session not found
            MessageTimeoutError: If response not received within timeout
        """
        pass
    
    @abstractmethod
    async def broadcast(
        self,
        message_type: str,
        data: Dict[str, Any],
        exclude_apps: Optional[Set[str]] = None
    ) -> int:
        """
        Broadcast a message to all connected apps.
        
        Args:
            message_type: Type of message to send
            data: Message payload
            exclude_apps: Optional set of app_ids to exclude
            
        Returns:
            Number of apps the message was sent to
        """
        pass
    
    @abstractmethod
    def get_connected_apps(self) -> List[str]:
        """
        Get list of all connected app IDs.
        
        Returns:
            List of connected app identifiers
        """
        pass
    
    @abstractmethod
    def get_app_sessions(self, app_id: str) -> Set[SessionID]:
        """
        Get all session IDs for a specific app.
        
        Args:
            app_id: The app identifier
            
        Returns:
            Set of session IDs for the app
        """
        pass
    
    @abstractmethod
    def is_app_connected(self, app_id: str) -> bool:
        """
        Check if an app is currently connected.
        
        Args:
            app_id: The app identifier to check
            
        Returns:
            True if app is connected, False otherwise
        """
        pass


class ServerMessagingAPI(BackendMessagingInterface):
    """
    Concrete implementation of the messaging API.
    
    This class provides the actual messaging functionality using the
    connection registry and WebSocket manager integration.
    """
    
    def __init__(self, connection_registry: Optional[ConnectionRegistry] = None):
        self.connection_registry = connection_registry or get_connection_registry()
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self._websocket_manager: Optional[Any] = None  # Will be set by WebSocketManager
        
    def set_websocket_manager(self, manager: Any) -> None:
        """Set the WebSocket manager reference (called during initialization)."""
        self._websocket_manager = manager
    
    async def send_to_app(
        self, 
        app_id: str, 
        message_type: str, 
        data: Dict[str, Any]
    ) -> None:
        """Send a fire-and-forget message to a specific app."""
        connection = self.connection_registry.get_connection(app_id)
        if not connection:
            raise ConnectionNotFoundError(f"App {app_id} not connected")
        
        message = WSMessage(
            type=message_type,
            message_id=str(uuid.uuid4()),
            data=data
        )
        
        try:
            await connection.websocket.send_text(message.model_dump_json())
            logger.info(f"Sent message {message_type} to app {app_id}")
        except Exception as e:
            logger.error(f"Failed to send message to app {app_id}: {e}")
            raise MessagingError(f"Failed to send message: {e}")
    
    async def send_to_app_and_wait(
        self,
        app_id: str,
        message_type: str,
        data: Dict[str, Any],
        timeout: float = 30.0
    ) -> MessageResponse:
        """Send a message to a specific app and wait for response."""
        connection = self.connection_registry.get_connection(app_id)
        if not connection:
            raise ConnectionNotFoundError(f"App {app_id} not connected")
        
        message_id = str(uuid.uuid4())
        message = WSMessage(
            type=message_type,
            message_id=message_id,
            data=data
        )
        
        # Create future for response
        future = asyncio.Future()
        self.pending_requests[message_id] = future
        
        try:
            # Send message
            await connection.websocket.send_text(message.model_dump_json())
            logger.info(f"Sent request {message_type} to app {app_id}, waiting for response")
            
            # Wait for response with timeout
            try:
                response = await asyncio.wait_for(future, timeout=timeout)
                return response
            except asyncio.TimeoutError:
                raise MessageTimeoutError(f"Message {message_id} to app {app_id} timed out after {timeout}s")
            
        except Exception as e:
            logger.error(f"Failed to send message to app {app_id}: {e}")
            raise MessagingError(f"Failed to send message: {e}")
        finally:
            # Clean up pending request
            self.pending_requests.pop(message_id, None)
    
    async def send_to_session(
        self,
        session_id: SessionID,
        message_type: str,
        data: Dict[str, Any]
    ) -> None:
        """Send a fire-and-forget message to a specific session."""
        connection = self.connection_registry.get_connection_by_session(session_id)
        if not connection:
            raise ConnectionNotFoundError(f"Session {session_id} not connected")
        
        # Add session_id to data for context
        data_with_session = {**data, "session_id": str(session_id)}
        
        await self.send_to_app(connection.app_id, message_type, data_with_session)
    
    async def send_to_session_and_wait(
        self,
        session_id: SessionID,
        message_type: str,
        data: Dict[str, Any],
        timeout: float = 30.0
    ) -> MessageResponse:
        """Send a message to a specific session and wait for response."""
        connection = self.connection_registry.get_connection_by_session(session_id)
        if not connection:
            raise ConnectionNotFoundError(f"Session {session_id} not connected")
        
        # Add session_id to data for context
        data_with_session = {**data, "session_id": str(session_id)}
        
        return await self.send_to_app_and_wait(
            connection.app_id, message_type, data_with_session, timeout
        )
    
    async def broadcast(
        self,
        message_type: str,
        data: Dict[str, Any],
        exclude_apps: Optional[Set[str]] = None
    ) -> int:
        """Broadcast a message to all connected apps."""
        exclude_apps = exclude_apps or set()
        connections = self.connection_registry.get_all_connections()
        
        sent_count = 0
        for app_id, connection in connections.items():
            if app_id not in exclude_apps:
                try:
                    await self.send_to_app(app_id, message_type, data)
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to broadcast to app {app_id}: {e}")
        
        logger.info(f"Broadcast {message_type} to {sent_count} apps")
        return sent_count
    
    def get_connected_apps(self) -> List[str]:
        """Get list of all connected app IDs."""
        return list(self.connection_registry.get_all_connections().keys())
    
    def get_app_sessions(self, app_id: str) -> Set[SessionID]:
        """Get all session IDs for a specific app."""
        return self.connection_registry.get_app_sessions(app_id)
    
    def is_app_connected(self, app_id: str) -> bool:
        """Check if an app is currently connected."""
        return self.connection_registry.get_connection(app_id) is not None
    
    def resolve_pending_request(self, message_id: str, response: WSResponse) -> bool:
        """
        Resolve a pending request with a response.
        
        This method is called by the WebSocket manager when a response
        is received that matches a pending server-initiated request.
        
        Args:
            message_id: The message ID of the pending request
            response: The response received from the client
            
        Returns:
            True if a pending request was resolved, False otherwise
        """
        future = self.pending_requests.get(message_id)
        if future and not future.done():
            try:
                message_response = MessageResponse.from_ws_response(response)
                future.set_result(message_response)
                logger.debug(f"Resolved pending request {message_id}")
                return True
            except Exception as e:
                future.set_exception(e)
                logger.error(f"Error resolving pending request {message_id}: {e}")
                return True
        return False
    
    def cancel_pending_requests(self, reason: str = "Connection closed") -> None:
        """Cancel all pending requests."""
        for message_id, future in list(self.pending_requests.items()):
            if not future.done():
                future.set_exception(MessagingError(reason))
                logger.debug(f"Cancelled pending request {message_id}: {reason}")
        self.pending_requests.clear()
    
    def get_pending_request_count(self) -> int:
        """Get the number of pending requests."""
        return len([f for f in self.pending_requests.values() if not f.done()])
    
    def cleanup_completed_requests(self) -> int:
        """Clean up completed request futures and return count cleaned."""
        completed = [
            msg_id for msg_id, future in self.pending_requests.items() 
            if future.done()
        ]
        for msg_id in completed:
            self.pending_requests.pop(msg_id, None)
        
        if completed:
            logger.debug(f"Cleaned up {len(completed)} completed request futures")
        return len(completed)


# Connection event callback types
ConnectionEventCallback = Callable[[str], Awaitable[None]]  # app_id -> None
SessionEventCallback = Callable[[str, SessionID], Awaitable[None]]  # app_id, session_id -> None


class MessagingAPIWithEvents(ServerMessagingAPI):
    """
    Extended messaging API with connection event callbacks.
    
    This allows custom backends to register callbacks for connection
    and session lifecycle events.
    """
    
    def __init__(self, connection_registry: Optional[ConnectionRegistry] = None):
        super().__init__(connection_registry)
        self.connection_callbacks: Dict[str, List[ConnectionEventCallback]] = {
            'connect': [],
            'disconnect': []
        }
        self.session_callbacks: Dict[str, List[SessionEventCallback]] = {
            'session_created': [],
            'session_destroyed': []
        }
    
    def register_connection_callback(
        self, 
        event: str, 
        callback: ConnectionEventCallback
    ) -> None:
        """
        Register a callback for connection events.
        
        Args:
            event: 'connect' or 'disconnect'
            callback: Async function to call with app_id
        """
        if event in self.connection_callbacks:
            self.connection_callbacks[event].append(callback)
            logger.info(f"Registered {event} callback")
        else:
            raise ValueError(f"Unknown connection event: {event}")
    
    def register_session_callback(
        self, 
        event: str, 
        callback: SessionEventCallback
    ) -> None:
        """
        Register a callback for session events.
        
        Args:
            event: 'session_created' or 'session_destroyed'
            callback: Async function to call with app_id and session_id
        """
        if event in self.session_callbacks:
            self.session_callbacks[event].append(callback)
            logger.info(f"Registered {event} callback")
        else:
            raise ValueError(f"Unknown session event: {event}")
    
    async def _trigger_connection_event(self, event: str, app_id: str) -> None:
        """Trigger connection event callbacks."""
        for callback in self.connection_callbacks.get(event, []):
            try:
                await callback(app_id)
            except Exception as e:
                logger.error(f"Error in {event} callback for app {app_id}: {e}")
    
    async def _trigger_session_event(
        self, 
        event: str, 
        app_id: str, 
        session_id: SessionID
    ) -> None:
        """Trigger session event callbacks."""
        for callback in self.session_callbacks.get(event, []):
            try:
                await callback(app_id, session_id)
            except Exception as e:
                logger.error(f"Error in {event} callback for session {session_id}: {e}")
    
    # These methods will be called by the WebSocket router
    async def notify_connection_established(self, app_id: str) -> None:
        """Notify that a connection was established."""
        await self._trigger_connection_event('connect', app_id)
    
    async def notify_connection_closed(self, app_id: str) -> None:
        """Notify that a connection was closed."""
        await self._trigger_connection_event('disconnect', app_id)
    
    async def notify_session_created(self, app_id: str, session_id: SessionID) -> None:
        """Notify that a session was created."""
        await self._trigger_session_event('session_created', app_id, session_id)
    
    async def notify_session_destroyed(self, app_id: str, session_id: SessionID) -> None:
        """Notify that a session was destroyed."""
        await self._trigger_session_event('session_destroyed', app_id, session_id)